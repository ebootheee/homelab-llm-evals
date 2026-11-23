Here’s the corrected exposure map and patch/mitigation order.

## Corrected per-host table

| Host | Kernel verdict | Exposed listeners | Evidence / notes |
|---|---|---|---|
| **workstation** (192.168.10.12 / 100.101.1.10) | **Fixed** — Ubuntu 26.04 `7.0.0-43.43-generic` is the Ubuntu fixed build (`7.0.0-43.43`). | **None vulnerable.** `llama-swap` on `100.101.1.10:8080` negotiated MPTCP, but the kernel is fixed. | Draft wrongly called it vulnerable by comparing only to upstream `7.2.10`. Ubuntu backported the fix in `7.0.0-43.43`. Mitigation present, but not needed for this CVE. |
| **homesrv** (192.168.20.50 / 100.101.1.20) | **Vulnerable** — `5.15.0-201-generic` is below the Ubuntu fixed build `5.15.0-203.213` and below upstream `5.15.223`. | **Exposed:** `gitea` `*:3000` (container host port) and `ntfy` `100.101.1.20:8888` (container). Both negotiated MPTCP on LAN and tailnet. | `cloudflared` `*:20241` is inside its container network only; MPTCP probe was unreachable externally, so it is not externally exposed (verify internally if container-network threat model applies). `tailscaled` 443/8443/8444/10000 fell back to plain TCP, so they are **not** MPTCP listeners. The nft rule `ip hdrlength gt 5 drop` did not prevent MPTCP negotiation on the tested paths; `br_netfilter` is not loaded, so container/bridged paths may bypass host netfilter. |
| **kidspc** (tailnet) | **Vulnerable unless Mint/Ubuntu backport is present** — `7.0.0-42-generic` is below the Ubuntu fixed build `7.0.0-43.43` and below upstream `7.2.10`. | **None.** `ss -Mln` is empty. | Draft said “not checked”; evidence shows it was checked and has no MPTCP listeners. Mitigation present, but no listener means no CVE exposure. |
| **Steam Deck** (tailnet) | **Vulnerable unless Valve backported the fix** — `7.2.7-valve2` is below upstream `7.2.10`. | **None.** `ss -Mln` is empty. | Draft said “offline, skipped”; evidence says it is on tailnet and `ss -Mln` is empty. Has nft, but no MPTCP listener. |
| **nas01** | **Vulnerable unless TrueNAS backported the fix** — `6.12.105` is below upstream `6.12.113`. | **None.** No MPTCP listeners. | Draft said “fine”; kernel is not “fixed” by version, but there is no MPTCP listener, so exposure is 0. |
| **UniFi gateway** | **Kernel unknown/not specified in evidence.** | **None.** `80/443/8443` are plain TCP. | Not in draft. No evidence of an MPTCP listener; plain TCP listeners do not meet the CVE condition. |

### Exposure summary
- **Vulnerable + externally reachable MPTCP listeners:** only **homesrv**: `gitea:3000` and `ntfy:8888`.
- **Fixed kernel with MPTCP listener:** **workstation** (`llama-swap:8080`) — not vulnerable.
- **Vulnerable kernels but no MPTCP listeners:** **kidspc**, **Steam Deck**, **nas01** — exposure 0.
- **Plain TCP / non-MPTCP:** **homesrv tailscaled ports**, **UniFi gateway** — not exposed to this CVE.
- **Internal-only / unknown MPTCP:** **homesrv cloudflared:20241** — not externally exposed; verify internally if container-network reachability matters.

## Corrections to Hermes’ draft

1. **“gitea: 0 exposure” → gitea is exposed.**
   - Reason: the probe shows MPTCP negotiated on `homesrv:3000` from both LAN and tailnet. `homesrv` runs vulnerable `5.15.0-201-generic`, not the fixed `5.15.0-203.213`. The nft mitigation did not stop MPTCP negotiation.

2. **“ntfy: 0 exposure” → ntfy is exposed.**
   - Reason: MPTCP negotiated on `100.101.1.20:8888`; same vulnerable kernel on `homesrv`. Mitigation ineffective on the tested path.

3. **“tailscaled 443/8443/8444/10000: EXPOSED (kernel MPTCP listeners)” → not exposed.**
   - Reason: the probe explicitly says these tailscaled ports **fell back to plain TCP**. The CVE requires a socket listening with MPTCP enabled; plain TCP fallback does not meet that condition.

4. **“kidspc: not checked” → checked; vulnerable kernel but no exposure.**
   - Reason: evidence includes `ss -Mln` as empty. Kernel `7.0.0-42-generic` is below fixed builds/upstream thresholds, but no MPTCP listener exists.

5. **“Steam Deck: offline, skipped” → not offline; checked; no exposure.**
   - Reason: evidence says it is on tailnet and `ss -Mln` is empty. Kernel `7.2.7-valve2` is below upstream `7.2.10`, but no MPTCP listener exists.

6. **“workstation: vulnerable (7.0 < 7.2.10)” → fixed.**
   - Reason: `7.0.0-43.43-generic` is the Ubuntu 26.04/resolute fixed build. Comparing only to upstream `7.2.10` misses the Ubuntu backport. It has an MPTCP listener (`llama-swap:8080`), but the kernel is fixed.

7. **“nas01: fine” → kernel vulnerable but no exposure.**
   - Reason: `6.12.105` is below upstream fixed `6.12.113`; however, evidence says no MPTCP listeners, so exposure is 0. “Fine” should mean “no exposure,” not “fixed kernel.”

8. **Omitted hosts/listeners:** UniFi gateway and `cloudflared:20241` should be included.
   - UniFi: plain TCP only, no MPTCP listener evidence → not exposed.
   - cloudflared: inside container network only; external MPTCP probe unreachable → not externally exposed; verify internally if needed.

## Patch / mitigation order

1. **homesrv — highest priority.**
   - Patch from `5.15.0-201-generic` to `5.15.0-203.213` or later (Ubuntu jammy fixed build; upstream fixed `5.15.223`).
   - Until patched, restrict or disable MPTCP on the exposed listeners:
     - `gitea:3000`
     - `ntfy:100.101.1.20:8888`
   - Do not rely on `ip hdrlength gt 5 drop` as an MPTCP mitigation; evidence shows MPTCP still negotiated. Also account for `br_netfilter` not loaded, which weakens host-netfilter coverage for container/bridged paths.
   - Verify `cloudflared:20241` internally; if it is MPTCP-enabled and reachable from other containers, treat it as exposed internally and patch/restrict accordingly.

2. **workstation — already fixed; no CVE patch needed.**
   - Confirm `7.0.0-43.43-generic` remains installed and that the `-proposed` package is the fixed build. The MPTCP listener `llama-swap:8080` is not vulnerable on this kernel.

3. **kidspc — medium/low priority.**
   - Kernel `7.0.0-42-generic` is vulnerable unless Mint/Ubuntu backport is present. No MPTCP listeners currently, so exposure is 0. Patch to `7.0.0-43.43` or later when available, or apply vendor fixed kernel. Keep the nft mitigation in place as defense-in-depth, but it is not a proven MPTCP blocker.

4. **Steam Deck — low priority.**
   - Kernel `7.2.7-valve2` is below upstream `7.2.10`. No MPTCP listeners, so exposure is 0. Update to a Valve kernel containing the fix, or `7.2.10+` if available. Keep nft mitigation as defense-in-depth.

5. **nas01 — low priority.**
   - Kernel `6.12.105` is below upstream `6.12.113`. No MPTCP listeners, so exposure is 0. Update TrueNAS to a kernel with the fix when vendor-supported, or apply vendor backport.

6. **UniFi gateway — lowest priority / verify only.**
   - Evidence shows plain TCP `80/443/8443`, no MPTCP listener. No CVE exposure indicated. If kernel version is unknown, verify no MPTCP-enabled listeners exist; otherwise no action required for this CVE.

**Bottom line:** Hermes’ draft missed the real exposure on **homesrv** (`gitea` and `ntfy`), wrongly flagged **tailscaled** as MPTCP-exposed, wrongly called **workstation** vulnerable, and skipped/incorrectly dismissed **kidspc** and **Steam Deck**. Patch **homesrv** first; the other vulnerable-kernel hosts have no MPTCP listeners and can follow in lower-priority order.