## What each grant actually permits

**G1** — `src autogroup:member → dst [100.64.0.0/10, fd7a:115c:a1e0::/48], ip ["*"]`
- Every tailnet member (including the kids' PC and Steam Deck) can reach **every tailnet address** in both ranges on **all ports** — device-to-device, yes, but that's also every node's services, not just "device-to-device" in any meaningful sense.
- Critical detail: `fd7a:115c:a1e0::/48` is the tailnet IPv6 range and **contains the NAS's advertised 4via6 subnet route** (`fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128`). So G1 already permits any member to reach dropbear on `:2222` via the IPv6 path — plus everything else listening on that route, all ports. The comment "unchanged intent" doesn't change what it grants.

**G2** — `src autogroup:member → dst [192.168.20.50/32, fd7a:...16f2/128], ip ["tcp:2222"]`
- Every member → the two subnet-route addresses, TCP 2222 only.
- It is **redundant** for the actual goal: the IPv6 form is already covered by G1 (all ports), so G2 adds nothing new there. The only thing it genuinely opens is the **IPv4 literal path** — which iOS on IPv6-only 5G rewrites to carrier NAT64 and bypasses Tailscale entirely. So for the cellular case, G2 is effectively dead weight that also broadens exposure (see below).

## Over-grants and fixes

1. **G2's `src autogroup:member`** — this opens pre-boot SSH to *every* member, not just your iPhone. Fix: restrict the source, e.g. assign the iPhone a tag (`tag:iphone`) and use `src: ["tag:iphone"]` (or an equivalent device-scoped identifier). That's the one grant that actually needs narrowing.
2. **G1 already opens `:2222` via IPv6 to all members** — this is pre-existing, so it's not "new," but it means the stated goal ("my iPhone can reach it, nothing else new opens") is only true in the sense that you add no *new* exposure; the effective exposure is already broader than intended. Tailscale ACLs don't support subtracting a /128 from a /48, so you cannot cleanly exclude just the subnet route from G1 without breaking IPv6 device-to-device connectivity for everyone else. Honest options:
   - Accept G1 as-is and document that pre-boot SSH is already open to all members via the IPv6 route (and note this in the review); or
   - If you want it actually restricted, tighten G1's dst (e.g. drop the v6 range / narrow it) — but that breaks IPv6 tailnet connectivity for IPv6-only clients, so it needs a deliberate decision, not a silent tweak.
3. **G2's IPv4 literal is misleading** — harmless but useless over cellular; the iPhone must connect to the `fd7a:...` address (or whatever Tailscale/MagicDNS name you can get), not the IPv4 literal. Keep it in dst for redundancy or drop it; don't expect it to work on 5G.

**Net recommendation:** keep G1 unchanged (pre-existing, broad — flag it), replace G2 with a tag-restricted grant if you want defense-in-depth for the IPv6 path, and rely on the 4via6 address in the iPhone's SSH config. Note that removing G2 entirely is also defensible since G1 already covers the working path — but then nothing *new* opens at all, which may be exactly what you want; just be aware the exposure was already there via G1.

## NFS export (`share`)

- It allows `100.64.0.0/10` — i.e. **every tailnet device**, including the kids' PC and Steam Deck. That matches your stated intent (shared working drive), but it means share is readable/writable by any member with no per-device scoping, and it's coupled to G1: if you ever tighten G1, NFS access breaks for everyone, not just the iPhone.
- Note the export is v4-only (`100.64.0.0/10`); IPv6-only clients (like your cellular iPhone) won't match it cleanly — confirm whether the NAS serves share over the tailnet's IPv6 address and whether that matters for who actually mounts it.
- NFS is a server-side allowlist, not an ACL; Tailscale ACLs gate the traffic in front of it, so effective access = intersection of the two. Don't treat the export as the control — the ACL is.

## Safe testing

Each SSH connection to `:2222` burns one cryptroot passphrase attempt, even with empty stdin — so minimize and sequence carefully:

1. **Verify policy without SSH first**: confirm the route is advertised (`tailscale status --json` / debug routes on a test client), ping/traceroute the `fd7a:...` address from a non-iPhone member, and try a denied connection from an unauthorized device (e.g. kids' PC) — tailnet-layer rejection never reaches dropbear, so **zero attempts consumed**. This is also your proof that G2/G1 actually gate what you think they gate.
2. Confirm no other ports open on the route from the iPhone (e.g. 2049) — again tailnet-denied, not reaching dropbear.
3. Then do **one** real SSH attempt from the iPhone with correct credentials, expecting success. Don't loop it; if you need to retry, that's another attempt and risks lockout of the pre-boot unlock.
4. Do the final live test during a window where you can physically reach the console (or with the NAS/BMC accessible) in case the passphrase counter trips — a failed pre-boot unlock is worse than a slow review.

The one thing I'd push back on: don't approve G2 as written. Either narrow its `src` to the iPhone tag, or drop it and rely on G1 + the 4via6 address, and be explicit in the approval that pre-boot SSH is already reachable by all members via the IPv6 path through G1 — that's the exposure you're actually accepting.