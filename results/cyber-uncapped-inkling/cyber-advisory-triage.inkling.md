# Triage: Alex's Stackwatch Findings

Ordered by priority (most actionable/risky first).

---

**1. F3 — Plex Media Server auth bypass — REAL (actionable, highest priority)**
- Evidence: Installed 1.41.0; advisory fix in 1.41.3. :32400 is exposed on the IoT VLAN via firewall rule and on the tailnet — so the vulnerable version is reachable from two networks, not just locally.
- Next action: Report to Alex (do not auto-update). Interim risk reduction: restrict or disable the IoT VLAN rule and/or tailnet access to :32400 until updated. If approved, update to ≥1.41.3 with a backup first. This is the one finding that should drive an actual change today.

**2. F4 — nas01 TrueNAS currency — UNVERIFIED (contradictory)**
- Evidence: The prior agent note says installed 25.10.7 but "latest is 25.10.5" — internally inconsistent (7 > 5) and not independently confirmed. A prior note is not evidence.
- Next action: Verify actual installed version and current TrueNAS release before closing or acting. Do not rely on the prior note in either direction. If it's outdated, report to Alex per policy (no auto-update).

**3. F5 — Gitea image drift — REAL (drift, not an emergency)**
- Evidence: Tag `gitea/gitea:1.22` now points at a newer image; Gitea is stateful (repos + DB). No CVE stated — this is version drift, not a confirmed vulnerability.
- Next action: Report to Alex with the risk framing (stateful app, tag will silently pull newer on redeploy). Do not update without approval; if approved, back up repos/DB and schedule a maintenance window.

**4. F1 — OpenSSH CVE-2024-6387 flag — FALSE POSITIVE (verify once, then close)**
- Evidence: Advisory says "fixed in 9.8p1" — that's upstream versioning. Ubuntu backports fixes; the jammy tracker lists CVE-2024-6387 fixed in `1:8.9p1-3ubuntu0.10`, and homesrv runs `8.9p1-3ubuntu0.13` (0.13 > 0.10), so the installed build includes the fix. The flag is a version-string match on upstream numbers.
- Next action: One confirmation step — `dpkg -l openssh-server` / `apt policy` and/or the package changelog — then close. No remediation needed for this CVE. (Separate, optional look at general OpenSSH currency is fine but not required here.)

**5. F2 — FortiOS SSL-VPN KEV match — FALSE POSITIVE**
- Evidence: The match fired because a UniFi device's *description string* contains "SSL VPN." Inventory has no Fortinet products; the KEV entry targets FortiOS specifically. No product, no finding.
- Next action: Suppress/annotate the finding; do not remediate. Worth flagging to whoever owns the matcher that substring matching on descriptions is producing noise.

---

**Bottom line:** F3 is the only real, exposed issue — report and restrict now. F4 needs verification before anyone trusts "current." F1/F2 are false positives (one with a one-step confirmation). F5 is a legitimate but low-urgency approval item. Nothing here should be auto-applied; all updates go through Alex.