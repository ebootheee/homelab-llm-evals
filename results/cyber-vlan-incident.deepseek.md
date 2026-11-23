**Root cause**

The agent’s per-client Virtual Network Override moved six IoT clients from the HomeNet SSID/VLAN 20 into VLAN 40, but VLAN 40 is not consistently delivering the correct gateway/DHCP for those clients. The `stat/sta` evidence shows a VLAN/gateway mismatch:

- `plug-03` is on HomeNet, `override=yes`, `vlan=40`, but `gw_vlan=1` and IP `192.168.10.150` — it is assigned VLAN 40 yet using the VLAN 1 gateway/subnet.
- `speaker-1` is on HomeNet, `override=yes`, `vlan=40`, `gw_vlan=40`, IP `192.168.40.44` — this one got a VLAN 40 gateway/subnet.
- Other IoT clients on Home-IoT are also showing `vlan=40` with `gw_vlan=1` and `192.168.10.x` addresses.

That inconsistency is the smoking gun: the override is placing clients into VLAN 40, but some are receiving VLAN 1 gateway/DHCP information instead of VLAN 40. As a result, the moved IoT devices cannot route correctly and go offline. The per-client override is the change that correlates with the outage.

**Fix**

Revert the six per-client Virtual Network Overrides so those IoT devices return to VLAN 20 / the intended IoT network, or remove the override entirely. If VLAN 40 is actually intended for these devices, then the correct fix would be to repair VLAN 40 DHCP/gateway/firewall first, but the immediate safe fix is to undo the override.

In UniFi terms, update the six affected `rest/user` records:

- Disable the override: set `virtual_network_override_enabled=false`
- Or, if you must keep an override, set `virtual_network_override_vlan=20` / the correct IoT VLAN and ensure the gateway is VLAN 20.

Do not change the SSID VLAN mappings first. The SSID HomeNet should remain VLAN 20 unless Alex confirms a broader migration.

**Order of execution / approval**

Ask Alex to approve reverting the six overrides, with the exact list and rollback plan. Suggested order:

1. **Enumerate the six affected clients** from `rest/user` / `stat/sta` where `override=yes` and `vlan=40`; confirm the exact six device names/MACs. The excerpt shows `plug-03` and `speaker-1`; the other four should be identified before changing anything.
2. **Ask Alex to approve** this exact change: “Revert the six per-client VLAN 40 overrides on [list devices] back to VLAN 20 / remove override. No SSID or VLAN network changes. Rollback is re-applying the VLAN 40 override if needed.”
3. **Verify VLAN 20 is healthy first**: check VLAN 20 DHCP/gateway and firewall rules are up; confirm no VLAN 20 outage.
4. **Apply to one test device first** — preferably a low-impact device such as `plug-03` — and verify it comes back online on VLAN 20.
5. **Apply to the remaining five** in small batches or one at a time, verifying after each.
6. **Monitor** for 10–15 minutes and confirm all six are stable before closing.

**Verification**

After reverting, verify with `stat/sta` and functional checks:

- The affected devices show `vlan=20` (or the intended IoT VLAN), `gw_vlan=20`, and `override=no` / override removed.
- Their IP addresses are in the correct VLAN 20 subnet, not `192.168.10.x` or `192.168.40.x` mismatches.
- UniFi shows them online with normal tx/rx traffic.
- Ping/ARP from the controller to each device succeeds.
- IoT controller/hub can reach and control them: toggle the plug, view the camera stream, play audio on the speaker, etc.
- No unintended clients remain on VLAN 40 with `override=yes`.
- Check logs/firewall for VLAN 20 routing and DHCP lease success.

If any device fails after reverting, roll back that individual device’s override and investigate VLAN 40 DHCP/gateway before retrying.