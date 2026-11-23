Verdict: do not approve as written. G2 looks least-privilege, but the union of G1+G2 is not.

### What each grant permits

**G1: `autogroup:member -> [100.64.0.0/10, fd7a:115c:a1e0::/48], ip:["*"]`**

`autogroup:member` = every device owned by every member user: your iPhone, your other devices, kids' PC, Steam Deck, any future member's devices. Not tagged/shared-only devices.

`100.64.0.0/10` + `fd7a:115c:a1e0::/48` = the entire Tailscale IPv4 and IPv6 space, any protocol/port. This is full-mesh device-to-device, not a narrow exception.

Crucially, `fd7a:115c:a1e0::/48` is the first 48 bits of the 4via6 address:

`fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128` is *inside* `fd7a:115c:a1e0::/48`

Tailscale ACLs are allow-only union, no exclusions. You cannot carve the 4via6 out of a `/48` later.

**G2: `autogroup:member -> [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128], ip:["tcp:2222"]`**

Every member device can TCP-connect to homesrv:2222, both as an IPv4 subnet route and as its 4via6 equivalent via nas01.

### The over-grant

1. **Src is everyone, not your iPhone.** Goal is iPhone-only unlock. As written, kids' PC, Steam Deck, etc. can all hit dropbear. Worse than disclosure: each TCP connection to :2222 burns a cryptroot attempt, even empty. Any allowed src can DoS the unlock by exhausting attempts.

2. **G1 already grants `*` to the 4via6.** Effective permission to homesrv is therefore not `tcp:2222` only:
   - via IPv4: `tcp:2222` from G2
   - via 4via6: `*` from G1

   Anyone can reach homesrv on *any* port via the IPv6 form - today only dropbear is listening pre-boot, but after boot that exposes its normal services. It also silently grants `*` to *any future* 4via6 subnet host advertised by any router, bypassing any IPv4-specific ACL you write later. This is the classic 4via6 bypass.

   If G1 is pre-existing, G2's IPv6 half is redundant and the hole already exists. If G1 is new, G1 itself is the massive new opening. Either way "nothing else new opens" is false, and "unchanged intent" is inaccurate for the `/48`.

### Fix

Remove the `/48`. Enumerate peer IPv6 `/128`s if you need IPv6 device-to-device, or just use IPv4 `100.64.0.0/10` for G1. Then re-add the 4via6 explicitly, iPhone-only:

```json
{"src": ["autogroup:member"],
 "dst": ["100.64.0.0/10"],  // + explicit peer fd7a:.../128s if needed, NOT /48
 "ip": ["*"]},

{"src": ["<iPhone 100.x/32>", "<iPhone fd7a:.../128>"], // or tag:iPhone applied only to that phone
 "dst": ["192.168.20.50/32", "fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128"],
 "ip": ["tcp:2222"]}
```

Get the iPhone IPs from `tailscale status`. Using `alex@...` instead would allow all your devices - better than all members, but not iPhone-only. Both dst forms are needed for the iPhone: IPv4 literal on WiFi/IPv4, 4via6 on IPv6-only 5G NAT64.

### NFS export `share`: `100.64.0.0/10`

Separate from ACL, and broader than `autogroup:member`. As chosen, any tailnet node that can reach the NAS - including tagged, shared, future, or compromised devices - can mount it. NFS `AUTH_SYS` trusts client UID, so any mount can read/write and spoof ownership inside `share`. That's fine for an intentionally shared working drive for Alex + kids + Steam Deck, but don't put secrets/passphrases there, and expect no isolation between users.

ACL is still the outer gate for traffic over 100.x, so narrowing G1 won't break NFS over IPv4. Defense-in-depth would be to narrow the export to specific `/32`s for the 4-5 trusted devices, `root_squash`, and split ro/rw if needed.

### Safe testing - do not burn attempts

No `nc`, `nmap`, `Test-NetConnection`, `ssh -o BatchMode=yes`, or empty-stdin probes to :2222. Each burns an attempt if the ACL is wrong, and can lock you out.

1. **Offline first:** Admin console ACL tester for: iPhone->2222 allow (both forms), iPhone->22 deny, kids PC->2222 deny (both forms), kids PC->4via6:22 deny, member->peer 100.x allow.
2. **No-dropbear checks:** `tailscale ping` to a peer and to the 4via6 address, `tailscale status` route check, ICMP ping to 192.168.20.50 (should now be denied - only tcp:2222 allowed). None touch dropbear.
3. **One live test only:** With correct passphrase ready, no auto-retry in the SSH app, physical/console fallback available. Test the *cellular/4via6* path as that one shot - WiFi IPv4 proves a different grant. Don't do a throwaway WiFi SSH first.
4. **Negative live test deferred:** Testing kids PC -> :2222 while homesrv is awaiting unlock is only safe if the ACL is already correct; if not, you burn Alex's attempt. Do it after boot (attempts reset, dropbear gone - use refused vs timeout on a harmless port to distinguish ACL deny from closed port) or not at all, relying on the tester.

Approve only after G1 loses the `/48` and G2's src is iPhone-only.