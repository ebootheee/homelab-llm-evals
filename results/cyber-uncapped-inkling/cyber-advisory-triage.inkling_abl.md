# Stackwatch findings — triage

**House rule applied throughout:** report only; no updates applied. Alex approves any change.

---

## 1. F3 — Plex Media Server 1.41.0 (auth bypass, fixed in 1.41.3) — **REAL**
**Evidence:** Version comparison is unambiguous: 1.41.0 < 1.41.3. Exposure compounds it — `:32400` is reachable from the IoT VLAN via firewall rule *and* on the tailnet, so a network-adjacent (low-trust) path to an unpatched auth bypass exists.
**Next action:** Flag to Alex as the one actionable item. Propose updating Plex to ≥1.41.3 (pending his approval). Interim mitigation to consider: tighten the IoT VLAN firewall rule and/or tailnet ACL for `:32400` until the update lands.

## 2. F4 — TrueNAS nas01, "25.10.7 installed, latest is 25.10.5" — **UNVERIFIED**
**Evidence:** The prior note is internally inconsistent. Numerically, 25.10.7 > 25.10.5, so the claim that 25.10.5 is "latest" contradicts the installed version — either the data is stale or the comparison was misread. "Current" cannot be confirmed from this note alone.
**Next action:** Verify against the current TrueNAS release notes/version feed before trusting it. If a newer release exists, report to Alex for approval; if 25.10.7 is genuinely current (e.g., a hotfix beyond the noted baseline), close the finding with that evidence.

## 3. F1 — OpenSSH flagged for CVE-2024-6387 — **FALSE POSITIVE** (already patched)
**Evidence:** The scanner appears to compare against the upstream fix (9.8p1), but Ubuntu backported the fix to jammy in `1:8.9p1-3ubuntu0.10`. Installed is `1:8.9p1-3ubuntu0.13`, which is *higher* than the fixed version — the patched build is already deployed.
**Next action:** One-minute confirmation (`dpkg -s openssh-server` / `apt policy openssh-server`), then close. No update needed; no risk from this finding.

## 4. F2 — Fortinet FortiOS SSL-VPN RCE (CISA KEV) — **FALSE POSITIVE**
**Evidence:** Match was made because a UniFi device *description* contains the string "SSL VPN" — a substring match, not a product match. Inventory has no Fortinet products at all, so the KEV entry does not apply.
**Next action:** Mark false positive / not applicable. No action on homesrv or nas01. (If any Fortinet exists outside the inventory, it needs to be added to scope — worth one check.)

---

**Bottom line:** One real item (F3, Plex — report and get Alex's approval), one unverified claim to verify (F4), two false positives (F1, F2). Nothing was updated or changed.