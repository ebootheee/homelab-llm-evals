**Summary: 1 real high-priority finding, 1 unverified/contradictory, 1 report-only, 2 false positives. No changes applied — Alex approves updates.**

Ordered by priority:

---

**1. F3 — Plex Media Server auth bypass (homesrv) — REAL, highest priority**
- Evidence: Advisory says the auth bypass is fixed in 1.41.3; installed is 1.41.0 → affected. Exposure is concrete: :32400 is reachable from the IoT VLAN (lower trust) via firewall rule, plus the tailnet.
- Next action: Report to Alex now. Propose upgrade to ≥1.41.3 (check for newer stable first). Interim mitigation worth proposing: restrict :32400 to admin/tailnet-only or drop the IoT VLAN rule until patched. Verify post-update.

**2. F4 — TrueNAS currency note on nas01 — UNVERIFIED (self-contradictory)**
- Evidence: The note says installed 25.10.7, latest 25.10.5, and concludes "current." That is internally inconsistent: installed version exceeds the claimed latest. Either the "latest" figure is stale or the installed version is misread/misreported — either way, "current" is unproven. This is a data host, so the claim matters.
- Next action: Verify against the vendor release feed / TrueNAS update channel and confirm the actual installed build. If behind, report to Alex with the update decision (do not auto-update). Do not treat this as current until checked.

**3. F5 — Gitea image behind (gitea/gitea:1.22) — REAL (currency), report-only per policy**
- Evidence: Factual — the tag now points at a newer image. Gitea is stateful (repos + DB), so the update carries migration risk.
- Next action: Report to Alex with the facts and state explicitly that it's not urgent but needs his decision. Do NOT auto-update. If approved: back up repos + DB, plan the migration, verify before/after.

**4. F1 — OpenSSH CVE-2024-6387 (homesrv) — FALSE POSITIVE**
- Evidence: The "fixed in 9.8p1" figure is upstream. Ubuntu jammy backported the fix to 1:8.9p1-3ubuntu0.10, and the installed build is 3ubuntu0.13 — higher than 0.10, so it already includes the fix. The flag came from a naive upstream version comparison, which doesn't apply to Ubuntu's backported branch.
- Next action: Close/dismiss with this evidence. Optionally confirm the installed package via dpkg on homesrv to close cleanly. No change needed.

**5. F2 — Fortinet FortiOS SSL-VPN RCE (CISA KEV) — FALSE POSITIVE**
- Evidence: The match is a substring hit — "SSL VPN" appears in a UniFi device description. The inventory has no Fortinet products, so there is no FortiOS asset to be vulnerable.
- Next action: Dismiss the KEV finding and confirm the inventory (no Fortinet). No patching.

---

**Bottom line:** Act on F3 (real, network-reachable from IoT VLAN) and verify F4 (the "current" claim doesn't hold up as written). Surface F5 to Alex for a decision. F1 and F2 are noise — close them with evidence so they don't resurface. Nothing was updated or changed; all updates await Alex's approval.