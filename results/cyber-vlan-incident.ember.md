Saturday 8am - this is not RF, not DHCP server down, and not fixable by a firmware upgrade.

### Root cause

Yesterday's change used per-client **Virtual Network Override** (`rest/user virtual_network_override_*`) to move HomeNet clients from VLAN 20 to VLAN 40.

That feature only works correctly on the 8.x AP train. On the 6.x APs in this house it fails-open to the AP's native/untagged VLAN 1, and breaks VLAN 40 tagging AP-wide.

Evidence from `stat/sta` - pattern is by AP firmware, not by client, SSID, or override flag:

| AP | FW | Client | Expected VLAN 40 | Actual |
|---|---|---|---|---|
| Office U7 Pro Max | 8.1.x | speaker-1, HomeNet, override=yes | `vlan=40 gw_vlan=40 ip=192.168.40.44` | **matches** |
| Kitchen U7NHD | 6.7.57 | plug-03, HomeNet, override=yes | `vlan=40 gw_vlan=40 ip=192.168.40.x` | `gw_vlan=1 ip=192.168.10.150` |
| Basement U7PG2 | 6.8.2 | tv-living, Home-IoT, override=no | `vlan=40 gw_vlan=40 ip=192.168.40.x` | `gw_vlan=1 ip=192.168.10.187` |
| Basement U7PG2 | 6.8.2 | appletv-den, Home-IoT, override=no | `vlan=40 gw_vlan=40 ip=192.168.40.x` | `gw_vlan=1 ip=192.168.10.191` |
| Backyard U7MSH | 6.8.2 | cam-garage, Home-IoT, override=no | `vlan=40 gw_vlan=40 ip=192.168.40.x` | `gw_vlan=1 ip=192.168.10.203` |

Key points:

1. **Only Office works.** It's the only 8.1.x AP, and the only one with `gw_vlan=40` and a 192.168.40.x address - the VLAN 40 subnet.
2. **All 6.x APs fail identically,** whether override=yes (plug-03) or override=no and native Home-IoT (tv-living, cam-garage, appletv-den). This is AP-wide VLAN tagging failure after the controller push, not just the 6 moved clients.
3. **Clients are associated and passing traffic** - e.g. appletv-den `rx_bytes-r=3.1MB/s`, plug-03 present in sta. So WiFi, SSID, and AP up/down are fine. They are landing on VLAN 1 / 192.168.10.0/24, the trusted LAN, instead of isolated VLAN 40 / 192.168.40.0/24.
4. That explains "half offline": IoT services/firewall rules on VLAN 40 can't reach VLAN 1 clients, so they show offline in the IoT platform despite being associated. It's also a security fail-open - IoT devices are on the main LAN.
5. **Upgrade is not a fix.** You noted all four are on the newest firmware published for them. 6.7.57 / 6.8.2 is the latest train for U7NHD/U7PG2/U7MSH, 8.1.x is for U7 Pro Max. The 8.x fix cannot be loaded on the 6.x models.

### Fix

Do not use Virtual Network Override on 6.x APs. Roll it back, restore native SSID VLAN tagging, and achieve VLAN 40 by SSID association to Home-IoT, not by override.

Long term: replace the 6.x APs with 8.x-capable models if you want override, or stay with SSID-based segmentation. File a UniFi ticket with this stat excerpt and firmware list.

### Order - approvals needed from Alex

I would not do this without explicit approval, in this order:

**1. Freeze and snapshot - no approval needed**
Export controller config and the full list of the 6 overridden devices (only 2 are in the excerpt). Confirm DHCP reservations.

**2. Ask Alex to approve rollback of the override method**
Remove `virtual_network_override_*` for all 6 devices via the same REST API. Interim result: they return to HomeNet VLAN 20, their last working state.

**3. Ask Alex to approve sequential AP reprovision**
Force reprovision/restart Kitchen, then Basement, then Backyard - one at a time, ~minutes of WiFi loss per AP. Do NOT touch Office - it's the working control.
Gate: pilot Kitchen first. Do not proceed to the others until native Home-IoT clients on Kitchen return to `gw_vlan=40`.

**4. Ask Alex to approve the SSID migration, or accept VLAN 20 interim**
Once native VLAN 40 is verified working on all 3 APs, move the 6 devices to Home-IoT SSID natively for VLAN 40. This may require touching IoT devices that won't roam SSIDs automatically. If Alex doesn't want that Saturday morning, stop at step 2/3 - native Home-IoT devices will recover, moved devices stay on VLAN 20.

### Verification

Re-run `stat/sta` after each AP:

- No Home-IoT / VLAN 40 client with `gw_vlan=1` or 192.168.10.x on any AP
- All VLAN 40 clients: `vlan=40 gw_vlan=40 ip=192.168.40.x`, `override=no` (or SSID-migrated)
- speaker-1 on Office unchanged as control
- Ping VLAN 40 gateway, ping IoT controller/Home Assistant, DHCP lease present in controller
- IoT app shows tv-living, cam-garage, appletv-den, plug-03 and the other moved devices online
- No IoT clients remaining on VLAN 1

If the Kitchen pilot does not restore `gw_vlan=40` after override removal + reprovision, stop, restore controller backup, and escalate - then check switch trunks as secondary, but current evidence points to the AP firmware feature, not the switch.