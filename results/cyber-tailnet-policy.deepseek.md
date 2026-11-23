I’d not approve this as-is. The two grants are additive allow rules, so G1’s broad “all ports to all 4via6 addresses” makes G2 mostly redundant and opens far more than the intended `homesrv:2222` path.

## What each grant actually permits

### G1
```text
src autogroup:member
dst [100.64.0.0/10, fd7a:115c:a1e0::/48]
ip ["*"]
```

This permits every tailnet member device to reach:

- every Tailscale IPv4 address in `100.64.0.0/10`,
- every address under `fd7a:115c:a1e0::/48`, which includes Tailscale IPv6 device addresses **and** the 4via6 subnet-mapped addresses,
- on **all protocols and all ports**.

So G1 allows all member devices to reach the NAS’s 4via6 form of `192.168.20.50` on every port, including TCP 2222. It also allows all member devices to reach any other 4via6 destination on all ports. That is much broader than “device-to-device, unchanged intent” if the intent was only tailnet device-to-device traffic.

### G2
```text
src autogroup:member
dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128]
ip ["tcp:2222"]
```

This permits every tailnet member device to reach:

- `192.168.20.50` on TCP 2222,
- the specific 4via6 address `fd7a:115c:a1e0:b1a:0:1:c0a8:1432` on TCP 2222.

So G2 is not restricted to Alex’s iPhone. It is open to all member devices. Also, because G1 already allows all ports to the 4via6 address, G2’s TCP 2222 restriction is not actually restricting anything for that 4via6 destination. Grants are additive; G1’s broad allow remains.

## Over-grants and fixes

### G1 over-grant
G1 includes `fd7a:115c:a1e0::/48`, which contains the 4via6 prefix `fd7a:115c:a1e0:b1a:0:1::/96`. That opens all ports/protocols to all 4via6 destinations, including `homesrv`.

Fix options:

1. If G1 is meant to preserve ordinary device-to-device access, narrow its destination to actual tailnet device addresses only, not subnet-routed 4via6 addresses. Use tag-based destinations for devices, e.g.:
   ```json
   "dst": ["tag:tailnet-device"]
   ```
   or otherwise split the IPv6 range so it excludes the 4via6 prefix. Do not use a broad `fd7a:115c:a1e0::/48` destination for device-to-device if 4via6 routes are in scope.

2. If G1 must remain broad because it is truly the existing unchanged policy, then explicitly accept that it already permits all-port access to 4via6 destinations. In that case, G2 cannot enforce “only TCP 2222” unless you remove the broad 4via6 allow from G1.

### G2 over-grant
G2 uses `src autogroup:member`, so it permits all member devices, not just Alex’s iPhone.

Fix: restrict the source to a tag applied only to Alex’s iPhone, e.g.:
```json
"src": ["tag:alex-iphone"]
```
Apply `tag:alex-iphone` only to the iPhone. Avoid `user:alex` unless Alex has only that one device, because a user-based source would include all of Alex’s devices.

So the tightened intent should look conceptually like:
- G1: device-to-device only, excluding 4via6 subnet routes.
- G2: `src tag:alex-iphone` → `dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128]`, `ip ["tcp:2222"]`.

Also note: for IPv6-only 5G, the iPhone may need to use the 4via6 IPv6 literal explicitly. If it uses the IPv4 literal `192.168.20.50`, iOS may NAT64 it and bypass Tailscale. Test with the 4via6 address.

## NFS export `share` comments

The NAS NFS export `share` allows `100.64.0.0/10`. That means every tailnet device with a Tailscale IPv4 address can access that export, subject to Tailscale ACLs also allowing NFS traffic. This matches Alex’s stated intent that `share` is shared with every tailnet device, including the kids’ PC and Steam Deck. It is broad but intentional.

Caveats:

- It is IPv4-only. If clients mount via Tailscale IPv6 or 4via6 IPv6 addresses, the NFS export may deny unless IPv6 ranges are also allowed.
- It does not by itself restrict which devices can mount; it relies on Tailscale ACLs to gate NFS access. If G1 allows all ports to all devices, NFS is effectively open to all member devices.
- If any tailnet device is compromised, it can reach `share` unless ACLs restrict NFS port 2049 to intended devices. Since Alex intentionally shares it broadly, this may be acceptable, but it is a security tradeoff.

The NFS export is separate from the SSH dropbear policy. It does not affect the `:2222` SSH path directly, but it is part of the overall tailnet exposure.

## Testing safely

Because each SSH connection to `:2222` consumes one cryptroot passphrase attempt, even with empty stdin, avoid repeated SSH attempts.

Suggested safe test sequence:

1. **Test route/policy without SSH authentication**
   - From the iPhone over cellular, use `tailscale ping` to the 4via6 address to verify Tailscale path.
   - Use a TCP-only probe such as `nc -vz` or `nmap` to the 4via6 address on port 2222. This tests TCP reachability without starting an SSH password attempt.
   - Example IPv6 probe:
     ```sh
     nc -vz -6 fd7a:115c:a1e0:b1a:0:1:c0a8:1432 2222
     ```
     or from a tool that supports IPv6.

2. **Test negative cases**
   - From a non-iPhone member device, e.g. the kids’ PC or Steam Deck, try the same TCP probe to the 4via6 address on 2222. After the fix, it should fail because G2 is restricted to `tag:alex-iphone` and G1 no longer allows all ports to 4via6.
   - Try TCP 2223 or another port to confirm G1 no longer opens all ports to 4via6. It should fail.

3. **Test the SSH path with exactly one attempt**
   - Only after TCP reachability is confirmed, make a single SSH attempt with a strict one-prompt setting:
     ```sh
     ssh -p 2222 \
       -o ConnectTimeout=10 \
       -o NumberOfPasswordPrompts=1 \
       -o PreferredAuthentications=password \
       -o PubkeyAuthentication=no \
       user@[fd7a:115c:a1e0:b1a:0:1:c0a8:1432]
     ```
     Use the correct cryptroot passphrase if you are testing the unlock. Do not retry repeatedly.
   - If you do not know the passphrase, do not perform the SSH step; rely on TCP-only reachability and policy review.

4. **Check from the iPhone specifically**
   - Ensure the iPhone uses the 4via6 IPv6 literal, not the IPv4 literal, when on IPv6-only 5G. The IPv4 literal may be NAT64-rewritten and bypass Tailscale.

5. **Avoid parallel SSH attempts**
   - Do not run multiple SSH clients or scripts that automatically retry. Set `NumberOfPasswordPrompts=1` and a short timeout. If a connection consumes an attempt, treat it as a scarce resource.

Overall: G2’s destination is correct, but its source is too broad. G1’s `fd7a:115c:a1e0::/48` destination is the main over-grant because it includes 4via6 subnet routes and permits all ports/protocols to them. Tighten G1 to exclude 4via6, and restrict G2’s source to a tag applied only to Alex’s iPhone.