Here is the review of the proposed Tailscale ACL and NFS configuration.

### 1. Analysis of Grant G1
**Definition:**
`src autogroup:member -> dst [100.64.0.0/10, fd7a:115c:a1e0::/48], ip ["*"]`

**What it actually permits:**
This grant allows **any** device in the tailnet to communicate with **any other** device in the tailnet over **all protocols and ports**.
- The destination `100.64.0.0/10` covers the entire Tailscale CGNAT range (IPv4).
- The destination `fd7a:115c:a1e0::/48` covers the entire Tailscale 4via6 IPv6 range.
- `ip ["*"]` means all protocols (TCP, UDP, ICMP, etc.) and all ports.

**Over-grant:**
This is the standard "full mesh" permission. It is **not** an over-grant relative to typical Tailscale defaults (which often start with this exact rule for ease of use). However, in the context of your goal ("nothing else new opens"), this grant is **neutral**. It does not open *new* paths; it simply maintains the existing baseline where any tailnet peer can talk to any other tailnet peer.

**Fix:**
No fix required for G1 if you intend to keep the tailnet as a fully connected mesh. If you wanted stricter isolation, you would replace this with specific host-to-host rules, but that is outside the scope of "enable SSH to NAS."

---

### 2. Analysis of Grant G2
**Definition:**
`src autogroup:member -> dst [192.168.20.50/32, fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128], ip ["tcp:2222"]`

**What it actually permits:**
This grant allows **any** device in the tailnet to connect via **TCP port 2222** to the NAS's advertised subnet IP (`192.168.20.50`) or its 4via6 equivalent.

**Over-grant & Critical Issue:**
This grant is **over-granted** in terms of source scope, but more critically, it is **redundant and potentially misleading** due to how Tailscale handles subnet advertising vs. tailnet IPs.

1.  **Source Scope Over-grant:** `src autogroup:member` allows *every* tailnet device (including the kids' PC and Steam Deck) to SSH into the NAS on port 2222. If your goal is "my iPhone can reach... and nothing else new opens," you should restrict the source to only your iPhone.
    *   **Fix:** Change `src autogroup:member` to `src [alex-iphone]` (assuming the device name or tag is known).

2.  **Destination Scope Over-grant/Redundancy:** You are granting access to the **subnet IP** (`192.168.20.50`). However, Tailscale ACLs apply to traffic flowing over the tailnet. If your iPhone connects to `192.168.20.50`, Tailscale will route it via the NAS (which advertises that subnet). This works. **However**, you also granted access to the 4via6 address. This is necessary for iOS on IPv6-only 5G, as you noted.

    **But here’s the subtle over-grant:** Since G1 already allows *any* tailnet member to talk to *any* tailnet peer on *all* ports, and the NAS is a tailnet peer (it has a `100.x` IP), **G2 is technically redundant for devices that can reach the NAS via its Tailscale IP (`100.x`)**.

    **Wait, is it redundant?**
    - If your iPhone connects to `192.168.20.50`, it is using the *advertised subnet*, not the tailnet IP. G1 does **not** cover advertised subnet IPs unless you explicitly include them in the destination list or use `autogroup:member` with a matching route.
    - Actually, G1's destination is `100.64.0.0/10` and `fd7a:...::/48`. It does **not** include `192.168.20.0/24`. So G1 does *not* permit traffic to the subnet IP. Therefore, G2 is **necessary**.

    **So, the only over-grant in G2 is the source.**

    **Revised G2:**
    ```json
    {
      "src": ["alex-iphone"],  // Replace with your iPhone's device name or tag
      "dst": ["192.168.20.50/32", "fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128"],
      "ip": ["tcp:2222"]
    }
    ```

    **Additional Note on 4via6:** The 4via6 address `fd7a:115c:a1e0:b1a:0:1:c0a8:1432` corresponds to `192.168.20.50`. This is correct.

---

### 3. Comments on the NFS Export
**Configuration:** `share` export allows `100.64.0.0/10`.

**Analysis:**
- **Consistency:** This aligns with G1, which allows full tailnet-to-tailnet communication. Any tailnet device can reach any other tailnet device's IP in `100.64.0.0/10`. Therefore, any tailnet device can mount `share` if it has the correct NFS client configuration and permissions.
- **Security Implication:** Since G1 allows full mesh, the NFS export scope is consistent with the network policy. There is no mismatch here.
- **Risk:** If you later tighten G1 to restrict traffic between peers, you must also tighten the NFS `allow` list to match. For now, it is fine.
- **Recommendation:** Ensure that the NFS export also specifies `rw` or `ro` appropriately and that file permissions on the NAS are set correctly, as Tailscale ACLs only control network reachability, not file-level access.

---

### 4. How to Test Safely

#### Step 1: Validate ACL Syntax
Use `tailscale acl validate` (or the admin UI) to ensure the JSON is syntactically correct and that device names/tags in `src` resolve correctly.

#### Step 2: Test from iPhone (Positive Test)
1.  Ensure your iPhone is on cellular data (5G/4G LTE) to trigger the IPv6-only path if applicable, or Wi-Fi to test the IPv4 path.
2.  Open Terminal (or a terminal app like a-Shell).
3.  Run:
    ```bash
    ssh -p 2222 user@192.168.20.50
    ```
    - If on IPv6-only cellular, you may need to use the 4via6 address explicitly if the IPv4 literal fails:
      ```bash
      ssh -p 2222 user@[fd7a:115c:a1e0:b1a:0:1:c0a8:1432]
      ```
    - **Expected:** You should be prompted for the cryptroot passphrase. Enter it. You should get a shell.

#### Step 3: Test from Another Device (Negative Test)
1.  From another tailnet device (e.g., your laptop), run:
    ```bash
    nc -zv -w 5 192.168.20.50 2222
    ```
    - **Expected:** Connection refused or timeout, because G2 now only allows `alex-iphone`.
    - *Note:* If you left G2 as `autogroup:member`, this test would succeed, confirming the over-grant.

#### Step 4: Test NFS Mount (Positive Test)
1.  From your iPhone (or any tailnet device), attempt to mount `share`:
    ```bash
    mount -t nfs nas01:/share /mnt/share
    ```
    - **Expected:** Success, since G1 allows full mesh and NFS export allows `100.64.0.0/10`.

#### Step 5: Verify No New Ports Opened
1.  From your iPhone, try to connect to a different port on the NAS subnet IP (e.g., port 22 or 80):
    ```bash
    nc -zv -w 5 192.168.20.50 22
    nc -zv -w 5 192.168.20.50 80
    ```
    - **Expected:** Connection refused/timeout, because G2 only allows `tcp:2222`.

### Summary of Recommended Changes
1.  **Keep G1** as is (standard full mesh).
2.  **Modify G2** to restrict source to your iPhone:
    ```json
    {
      "src": ["alex-iphone"],
      "dst": ["192.168.20.50/32", "fd7a:115c:a1e0:b1a:0:1:c0a8:1432/128"],
      "ip": ["tcp:2222"]
    }
    ```
3.  **NFS Export** is fine as is, given G1's full mesh permission.

This ensures only your iPhone can SSH to the NAS over cellular, while maintaining existing tailnet connectivity for other services like NFS.