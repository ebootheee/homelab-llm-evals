# CVE-2026-98432 — Corrected Exposure Map

## Per-host table

| Host | Kernel | Fix status | MPTCP listeners (probe) | Verdict |
|---|---|---|---|---|
| **homesrv** | 5.15.0-201-generic (jammy) | **Not fixed** — jammy fix is 5.15.0-203.213 | gitea *:3000 → MPTCP negotiated (LAN + tailnet); ntfy 100.101.1.20:8888 → MPTCP negotiated; cloudflared 20241 → **unverified** (not reachable outside container net); tailscaled 443/8443/8444/10000 → plain TCP fallback; peerapi → **unverified** | **EXPOSED: gitea:3000, ntfy:8888** |
| **workstation** | 7.0.0-43.43-generic (resolute, -proposed) | **Fixed** — matches Ubuntu fixed build resolute 7.0.0-43.43 | llama-swap 100.101.1.10:8080 → MPTCP negotiated | Not exposed (patched kernel); verify running kernel & consider stable build |
| **kidspc** | 7.0.0-42-generic | **Not fixed** — resolute fix is 7.0.0-43.43 | none (`ss -Mln` empty) | Not exposed; patch anyway |
| **Steam Deck** | 7.2.7-valve2 | **Not fixed** — upstream fix is 7.2.10 | none (`ss -Mln` empty) | Not exposed; patch when online |
| **nas01** | 6.12.105 (TrueNAS 25.10.7) | **Not fixed** — upstream fix is 6.12.113 | none (no MPTCP listeners) | Not exposed; patch via TrueNAS update |
| **UniFi gateway** | unknown | unknown | plain TCP only (80/443/8443) | Not exposed for this CVE |

## Corrections to Hermes' draft

1. **"gitea: 0 exposure" → WRONG.** Probe confirmed MPTCP negotiation on homesrv:3000 over both LAN and tailnet, and the kernel (5.15.0-201) predates the jammy fix (5.15.0-203.213). Exposed.
2. **"ntfy: 0 exposure" → WRONG.** Probe confirmed MPTCP negotiation on 100.101.1.20:8888, same vulnerable kernel. Exposed (tailnet-only listener, but still remotely triggerable over the tailnet).
3. **"tailscaled 443/8443/8444/10000: EXPOSED (kernel MPTCP listeners)" → WRONG.** The probe fell back to plain TCP on all four ports — no MPTCP negotiation, so no exposure despite the vulnerable kernel. (Tailscale Serve ports are not MPTCP-enabled here.)
4. **"kidspc: not checked" → CHECKED; not exposed.** `ss -Mln` is empty → no listening socket with MPTCP enabled. Kernel is below the fixed resolute build, so it still needs patching, but there is no attack surface today.
5. **"Steam Deck: offline, skipped" → CHECKED; not exposed.** `ss -Mln` is empty despite kernel 7.2.7-valve2 being below upstream fix 7.2.10. Patch when online; the "has nft" detail is unverified — no rule content was provided, so don't count it as mitigation.
6. **"workstation: vulnerable (7.0 < 7.2.10)" → WRONG.** Ubuntu backports fixes per release; the resolute fixed build is 7.0.0-43.43 and workstation runs exactly that string. The upstream 7.2.10 comparison does not apply. llama-swap negotiated MPTCP, but the kernel is patched → not exposed. Caveat: it was installed from `-proposed` — confirm with `uname -r` and move to stable once available.
7. **"nas01: fine" → PARTIALLY WRONG.** Kernel 6.12.105 < upstream fix 6.12.113, so it is unpatched by versioning. Not exposed today (no MPTCP listeners), but "fine" overstates it — schedule the TrueNAS update.
8. **Missing from draft:** UniFi gateway (plain TCP only → not exposed, no action needed for this CVE); homesrv's cloudflared:20241 and tailscaled peerapi (unverified — cloudflared is unreachable outside its container network and peerapi port was never probed; do not claim either is safe).

## Mitigation status — the existing nft rule does NOT cover the exposed listeners

- `ip hdrlength gt 5 drop` drops packets carrying **IP options** (IHL > 5). MPTCP negotiates via **TCP options** (MP_CAPABLE), not IP options — this rule does not block the attack path. Do not count it as mitigation for this CVE.
- `br_netfilter` is **not loaded** on workstation or homesrv, so host prerouting rules do not see bridged container traffic. gitea and ntfy are containers — even if the rule were effective against the attack, it would not apply to them. The exposed listeners are effectively unmitigated until patched or access is restricted at the container/host-firewall level.

## Patch / mitigation order

1. **homesrv → 5.15.0-203.213** (first; only host with confirmed exposure). Until patched: restrict gitea:3000 to tailnet-only or otherwise firewall it — host prerouting rules won't see container traffic without br_netfilter, so use docker/host-level filtering, and accept that ntfy:8888 is tailnet-exposed meanwhile.
2. **kidspc → 7.0.0-43.43** (no listeners, but unpatched kernel; cheap to fix).
3. **workstation** — verify running kernel is actually 7.0.0-43.43 and move from `-proposed` to the stable build (already at fixed version; no exposure).
4. **nas01 → TrueNAS update with kernel ≥ 6.12.113** (no exposure, unpatched).
5. **Steam Deck → 7.2.10+ when online** (no listeners, unpatched).
6. **UniFi gateway** — no action for this CVE; plain TCP only. Re-check if MPTCP is ever enabled.

Bottom line: the draft inverted workstation and tailscaled, missed gitea and ntfy entirely, and left kidspc/Steam Deck/nas01 unverified. Only homesrv is actually exposed (gitea:3000 and ntfy:8888), and the existing nft rule plus missing br_netfilter mean it is currently unmitigated.