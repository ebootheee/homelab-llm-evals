## Verdict: NOT isolated — do not trust the current state

The IoT VLAN (40 / 192.168.40.0/24) is **not** isolated from the rest of the house right now:

- Both LAN_LOCAL rules are **`enabled: false`** — "block iot -> lan" and "block iot -> gw mgmt" are inert.
- There are **no LAN_IN rules** (not directly relevant to IoT→LAN, but confirms the firewall is essentially unconfigured for this purpose).
- The only enabled rule is WAN_OUT "drop seedbox", which only affects outbound traffic to the seedbox — irrelevant to local isolation.
- **mDNS reflector is enabled across Default, 20 and 40**, so IoT devices are discoverable/resolvable across those networks by design. Even with firewall rules in place, reflection defeats the "invisible" part of segmentation. This must be addressed separately (not applied yet).

So: local reachability from VLAN 40 to Default (workstation .12, NAS BMC .144, gateway) and to home-private (homesrv .50 / Plex :32400, NAS .107) is currently **open**.

## Exact rules to add/enable (not applied yet)

Important flaw in the existing disabled rule: `dst_firewallgroup: rfc1918` matches **192.168.0.0/16**, which includes the IoT subnet itself (192.168.40.0/24). Naively enabling it risks blocking IoT→IoT traffic (cameras/speakers on the same VLAN). Don't just flip the switch — replace it with explicit rules:

```
ruleset: LAN_LOCAL
index:   19999
name:    "allow iot -> iot"
src:     networkconf = Home-IoT (192.168.40.0/24)
dst:     networkconf = Home-IoT
action:  allow                      # self-VLAN exception, must precede the drop
```

```
ruleset: LAN_LOCAL
index:   20000
name:    "block iot -> default"
src:     networkconf = Home-IoT
dst:     networkconf = Default (192.168.10.0/24)   # workstation .12, NAS BMC .144, gateway IP
action:  drop
logging: true                        # mirror the "drop seedbox" pattern
```

```
ruleset: LAN_LOCAL
index:   20001
name:    "block iot -> home-private"
src:     networkconf = Home-IoT
dst:     networkconf = home-private (VLAN 20, 192.168.20.0/24)   # homesrv .50 :32400, NAS .107
action:  drop
logging: true
```

```
ruleset: LAN_LOCAL
index:   20002
name:    "block iot -> vpn1"
src:     networkconf = Home-IoT
dst:     networkconf = vpn1 (192.168.30.0/24)
action:  drop
```

```
ruleset: LAN_LOCAL
index:   20003
name:    "block iot -> guest"
src:     networkconf = Home-IoT
dst:     networkconf = guest (VLAN 30 — subnet not in the data; fill in before applying)
action:  drop
```

Notes on ordering/semantics:
- Rules are evaluated by `rule_index` ascending, first match wins — the self-allow at 19999 must precede the drops. Keep indices non-overlapping with existing entries (20000/20001 are taken by the disabled rules; either delete those two or repurpose the index space after backing them up).
- Drop rule 20001 replaces "block iot -> gw mgmt" entirely: blocking IoT→Default at network level covers ports 22/443/8443 **and** everything else (80, 8080, controller UI, etc.), which is strictly stronger than the port-only rule. If you want to keep a specific management-port rule for audit clarity, add it as index 20001a but the network-level drop makes it redundant.
- Do **not** rely on `rfc1918` as the dst — it's too broad (self-match) and too vague (doesn't document intent). Explicit per-network rules are the correct form here.
- Leave WAN_OUT alone except to confirm no rule accidentally permits IoT→RFC1918 via a WAN path; the seedbox drop is unaffected.

**Required additional change (separate from firewall rules, also not applied yet):** remove Home-IoT (VLAN 40) from the mDNS reflector scope — restrict reflection to Default (and/or 20 if you genuinely want cross-network discovery there; do not reflect 40). This is a settings change in the UniFi controller, not a firewall rule.

## Backup and rollback

Backup (before any change):
1. `GET rest/firewallrule` — full dump to a timestamped file with restrictive permissions (0600, root/admin-only). Record current enabled states of both disabled rules.
2. `GET rest/networkconf` — **do not store or paste this unredacted**: per the API note it returns `x_ipsec_pre_shared_key` in plaintext. Redact that field before saving, sharing, or including in tickets; treat any such output as secret material and keep it out of logs/chat.
3. Take a controller config backup via the UniFi UI (Settings → Backup) so you have a full-state restore point independent of the API.

Rollback:
1. Disable/delete the four new LAN_LOCAL rules (or re-disable the originals), restore the mDNS reflector scope to its prior value.
2. Verify with `GET rest/firewallrule` that the ruleset matches the backup exactly (diff against the pre-change dump), and confirm via API that VLAN 40 is no longer in the reflector scope.

## Verification afterwards (post-change, read-only tests)

From an IoT device or a VLAN 40 test client:
- `nc -zv` / TCP connect to workstation .12, NAS BMC .144, gateway IP on 22/80/443/8443 → expect timeout/refused.
- Connect to homesrv .50 on :32400 and NAS .107 → expect refused/timeout.
- Connect to vpn1 and guest subnets → expect refused/timeout.
- Confirm IoT→internet still works (DNS resolution + an external HTTPS fetch) — the drops must not break outbound.
- Confirm mDNS is no longer reflected across Default/20/40 (from a Default device, confirm IoT devices are not discovered; from IoT, confirm LAN services don't appear via reflection).

From the API:
- `GET rest/firewallrule` — confirm all four drop rules show `enabled: true` with correct src/dst and indices, self-allow at 19999 first.
- Check firewall log entries (logging enabled on the drops) for actual hits from a known IoT client.

One caveat to flag honestly: exact rule behavior (e.g., whether intra-VLAN traffic traverses LAN_LOCAL at all, and the precise match semantics of `networkconf` vs `firewallgroup` in this controller version) should be confirmed against the live API before applying — I've described the correct intended configuration, not a verified-against-live-device result.