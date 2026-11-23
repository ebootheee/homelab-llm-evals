Here is the corrected exposure map, audit corrections, and remediation plan for CVE-2026-98432.

### 1. Corrected Per-Host Exposure Table

| Host | Kernel Version | Fixed? (Verdict) | Exposed MPTCP Listeners (Evidence) | Status |
| :--- | :--- | :--- | :--- | :--- |
| **workstation** | `7.0.0-43.43` | **Yes** (Ubuntu 26.04 fixed build) | `llama-swap` on `100.101.1.10:8080` | **Mitigated** (Fixed Kernel + nft rules) |
| **homesrv** | `5.15.0-201` | **No** (< 5.15.223) | `gitea *:3000`, `ebrian-ntfy ...:8888` | **EXPOSED** (Vulnerable Kernel + Active MPTCP) |
| **kidspc** | `7.0.0-42` | **No** (< 7.2.10, not Ubuntu fixed build) | None (`ss -Mln` empty) | **Low Risk** (Vulnerable Kernel, No Attack Surface) |
| **Steam Deck** | `7.2.7` | **No** (< 7.2.10) | None (`ss -Mln` empty) | **Low Risk** (Vulnerable Kernel, No Attack Surface) |
| **nas01** | `6.12.105` | **No** (< 6.12.113) | None (Explicitly stated) | **Low Risk** (Vulnerable Kernel, No Attack Surface) |
| **UniFi Gateway** | N/A (APPL) | **N/A** | None (Plain TCP only) | **Safe** |

---

### 2. Corrections to Hermes' Draft

| Draft Claim | Correction | Reason / Evidence |
| :--- | :--- | :--- |
| **"workstation: vulnerable (7.0 < 7.2.10)"** | **Incorrect.** Godzira is **Fixed**. | The evidence states Ubuntu fixed build for 26.04 is `7.0.0-43.43`. Godzira is running exactly this version. It does not need to match the upstream generic version number if the distro backport is applied. |
| **"gitea: 0 exposure"** | **Incorrect.** Gitea is **EXPOSED**. | The MPTCP probe explicitly states `gitea homesrv:3000 = MPTCP negotiated`. The kernel on homesrv (`5.15.0-201`) is older than the fix (`5.15.223`). |
| **"ntfy: 0 exposure"** | **Incorrect.** ntfy is **EXPOSED**. | The MPTCP probe explicitly states `ntfy 100.101.1.20:8888 = MPTCP negotiated`. Same kernel vulnerability as gitea. |
| **"tailscaled ... EXPOSED (kernel MPTCP listeners)"** | **Incorrect.** Tailscaled is **NOT Exposed** to this specific CVE vector. | The probe shows tailscaled ports `fell back to plain TCP`. The CVE requires the socket to be listening with MPTCP enabled/negotiated. Plain TCP sockets are not vulnerable to this specific use-after-free in the MPTCP stack. |
| **"kidspc: not checked"** | **Incomplete.** kidspc is **Low Risk**. | Kernel `7.0.0-42` is vulnerable (< 7.2.10). However, `ss -Mln` is empty, meaning there are no MPTCP listeners to trigger the bug. It is safe from remote exploitation until an MPTCP service starts. |
| **"Steam Deck: offline, skipped"** | **Incorrect.** Steam Deck is **Low Risk**. | Kernel `7.2.7` is vulnerable (< 7.2.10). However, `ss -Mln` is empty. No MPTCP listeners = no remote trigger. |
| **"nas01: fine"** | **Misleading.** nas01 is **Vulnerable but Low Risk**. | Kernel `6.12.105` is vulnerable (< 6.12.113). However, there are "No MPTCP listeners." It is not "fine" in terms of kernel version, but it is safe from remote exploitation currently. |

---

### 3. Patch / Mitigation Order

**Priority 1: Immediate Patching (High Exposure)**
*   **Host:** `homesrv`
*   **Action:** Upgrade kernel to `5.15.0-203.213` (Ubuntu 22.04 fixed build) or apply the upstream patch for `5.15.223`.
*   **Reason:** This is the only host with a vulnerable kernel **and** active, reachable MPTCP listeners (`gitea`, `ntfy`). It is actively exposed to remote exploitation.
*   **Interim Mitigation (if patching is delayed):**
    *   The existing nft rule `ip hdrlength gt 5 drop` is already applied. This blocks standard MPTCP extension headers. However, since MPTCP was successfully negotiated in the probe, verify if this rule is actually dropping the traffic or if the service is using a different mechanism. If the rule is effective, exposure is reduced but not eliminated (some edge cases might bypass simple header length checks). **Patching is preferred.**

**Priority 2: Kernel Updates (Medium/Low Exposure)**
*   **Host:** `Steam Deck`
    *   **Action:** Update kernel to `7.2.10` or later.
    *   **Reason:** Vulnerable kernel, but no MPTCP listeners. Low risk, but should be patched for completeness.
*   **Host:** `nas01` (TrueNAS)
    *   **Action:** Update to a TrueNAS release containing kernel `6.12.113` or later.
    *   **Reason:** Vulnerable kernel, no MPTCP listeners. Low risk.
*   **Host:** `kidspc`
    *   **Action:** Update kernel to `7.2.10` or later (or install the Ubuntu/Mint backport if available).
    *   **Reason:** Vulnerable kernel, no MPTCP listeners. Low risk.

**Priority 3: Verification (No Action Needed)**
*   **Host:** `workstation`
    *   **Action:** None.
    *   **Reason:** Already running the fixed Ubuntu kernel (`7.0.0-43.43`). The nft rule is an extra layer of defense but not strictly necessary for this CVE.
*   **Host:** `UniFi Gateway`
    *   **Action:** None.
    *   **Reason:** No MPTCP listeners, plain TCP only.

### Summary of Key Insight
Hermes' draft failed because it confused **"kernel version < upstream fix"** with **"vulnerable"** without checking for distro-specific backports (workstation) and assumed that any service on a vulnerable kernel was exposed, ignoring the **MPTCP negotiation state** (tailscaled fell back to TCP) and the **presence of listeners** (kidspc/Steam Deck/nas01 have no MPTCP sockets). The critical exposure is solely on **homesrv**.