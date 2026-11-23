**Root Cause:**
The devices are offline because they were moved to **VLAN 40**, but their IP addresses remain on the **192.168.10.x** subnet (which belongs to VLAN 1, the default/home network).

*   **Evidence from `stat/sta`:**
    *   `plug-03` (VLAN 40) has IP `192.168.10.150`.
    *   `speaker-1` (VLAN 40) has IP `192.168.40.44` (This one is actually on a different subnet, likely VLAN 8, but see note below).
    *   `tv-living`, `cam-garage`, `appletv-den` are also on VLAN 40 but have IPs in `192.168.10.x`.
    *   **Key Indicator:** `gw_vlan=1` for all devices except `speaker-1` (which has `gw_vlan=40`). This means the router thinks their gateway is on VLAN 1, but they are physically/logically on VLAN 40. Without Inter-VLAN routing or a correct gateway IP on VLAN 40, these devices cannot reach the internet or local resources on other VLANs.
    *   `speaker-1` is an outlier: It has `gw_vlan=40` and IP `192.168.40.44`. This suggests VLAN 40 might actually be mapped to subnet `192.168.40.0/24` (or similar), while the other devices are stuck with old DHCP leases from VLAN 1.

**Why this happened:**
The agent used **Per-Client Virtual Network Override** to force VLAN 40 on devices that were previously on VLAN 20 (HomeNet). However:
1.  The devices retained their old IP addresses (from the 192.168.10.x range) via DHCP lease persistence or static IPs.
2.  The gateway assignment (`gw_vlan`) was not updated to match the new VLAN for most devices, or the DHCP server on VLAN 40 is configured differently than expected.
3.  `speaker-1` shows that VLAN 40 likely uses a different subnet (e.g., 192.168.40.x), confirming that devices with 192.168.10.x IPs are misaligned.

---

**The Fix:**
1.  **Renew DHCP Leases** for all affected devices to get new IP addresses from the correct VLAN 40 pool.
2.  **Verify Gateway Assignment:** Ensure that the UniFi controller is correctly assigning `gw_vlan=40` for devices on VLAN 40. If not, check the Gateway settings in the UniFi Network application.
3.  **Confirm VLAN 40 Subnet:** Verify that VLAN 40 is assigned to the correct subnet (likely `192.168.40.0/24` based on `speaker-1`).

---

**Execution Order (Ask Alex to Approve):**

1.  **Approve DHCP Lease Renewal for Affected Devices:**
    *   Reboot or force DHCP renewal on: `plug-03`, `tv-living`, `cam-garage`, `appletv-den`.
    *   *Note:* `speaker-1` may already be correct, but verify it.

2.  **Verify Gateway VLAN Assignment in UniFi Controller:**
    *   Check the Gateway settings for VLAN 40. Ensure it is set to assign the correct gateway IP (e.g., `192.168.40.1` if that’s the subnet).
    *   If necessary, re-apply the Virtual Network Override to ensure `gw_vlan` is updated.

3.  **Confirm Subnet Configuration for VLAN 40:**
    *   Verify that the DHCP server for VLAN 40 is serving IPs from the correct range (e.g., `192.168.40.0/24`).

---

**Verification Steps:**

1.  **Check `stat/sta` Again:**
    *   Confirm all devices on VLAN 40 have IPs in the correct subnet (e.g., `192.168.40.x`).
    *   Confirm `gw_vlan=40` for all these devices.
    *   Example expected output:
        ```
        plug-03     ap=Kitchen   essid=HomeNet vlan=40 gw_vlan=40 ip=192.168.40.xxx
        tv-living   ap=Basement  essid=Home-IoT  vlan=40 gw_vlan=40 ip=192.168.40.xxx
        cam-garage  ap=Backyard  essid=Home-IoT  vlan=40 gw_vlan=40 ip=192.168.40.xxx
        appletv-den ap=Basement  essid=Home-IoT  vlan=40 gw_vlan=40 ip=192.168.40.xxx
        ```

2.  **Ping Test:**
    *   From a device on VLAN 40, ping the gateway IP (e.g., `192.168.40.1`).
    *   Ping an external site (e.g., `8.8.8.8`) to confirm internet access.

3.  **Check Device Status in UniFi Controller:**
    *   Ensure all devices show as "Online" and connected to the correct SSID/VLAN.

4.  **Monitor for 15 Minutes:**
    *   Watch `stat/sta` for any reconnections or IP changes.