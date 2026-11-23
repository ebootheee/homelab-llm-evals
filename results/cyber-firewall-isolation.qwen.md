### Verdict
**The IoT VLAN is NOT isolated.**

**Reasoning:**
1.  **Primary Isolation Rule is Disabled:** The rule intended to block traffic from the IoT network (`Home-IoT`) to the rest of the LAN (`rfc1918` group) exists but is set to `enabled: false`. In UniFi legacy firewall logic, disabled rules are ignored.
2.  **Management Access is Open:** The rule blocking IoT access to gateway management ports (22, 443, 8443) is also `enabled: false`. This allows IoT devices to potentially SSH/HTTPS into the UCG itself.
3.  **mDNS Leakage:** The mDNS reflector is enabled for VLAN 40 (IoT). While mDNS is broadcast-based and often considered "low risk," it allows IoT devices to discover services on other VLANs (like Plex on VLAN 20 or NAS on Default) if the gateway reflects those queries. This violates strict isolation principles.
4.  **No Inbound Rules:** There are no `LAN_IN` rules, which is standard for local traffic, but relies entirely on the `LAN_LOCAL` rules to block cross-VLAN communication. Since the blocking rules in `LAN_LOCAL` are off, IoT can initiate connections to any RFC1918 address (including Default 192.168.10.x and home-private 192.168.20.x).

---

### Exact Rules to Add/Modify

**Important Note on UniFi Legacy Firewall Logic:**
UniFi processes firewall rules in order of `rule_index` (lowest first). To ensure isolation, we must **enable** the existing disabled rules and add a specific rule to block mDNS if strict isolation is required. We will also add a logging rule for visibility.

#### Step 1: Enable Existing Blocking Rules
These rules already exist but are disabled. Change their `enabled` field to `true`.

1.  **Rule:** `block iot -> lan`
    *   **Ruleset:** `LAN_LOCAL`
    *   **Rule Index:** `20000` (Keep existing index)
    *   **Action:** `drop`
    *   **Source:** `Home-IoT` (Network ID for VLAN 40)
    *   **Destination:** `rfc1918` (Firewall Group)
    *   **Change:** Set `enabled: true`

2.  **Rule:** `block iot -> gw mgmt`
    *   **Ruleset:** `LAN_LOCAL`
    *   **Rule Index:** `20001` (Keep existing index)
    *   **Action:** `drop`
    *   **Source:** `Home-IoT`
    *   **Destination Port:** `22,443,8443`
    *   **Change:** Set `enabled: true`

#### Step 2: Add New Rule for mDNS Isolation (Optional but Recommended)
To prevent IoT devices from discovering services on other VLANs via the mDNS reflector, add a rule to drop mDNS traffic from IoT to all other LAN segments.

3.  **Rule:** `block iot -> lan mdns`
    *   **Ruleset:** `LAN_LOCAL`
    *   **Rule Index:** `20002` (Place after existing IoT rules)
    *   **Action:** `drop`
    *   **Source:** `Home-IoT`
    *   **Destination:** `rfc1918`
    *   **Protocol:** `udp`
    *   **Destination Port:** `5353` (mDNS port)
    *   **Logging:** `true` (To verify if IoT is trying to discover services)

#### Step 3: Add Logging Rule for General IoT Outbound (Optional)
To monitor what IoT devices are trying to reach, add a logging rule before the drop rules. Note: In UniFi, you typically log *before* dropping if you want to see dropped packets. However, since we are enabling existing drops, we can add a separate logging rule at a lower index.

4.  **Rule:** `log iot -> lan`
    *   **Ruleset:** `LAN_LOCAL`
    *   **Rule Index:** `19000` (Lower than 20000 so it matches first)
    *   **Action:** `accept` (Use `accept` with logging, or use `log` action if available in your UniFi version. In legacy, often you use an `accept` rule with `logging: true` just before the drop rules to catch traffic.)
    *   **Source:** `Home-IoT`
    *   **Destination:** `rfc1918`
    *   **Logging:** `true`

*Note: If you use an `accept` rule with logging, it will log the connection but allow it. To log *and* drop, you typically need two rules: one that logs and accepts (with a higher priority/lower index), and one that drops. However, since we want to **block**, the simplest approach in UniFi legacy is to enable the existing `drop` rules and add `logging: true` to them if possible via API, or add a separate logging rule.*

**Recommended Final Rule Order for `LAN_LOCAL` (IoT-related):**
1.  Index `19000`: `log iot -> lan` (Action: `accept`, Logging: `true`) – *Optional, for visibility*
2.  Index `20000`: `block iot -> lan` (Action: `drop`) – **Enabled**
3.  Index `20001`: `block iot -> gw mgmt` (Action: `drop`) – **Enabled**
4.  Index `20002`: `block iot -> lan mdns` (Action: `drop`, Port: `5353`) – **New**

---

### Backup and Rollback Plan

#### 1. Backup
Before making changes:
1.  **API Snapshot:** Use the UniFi API to export the current state of `rest/networkconf` and `rest/firewallrule`.
    ```bash
    # Example using curl (adjust token/IP)
    curl -k -X GET "https://<UCG_IP>/api/site/default/networkconf" -H "Cookie: <SESSION_COOKIE>" > networkconf_backup.json
    curl -k -X GET "https://<UCG_IP>/api/site/default/firewallrule" -H "Cookie: <SESSION_COOKIE>" > firewallrule_backup.json
    ```
2.  **Console Export:** In the UniFi Controller UI, go to **Settings** > **Backup** and create a manual backup file (`.ufb`).
3.  **Note Current State:** Record the current `enabled` status of rules `20000` and `20001` in `LAN_LOCAL`.

#### 2. Rollback Plan
If issues arise (e.g., IoT devices stop working, cameras offline):
1.  **Revert API Changes:**
    *   Set `enabled: false` for rules `20000`, `20001`, and `20002` in `LAN_LOCAL`.
    *   Delete the new logging rule (`19000`) if added.
    *   Push changes via API or UI.
2.  **Restore Backup:** If the above fails, restore the `.ufb` backup file created in Step 1.
3.  **Verify:** After rollback, confirm IoT devices can reach the internet and local services (if needed) again.

---

### Verification of Isolation

After applying the rules:

1.  **Test from IoT Device to LAN (Should FAIL):**
    *   From an IoT device (e.g., a smart speaker on VLAN 40), ping `192.168.10.12` (workstation) and `192.168.20.50` (homesrv).
    *   **Expected Result:** No reply (timeout).
    *   **Check Logs:** In UniFi Controller > **System** > **Logs**, filter for `firewall`. Look for `DROP` entries with source IP in `192.168.40.x` and destination in `192.168.10.x` or `192.168.20.x`.

2.  **Test from LAN to IoT (Should SUCCEED, unless you want bidirectional isolation):**
    *   From a PC on Default VLAN (`192.168.10.x`), ping an IoT device (e.g., `192.168.40.x`).
    *   **Expected Result:** Reply received. (Note: The current rules only block IoT->LAN, not LAN->IoT. If you want bidirectional isolation, add a rule to block `rfc1918` -> `Home-IoT`.)

3.  **Test mDNS Isolation (Should FAIL):**
    *   From an IoT device, run `avahi-browse` or similar tool to see if it discovers services like Plex (`plexmedia.server`) on other VLANs.
    *   **Expected Result:** No discovery of services outside VLAN 40.

4.  **Test Gateway Management Access (Should FAIL):**
    *   From an IoT device, try to connect to `https://<UCG_IP>:8443` or SSH to `<UCG_IP>`.
    *   **Expected Result:** Connection refused/timeout.

5.  **Check mDNS Reflector:**
    *   Consider disabling the mDNS reflector for VLAN 40 in **Settings** > **Networks** > **VLAN 40** > **mDNS** to prevent broadcast leakage entirely. This is a configuration change, not a firewall rule, but complements the firewall rules.