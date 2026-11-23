Let me carefully analyze this Tailscale ACLs scenario.

Setup:
- NAS (tailnet peer "nas01") advertises subnet routes 192.168.20.50/32 and its 4via6 form fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128. The 4via6 route exists because iOS on IPv6-only 5G rewrites IPv4 literals to carrier NAT64, bypassing Tailscale.
- Proposed policy grants:
  - G1: src autogroup:member -> dst [100.64.0.0/10, fd7a:115c:a1e0::/48], ip ["*"] (comment: "device-to-device, unchanged intent")
  - G2: src autogroup:member -> dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128], ip ["tcp:2222"]
- NAS NFS export `share` allows 100.64.0.0/10 (Alex chose this: share is the shared working drive for every tailnet device, incl. kids' PC and Steam Deck).
- Each SSH connection to :2222 consumes one cryptroot passphrase attempt, even with empty stdin.

Task: Produce what each grant actually permits, any over-grant and its fix, comments on the NFS export, and how to test safely.

Key analysis points:

G1: src autogroup:member → dst [100.64.0.0/10, fd7a:115c:a1e0::/48], ip ["*"]
- 100.64.0.0/10 is the entire Tailscale CGNAT range (tailnet address space). So G1 permits any member to talk to ANY tailnet peer on ANY port — that's device-to-device broad access. It also includes fd7a:115c:a1e0::/48 which is the tailnet's IPv6 ULA prefix (100.x is IPv4, fd7a:... is IPv6). The comment says "unchanged intent" but it permits everything to everything — including port 2222? Wait, G1 dst is [100.64.0.0/10, fd7a:115c:a1e0::/48] which covers tailnet addresses only, not the subnet route 192.168.20.50 (that's a real LAN address, not in 100.64.0.0/10). So G1 does NOT cover the pre-boot unlock SSH on 192.168.20.50:2222 via IPv4. But wait — the 4via6 form fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128 is in fd7a:115c:a1e0::/48! That's why G2 exists... Actually wait.

Let me think about the 4via6 route. Tailscale has a feature where subnet routes can be announced as IPv4 and also as "4via6" — i.e., the IPv4 subnet is represented in the tailnet's IPv6 range via NAT64-like prefix mapping (fd7a:115c:a1e0:b1a::/64 or similar). The 4via6 address fd7a:115c:a1e0:b1a:0:1:c0a8:1432 encodes 192.168.20.50 — let's check: c0a8:1432 = 192.168.20.50? c0 = 192, a8 = 168, 16 = 22, f2 = 242. Yes! So the 4via6 form of 192.168.20.50 is fd7a:115c:a1e0:b1a:0:1:c0a8:1432 (the /128). Note "0:1:c0a8:1432" — the prefix b1a... hmm, actually the standard Tailscale 4via6 uses fd7a:115c:a1e0:b1a::/64? Let me not worry too much; the point is the 4via6 address encodes the IPv4.

Now G2: dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128], ip ["tcp:2222"] — permits members to reach the NAS's subnet-route address on TCP 2222 only. That's exactly the goal: iPhone can reach pre-boot unlock SSH over cellular (via tailnet).

But wait — is G2 actually needed given G1? G1 covers fd7a:115c:a1e0::/48 with ip ["*"], and the 4via6 address fd7a:115c:a1e0:b1a:0:1:c0a8:1432 is within fd7a:115c:a1e0::/48. So G1 already permits any member → the 4via6 form of the SSH host on ANY port, including 2222! So G2's IPv6 leg is redundant — G1 already grants it (and more: all ports). G2 only adds the IPv4 /32 leg (192.168.20.50/32), which is NOT covered by G1 since G1's dst is tailnet ranges only.

So over-grant analysis:
- G1 already permits any member → 4via6 address of the SSH host on ALL ports (e.g., NFS 2049? no wait, NFS is on the LAN address...). Hmm. Actually, does G1's coverage of the 4via6 route mean anyone can reach the NAS's pre-boot SSH via the IPv6 form with any port? Yes — ip ["*"] means all ports/protocols. So the "device-to-device, unchanged intent" grant already punches a hole: any member can connect to the 4via6 address of the NAS on port 2222 (and everything else). Actually also, more broadly, G1 permits all members → all tailnet peers on all ports — that's the "device-to-device" intent, fine for tailnet addresses. But it also implicitly covers the 4via6 subnet route address because the 4via6 address lives in fd7a:115c:a1e0::/48. So G1 over-grants relative to the goal: any member can reach the pre-boot unlock SSH host on ANY port via the 4via6 form, not just tcp:2222.

Wait, actually, is that right? Tailscale ACLs: dst for subnet routes — in Tailscale ACLs, when you reference a subnet route address (e.g., 192.168.20.50/32), the destination is the subnet-routed address. The 4via6 form is also a valid dst. G1's dst fd7a:115c:a1e0::/48 covers it. Yes.

So the fix for G2/G1: tighten G1 to exclude the 4via6 SSH host, or add an explicit deny... Tailscale ACLs don't have deny rules (well, actually they do? No — Tailscale ACLs are allow-only; there's no "deny" in classic ACLs. Actually, Tailscale added "deny" rules? Let me recall. In Tailscale ACLs, you can have "action": "accept" or "drop"? Yes! Tailscale ACLs support deny rules via action: drop? Hmm.

Tailscale ACL syntax: 
```json
{
  "acls": [
    {"action": "accept", "src": [...], "dst": [...], "ip": [...]},
    {"action": "drop", "src": [...], "dst": [...], "ip": [...]}
  ]
}
```
Yes — Tailscale supports deny rules with action "drop" (since ~2023?). Let me recall: Tailscale ACLs support `"action": "accept"` (default) and `"action": "drop"`. Yes, deny rules exist in the ACL JSON syntax. The docs: "You can also use drop to explicitly deny traffic" — I believe deny/drop rules were added. Yes, Tailscale supports deny rules (action: drop) in ACLs.

So fix options:
1. In G1, narrow dst to tailnet ranges but exclude the 4via6 SSH host — but CIDR exclusions aren't expressible directly; you'd need a drop rule for the specific /128.
2. Or change G1's ip to exclude 2222? No — G1 is device-to-device for all ports; the issue is only that it covers the 4via6 SSH host address. You can't subtract one /128 from a /48 in Tailscale ACLs (no subtraction). So you need a drop rule: src autogroup:member → dst fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128, ip ["*"] with action drop... but then G2's accept for tcp:2222 would be overridden by the drop? Order matters: in Tailscale ACLs, more specific rules take precedence; deny rules beat allow rules regardless of order? Let me recall: "Rules are evaluated from most specific to least specific" — actually Tailscale evaluates ACLs and any matching accept allows; drops override accepts. The documented behavior: "deny rules take precedence over allow rules" — yes, in Tailscale, a drop rule wins over an accept rule. From the docs: "If a packet matches both an accept and a drop rule, it is dropped." I believe that's right.

Alternative cleaner fix: don't rely on G1 covering the 4via6 address; instead, remove the 4via6 route from... no, the 4via6 route is needed for iOS NAT64 rewriting.

Better fix: change G2 to be the only grant for the SSH host and add a drop rule in G1's scope. Or: change G1 dst to [100.64.0.0/10] only (drop fd7a:115c:a1e0::/48)? But wait — is fd7a:115c:a1e0::/48 needed for device-to-device IPv6? The tailnet's IPv6 range... Tailscale assigns IPv6 addresses in the ULA prefix. If the tailnet uses IPv6, members have fd7a:115c:a1e0::/48 addresses, so G1 needs that for device-to-device over IPv6. But the specific /128 (the 4via6 SSH host) is inside it. So you can't just remove fd7a... without breaking IPv6 device-to-device.

Hmm, wait — actually, is the 4via6 address a tailnet address or a subnet route? The NAS advertises subnet routes: 192.168.20.50/32 and its 4via6 form fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128. These are subnet routes, not tailnet addresses. The 4via6 route is how the IPv4 subnet route is represented for IPv6-only clients. So dst in ACLs can reference either form.

So G1 as written permits: any member → any address in 100.64.0.0/10 (all tailnet IPv4 addresses) and fd7a:115c:a1e0::/48 (all tailnet IPv6 AND the 4via6 subnet route), on all ports. The over-grant relative to goal: members can reach the pre-boot SSH host (4via6 form) on ALL ports — e.g., tcp:22? No wait, the SSH is on 2222; other ports on that address — what else listens there? Pre-boot dropbear on :2222. But "all ports" means if something else is exposed via the route... The subnet route /32 only covers that one host. So via 4via6 form, any member can reach ANY port of the pre-boot SSH host — including port 2222 (intended) but also anything else bound there. Since it's a pre-boot environment with dropbear on 2222, the practical exposure is 2222 anyway... but the point is the grant is broader than needed: ip ["*"] instead of tcp:2222. Also G1 permits members to reach tailnet peers on all ports — that's intended device-to-device.

Hmm wait, also there's a subtlety: does G1 permit reaching 192.168.20.50 (IPv4)? No — dst doesn't include the /32. So over cellular via IPv4... iOS rewrites to NAT64 so it uses the 4via6 form. On an IPv4-capable client, G2's IPv4 leg permits tcp:2222 only. Good.

Another subtlety: G1's comment "device-to-device, unchanged intent" — the problem is that fd7a:115c:a1e0::/48 now includes the 4via6 subnet route address (fd7a:115c:a1e0:b1a:0:1:c0a8:1432). So G1 silently grants all-ports access to the pre-boot SSH host via the 4via6 form. The fix: add an explicit drop rule for that /128 with ip ["*"], or change G2's... no wait, you can't narrow G1's dst by subtracting. Options:

Option A: Add deny/drop rule:
```json
{"action": "drop", "src": ["autogroup:member"], "dst": ["fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128"], "ip": ["*"]}
```
placed in the ACL; drops override accepts. Then G2's accept for tcp:2222... wait, if drop wins over accept, then the drop rule would also block tcp:2222! Drop rules take precedence. So you'd need a more specific accept for tcp:2222 — Tailscale evaluates rules by specificity? Let me recall the actual semantics.

Tailscale ACL evaluation: Rules are evaluated in order? Or most-specific-wins? From Tailscale docs (Access Controls / ACLs): "Rules are processed from top to bottom"? Hmm. Actually I recall: "ACLs are evaluated in order, and the first matching rule wins"? No...

Let me think. The Tailscale ACL documentation says: "Each ACL is a list of rules; traffic is allowed if it matches any accept rule and no drop rule" — something like that. Actually I recall from the tailscale docs on ACLs: "Deny rules: A deny rule (action: drop) denies traffic even if an allow rule matches." And ordering: I believe Tailscale evaluates all rules and a packet is allowed iff it matches at least one accept and no drop. Let me check memory of the actual doc:

From Tailscale docs (ACL reference):
- "acls": list of rules. Each rule has action (accept or drop), src, dst, ip.
- "Rules are evaluated in order" — hmm.

Actually I'm fairly confident about this from the docs: "If a packet matches both an allow and a deny rule, the deny wins." And there's no ordering dependence except... Actually I remember the doc saying rules are evaluated in order of specificity? Let me just recall the actual statement: In Tailscale ACLs, "deny rules take precedence over allow rules" — yes, that's documented. E.g., from the docs on "Deny rules": "Deny rules (action: drop) can be used to explicitly deny traffic... A packet is allowed only if it matches an accept rule and does not match any drop rule." Something like that.

So Option A with a drop rule for ip ["*"] on the /128 would block tcp:2222 too — need the drop rule to be more specific in ip than the accept? No — drop wins regardless of specificity? If drop wins over any accept, then G2's accept for tcp:2222 is also dropped. Then you'd need... hmm.

Alternative: make the drop rule specific enough: drop dst /128 with ip ["*"] but then re-add accept for tcp:2222 — but drop still wins. So that doesn't work if drop always wins. Unless specificity matters: more specific rules win over less specific ones? Tailscale docs: "Rules are evaluated from most specific to least specific" — I actually recall this now! Yes: "Tailscale evaluates ACLs by specificity" — hmm.

Let me think about the actual implementation. Tailscale's ACL evaluation is done in the control plane; the docs say: "The order of rules does not matter; the most specific matching rule wins"? Or "first match wins"? 

I recall from tailscale.com/kb/1187 (ACLs): "Rules are evaluated in order, top to bottom, and the first rule that matches determines the action"? Hmm, I'm not certain.

Actually, I remember more specifically now: Tailscale ACL docs state that deny rules take precedence over allow rules regardless of order, and that within accepts, any match allows. Let me just present it carefully with a hedge: "drop rules override accepts (verify against your tailnet's ACL version)".

Alternative cleaner fix avoiding drop-rule subtleties: change G1's dst to exclude the 4via6 SSH host by not including fd7a:115c:a1e0::/48 in G1... but that breaks IPv6 device-to-device. Alternatively, split G1: keep IPv4 tailnet range + a narrower IPv6? The tailnet's IPv6 prefix is /48; the 4via6 route lives inside it. Can't subtract.

Hmm — actually wait. Is that true? Tailscale subnet routes with 4via6: the 4via6 form uses the same fd7a:115c:a1e0::/48? The address given is fd7a:115c:a1e0:b1a:0:1:c0a8:1432 — that's within fd7a:115c:a1e0::/48 (fd7a:115c:a1e0:XXXX...). Yes.

OK here's another approach to the fix: instead of a drop rule, change G1 to accept only what it should: device-to-device between tailnet addresses. The problem is the 4via6 address is indistinguishable from tailnet addresses in the /48. So the cleanest fix is:

Option B: Change G2 to cover both forms and make G1 not include the 4via6 SSH host — impossible without drop.

Option C: Use a more specific dst for G1's IPv6 leg: instead of fd7a:115c:a1e0::/48, use... the tailnet peers' IPv6 addresses are unknown (can't enumerate). So no.

Option D: Change the NAS to not advertise the 4via6 route as a subnet route but... no, needed for iOS.

Option E: Accept that G1 grants all-ports access to the 4via6 SSH host via the /48, and instead tighten by adding drop rule with ip ["*"] on the /128 plus accept for tcp:2222 — if drop always wins, this fails; if specificity matters (more specific accept beats less specific drop?), it works.

Let me actually recall Tailscale's documented semantics precisely. From the Tailscale docs (https://tailscale.com/kb/1187/acls or the ACL reference page):

"ACLs are a list of rules... Each rule has an action (accept or drop), a src set, a dst set, and an ip set. ... Traffic is allowed if it matches at least one accept rule and no drop rule matches." I'm fairly confident that's the semantics — "drop wins over accept". And there's also: "More specific rules take precedence over less specific rules" — hmm, I genuinely recall a specificity rule in Tailscale ACLs. Let me think about the implementation: tailscale uses a "ruleset" with a tree structure; evaluation is done via a "most specific match wins" approach? 

From the actual docs (I've read them): "Rules are evaluated from most to least specific. A packet matches the first rule that applies..." Hmm no.

OK, I found it in memory: Tailscale docs on ACLs say: "The order of rules does not matter. If a packet matches both an accept and a drop rule, it is dropped." And separately there's about `src`/`dst` specificity for autogroups... Actually the doc says: "Rules are evaluated in order of decreasing specificity"? 

I'll just present the fix with the drop rule and note that drop rules override accepts, so you must make sure G2's accept still wins — the safest correct approach given drop-wins semantics: make the drop rule NOT match tcp:2222. I.e., drop rule: dst /128, ip ["*"] minus 2222? Can't subtract ports... "ip" supports ranges like "tcp:1-65535"? You can write ip ["tcp:1-65535"]? That still includes 2222.

Hmm. Alternatively flip it: make G1 not cover the 4via6 SSH host by changing G1's dst fd7a:115c:a1e0::/48 → but exclude... 

Actually, wait — maybe simpler and cleaner: change G1 to dst [100.64.0.0/10] only (drop the IPv6 leg)? But then IPv6 device-to-device breaks — members on IPv6 tailnet addresses can't talk to each other. Is that acceptable? The goal is iPhone → SSH over cellular; iOS uses 4via6 (NAT64) not tailnet IPv6 for the subnet route. Device-to-device IPv6 between peers... The comment says "unchanged intent" — device-to-device. Removing IPv6 breaks that intent.

Alternative: keep G1 but add a drop rule that excludes tcp:2222 by using ip ["*"] on dst /128 and then a MORE specific accept? If drop wins over everything, no good. If specificity matters (more specific accept beats less specific drop), then: drop rule dst /128 ip "*" vs accept rule dst /128 ip "tcp:2222" — the accept is more specific (narrower ip set). Tailscale docs on deny rules... 

Let me just look at what I actually know about Tailscale ACL evaluation from the official docs, which I have decent memory of:

From https://tailscale.com/kb/1187/acls (I recall):
- "Each rule has an action: accept or drop. ... If a packet matches any drop rule, it is dropped, regardless of whether it also matches an accept rule." — I'm fairly confident this is right. There's also mention that accept rules are evaluated... and "the most specific matching rule wins"? 

Hmm, actually now I recall the real doc text: "Rules are processed in order from first to last... no wait."

I'll hedge appropriately: present both options — (a) if your tailnet version supports drop rules with specificity, use a drop + accept; (b) simplest robust fix: change G1's dst IPv6 leg to the tailnet's IPv6 prefix EXCLUDING... can't. 

Alternative robust fix that avoids drop-rule semantics entirely: Don't include fd7a:115c:a1e0::/48 in G1; instead enumerate device-to-device via autogroup:member → dst [100.64.0.0/10] and rely on... no, IPv6 peers need the /48.

Hmm wait — actually, is that right? Do tailnet members have fd7a:115c:a1e0::/48 addresses? The 4via6 route address fd7a:115c:a1e0:b1a:0:1:c0a8:1432 — the "b1a" in the third group... Tailscale's NAT64 prefix is fd7a:115c:a1e0:b1a::/64? Hmm, I think the actual Tailscale 4via6 prefix is fd7a:115c:a1e0:b1a::/64 or similar. The given address has "b1a" as the third hextet (fd7a:115c:a1e0:b1a:...), which is consistent with a /48 containing it.

OK here's the thing — I shouldn't get lost in recalling exact Tailscale semantics. The task is a security review; I should produce accurate analysis of the grants and give sensible fixes with appropriate caveats. Let me structure:

1. What each grant actually permits:
   - G1: src = any tailnet member (autogroup:member), dst = all tailnet addresses (100.64.0.0/10 IPv4 + fd7a:115c:a1e0::/48 IPv6), ip = any protocol/port. This is a broad device-to-device rule. Critically, because the NAS's 4via6 subnet route (fd7a:...:b1a:0:1:c0a8:1432/128) lives inside fd7a:115c:a1e0::/48, G1 already permits every member to reach the pre-boot SSH host (via its 4via6 address) on ANY port — not just tcp:2222. So the "unchanged intent" comment is misleading: it silently opens the SSH host's IPv6 form broadly. Also note G1 does NOT cover the IPv4 subnet route 192.168.20.50/32 (not in dst ranges) — so over cellular via NAT64, iOS reaches it through the 4via6 form; on a plain IPv4 client, G1 alone doesn't reach it at all.
   - G2: src = any member, dst = the two forms of the pre-boot SSH host (IPv4 /32 + 4via6 /128), ip = tcp:2222 only. This is exactly the goal and nothing more — IF it's actually needed for the IPv4 leg. Note: G2's 4via6 leg is redundant with G1's ip ["*"] coverage (G1 already allows all ports there), so the effective incremental effect of G2 is only the IPv4 /32 leg (tcp:2222). And because G1 already covers the 4via6 address on all ports, G2 doesn't tighten anything for the iOS path — it just adds a redundant accept.

   Over-grant: G1 grants all-ports access to the pre-boot SSH host via the 4via6 form (e.g., any member can reach port 22/2222/whatever on that address). Also G1 grants all members → ALL tailnet peers on all ports, which is the stated intent but worth confirming it's acceptable (kids' PC and Steam Deck are members — they get full access to everything on every tailnet device, including e.g. NFS on other devices? Well, NFS export is on this NAS; G1 allows members → NAS tailnet address on all ports including 2049).

2. Fixes:
   - Add a drop rule for the 4via6 SSH host /128 with ip ["*"]... but then it blocks 2222 too if drop wins. Need to think. Let me settle the Tailscale semantics: I'm now fairly confident that in Tailscale ACLs, deny (drop) rules take precedence over allow rules. From the docs: "If a packet matches both an accept and a drop rule, it is dropped." So a drop on /128 ip ["*"] would block 2222 as well — bad.
   - Better fix: change G1's dst to exclude the 4via6 SSH host by narrowing the IPv6 leg. Since you can't subtract, the robust approach is: keep G1 for tailnet addresses but add an explicit drop rule scoped to ip ["tcp:2222"]?? No — that would block the intended port.
   
   Hmm, actually maybe the right fix is different: since G1 already covers the 4via6 address with all ports, and the goal is "only tcp:2222 on the SSH host," the cleanest correct fix is to NOT let G1 cover the 4via6 SSH host. Options:
   a) Remove the 4via6 route from the NAS (but then iOS NAT64 rewriting bypasses Tailscale — that's why it exists; removing breaks cellular access). No.
   b) Change G1 to dst [100.64.0.0/10] + fd7a:115c:a1e0::/48 minus the /128 — impossible in ACL syntax... unless you use a drop rule. Let me handle the drop-rule precedence correctly: In Tailscale, I believe deny rules DO take precedence, and to get "tcp:2222 allowed, everything else dropped" on the /128, you can write TWO rules:
      - accept: src member → dst /128, ip ["tcp:2222"] (this is G2's 4via6 leg)
      - drop: src member → dst /128, ip ["*"] — but this would also match tcp:2222 and drop wins. Bad.
   So instead the drop rule must be ip "all except 2222" — not expressible? Tailscale ip sets support ranges and lists; can you write "tcp:1-65535" minus... no subtraction.

   c) Alternative: change G1's IPv6 leg to a narrower prefix that excludes the /128. The tailnet IPv6 prefix is /48; the 4via6 address is in it. But wait — what about the actual tailnet IPv6 addresses? They're also in fd7a:115c:a1e0::/48. No way to separate without knowing every peer's address.

   d) Alternative: restructure G1 entirely: dst = [100.64.0.0/10] for IPv4 tailnet + drop the IPv6 leg of G1 and instead... no, breaks IPv6 device-to-device.

   e) Alternative: accept the over-grant but note it's bounded (only that one host's all ports — which in practice is just 2222 since it's a pre-boot dropbear box). Then add the drop rule anyway with correct specificity. Let me reconsider Tailscale semantics once more. 

   Actually — I now recall more clearly! Tailscale ACL docs on deny rules: "Deny rules take precedence over allow rules." And there's also documented behavior that MORE SPECIFIC rules win? The doc for ACLs says: "Rules are evaluated in order of specificity, with the most specific matching rule winning" — hmm.

   Let me think about the actual codebase (tailscale/controlplane or the app's ACL evaluation). Tailscale uses a "ruleset" where each rule has src/dst sets and ip sets; evaluation is done via CIDR trees and port sets, computing match counts... The doc says: "If a packet matches both accept and drop rules, it is dropped" — I'm confident enough in this. And ordering: "Rules are processed in order from most specific to least specific"? 

   You know what, I'll present the fix as: add a drop rule for the 4via6 /128 with ip ["*"] and then re-add G2 — but note that if your tailnet version gives drop precedence over accept (which it does), you must instead scope the drop to exclude 2222... 

   Ugh, this is getting circular. Let me just settle on the cleanest correct approach:

   **Cleanest fix**: Don't put fd7a:115c:a1e0::/48 in G1 at all. Instead, keep device-to-device as IPv4 tailnet only? No...

   Alternative cleanest fix: Make G1 dst = [100.64.0.0/10] (IPv4 tailnet only) and add a separate grant for IPv6 device-to-device with dst fd7a:115c:a1e0::/48 but ip ["*"]... same problem.

   OK alternative: change G1's ip to exclude the 2222 port? No — G1 is device-to-device for all ports; you can't express "all ports except 2222" either (well, you CAN: ip ["tcp:1-65535"]... no subtraction; but you could enumerate? "*" covers everything).

   Hmm, wait — actually maybe I should reconsider: is the over-grant in G1 actually a real problem for the goal? The goal: "iPhone can reach homesrv's pre-boot unlock SSH (dropbear on 192.168.20.50:2222) over cellular, and nothing else new opens."

   "Nothing else new opens" — the key phrase! So the review should check: does this change open anything beyond what was intended? G1 as written permits every member → every tailnet address AND the 4via6 SSH host on all ports. Before the change, presumably G1 already existed ("unchanged intent") and already included fd7a:115c:a1e0::/48 — so the 4via6 exposure was ALREADY there before this change? The comment says "device-to-device, unchanged intent" — implying G1 is pre-existing and unchanged. If G1 is unchanged, then the 4via6 all-ports exposure to the SSH host already existed... but wait, did the NAS previously advertise the 4via6 route? The setup says the NAS advertises both routes (given). So G1 already covered the 4via6 address on all ports.

   Hmm, but then what's the actual problem with the proposed policy? Let me re-read the task.

   "Proposed policy grants:
   G1: src autogroup:member -> dst [100.64.0.0/10, fd7a:115c:a1e0::/48], ip ["*"] (comment: "device-to-device, unchanged intent")
   G2: src autogroup:member -> dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128], ip ["tcp:2222"]"

   The review asks: "what each grant actually permits, any over-grant and its fix, comments on the NFS export, and how you'd test the result safely."

   So the expected findings:
   1. G1 is broad (all members → all tailnet addrs, all ports) — that's the stated device-to-device intent, but it ALSO covers the 4via6 SSH host on ALL ports — over-grant vs. the goal of "only tcp:2222 opens". Fix: add a drop rule for the /128 (with ip ["*"])... precedence issue again. OR fix by tightening G1's dst to exclude... 

   Let me think about what Tailscale actually supports for excluding a host from a prefix in an ACL dst. In Tailscale ACLs, dst can be a list of CIDR/hosts; there's no subtraction. However! There IS a way: you can give the NAS its own... no.

   Actually — hmm, what about using `autogroup` or tags for the SSH host? No, the issue is the /48 prefix includes the /128.

   Practical fix that definitely works in Tailscale ACLs:
   - Drop rule: src autogroup:member → dst fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128, ip ["*"] — and then G2's accept for tcp:2222. If drop wins over accept, 2222 is blocked → bad. 
   
   Let me actually nail down Tailscale's precedence. I'm going to reason from the documented behavior I remember most strongly: The Tailscale docs (Access Controls) state: "Deny rules take precedence over allow rules" — YES, I'm confident this is documented. E.g., the doc example shows a drop rule for a specific port that overrides a broad accept. And also: "If a packet matches both an accept and a drop rule, it is dropped." So yes, drop wins.

   Given drop wins, the correct fix is NOT drop-then-accept on the same host. Instead:
   - Remove fd7a:115c:a1e0::/48 from G1's dst; keep only 100.64.0.0/10? That breaks IPv6 device-to-device between peers (members with fd7a:... addresses can't talk to each other). But wait — does the tailnet even use IPv6 for peer-to-peer? Tailscale supports IPv6 in the tailnet if enabled. The given G1 includes the /48, so yes presumably IPv6 is used.
   
   - OR: change G1's dst to [100.64.0.0/10] and add a separate grant for device-to-device IPv6 excluding the SSH host — impossible without enumeration... unless you enumerate: dst = fd7a:115c:a1e0::/48 with ip ["*"] minus /128... no subtraction.

   - OR: accept the over-grant as bounded and note it, then add a drop rule for the 4via6 /128 with ip ["tcp:2222"]?? That blocks the intended port — bad.

   Hmm hold on. Let me reconsider — maybe Tailscale ACLs DO support specificity ordering and deny rules only beat less-specific accepts. From the actual docs (I'll reconstruct from memory of reading them): 

   "Rules are evaluated in order, but more specific rules take precedence over less specific rules..." — I genuinely recall something like "Specificity is determined by the number of bits in the CIDR and the port range" and "the most specific rule wins." Actually yes! I'm now fairly sure Tailscale ACLs use most-specific-wins, not first-match. The docs say: "If a packet matches multiple rules, the most specific matching rule wins" — where specificity = number of bits in dst/src CIDR + ip set specificity? Something like that.

   Given uncertainty, best approach: present the fix with explicit caveat and offer the robust alternative: restructure G1 to not include the /48 at all; instead grant device-to-device IPv6 only to peers via... 

   You know what — there's a much cleaner fix that sidesteps everything: **Don't advertise the 4via6 route with ip ["*"] coverage; instead, change G1's dst to tailnet addresses only and explicitly enumerate... no.**

   Alternative robust fix: **Make G2 the only grant for the SSH host by removing the 4via6 route from G1's reach via a drop rule, and verify precedence empirically (test).** That's honest engineering: state the semantics with a caveat and tell them to test.

   OR — simplest and cleanest: **Change G1 to dst [100.64.0.0/10] only, and let IPv6 device-to-device be handled by... nothing?** If the tailnet is IPv4-only for peer traffic (IPv6 enabled only for NAT64), then dropping the /48 from G1 loses nothing. But we don't know that.

   Another clean fix: **split G1 into two rules**:
   - G1a: src member → dst [100.64.0.0/10], ip ["*"] (device-to-device IPv4)
   - G1b: src member → dst [fd7a:115c:a1e0::/48], ip ["*"] — same problem.

   OK here's the thing. Let me reconsider whether drop rules actually take precedence over accepts in Tailscale. I want to be accurate. Memory of tailscale docs "ACL reference" page: 

   - `action`: "accept" (default) or "drop"
   - "Deny rules... A deny rule takes precedence over allow rules." — I'm ~85% confident this is documented.

   And the doc also says: "Rules are evaluated in order from most specific to least specific" — hmm, actually that might be from the "autogroups" or from the `src`/`dst` matching docs... 

   There's also a known gotcha: Tailscale ACLs don't support denying a single port within a broad accept cleanly; the documented pattern for "allow everything except 2222" is to use ip ["*"] on a broad dst and then a drop rule with ip ["tcp:2222"]... which works because drop wins. Wait, that's exactly the documented pattern! "Deny rules take precedence over allow rules" — so to deny port 2222 within an all-ports accept, add a drop rule for tcp:2222. YES. That's the standard documented pattern. So drop > accept, confirmed enough.

   Therefore, for our fix: we want "allow tcp:2222 on the /128, deny everything else". With drop-wins semantics:
   - Accept rule (G2): dst /128, ip ["tcp:2222"] → allows 2222.
   - Drop rule: dst /128, ip ["*"] → matches everything including 2222 → blocks 2222. BAD.

   So the drop rule must exclude 2222. Tailscale ip sets: can you express "all ports except 2222"? You can list ranges: ip ["tcp:1-2221", "tcp:2223-65535"] — YES! That's expressible! "tcp:1-2221" and "tcp:2223-65535". Or more simply, since it's pre-boot dropbear on 2222, deny ip ["*"] minus... you can also just enumerate the ports you want to allow and... no wait, we want to DENY everything except 2222. So ip ["tcp:1-2221", "tcp:2223-65535"] for the drop rule. That works but is clunky. Alternatively, since G1's problem is only about the /128, and G2 already accepts tcp:2222... 

   Wait, actually — hold on. Let me reconsider. What if we flip it: make the DROP rule ip ["*"] on the /128, and then make the ACCEPT rule for tcp:2222 MORE specific? If Tailscale evaluates most-specific-wins (not drop-always-wins), then accept (more specific ip set) wins. The docs... 

   Ugh. OK let me just decide: I'll present it as "add a drop rule for the /128 covering all ports except 2222" using the two-range trick, which works under either evaluation semantics (drop always wins; the accept for 2222 isn't matched by the drop). That's robust and correct under drop-wins semantics. 

   Also alternative: change G1 to dst [100.64.0.0/10] only — if the tailnet doesn't actually use IPv6 peer-to-peer, that's cleanest. But given G1 includes the /48 ("unchanged intent"), IPv6 device-to-device is presumably intended; keep it and add the drop rule.

   Actually, wait — one more consideration. Is the over-grant in G1 actually a problem worth fixing? The goal: "nothing else new opens." If G1 already existed (unchanged), then the 4via6 all-ports exposure to the SSH host already exists — it's not NEW. But the proposed policy adds G2 which is fine. Hmm, but the review should still flag: G1 grants any member → the pre-boot SSH host on ALL ports via 4via6; that means e.g. the kids' PC can reach port 22/2222/whatever on that host — wait, but what does "nothing else new opens" mean then? The change adds G2 (tcp:2222 on both forms). Before the change: members could already reach the 4via6 SSH host on all ports via G1! So actually the cellular access path was ALREADY open before this policy — G2's 4via6 leg is redundant, and G2's IPv4 leg adds new access (tcp:2222 on the IPv4 form). Interesting.

   But hold on — is that right? Does G1's dst fd7a:115c:a1e0::/48 actually match a subnet-route 4via6 address? Subnet routes in Tailscale ACLs: you can reference subnet route addresses in dst. The 4via6 form is the tailnet-side representation of the subnet route. I believe yes — the docs mention that for subnet routes, you can use either the IPv4 address or its 4via6 form. So yes, G1 matches it.

   Hmm, but actually there's a subtlety: does the NAS need to advertise the 4via6 route AND have the client resolve it? Yes — the setup says the 4via6 route exists precisely so iOS on IPv6-only 5G can reach it (iOS rewrites IPv4 literals to NAT64, which would bypass Tailscale). So with G1's dst covering fd7a:115c:a1e0::/48, the iPhone CAN already reach the SSH host via the 4via6 form on all ports — before this policy change. So what does G2 add? Only the IPv4 /32 leg (tcp:2222) for clients that speak IPv4 to the subnet route. And it adds redundancy/clarity.

   So the honest review finding: G1 (unchanged) already permits all-ports access to the SSH host via 4via6 — so "nothing else new opens" is already violated in spirit by the existing G1; the proposed change doesn't fix it. The fix: add a drop rule for the /128 (all ports except 2222), or narrow G1.

   Also — what about the IPv4 leg? Before this change, could any member reach 192.168.20.50 at all? No — neither G1 nor (old policy) covered it. After: members can reach tcp:2222 on the IPv4 form. That's the intended new opening. Good.

   Another subtlety: does G2 permit reaching the SSH host from ANY member, including the kids' PC and Steam Deck? Yes — autogroup:member includes everyone. The goal says "my iPhone can reach" — but the grant is for all members. Over-grant relative to intent: any member (kids' PC, Steam Deck) can now reach the pre-boot SSH host on :2222. And each SSH connection consumes a cryptroot passphrase attempt! So kids' devices could burn passphrase attempts — that's a real operational risk. Fix: restrict src to the iPhone specifically (e.g., tag or specific device) instead of autogroup:member. That's probably the most important finding given the "Each SSH connection to :2222 consumes one cryptroot passphrase attempt" note!

   Yes — that's the key trap. G2 grants all members → SSH host; each connection burns a passphrase attempt; kids' PC/Steam Deck are members and could hammer it, locking out Alex's iPhone (cryptroot lockout after N attempts). Fix: scope G2 src to Alex's iPhone (e.g., `src: [tag:iphone]` or the specific device, or a group containing just his phone). Also note: even Alex's own devices — he wants "my iPhone" specifically.

   Also G1: all members → all tailnet addrs on all ports — that's the stated device-to-device intent; but it also includes... wait, does G1 cover the NFS export? The NFS export is on the NAS at its LAN address 192.168.20.50? Or at its tailnet address? "The NAS NFS export `share` allows 100.64.0.0/10 (Alex chose this: share is the shared working drive for every tailnet device, incl. the kids' PC and Steam Deck)." So the NFS server (on the NAS) accepts connections from any address in 100.64.0.0/10 — i.e., any tailnet client. That's a separate control (the NFS export itself), not the Tailscale ACL. The review should comment: the NFS export allows all tailnet addresses → all members can mount share; that's Alex's stated intent and it's consistent with G1 (device-to-device). But note: the export is NOT restricted to :2049 or anything — it's a filesystem mount, so any member can read/write the shared drive. That's intended. Also note: NFS over Tailscale — the ACL G1 already allows members → NAS tailnet address on all ports (including 2049), so the NFS export is consistent with the ACL; no new opening from this policy change for NFS. But worth noting: since G1 permits all-ports to all tailnet addresses, and the NAS's tailnet address is in that range, members can reach whatever else listens on the NAS's tailnet address (e.g., SMB? SSH on tailnet port 22?) — the NFS export note is about what the server accepts; the ACL governs whether traffic flows at all. Comment: keep them in sync; don't let the export be broader than the ACL or vice versa... actually the export being broader than the ACL just means the ACL gates it (fine). The risk is the reverse: export allows 100.64.0.0/10 but if you later narrow G1, the export still says "any tailnet addr" — fine, ACL wins.

   Also: should the NFS export be restricted to specific devices? Alex chose all-tailnet; that's his call for a shared drive. Comment: it means any member incl. kids' PC and Steam Deck can read/write share — confirm that's intended (it is, per the note). Also note NFS over Tailscale: consider whether to restrict via export to specific hosts instead of the whole /10 — but Alex deliberately chose shared. Fine, just note it and maybe suggest watching for writes from kids' devices.

   Also, one more check on G1: dst includes fd7a:115c:a1e0::/48 — this covers ALL tailnet IPv6 addresses AND the 4via6 subnet route /128. And ip ["*"] means any protocol (TCP/UDP) and port. So G1 = "all members can talk to anything on the tailnet, all protocols/ports." That's broad but stated as unchanged intent. The review should note it's broad by design and flag the 4via6 SSH host exposure specifically.

   Also: does G2 need ip ["tcp:2222"] or would "*" also be fine? No — keep tcp:2222, that's the point.

   Another check: src autogroup:member — is that valid syntax? Yes, `autogroup:member` is a valid Tailscale src/dst selector (all members). Also there's `autogroup:nonroot` etc. Fine.

   Now — the pre-boot unlock SSH angle: "pre-boot" means dropbear runs before the main OS boots (e.g., in a bootloader/initramfs or a custom boot flow). The NAS advertises subnet routes; the iPhone reaches 192.168.20.50:2222 over cellular via Tailscale. Each connection consumes a cryptroot passphrase attempt — meaning the SSH service is gated by a passphrase that's consumed per connection (like a challenge-response where each auth attempt counts against cryptroot). So:
   - G2 grants ALL members → all members can burn passphrase attempts. Kids' PC / Steam Deck could connect repeatedly and lock Alex out (cryptroot has limited retries before it stops booting or requires physical access). Fix: restrict G2 src to Alex's iPhone (and maybe his other devices he trusts), e.g., a tag like `tag:iphone` or the specific device name/ID.
   - Also note: even Alex's iPhone connecting repeatedly — each connection burns an attempt; test carefully.

   How to test safely:
   1. Before applying, use Tailscale's "dry run"? There's no dry-run for ACLs... but you can check the policy with `tailscale debug` ... hmm. Practical safe testing:
      - Apply G2 (the new grant) only after tightening src; keep G1 as-is or with the drop rule.
      - Test from Alex's iPhone (or a controlled device) — but each connection burns an attempt! So test with minimal connections: e.g., `ssh -p 2222 user@192.168.20.50` — wait, over cellular via NAT64, the iPhone resolves... The point of the 4via6 route is that iOS rewrites IPv4 literals to NAT64 and bypasses Tailscale; with the 4via6 route advertised, iOS uses the tailnet path instead. Testing from the iPhone: open the SSH app, connect once.
      - Use `tailscale ssh`? No — this is a raw TCP service on the subnet route, not Tailscale SSH.
      - Test with a single connection and expect exactly one passphrase attempt; check cryptroot state (e.g., via the NAS's boot log or by checking that it still boots).
      - Verify negative cases: from a member NOT intended to have access (e.g., kids' PC or Steam Deck — but those are members; if you scope src to Alex's iPhone, test from another member and confirm it's denied). Also verify the IPv4 form is denied for non-members... no, all are members. Test: from a device not in the allowed src set, attempt connection → expect failure (and NO passphrase attempt consumed — important! A denied connection never reaches dropbear, so no attempt burned).
      - Check the ACL with `tailscale status` / the admin console; use `tailscale debug prefs`? Not needed. There's `tailscale netcheck`? The useful tool: from a client, `tailscale ssh` doesn't apply. For verifying ACLs, Tailscale has `tailscale status --json` and the admin console shows "ACL" evaluation... Actually there IS a way: `tailscale debug acl`? Hmm. There's `tailscale debug` subcommands like `tailscale debug prefs`, `tailscale debug routes`. For ACL testing, Tailscale has an "ACL checker" in the admin console (the "Test ACLs" feature?) — I recall a "check access" tool. Safest: say "use the admin console's ACL/policy validation and then test from real devices."
      - Also test that G1's broad grant still works (device-to-device between peers) — e.g., ping tailnet peer.
      - Test the drop rule: from a member, attempt to reach the 4via6 SSH host on port 22 or another port → expect failure; attempt on 2222 → allowed (but burns an attempt! So maybe test the non-2222 ports first, and only connect to 2222 once, deliberately).
      - Keep a physical/console path: ensure Alex is physically near the NAS or has local access before testing, so a cryptroot lockout can be recovered (e.g., reset attempts via console). Since each connection burns an attempt and lockout could prevent boot, test with one connection at a time, and know the recovery procedure.
      - Consider using `tailscale`'s ability to check: `ssh -p 2222 ...` from iPhone — but wait, does the iPhone even have SSH? Alex wants to reach it; fine.

   Also worth noting: G1 comment "unchanged intent" — flag that the comment is misleading: the grant covers the 4via6 SSH host on all ports; and note the broader device-to-device intent is broad (all members → all tailnet addrs, all ports) — that's Alex's choice but worth confirming given kids' devices are members.

   Another point: G2 dst includes both forms of the SSH host — good, because clients reach it via different paths (IPv4 direct vs NAT64/4via6). But note that with G1 already covering the 4via6 form on all ports, G2's IPv6 leg is redundant; only the IPv4 leg is new. And actually — wait, should double-check: does the iPhone reach the SSH host via the 4via6 route at all? The setup says "The 4via6 route exists because iOS on IPv6-only 5G rewrites IPv4 literals to carrier NAT64, bypassing Tailscale." So when Alex types 192.168.20.50:2222 in the iPhone's SSH client, iOS rewrites it to the carrier NAT64 address (e.g., 64:ff9b::c0a8:1432) which bypasses Tailscale — that would reach the NAS directly?? No wait — the carrier NAT64 address is on the cellular network, not the tailnet; the NAS isn't reachable there... unless the NAS's LAN is behind the same NAT? Hmm. The point of the 4via6 route: with the 4via6 subnet route advertised, Tailscale clients (including iOS) can reach the subnet via the tailnet using the 4via6 address; iOS rewriting IPv4 literals to carrier NAT64 would bypass Tailscale and fail (or reach something else). With the 4via6 route... hmm, actually how does that help? 

   Let me think: On iOS with IPv6-only 5G (no IPv4 connectivity), when you type an IPv4 address literal like 192.168.20.50, iOS rewrites it to NAT64 form (64:ff9b::c0a8:1432 or similar) and connects via the carrier's NAT64 — bypassing Tailscale entirely. That would fail because the NAS isn't on the carrier network. The fix: advertise the 4via6 route fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128 via Tailscale, so that... hmm, but iOS still rewrites the literal to carrier NAT64 (64:ff9b::c0a8:1432), not to the tailnet's 4via6 form. Unless Alex types the 4via6 address directly? Or unless Tailscale on iOS intercepts and resolves...

   Actually, I think the real mechanics: Tailscale's subnet routes with "4via6" — when a client has both IPv4 subnet route and its 4via6 form, and the client is IPv6-only (carrier NAT64), Tailscale uses the 4via6 form to reach the subnet. The iOS app rewriting IPv4 literals to carrier NAT64 is a known issue; the 4via6 route lets the connection go through Tailscale instead. Perhaps Alex types the 4via6 address directly in his SSH client, or the tailnet's DNS resolves it. Details aside — the given setup says "The 4via6 route exists because iOS on IPv6-only 5G rewrites IPv4 literals to carrier NAT64, bypassing Tailscale" — meaning without the 4via6 route (or with the rewrite), access would bypass Tailscale; with it, iOS can reach the subnet via the tailnet's 4via6 form. So Alex will presumably connect using the 4via6 address or a hostname that resolves to it.

   Anyway — for the review, I don't need to fully resolve this; I should note: G2 covers both forms (good); iOS will use the 4via6 form, which is already covered by G1 on all ports — so G2's 4via6 leg is redundant; and if Alex connects via the 4via6 address, he gets all-port access to that host via G1 regardless of G2. That's a key finding: the "nothing else new opens" goal is undermined by G1's existing coverage of the 4via6 SSH host on all ports.

   Also note: does G1 cover the IPv4 subnet route? No — dst [100.64.0.0/10, fd7a:115c:a1e0::/48] doesn't include 192.168.20.50/32. So on an IPv4-capable client (e.g., laptop), G1 alone does NOT reach the SSH host; G2 adds that. Good — that's the intended new opening.

   Now, over-grants and fixes:
   
   1. G2 src = autogroup:member → every member (incl. kids' PC, Steam Deck) can burn cryptroot passphrase attempts on the pre-boot SSH host. Fix: restrict src to Alex's iPhone (and maybe a small group of trusted devices). E.g., `src: [tag:iphone]` or the device ID. This is the biggest fix.
   
   2. G1 covers the 4via6 SSH host on all ports → any member can reach that host on any port (e.g., 22? whatever's bound) via the 4via6 form. Fix: add a drop rule for the /128 with ip covering everything except tcp:2222 (e.g., ip ["tcp:1-2221", "tcp:2223-65535"] — plus UDP/other protocols? If we want to block all non-TCP too... drop rule ip can include "udp:*" etc. Simpler: since the host is a pre-boot box with dropbear on 2222, deny everything except 2222 by listing ranges; or if your Tailscale version supports it, use ip ["*"] on the drop rule and rely on... no, drop wins → blocks 2222. Use the two-range trick, or deny all non-2222 protocols: ip ["udp:*", "tcp:1-2221", "tcp:2223-65535"].) Alternatively, restructure G1 to not include fd7a:115c:a1e0::/48 — but that breaks IPv6 device-to-device. Or enumerate tailnet peers... no.
   
   Actually — cleaner alternative fix for #2: change G1's dst IPv6 leg from fd7a:115c:a1e0::/48 to a set of the actual tailnet peer addresses? Not maintainable. The drop rule is the right approach. Or simplest honest option: since G1 is "unchanged intent," accept that it already opens all-ports access to the 4via6 SSH host and note it; if Alex wants strict "only tcp:2222," add the drop rule. I'll present both.

   3. G2's 4via6 leg is redundant (G1 covers it) — harmless but misleading; keep for clarity or remove to reduce confusion. Not a security issue per se. Actually keeping it documents intent; fine either way.

   4. NFS export: allows 100.64.0.0/10 → any tailnet device (incl. kids' PC, Steam Deck) can mount/read/write share. That's Alex's stated choice — consistent with G1's all-ports device-to-device grant and with the shared-drive intent. Notes: (a) it's broader than the SSH goal but it's a separate, deliberate control; (b) NFS over Tailscale means the export is only as safe as the tailnet — fine; (c) consider whether kids' devices should write to share (Alex chose shared, so yes); (d) note that the export being /10 means any device with a tailnet address can mount it — including future members you don't know about; if you want tighter control, restrict the export to specific hosts/tags and add an ACL grant for those — but Alex deliberately chose this, so just confirm. Also note: don't confuse the export (server-side) with the ACL (client-side); both must allow traffic. G1 already allows members → NAS tailnet address on all ports, so NFS (2049) flows; the export permits it server-side. Consistent. No change needed for this policy; just flag that the kids' PC and Steam Deck have full read/write to share — intended but worth confirming, and note that this is unchanged by G1/G2.

   5. Testing safely:
      - Pre-test in the admin console / ACL validation (Tailscale shows policy evaluation; there's also `tailscale debug` ... I should be careful about claiming specific commands. There IS a way to test ACLs: Tailscale has an "ACL checker"? I recall the admin console has "Test access" or you can use the API. Safer: say "validate the policy in the admin console (it shows errors and lets you check rules), then test from real devices.")
      - Since each connection burns a cryptroot attempt: do ONE deliberate test connection from Alex's iPhone; expect exactly one attempt consumed; verify boot still succeeds / attempts remaining. Have Alex physically at the NAS or with console access before testing, since lockout could prevent boot.
      - Negative tests first (no passphrase burned): from a non-allowed member (e.g., kids' PC/Steam Deck — if G2 src is scoped to Alex's iPhone) attempt the connection → expect denial; confirm no passphrase attempt consumed (check cryptroot state / boot log). Also test the 4via6 form from a member on port 22 or another port → expect denial via drop rule.
      - Test IPv4 leg: from an IPv4-capable device (Alex's laptop) connect to 192.168.20.50:2222 → allowed (burns one attempt! so maybe skip or do once).
      - Verify G1 still works: ping/tailnet-connect between peers.
      - Use `tailscale status` / `tailscale netcheck`? Not needed. Maybe mention `tailscale ssh` is not applicable (this is raw TCP on a subnet route, not Tailscale SSH).
      - Also verify the 4via6 route is advertised: `tailscale status` shows routes; and from iPhone, confirm the connection goes via tailnet (e.g., check that it's not going over cellular NAT64 — hard to verify directly; can check with a packet capture or by testing that access works while... hmm, simple: if it connects at all on IPv6-only 5G, it went through the tailnet).
      - Important: don't test from multiple devices unnecessarily; each :2222 connection burns an attempt. Budget attempts accordingly (e.g., cryptroot may allow N attempts per boot — check the NAS docs/config).

   Also mention: G1's comment "unchanged intent" is misleading because the /48 now includes a subnet-route address that isn't a tailnet peer — device-to-device intent was for peers; it now silently extends to the 4via6 SSH host on all ports.

   Another subtle point: G1 dst [100.64.0.0/10, fd7a:115c:a1e0::/48] — the tailnet's IPv4 range and IPv6 range. Note that subnet routes (192.168.20.50/32) are NOT in 100.64.0.0/10, so G1 doesn't cover LAN addresses — good; only the 4via6 form leaks in via the /48.

   Also: should G2 include UDP? No — SSH is TCP. ip ["tcp:2222"] is right.

   One more: "nothing else new opens" — also check: does G2 open anything beyond the SSH host? dst is exactly the two forms of that one host. src is all members (broad, but that's the intended grant scope... though for a passphrase-burning service, all members is too broad). So the "nothing else new opens" goal: G2 opens tcp:2222 on the SSH host to ALL members — broader than Alex's ask (his iPhone only). That's the main over-grant in the proposed change itself.

   Also consider: should the SSH host be reachable from the tailnet at all via its LAN IPv4 address? The /32 is a subnet route; fine.

   Also: does G1 already allow members → NAS tailnet address on port 2222? Yes (all ports). So the pre-boot SSH host's tailnet address — wait, does the NAS have a tailnet address? It's a tailnet peer ("nas01"), so yes it has a tailnet address in 100.64.0.0/10 / fd7a:...::/48. G1 allows members → that tailnet address on all ports — including 2222! So if the pre-boot SSH service were also listening on the NAS's tailnet address, it'd be reachable already. But the setup says the SSH is on the subnet route address (192.168.20.50:2222), which is a LAN address, not the tailnet address. So G1 doesn't cover the IPv4 form; G2 adds it. And the 4via6 form leaks via G1's /48. Consistent with my analysis.

   Now let me also double-check the 4via6 address math: fd7a:115c:a1e0:b1a:0:1:c0a8:1432. The last 32 bits: c0a8:1432 → c0=192, a8=168, 16=22, f2=242 → 192.168.20.50. ✓. And it's within fd7a:115c:a1e0::/48? fd7a:115c:a1e0:b1a:... — the /48 covers fd7a:115c:a1e0:XXXX where XXXX is the 4th