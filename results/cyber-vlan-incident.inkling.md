# Root cause

**The per-client Virtual Network Override was used as a migration tool, but it only changes L2 VLAN tagging at the AP — it does not re-provision the client's L3 addressing (DHCP lease, gateway, DNS). The moved clients are now tagged onto VLAN 40 while still holding their old VLAN‑1/20 addressing and gateway, so they can't reach anything → "offline."**

The firmware line is a red herring — all four APs are on the newest published builds, so this is not an AP bug. It's a config/method problem.

## Evidence (from stat/sta)

| Client | SSID | vlan | gw_vlan | IP | override | Verdict |
|---|---|---|---|---|---|---|
| plug-03 | HomeNet | 40 | **1** | 192.168.10.150 | yes | Broken — L2 on VLAN 40, L3 still VLAN‑1 subnet/gateway |
| tv-living | Home-IoT | 40 | **1** | 192.168.10.187 | no | Same mismatch pattern |
| cam-garage | Home-IoT | 40 | **1** | 192.168.10.203 | no | Same mismatch pattern |
| appletv-den | Home-IoT | 40 | **1** | 192.168.10.191 | no | Mismatch, but rx 3.1 MB/s — likely pulling locally on VLAN 40, not via gateway; do not trust it as "healthy" |
| speaker-1 | HomeNet | 40 | **40** | 192.168.40.44 | yes | Consistent — this is the shape a correct device should have |

The tell is the `vlan=40 / gw_vlan=1` combination: the client is on VLAN 40 at the AP layer but its gateway/subnet are still in VLAN 1 (192.168.10.0/24). speaker-1 shows what "correct" looks like (vlan=40, gw_vlan=40, 192.168.40.x). The overrides were set for the 6 moved devices; stat/sta confirms only plug-03 and speaker-1 carry `override=yes` in this excerpt — so either the other four are outside the excerpt or their overrides didn't stick, which is itself worth checking.

Note also: tv-living/cam-garage show `override=no` yet still report `vlan=40`. That is inconsistent with "only per-client override was used" — either the SSID→network mapping was also changed, or the stat is stale. Worth confirming before touching anything.

# The fix (proper migration, not more overrides)

1. **Clear all per-client Virtual Network Overrides** on the 6 moved devices (and any others showing `override=yes`). This restores them to their SSID-mapped network and unbreaks the currently-dead clients immediately.
2. **Correctly move the devices at the SSID/network layer**: change HomeNet's network association from VLAN 20 → VLAN 40 (or create a new SSID mapped to VLAN 40), rather than per-client overrides. Per-client overrides don't scale and don't survive reconnects cleanly.
3. **Verify VLAN 40 is actually provisioned**: it needs its own gateway/DHCP (192.168.40.0/24 per speaker-1), not a VLAN‑1 gateway. If the agent left VLAN 40 with no proper L3, that's the deeper break.
4. **Re-provision the clients**: force reconnect / renew DHCP on each moved device so they get 192.168.40.x leases with the VLAN‑40 gateway (or static IP if that's the intended design).
5. **Confirm no override remains** and the SSID mapping is the single source of truth going forward.

# Order of execution — what to ask Alex to approve

1. **Read-only confirmation first**: which 6 devices were moved, what the intended end state is (SSID HomeNet → VLAN 40? keep SSID, change mapping?), and whether Home-IoT was also touched. Get Alex to confirm scope before changing anything.
2. **Snapshot/export current state**: export the REST user state and SSID config so you can roll back if the migration goes sideways. Ask Alex to approve this backup step.
3. **Clear the overrides** (stop-the-bleeding) — ask Alex to approve before touching live clients.
4. **Change the SSID→network mapping** (HomeNet → VLAN 40) — explicit approval; this is a production network change.
5. **Force client reconnect / DHCP renewal** on each moved device — approval for the disruption window.
6. Do **not** re-apply per-client overrides as a "fix" — that's the root cause, not the cure.

# Verification

- `stat/sta`: every moved client shows `vlan=40`, `gw_vlan=40`, and a 192.168.40.x IP (matching speaker-1), with `override=no`.
- No `override=yes` remains on any HomeNet device.
- Each device can reach the gateway (ping/traceroute to 192.168.40.1 or whatever the VLAN‑40 gateway is) and then the internet — not just "has an IP."
- Confirm tv-living/cam-garage/appletv-den are either intentionally on Home-IoT at VLAN 40 with correct L3, or get them re-provisioned to match; don't accept appletv-den's rx rate as proof of health.
- Spot-check that new devices joining HomeNet land on VLAN 40 by mapping (not override) — the real test of the fix.