## Verdict: NOT isolated. The two IoT rules are disabled.

Current state as retrieved:
- `block iot -> lan` (LAN_LOCAL 20000) and `block iot -> gw mgmt` (LAN_LOCAL 20001) are both `enabled: false` → nothing blocks IoT → house today. Default allow applies.
- The disabled rules are also flawed if simply enabled:
  - `dst_firewallgroup: rfc1918` includes **192.168.0.0/16, which contains Home-IoT itself (192.168.40.0/24)** — the rule as written can self-block IoT→IoT and relies on group membership rather than an explicit list of house networks. It also doesn't explicitly cover guest VLAN 30 (subnet unknown — fetch it; don't guess).
  - `block iot -> gw mgmt` has **no destination** — it matches IoT → any local host on those ports (broader than intended, but harmless). It also doesn't block the gateway on other ports, and blocks nothing else about the gateway.
- **mDNS reflector is enabled across Default, 20 and 40** — firewall rules do not filter multicast. Even with rules enabled, IoT devices will still discover house services via mDNS (e.g., Plex on homesrv .50 / 192.168.20.0/24, :32400). This is a discovery leak you must close separately.
- No LAN_IN rules exist — fine; LAN_IN is WAN→LAN, not relevant to IoT isolation. The WAN_OUT "drop seedbox" rule is unrelated.
- House → IoT direction is currently unrestricted (and would remain so). Decide whether you want two-way or one-way isolation.

## Exact rules to add/replace (LAN_LOCAL, lowest index = highest priority)

Do not use the `rfc1918` group. Build a new group `house-lan` = Default 192.168.10.0/24 + home-private 192.168.20.0/24 + vpn1 192.168.30.0/24 + guest VLAN 30 subnet (fetch via API first).

| # | Index | Name | Match | Action |
|---|-------|------|-------|--------|
| 1 | 20000 | allow iot -> gw dns *(only if IoT needs house DNS — verify; otherwise omit)* | src Home-IoT, dst networkconf = gateway's LAN network (confirm via API, likely Default), port "53" | accept |
| 2 | 20001 | block iot -> house-lan | src Home-IoT, dst firewallgroup `house-lan` | drop, logging: true |
| 3 | 20002 | block iot -> gw mgmt | src Home-IoT, dst networkconf = gateway LAN network, port "22,443,8443" | drop, logging: true *(redundant with #2 for the gateway; keep only for per-rule drop logs)* |
| 4 | 20003 | block house -> iot *(optional, two-way isolation)* | src firewallgroup `house-lan`, dst networkconf Home-IoT | drop, logging: true |

Order: #1 must evaluate before #2. Keep #3/#4 after the drops. Note rule #2 will break IoT name resolution if IoT uses gateway DNS — that's what #1 is for. Also note intra-VLAN IoT→IoT traffic (cameras/TVs in 192.168.40.0/24) may bypass LAN_LOCAL entirely, which is fine and expected.

Separately: **remove Home-IoT from the mDNS reflector set** (Default + 20 only). That's the one change that closes the discovery leak; firewall rules alone don't.

## Back up & roll back

1. Before changing anything, snapshot via API: `rest/firewallrule` (all rulesets) and `rest/networkconf` for Default, 20, 40, vpn1, guest — plus the mDNS reflector settings.
2. **Redact before storing/pasting**: `rest/networkconf` returns `x_ipsec_pre_shared_key` in plaintext. Store the snapshot as a restricted file (0600), never in tickets/chat/logs; treat it as a secret.
3. Rollback: re-apply the snapshot via the API — disable the new rules (or delete them and restore the two disabled originals), restore the reflector set to Default+20+40, then re-run the verification tests below. Since nothing has been changed yet, "rollback" today = leave state as-is.

## Verify afterwards (after changes are applied — not now)

- Confirm via API that rules are `enabled: true` at the expected indexes and reflector no longer includes Home-IoT.
- From an IoT client/test device in VLAN 40: TCP to workstation .12 (Default), homesrv .50 :32400 (20), gateway ports 22/443/8443, a host in vpn1 and guest → expect timeouts/drops.
- mDNS: confirm IoT no longer sees house services (e.g., no Plex discovery via `avahi-browse`/`dns-sd`) after the reflector change.
- Positive controls: IoT→Internet still works; IoT→IoT same-subnet still works; house→IoT behaves as you intended (allowed unless rule #4 added).
- Check firewall logs for drops on the new rules — confirm hits, not silent mismatch.

**Do not apply any of this yet** — all of the above is recommendations only, per your instruction.