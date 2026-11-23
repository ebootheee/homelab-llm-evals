**Verdict: No — the IoT VLAN is not isolated.**  
The two LAN_LOCAL drop rules that would block IoT traffic are both **disabled**, and there are **no LAN_IN rules**. UniFi legacy inter-VLAN routing is therefore allowed by default, so IoT devices can reach the rest of the house. The enabled `WAN_OUT` “drop seedbox” rule is unrelated to inter-VLAN isolation. Additionally, the **mDNS reflector is enabled across Default, VLAN 20, and VLAN 40**, which can leak/reflect mDNS discovery across VLAN boundaries even if firewall rules are added. Firewall rules alone may not fully neutralize mDNS reflector behavior; disable mDNS reflection for VLAN 40 (or block UDP 5353/224.0.0.251 as a fallback) before considering the IoT VLAN isolated.

## Exact rules to add

Do not change anything yet. Add the following as **new enabled rules**; do not reuse the disabled rule indices. Use unused indices after the existing disabled rules so the disabled rules remain inert and the new rules are evaluated before the default allow.

### 1) Block IoT → all RFC1918 / local networks
- **Ruleset:** `LAN_LOCAL`
- **Rule index:** `20002`
- **Order:** after existing disabled `20000`/`20001`, before default allow
- **Name:** `block iot -> lan enabled`
- **Enabled:** `true`
- **Match:** `src_networkconf: Home-IoT` → `dst_firewallgroup: rfc1918`
- **Action:** `drop`
- **Logging:** `true` (recommended during verification)

This blocks IoT-initiated routed traffic to Default, home-private, vpn1, guest, and any other RFC1918 destination. Intra-VLAN switched traffic is not routed through the gateway, so this should not block IoT-to-IoT traffic.

### 2) Block non-IoT RFC1918 → IoT
- **Ruleset:** `LAN_LOCAL`
- **Rule index:** `20003`
- **Order:** after `20002`, before default allow
- **Name:** `block lan -> iot enabled`
- **Enabled:** `true`
- **Match:** `src_firewallgroup: rfc1918` → `dst_networkconf: Home-IoT`
- **Action:** `drop`
- **Logging:** `true` (recommended during verification)

This blocks the rest of the house from initiating routed traffic into the IoT VLAN. Note: because `rfc1918` includes the IoT subnet itself, this is broad; intra-VLAN traffic is normally switched and not affected, but verify that IoT-to-IoT traffic still works as expected.

### 3) Optional / recommended if you want gateway-management isolation explicitly
If gateway management is reachable via a routed local IP and you want an explicit port-level block, add a **LAN_IN** rule rather than relying on the disabled `LAN_LOCAL` rule 20001. The existing `20001` is disabled and appears to be in the wrong ruleset for gateway-management traffic.

- **Ruleset:** `LAN_IN`
- **Rule index:** `20002` (or next free index in `LAN_IN`)
- **Order:** before default allow
- **Name:** `block iot -> gw mgmt enabled`
- **Enabled:** `true`
- **Match:** `src_networkconf: Home-IoT`, `dst_port: 22,443,8443`, protocol TCP (or as required)
- **Action:** `drop`
- **Logging:** `true`

However, if rule 20002 above already blocks IoT → RFC1918 and gateway management IPs are RFC1918 and subject to LAN_LOCAL, this may be redundant. Verify the actual gateway-management IP and ruleset behavior first.

### mDNS reflector prerequisite
Because mDNS reflector is enabled across VLAN 40, add/disable this as a required companion change:
- Disable mDNS reflector for VLAN 40 / Home-IoT, or
- If you cannot disable it, add a fallback block for mDNS:
  - **Ruleset:** `LAN_LOCAL`
  - **Rule index:** next free, e.g. `20004`
  - **Match:** `src_networkconf: Home-IoT`, `dst_port: 5353`, protocol UDP, destination multicast `224.0.0.251/32` if supported by the API/legacy rule model
  - **Action:** `drop`
  - Also add the reverse for other networks → IoT if needed.

Do not rely solely on the mDNS firewall rule; the reflector setting should be removed for VLAN 40.

## Backup and rollback

Before adding anything:

1. Export the current firewall configuration:
   - `GET rest/firewallrule` and save raw JSON.
   - `GET rest/firewallgroup` and save raw JSON.
   - `GET rest/networkconf` and save raw JSON, but **redact/secure the plaintext `x_ipsec_pre_shared_key` values**. Do not store unredacted copies in shared tickets/logs.
2. Export the mDNS/multicast settings for VLAN 40 / all networks.
3. Record the exact existing rule indices and enabled/disabled states.
4. Take a configuration backup if your controller supports it, or snapshot the API responses.
5. Make changes via API/UI only after recording the current state.

Rollback plan:
- Delete the newly added rules by their exact `rule_index` and `ruleset` (e.g., `LAN_LOCAL` 20002, 20003, and any optional LAN_IN/mDNS rules).
- Restore the mDNS reflector setting to its prior state if you changed it.
- Do not enable or modify the existing disabled rules 20000/20001 during rollback unless that was part of the intended change.
- If needed, restore the saved firewallrule JSON exactly, but verify that API writes do not reintroduce stale plaintext secrets from networkconf backups.

## Verification after adding rules

Do not trust the UI alone. Verify with logs and traffic tests:

1. **Rule state check**
   - Confirm new rules are `enabled: true` and in the intended ruleset/index order.
   - Confirm the old disabled rules remain disabled.

2. **Traffic tests from IoT VLAN**
   - From an IoT device, ping/curl/ssh to:
     - Default gateway/hosts: `192.168.10.12`, `192.168.10.144`
     - home-private: `192.168.20.50` (Plex port 32400), `192.168.20.107`
     - vpn1: `192.168.30.x`
     - guest VLAN 30 subnet
   - Expect drops and no responses.
   - Test IoT-to-IoT intra-VLAN traffic still works.
   - Test IoT internet access still works if that is intended.

3. **Reverse-direction tests**
   - From Default/private/guest/vpn1, try to reach IoT hosts/services.
   - Expect drops.

4. **Gateway management test**
   - From IoT, try SSH/HTTPS/8443 to the gateway management IP.
   - Expect drop if you added the LAN_IN rule or if rule 20002 covers it.

5. **mDNS verification**
   - From IoT, browse/query mDNS for devices on Default/private VLANs.
   - From Default/private, query for IoT devices.
   - Expect no cross-VLAN discovery if mDNS reflector for VLAN 40 is disabled/blocked.

6. **Firewall logs**
   - Check UniFi firewall logs for hits on the new rules.
   - Look for `block iot -> lan enabled`, `block lan -> iot enabled`, and any mDNS/gateway-management rule names.
   - If traffic still passes without log hits, the traffic may be bypassing the ruleset (e.g., mDNS reflector, intra-VLAN switching, or wrong ruleset such as LAN_IN vs LAN_LOCAL).

7. **Confirm no unintended breakage**
   - Verify IoT devices still get DHCP/DNS/internet as required.
   - If DNS or gateway services fail, adjust with narrow allow rules before the drop rules, e.g., allow IoT → gateway DNS/Internet, then drop the rest.

Bottom line: the IoT VLAN is currently not isolated. Add enabled LAN_LOCAL drop rules for IoT → RFC1918 and RFC1918 → IoT, and disable mDNS reflector for VLAN 40. Do not enable the existing disabled rules unless you intentionally want to replace the new rules; keep the changes reversible by recording exact indices and states first.