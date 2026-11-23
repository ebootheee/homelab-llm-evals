# Corrected exposure map — CVE-2026-98432

## Per-host table

| Host | Kernel verdict | Exposed listeners (per probe) | Evidence / notes |
|---|---|---|---|
| **workstation** | **NOT vulnerable** — 7.0.0-43.43 is Ubuntu's fixed resolute build (backport), not "7.0 < 7.2.10" | llama-swap 100.101.1.10:8080 — MPTCP negotiated, but kernel fixed → **not exposed** | `ss -Mln` + probe from workstation itself; installed from -proposed = the fixed build |
| **homesrv** | **VULNERABLE** — 5.15.0-201 < jammy fixed 5.15.0-203.213 | **gitea \*:3000** (LAN + tailnet) — MPTCP negotiated → EXPOSED; **ntfy 100.101.1.20:8888** (tailnet) — MPTCP negotiated → EXPOSED; cloudflared \*:20241 — internal-only, probe confirms unreachable from outside container network → not externally exposed; tailscaled 443/8443/8444/10000 — plain TCP fallback → **not exposed**; peerapi — **untested** | `ss -Mln` + probe; br_netfilter NOT loaded → prerouting rule does not see bridged/container traffic |
| **kidspc** | **VULNERABLE (unpatched)** — 7.0.0-42 < fixed 7.0.0-43.43 | **none** — `ss -Mln` empty | `ss -Mln`; mitigation present but unproven for this CVE |
| **Steam Deck** | **VULNERABLE (unpatched)** — 7.2.7 < upstream fix 7.2.10 | **none** — `ss -Mln` empty | On tailnet, not offline; "has nft" but rule set unknown — do not assume the prerouting mitigation is in place |
| **nas01** | **VULNERABLE (unpatched)** — 6.12.105 < upstream fix 6.12.113 | **none** — no MPTCP listeners | TrueNAS 25.10.7; not "fine" — unexposed but unpatched |
| **UniFi gateway** | Unknown/not affected | **none** — 80/443/8443 plain TCP, no MPTCP indicated | Not mentioned in draft; include for completeness |

## Corrections to Hermes' draft

1. **workstation "vulnerable (7.0 < 7.2.10)" → NOT vulnerable.** The comparison used upstream version numbers and ignored Ubuntu's backport. Resolute's fixed build is exactly 7.0.0-43.43, which is what's installed. llama-swap negotiates MPTCP, but the fixed kernel closes the hole.
2. **gitea "0 exposure" → EXPOSED.** Probe shows MPTCP negotiated on LAN and tailnet; homesrv runs 5.15.0-201, below jammy's fixed 5.15.0-203.213. This is the widest exposure in the fleet (LAN + tailnet).
3. **ntfy "0 exposure" → EXPOSED.** Probe shows MPTCP negotiated; same unpatched kernel. Reachable via tailnet only, but still remotely triggerable.
4. **tailscaled "EXPOSED (kernel MPTCP listeners)" → NOT exposed via this CVE.** `ss -Mln` listing alone does not establish exposure. The probe fell back to plain TCP on all four ports — MPTCP was never negotiated, so the vulnerable path isn't exercised. peerapi is untested (not probed) — flag as unknown, do not clear it.
5. **kidspc "not checked" → CHECKED and currently clean.** `ss -Mln` is empty → no exposed listeners; kernel 7.0.0-42 is unpatched (< 7.0.0-43.43); mitigation present but not proven to block this CVE.
6. **Steam Deck "offline, skipped" → NOT offline/skipped.** It is on the tailnet with `ss -Mln` empty (no exposed listeners) and kernel 7.2.7 < 7.2.10 → unpatched. "Has nft" ≠ mitigation in place; rule set not evidenced.
7. **nas01 "fine" → NOT fine in patch state.** No MPTCP listeners → not exposed, but kernel 6.12.105 < 6.12.113 → unpatched. "Fine" conflates exposure with patch status.
8. **cloudflared — missing from draft entirely.** Internal-only exposure (container network); probe confirms unreachable externally. Not an external risk, but lives on homesrv's unpatched kernel — resolve by patching homesrv.
9. **UniFi gateway — missing from draft entirely.** Plain TCP on 80/443/8443, no MPTCP indicated → not affected by this CVE.

## Mitigation caveat (applies to workstation/homesrv/kidspc)

The `ip hdrlength gt 5 drop` prerouting rule drops IPv4 packets with IP options. It is **not evidenced to block this CVE's trigger path**, and **br_netfilter is not loaded on workstation or homesrv** — so the rule does not see bridged/forwarded traffic, i.e., it does not protect homesrv's containerized listeners (gitea, ntfy, cloudflared). Treat it as defense-in-depth only; do not rely on it as a substitute for patching.

## Patch / mitigation order

1. **homesrv** — apply jammy fixed build 5.15.0-203.213. Highest priority: gitea (LAN + tailnet) and ntfy (tailnet) are exposed, and the nft mitigation does not cover container traffic.
2. **kidspc** — update to 7.0.0-43.43+ (or newer fixed build). No listeners, but unpatched kernel; keep/verify the nft rule as defense-in-depth.
3. **workstation** — confirm 7.0.0-43.43 is in place (it is); no patch needed. Keep mitigation as backstop. llama-swap is tailnet-only and kernel-fixed → no action beyond monitoring.
4. **Steam Deck** — update to 7.2.10+ (valve kernel; check vendor backports). No listeners, but unpatched; lower priority.
5. **nas01** — TrueNAS/kernel 6.12.113+ when available. No MPTCP listeners → lowest priority.
6. **UniFi gateway** — no action (plain TCP, not affected).

**Bottom line:** the only actually-exposed hosts are homesrv's gitea and ntfy (both on an unpatched 5.15 kernel). Everything else is either fixed, listenerless, or internal-only — but kidspc, Steam Deck and nas01 all carry unpatched kernels and should be patched in that order even though none currently expose a listener.