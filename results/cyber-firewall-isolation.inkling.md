## Verdict: NOT isolated — do not trust the current state

The two blocking rules are **disabled** (`enabled: false`), so nothing currently stops VLAN 40 from reaching the rest of the LAN. On top of that, even if you just flip them on, both rules are wrong in ways that would either break IoT or miss the point:

1. **"block iot -> lan" (20000)** — dst is `rfc1918` = 10/8 + 172.16/12 + 192.168/16. That group **contains Home-IoT's own subnet** (192.168.40.0/24 ⊂ 192.168.0.0/16). Enabling it as-is would drop intra-IoT traffic too (TV↔speakers, camera streams among themselves). It also doesn't scope to anything you actually want blocked.
2. **"block iot -> gw mgmt" (20001)** — `dst_port: 22,443,8443` with **no destination restriction** means it matches IoT→*anywhere* on those ports (NAS web UI, homesrv's services, etc.), not just the gateway. Over-broad and still disabled.
3. **mDNS reflector enabled across Default, 20, and 40** — this is a separate leak channel that firewall rules don't touch. Reflected mDNS will advertise LAN/private service discovery to IoT clients even with drop rules in place. This must be fixed at the reflector level, not with firewall rules.
4. No `LAN_IN` rules exist — fine if you intend default-allow inbound from local networks, but confirm that's the desired posture for this gateway.

## Exact rules to add/fix (proposed, not applied)

First: create a firewall group **`lan-not-iot`** containing only: Default 192.168.10.0/24, home-private 192.168.20.0/24, vpn1 192.168.30.0/24, and guest VLAN 30's subnet (**unknown — must fetch before finalizing**; do not use `rfc1918` as a substitute).

**Rule A — replace the disabled 20000:**
```json
{
  "ruleset": "LAN_LOCAL",
  "rule_index": 20000,
  "name": "block iot -> lan",
  "enabled": true,
  "src_networkconf": "Home-IoT",
  "dst_firewallgroup": "lan-not-iot",
  "action": "drop",
  "logging": true
}
```

**Rule B — replace the disabled 20001:**
```json
{
  "ruleset": "LAN_LOCAL",
  "rule_index": 20001,
  "name": "block iot -> gw mgmt",
  "enabled": true,
  "src_networkconf": "Home-IoT",
  "dst_networkconf": "Default",
  "dst_port": "22,443,8443",
  "action": "drop",
  "logging": true
}
```
(Better still: scope `dst` to the gateway's actual management IP rather than the whole Default subnet if you want to allow IoT→other Default hosts — but given the audit goal, blocking the whole Default subnet is defensible.)

Ordering: keep these at indices 20000/20001 — they're already the lowest indices in `LAN_LOCAL`, and first-match evaluation means any future allow rules must get higher indices or be scoped to IoT's own subnet. No other LAN_LOCAL rules exist, so ordering is trivial today; don't let anyone append allows below these.

**Also required (not a firewall rule):** remove Home-IoT (VLAN 40) from the mDNS reflector network set — or disable reflection involving it entirely. Note this may break IoT device discovery between TVs/speakers if they rely on reflected mDNS; verify whether intra-IoT discovery needs to stay.

## Backup & rollback

- **Before touching anything:** export `rest/firewallrule` (full ruleset JSON), `rest/networkconf` for all networks, and the reflector configuration via the API; take a full config backup in UniFi OS as well. Store offline, access-restricted.
- ⚠️ The API note is important: `rest/networkconf` responses include `x_ipsec_pre_shared_key` **in plaintext**. Treat every export containing that field as a secret — don't paste it into tickets, chat, or version control; rotate the PSK if it's ever been exposed in a shared channel.
- Record the exact pre-change state (both disabled rules' JSON, reflector config, network list) before editing.
- **Rollback:** revert to the exported ruleset JSON (re-disable the new/fixed rules, restore the original disabled ones) and restore the reflector setting; or restore the full backup taken pre-change. Keep changes reversible: disable-first, test, then delete — don't delete anything on day one.

## Verification afterwards

- Confirm both rules show `enabled: true` and hit counters/logs increment (logging is on) after generating test traffic.
- From a test host on VLAN 40: attempt TCP connections to 192.168.10.12 (workstation, :22/:443), 192.168.10.144 (NAS BMC), 192.168.20.50 (homesrv, :32400 — expect blocked), and gateway management ports on Default. All should fail/timeout.
- Verify intra-IoT traffic still works (TVs/speakers discovery, camera streams among themselves).
- Verify mDNS from an IoT client no longer shows LAN/private service advertisements (e.g. `dns-sd -B _services._dns-sd._udp` / `avahi-browse`).
- Confirm internet access still works from VLAN 40 if that's intended — outbound appears default-allowed (only the seedbox drop exists in WAN_OUT), so test explicitly rather than assume.

## Data gaps to close before applying

- Guest VLAN 30 subnet is not in the output — fetch it; Rule A's group can't be finalized without it.
- Gateway management IP/interface isn't given — confirm whether Rule B should target the Default subnet or just the gateway's IP.
- Whether IoT devices need internet access is unstated — assumed default-allow, but verify after the change.

Nothing has been changed yet; this is a plan only.