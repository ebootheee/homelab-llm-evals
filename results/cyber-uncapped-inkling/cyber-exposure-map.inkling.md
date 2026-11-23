# Corrected exposure map — CVE-2026-98432

## Per-host table

| Host | Kernel verdict | Exposed listeners (MPTCP + reachable + vulnerable kernel) | Evidence |
|---|---|---|---|
| **homesrv** (22.04, 5.15.0-201) | **Vulnerable** — below fixed build 5.15.0-203.213 | **gitea *:3000** (LAN + tailnet) and **ntfy 100.101.1.20:8888** (tailnet) | Probe: both negotiate MPTCP on LAN/tailnet; kernel unfixed. cloudflared :20241 not reachable outside container network (unverified, limited scope). tailscaled 443/8443/8444/10000 fell back to plain TCP → **not** exposed. peerapi — never probed, unverified. |
| **workstation** (26.04, 7.0.0-43.43) | **Patched** — matches Ubuntu fixed build exactly | None | llama-swap 100.101.1.10:8080 negotiates MPTCP, but the kernel is the fixed build; no exposure via this CVE. Note: installed from -proposed — verify it sticks and move to stable if possible. |
| **kidspc** (Mint, 7.0.0-42) | **Vulnerable** — below Ubuntu's fixed 7.0.0-43.43 mapping | None | `ss -Mln` empty; no MPTCP listeners. Kernel still unpatched. |
| **Steam Deck** (7.2.7-valve2) | **Vulnerable** — below upstream fix 7.2.10 | None | `ss -Mln` empty; on tailnet per evidence. Not exposed via this CVE, but not "skipped". |
| **nas01** (TrueNAS 25.10.7, 6.12.105) | **Vulnerable** — below upstream fix 6.12.113 | None | No MPTCP listeners; no exposure via this CVE, but kernel unpatched. |
| **UniFi gateway** | Unknown/unverifiable | None via this CVE | Plain TCP on 80/443/8443; no MPTCP listeners → not triggerable regardless of kernel. |

## Corrections to Hermes' draft

1. **"gitea: 0 exposure" → WRONG.** gitea is a container host port (*:3000), the probe shows MPTCP negotiation on LAN and tailnet, and homesrv runs 5.15.0-201 — below the fixed 5.15.0-203.213. This is the one genuinely exposed service in the fleet.
2. **"ntfy: 0 exposure" → WRONG.** ntfy (100.101.1.20:8888) negotiates MPTCP on the tailnet, same vulnerable kernel. Tailnet peers are remote attackers for this purpose.
3. **"tailscaled 443/8443/8444/10000: EXPOSED (kernel MPTCP listeners)" → WRONG.** The probe shows these fell back to plain TCP — that is exactly the negative control for this CVE. `ss -Mln` listing a socket does not mean it negotiates MPTCP; the empirical probe is authoritative. Not exposed via this CVE.
4. **"kidspc: not checked" → WRONG/incomplete.** It was checked — empty listener list, but kernel 7.0.0-42 is below the fixed build. No exposure, but unpatched.
5. **"Steam Deck: offline, skipped" → WRONG.** Evidence says it's on the tailnet. Not exposed via this CVE (no MPTCP listeners), but the kernel (7.2.7-valve2 < 7.2.10) is unfixed and it must not be skipped.
6. **"workstation: vulnerable (7.0 < 7.2.10)" → WRONG/misapplied.** The upstream version list (7.2.10+) does not govern Ubuntu's backport; resolute's fixed build is 7.0.0-43.43 and workstation runs exactly that. Not vulnerable per the provided mapping.
7. **"nas01: fine" → WRONG/incomplete.** Kernel 6.12.105 < 6.12.113 is unpatched; only the absence of MPTCP listeners prevents exposure via this CVE. Not "fine" — flag for patching.
8. **The mitigation is ineffective, and Hermes treated it as a control.** `ip hdrlength gt 5 drop` drops IPv4 packets carrying header *options*; MPTCP negotiation uses TCP options (MP_CAPABLE/MP_JOIN), so this rule does not block the attack at all. Additionally, br_netfilter is NOT loaded on workstation or homesrv, meaning host prerouting rules never see bridged container traffic — on homesrv the rule wouldn't apply to gitea/ntfy even if it were effective. Do not rely on it as mitigation for this CVE.

## Patch / mitigation order

1. **homesrv (critical).** Patch jammy to ≥5.15.0-203.213. Until patched, restrict access to the exposed listeners — firewall gitea *:3000 and ntfy :8888 to known source IPs/interfaces (the existing nft rule will not help), or disable MPTCP on those sockets if it isn't needed. This is the only host with live exposure.
2. **kidspc.** Patch to ≥7.0.0-43.43 equivalent (Mint kernel). No listeners → no exposure, but unpatched kernel on a tailnet host.
3. **Steam Deck.** Update valve kernel to a build containing the 7.2.10 fix; confirm Valve's fixed build since it's a fork — upstream versioning is only a proxy.
4. **nas01.** Apply TrueNAS update with kernel ≥6.12.113. No MPTCP listeners → lower priority, but do not call it "fine" yet.
5. **workstation.** Already on the fixed build; verify the -proposed install persists and move to stable if available. No exposure via this CVE.
6. **UniFi gateway.** Plain TCP, no MPTCP listeners — no action needed for this CVE; monitor.

Bottom line: exactly one host is exposed (homesrv, gitea + ntfy), one host is patched but on a proposed build (workstation), and three hosts are unpatched-but-not-exposed (kidspc, Steam Deck, nas01). The `ip hdrlength` rule should be treated as decorative for this CVE, not a control.