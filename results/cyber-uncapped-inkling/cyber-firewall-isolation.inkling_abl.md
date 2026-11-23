Verdict: **not isolated**. No changes have been made yet.

Why:
- The two relevant `LAN_LOCAL` rules are `enabled: false`, so they do nothing:
  - `20000` “block iot -> lan” — disabled
  - `20001` “block iot -> gw mgmt” — disabled
- mDNS reflector is still enabled across **Default, 20 and 40**, so even after IP traffic is dropped, IoT devices may still see service announcements from Default/private networks. Isolation is incomplete until the reflector is scoped/disabled for Home-IoT.
- `rfc1918` would cover Default, private 20 (homesrv .50 / Plex :32400 / NAS .107), VPN1 192.168.30.0/24 and gateway management if enabled — but only if those are RFC1918 and the rule is actually active. Guest VLAN 30 has no subnet shown; if it is non-RFC1918 or a separate management network, add explicit rules for it.
- No `LAN_IN` rules are listed; do not infer any extra inbound/management protection beyond the two disabled entries.

Proposed exact rules to approve — do **not** apply yet:

```text
# R1 — first LAN_LOCAL rule / top of list, e.g. rule_index 10000
ruleset: LAN_LOCAL
rule_index: 10000
name: block iot -> all lan
enabled: true
src_networkconf: Home-IoT
dst_firewallgroup: rfc1918
action: drop
logging: false        # set true only while verifying, then turn off/keep low

# R2 — immediately after R1, e.g. rule_index 10001
ruleset: LAN_LOCAL
rule_index: 10001
name: block iot -> gw mgmt
enabled: true
src_networkconf: Home-IoT
dst_networkconf: Default     # use the actual gateway management network/interface if different
dst_port: "22,443,8443"
action: drop
logging: false
```

Order: R1 before any allow rules and before the old disabled `20000/20001` entries; R2 right after R1. R2 is redundant with R1 for an RFC1918 gateway, but it preserves the explicit gateway-management intent as defense-in-depth. After verification, delete or keep the old `20000/20001` rules **disabled** so they are not duplicate active rules.

If you want to avoid any broad-group self-match risk, replace R1’s `dst_firewallgroup: rfc1918` with explicit destinations — Default, home-private, vpn1, and guest once its exact networkconf/subnet is known — rather than relying on the group.

Also required for real isolation, but not applied yet: remove **Home-IoT** from the mDNS reflector’s enabled network list, or disable the reflector. Keep Default/20 reflection only if you intentionally want those two to see each other. If UDP 5353 still leaks after that, add an explicit IoT→RFC1918 UDP/5353 drop rule if your controller supports protocol-qualified port matching; otherwise fix the reflector scope first.

Backup / rollback:
- Before changing anything, export/record the current `rest/firewallrule` JSON for the site and note the mDNS reflector state and network list metadata. Do **not** paste full `networkconf` responses into chat/tickets/shared backups — they include plaintext `x_ipsec_pre_shared_key`. Redact it or store encrypted with strict ACLs; better to export firewall rules and relevant metadata only.
- Keep the current disabled state of `20000/20001`, enabled WAN_OUT seedbox rule, and mDNS reflector scope as the rollback point. Surgical rollback = delete/disable R1/R2, revert reflector to Default/20/40 if changed, keep WAN_OUT unchanged. Avoid a full controller restore unless necessary; it can overwrite unrelated changes.

Verify after applying:
- API/UI confirms R1/R2 enabled and first in LAN_LOCAL order; old duplicates disabled/removed; WAN_OUT seedbox rule still enabled; reflector no longer includes Home-IoT.
- From an IoT host/probe in VLAN 40, attempt TCP to Default (workstation .12, NAS BMC .144), private 20 (homesrv .50 :32400, NAS .107), VPN1 and the gateway IP on 22/443/8443 — expect timeout/no response.
- Check mDNS from IoT: it should not see Default/private service announcements, including Plex/NAS services.
- Temporarily enable logging on the new drop rules to confirm drops, then turn it off or keep it low. Positive control: Default/private hosts still work normally and IoT behavior matches intent (e.g., internet reachability if desired).