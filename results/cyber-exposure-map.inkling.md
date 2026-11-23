# Corrected Exposure Map

## Per-host table

| Host | Kernel verdict | Exposed listeners (per evidence) | Notes |
|---|---|---|---|
| **workstation** (26.04, tailnet 100.101.1.10) | **FIXED** — 7.0.0-43.43 is the fixed Ubuntu build for resolute (backport of upstream fix; installed from -proposed) | **None.** llama-swap on 100.101.1.10:8080 negotiates MPTCP, but the kernel patched it | Draft wrongly called this vulnerable on "7.0 < 7.2.10" — that's the *upstream* versioning; Ubuntu backports fixes into 7.0.0-43.43. Also note: running -proposed is itself a risk; confirm the build is actually GA-equivalent before trusting it as "fixed" long-term |
| **homesrv** (22.04, tailnet 100.101.1.20) | **VULNERABLE** — 5.15.0-201 < jammy fix 5.15.0-203.213 | **gitea *:3000** (container, host port) — MPTCP negotiated on LAN **and** tailnet → exposed via two paths; **ntfy 100.101.1.20:8888** (container) — MPTCP negotiated → exposed | tailscaled 443/8443/8444/10000 = probe fell back to plain TCP → **not MPTCP listeners, not exposed**. peerapi = **not probed** — unverified. cloudflared 20241 = inside container network only, unreachable from outside → not externally exposed; internal exposure unverified |
| **kidspc** (Mint, tailnet) | **VULNERABLE** — 7.0.0-42 < fix build 7.0.0-43.43 | **None** — `ss -Mln` empty | Kernel is behind the fix but there is no MPTCP listener to attack; mitigation present (nft prerouting) |
| **Steam Deck** (tailnet) | **VULNERABLE** — 7.2.7-valve2 < upstream fix 7.2.10 | **None** — `ss -Mln` empty | Not offline; it's on the tailnet and was checked. Has nft but no specific mitigation rule is evidenced |
| **nas01** (TrueNAS 25.10.7) | **VULNERABLE** — 6.12.105 < upstream fix 6.12.113 | **None** — no MPTCP listeners | Draft's "fine" conflated "no exposure" with "patched"; kernel is behind the fix |
| **UniFi gateway** | Not assessed | Not assessed | Plain TCP 80/443/8443, no MPTCP probe, different platform — out of scope of this evidence |

## Corrections to Hermes' draft

1. **gitea: "0 exposure" → EXPOSED.** Vulnerable kernel (5.15.0-201) + probe confirms MPTCP negotiated on LAN and tailnet. Two attack paths, not zero.
2. **ntfy: "0 exposure" → EXPOSED.** Same kernel; probe confirms MPTCP negotiated on the tailnet listener.
3. **tailscaled 443/8443/8444/10000: "EXPOSED (kernel MPTCP listeners)" → NOT exposed.** The probe fell back to plain TCP for these — they are not MPTCP-enabled listening sockets, so the CVE's trigger condition is not met. peerapi remains unverified (no probe result).
4. **kidspc: "not checked" → checked; not exposed, but kernel unpatched.** `ss -Mln` was empty — no listeners to attack — yet 7.0.0-42 predates the fix. Patch anyway.
5. **Steam Deck: "offline, skipped" → wrong on both counts.** It's on the tailnet and was checked; `ss -Mln` empty → not exposed; but 7.2.7 < 7.2.10 means the kernel is vulnerable. Patch when available.
6. **workstation: "vulnerable (7.0 < 7.2.10)" → fixed.** Ubuntu backports the fix into 7.0.0-43.43; the upstream version cutoff does not apply to Ubuntu builds. No exposure.
7. **nas01: "fine" → not exposed, but kernel unpatched.** 6.12.105 < 6.12.113; no MPTCP listeners means no current exposure, but it is not a patched host.

## Mitigation caveat (applies to workstation / homesrv / kidspc)

The nft prerouting rule `ip hdrlength gt 5 drop` only drops IPv4 packets with header length > 20 bytes (IP options present). It does **not** disable MPTCP or patch the UAF — treat it as narrow, unverified defense-in-depth, not a fix. Additionally, **br_netfilter is NOT loaded on workstation or homesrv**: any traffic traversing a bridge (container-internal paths, bridged LAN) bypasses netfilter hooks entirely, so the prerouting filter does not cover those paths. On homesrv this matters for the containerized gitea/ntfy — host-facing published-port traffic should still hit PREROUTING, but verify empirically (e.g., send a crafted IP-options packet from an untrusted host and confirm the drop) before relying on it.

## Patch / mitigation order

1. **homesrv** — highest priority: vulnerable kernel + two exposed MPTCP listeners (LAN and tailnet paths). Update to jammy 5.15.0-203.213 or later; until patched, restrict gitea/ntfy exposure (Tailscale ACLs / firewall) and empirically verify the mitigation covers container paths given br_netfilter is off.
2. **kidspc** — vulnerable kernel, no listeners; patch 7.0.0-42 → 43+ (or GA build).
3. **Steam Deck** — vulnerable kernel, no listeners; patch to ≥ 7.2.10 when available.
4. **nas01** — vulnerable kernel, no listeners; apply TrueNAS update carrying 6.12.113+.
5. **workstation** — already fixed (7.0.0-43.43); keep mitigation as defense-in-depth; move off -proposed to the GA build and confirm the fix is present. No exposure.
6. **UniFi gateway** — not assessable from this evidence; verify separately if it runs a Linux MPTCP stack.

Bottom line: only **homesrv** has live, probe-confirmed exposure (gitea and ntfy). Every other host is either patched or exposed-in-kernel-but-not-attackable due to absent MPTCP listeners — but none of those kernels should be left unpatched.