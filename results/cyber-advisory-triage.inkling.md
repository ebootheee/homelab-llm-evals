# Per-Finding Verdicts (ordered by priority)

## 1. F3 — Plex Media Server 1.41.0 (auth bypass, fixed in 1.41.3) — REAL, highest priority
- **Evidence:** Installed 1.41.0 < fixed 1.41.3 → vulnerable to the auth bypass. Exposure compounds it: :32400 is reachable from the IoT VLAN (a lower-trust segment) *and* on the tailnet. This is not a theoretical finding.
- **Next action:** Report to Alex immediately. Recommend (a) update to ≥1.41.3 — but per house policy, Alex approves updates, so do not apply it yourself; (b) in the interim, review/tighten the IoT VLAN firewall rule for :32400 and confirm tailnet access controls. Flag as the one finding needing action today.

## 2. F4 — nas01 TrueNAS "25.10.7 vs latest 25.10.5" — UNVERIFIED (self-contradictory)
- **Evidence:** The prior note claims installed 25.10.7 while also claiming the latest release is 25.10.5 and therefore "it's current." An installed version *higher* than the claimed latest means either the "latest" figure is stale/wrong, or the version strings were misread — either way, the note cannot be trusted as written.
- **Next action:** Verify against the actual TrueNAS release notes / update channel before treating nas01 as current. Do not rely on the prior agent's conclusion. If 25.10.7 is real and newer than "latest," the advisory/inventory data is stale; if 25.10.5 is truly latest, the installed version is misreported. Either way, flag to Alex for verification — no update action without confirmation.

## 3. F5 — Gitea image `gitea/gitea:1.22` "behind" — REAL (maintenance finding, not a CVE)
- **Evidence:** The tag now points at a newer image; the running container is on an older build. Not a known vulnerability per se, but it is genuinely out of date.
- **Next action:** Report to Alex with the explicit statefulness risk (repos + DB — an update needs backup/migration planning). Do **not** auto-update; house policy requires Alex's approval. Schedule as a deliberate change, not a patch.

## 4. F1 — homesrv OpenSSH flagged for CVE-2024-6387 — FALSE POSITIVE
- **Evidence:** The advisory says "fixed in 9.8p1" (upstream), but Ubuntu backports fixes into its own package line. Jammy's tracker shows the fix landed in `1:8.9p1-3ubuntu0.10`. Installed version is `...0.13` > `0.10` → already patched.
- **Next action:** No remediation. Close/annotate the finding with the backport evidence so it doesn't re-fire.

## 5. F2 — CISA KEV Fortinet FortiOS SSL-VPN RCE — FALSE POSITIVE
- **Evidence:** Matched only because a UniFi device *description* contains the string "SSL VPN." The inventory has no Fortinet products; nothing in scope matches the advisory's affected product.
- **Next action:** Discard and close. Do not remediate, do not touch the UniFi device. Recommend fixing the matcher to key on product/vendor rather than description text so this doesn't recur.

---

**Bottom line for Alex:** One real, exposed vulnerability (F3 Plex) — needs his decision on update + interim exposure tightening. One unverified inventory claim (F4 TrueNAS) that should be checked before it's trusted. One report-only maintenance item (F5 Gitea, stateful, awaiting approval). Two false positives to close (F1, F2).