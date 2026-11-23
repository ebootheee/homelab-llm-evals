## What each grant actually permits

**G1 — `src autogroup:member → dst [100.64.0.0/10, fd7a:115c:a1e0::/48], ip ["*"]`**
- Every tailnet member (including the kids' PC and Steam Deck) may reach **any other tailnet device on any port, any protocol** — this is the "device-to-device" rule.
- Critically: the NAS's 4via6 subnet address `fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128` falls **inside** `fd7a:115c:a1e0::/48`. So G1 already permits any member to reach the NAS's pre-boot address on **every port**, not just 2222 — including whatever else is bound to that address once the NAS boots (NFS/SMB/HTTP admin UI/etc.). It also covers the IPv6 tailnet addresses of all devices.
- G1 does **not** cover `192.168.20.50/32` (that's not in either dst range) — which is why G2 exists.

**G2 — `src autogroup:member → dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128], ip ["tcp:2222"]`**
- Every member may reach the NAS subnet address on **TCP 2222 only** — exactly the intended exposure.
- For `192.168.20.50` it's correct and minimal. For the 4via6 form it's **redundant** (G1 already grants all ports there), so it adds nothing for iOS — the iPhone's access comes entirely from G1's broader rule.

## Over-grant and fix

The over-grant is in **G1**: it opens *all* ports on the 4via6 form of the NAS's subnet address (and everything else in the tailnet) to every member, whereas the goal is "only `tcp:2222` on the subnet addresses." The fix is to make the subnet addresses not be covered by G1 with `ip ["*"]`:

- Narrow G1's IPv6 dst to exclude the 4via6 subnet address — but Tailscale ACLs have no negation/exception syntax, so this means enumerating the /48 minus one /128 as a long CIDR list (impractical).
- Cleaner: restructure so device-to-device and the subnet route are separate. E.g. keep G1 for tailnet IPs only (`100.64.0.0/10` + `fd7a:115c:a1e0::/48` — accepting that the 4via6 address is inside it), and **remove the redundant 4via6 entry from G2** so the minimal grant is unambiguous — or better, drop the 4via6 subnet route's coverage from G1 by moving the NAS's 4via6 address into a dedicated rule.

Realistically, the practical fix: keep G1 as-is (it's pre-existing "unchanged intent") and **accept that the 4via6 form of the NAS is open on all ports to members** — or, if "nothing else new opens" is a hard requirement, remove `fd7a:115c:a1e0::/48` from G1's dst (breaking IPv6 device-to-device) or replace G1 with per-service rules. The honest answer: **G2 as written does not achieve the stated goal for iOS** — iOS gets its access via G1's `ip ["*"]`, not via the intended `tcp:2222` grant.

Also note: **every member** (including the kids' PC and Steam Deck) can reach dropbear on 2222 via both G1 and G2 — that's broader than "iPhone only" if Alex wants just him. If he wants iPhone-only, restrict `src` to his device or an autogroup of his devices.

## NFS export comment

The `share` export allowing `100.64.0.0/10` is **not** covered by the proposed grants in any new way — G1 already permits members → tailnet IPs on all ports, so NFS (typically TCP 2049) over tailnet IPs is already open to every member. This is fine *given Alex's stated intent* that `share` is shared with the kids' PC and Steam Deck — but it means:
- The export is **not** limited by G2/G1 beyond what device-to-device already allows; the "nothing else new opens" goal holds only in the sense that nothing *new* opens beyond the existing device-to-device rule.
- If Alex wants `share` restricted to specific devices, the ACL grant must be narrowed (e.g., a dedicated autogroup) — the current policy doesn't do that.

## Safe testing

1. **Preview/dry-run**: use Tailscale's ACL preview/test feature before pushing; confirm G2's IPv4 entry is granted and the 4via6 entry is redundant (or removed).
2. **Test from a non-iOS client first** (WiFi, IPv4): `nc -zv 192.168.20.50 2222` / `ssh` — verify it connects and that a *non*-2222 port (e.g., `nc -zv 192.168.20.50 443`) is refused. This confirms the IPv4 grant is minimal.
3. **Test from iOS over cellular** (the actual goal): connect to the **4via6 address** (`fd7a:115c:a1e0:b1a:0:1:c0a8:1432`) on port 2222 — not the IPv4 literal, which will be rewritten to carrier NAT64 and bypass Tailscale. Verify it reaches dropbear; verify a non-2222 port is refused.
4. **Mind the cryptroot passphrase counter**: each connection consumes one attempt even with empty stdin. Do **not** hammer :2222 — test once or twice, then stop. If you need to re-test after a failure, expect the NAS to lock/need recovery; have the unlock path ready (and consider testing against a throwaway SSH session first).
5. **Verify nothing else opens**: from a member device, scan the 4via6 address on other ports (e.g., 445, 2049, 80) — confirm refused/blocked except 2222. Then check that the IPv4 literal is *not* reachable from iOS over cellular (expected: NAT64 bypass) and only via Tailscale from IPv4-capable clients.
6. **Rollback plan**: keep the previous policy version; if anything misbehaves, revert before the kids or Steam Deck devices are affected.