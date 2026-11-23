Only 1 of these is urgent. Ordered by priority:

### 1. F3 - Plex on homesrv - REAL - act now
**Evidence:** Installed `1.41.0` < fixed `1.41.3` for auth bypass. And `:32400` is reachable from the IoT VLAN by firewall rule, and on the tailnet - i.e. untrusted / broad networks, not just your LAN.

**Do:**
1. Upgrade Plex Media Server to `>=1.41.3` ASAP.
2. Remove the IoT VLAN -> 32400 rule. Restrict tailnet exposure to trusted devices only - if you can't patch today, block IoT/tailnet access as a stopgap.
3. Check Plex logs for unauthenticated / unexpected access before the patch.

### 2. F4 - choden as TrueNAS version - UNVERIFIED
**Evidence:** Prior note says `25.10.7` installed, `latest is 25.10.5, so it's current`. That contradicts itself - installed can't be newer than latest under normal numbering. One/both numbers are wrong, so the "current" conclusion doesn't follow.

**Do:**
- Don't trust the prior agent note, and don't downgrade to 25.10.5.
- Verify live, read-only: TrueNAS UI > System, or CLI version/channel, and check the official latest for that release train.
- Re-triage only after you have a verified version. No patch/downgrade action until then.

### 3. F5 - gitea/gitea:1.22 - REAL, but DEFERRED - report only
**Evidence:** Tag now points at a newer image/digest than what's deployed, so it is behind. No CVE given. Gitea is stateful - repos + DB.

**Do:**
- Per house policy: **do NOT auto-update.** Report to you, Alex, for approval.
- Next step is a proposal from me: current vs new digest/changelog, DB backup/snapshot plan, and a maintenance window. Deploy only after you approve.

### 4. F1 - homesrv OpenSSH CVE-2024-6387 - FALSE POSITIVE
**Evidence:** Flagged as `8.9p1 Ubuntu-3ubuntu0.13`, "fixed in 9.8p1" upstream. But Ubuntu backported the fix: jammy fixed in `1:8.9p1-3ubuntu0.10`. Installed `.13` > `.10`, so already patched.

**Do:** No upgrade - do not chase upstream 9.8p1 on Ubuntu. Mark suppressed in stackwatch and fix its logic to check the Ubuntu revision, not just upstream version.

### 5. F2 - Fortinet FortiOS SSL-VPN KEV - NOT APPLICABLE
**Evidence:** Inventory has no Fortinet products at all. Match was a substring: a UniFi device description contains "SSL VPN".

**Do:** Close as not applicable. No UniFi patch for a FortiOS CVE. Fix stackwatch to match on product, not free-text description.

**TL;DR:** Patch + lock down Plex now. Verify choden as live. Gitea: wait for your approval. OpenSSH and Fortinet: ignore.