Only **homesrv is actually exposed**. Hermes inverted the probe results and mis-applied upstream version numbers to Ubuntu backports.

### Corrected per-host table

| Host | Kernel verdict | Exposed listeners | Evidence |
|---|---|---|---|
| **workstation** 192.168.10.12 / 100.101.1.10 | **Patched** | None exploitable | Ubuntu 26.04 running `7.0.0-43.43-generic` — exactly the Ubuntu resolute fixed build listed for CVE-2026-98432. `ss -Mln`: llama-swap 100.101.1.10:8080, probe: MPTCP negotiated. MPTCP listener exists, but kernel is fixed. nft `ip hdrlength gt 5 drop` present; `br_netfilter` not loaded. |
| **homesrv** 192.168.20.50 / 100.101.1.20 | **Vulnerable** | **gitea *:3000, ntfy 100.101.1.20:8888** | Ubuntu 22.04 `5.15.0-201-generic` < jammy fixed `5.15.0-203.213`. `ss -Mln` lists both as containers on host ports. Probe from 192.168.10.12: gitea MPTCP negotiated (LAN+tailnet), ntfy MPTCP negotiated. Containers share the host kernel — containerisation is not isolation for a kernel TCP bug. nft rule present, but `br_netfilter` NOT loaded, so bridged/container traffic cannot be credited as covered by the prerouting rule. |
| **homesrv** (other listeners) | — | None | tailscaled 443/8443/8444/10000: probe **fell back to plain TCP**. cloudflared *:20241: **not reachable outside its container network**. peerapi: listed in `ss -Mln`, no MPTCP probe evidence — not counted as exposed. |
| **kidspc** (Mint, tailnet) | Unpatched version, not exposed | None | Kernel `7.0.0-42-generic` predates fixed `7.0.0-43.43`, no fixed build in evidence. `ss -Mln`: empty. nft mitigation present. |
| **Steam Deck** (tailnet) | Unpatched version, not exposed | None | Kernel `7.2.7-valve2` < upstream fixed `7.2.10`, no backport in evidence. `ss -Mln`: empty. Has nft, but no rule stated as applied. |
| **nas01** TrueNAS 25.10.7 | Unpatched version, not exposed | None | Kernel `6.12.105` < upstream fixed `6.12.113`. No MPTCP listeners. |
| **UniFi gateway** | Not triggerable | None | 80/443/8443 plain TCP only — CVE requires an MPTCP-enabled listening socket. |

### Corrections to Hermes' draft

1. **"workstation: vulnerable (7.0 < 7.2.10)" — Wrong.** Upstream branch numbers don't override distro backports. Ubuntu fixed this on the 7.0 branch as `7.0.0-43.43`, and workstation is running exactly that build (from -proposed). Patched, despite llama-swap negotiating MPTCP.

2. **"gitea: 0 exposure" — Wrong, exposed.** Probe shows MPTCP negotiated on LAN and tailnet. Kernel `5.15.0-201` is below the `5.15.0-203.213` fix. Being in a container doesn't help; it's the host kernel's TCP stack, on a published host port.

3. **"ntfy: 0 exposure" — Wrong, exposed.** Same reasoning: MPTCP negotiated on 100.101.1.20:8888, vulnerable host kernel, container on host port.

4. **"tailscaled 443/8443/8444/10000: EXPOSED (kernel MPTCP listeners)" — Wrong, not exposed.** Probe shows they **fell back to plain TCP**. Appearing in `ss -Mln` output is not proof of MPTCP negotiation; the probe is. Hermes got gitea/ntfy vs tailscaled exactly backwards.

5. **"kidspc: not checked" — Wrong.** It was checked: `7.0.0-42`, empty `ss -Mln`, mitigation present. Unpatched kernel version, zero listeners.

6. **"Steam Deck: offline, skipped" — Wrong.** It was checked on the tailnet: `7.2.7-valve2`, empty `ss -Mln`. Unpatched version, zero listeners.

7. **"nas01: fine" — Misleading.** Kernel `6.12.105` is below fixed `6.12.113` — vulnerable version, just not triggerable with no MPTCP listeners. "Fine" overstates it.

8. **Omissions:** cloudflared 20241 is not externally reachable; UniFi is plain TCP only. Neither is exposed. Also, Hermes ignored the `br_netfilter` gap: the existing nft rule on homesrv shouldn't be counted as mitigation for the container services.

### Patch / mitigation order

1. **homesrv — immediate.** Upgrade to `5.15.0-203.213`+ and reboot. Until then treat gitea:3000 and ntfy:8888 as remotely exploitable from LAN/tailnet. Interim: restrict/firewall those ports or disable MPTCP on them, and verify nft coverage for container traffic (the current prerouting rule with `br_netfilter` unloaded doesn't cover it). Re-run `ss -Mln` + MPTCP probe after patching.

2. **kidspc — next routine update.** Move off `7.0.0-42` to a fixed build; keep the nft rule; re-check for listeners.

3. **Steam Deck / nas01 — vendor-paced, low urgency.** No listeners. Take Valve ≥7.2.10 and TrueNAS ≥6.12.113 kernels when available; monitor for new MPTCP listeners.

4. **workstation — verify only.** Already on the fixed build. Confirm the -proposed kernel survives reboot/upgrade and isn't downgraded.

5. **No action:** UniFi, tailscaled ports, cloudflared (external).