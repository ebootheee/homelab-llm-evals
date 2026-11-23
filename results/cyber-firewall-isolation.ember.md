No changes made. Proposal only, per your instruction.

### Verdict: NOT isolated

IoT VLAN 40 `192.168.40.0/24` can currently reach the rest of the house.

Reasoning from the API output:

1. **No LAN_IN rules exist.** In legacy UniFi firewall, inter-VLAN routing is LAN_IN and is allow-by-default. Nothing blocks IoT -> Default `192.168.10.0/24`, VLAN 20 `192.168.20.0/24`, vpn1 `192.168.30.0/24`, or guest.
   That includes workstation .12, NAS BMC .144, NAS .107, and homesrv .50:32400.

2. **Both protective rules are disabled:** `enabled: false` on LAN_LOCAL 20000 and 20001. They do nothing today.

3. **The main rule is in the wrong ruleset, even if enabled.** 
   `LAN_LOCAL 20000 "block iot -> lan" src:Home-IoT dst:rfc1918 drop` would not block IoT -> LAN hosts. LAN_LOCAL is LAN -> *gateway itself*. LAN -> LAN is LAN_IN.
   Enabling it as-is would give a false sense of security, and would likely break IoT DNS, because the gateway IP is in rfc1918 and the rule has no port exception.

4. **Gateway management is exposed to IoT.** LAN_LOCAL default is allow, and the mgmt drop rule is disabled.

5. **mDNS reflector is on for Default, 20, and 40.** Firewall rules do not stop it. IoT and LAN will still discover each other's AirPlay/Chromecast/printer services and hostnames. That's a discovery leak, and a deliberate exception if you want casting from LAN -> IoT to keep working.

The WAN_OUT `drop seedbox` rule is unrelated. Leave it alone.

### Exact rules to add

First, delete/disable the misplaced LAN_LOCAL 20000. Do not enable it.

Then add, in this order:

**1. Block IoT -> all RFC1918 LANs**
```
ruleset: LAN_IN
rule_index: 20000
name: block-iot-to-lan
enabled: true
logging: true
src_networkconf: Home-IoT (192.168.40.0/24)
dst_firewallgroup: rfc1918 (10/8, 172.16/12, 192.168/16)
action: drop
protocol: all
```
This is first in LAN_IN - there are currently no LAN_IN rules to pre-empt it. Stateful return traffic means LAN-initiated connections to IoT, e.g. to a camera/TV, will still work. IoT-to-IoT on same VLAN is L2-switched and unaffected.

**2. Block IoT -> gateway management, allow DNS**
```
ruleset: LAN_LOCAL
rule_index: 20000 (first after deleting old 20000; or enable existing 20001)
name: block-iot-to-gw-mgmt
enabled: true
logging: true
src_networkconf: Home-IoT
dst: gateway / local (no dst_networkconf, no dst_firewallgroup)
dst_port: 22,443,8443
action: drop
```
LAN_LOCAL destination is implicitly the gateway, so no dst group needed. DNS on 53 and DHCP broadcast are not matched by this rule and remain allowed by default. If you want stricter gateway isolation, replace this with allow 53,123 then drop-all in LAN_LOCAL - tell me and I'll spec that instead, as it can break other local services.

Decision needed: keep mDNS reflector on 40 for casting, accepting discovery visibility, or disable it for strict isolation.

### Backup and rollback

**Before any change:**
1. UniFi UI: Settings > System > Backup > Download. Store encrypted/offline.
2. API snapshot: GET `rest/firewallrule` and `rest/networkconf` to an encrypted vault. **Warning from your API note: `rest/networkconf` returns `x_ipsec_pre_shared_key` in plaintext.** Treat any backup/API dump as a credential. Redact that field before putting it in a ticket/chat, and rotate the PSK if a dump was ever shared.
3. Record the new rule names/indices for fast rollback.

**Rollback:**
Fast path: disable or DELETE the two new rules via UI/API. UniFi legacy firewall applies immediately, no reboot.
Full path: Settings > System > Backup > Restore. This reboots the gateway and restores the PSK and all config.

### Verify afterwards

From a test host on VLAN 40, e.g. `192.168.40.x`:

Should **fail** (timeout/drop, and drop counter/logging increments in UniFi):
- ping/curl/nc to `192.168.10.12`, `192.168.10.144`, `192.168.20.107`, `192.168.20.50:32400`
- nc/curl to gateway mgmt `192.168.40.1` ports 22,443,8443
- ping to vpn1/guest networks

Should **succeed**:
- DNS via gateway: `nslookup example.com 192.168.40.1`
- Internet, if intended for TVs/speakers/cameras
- From Default/VLAN 20 host: initiate to IoT camera/TV and get return traffic

Also check:
- UniFi Firewall stats/logs show hits on the two new drop rules
- mDNS discovery from IoT - if reflector still on, you will still see LAN services. That's expected unless you disable it.
- IPv6: rfc1918 does not cover IPv6. If IPv6 is enabled on these networks, test and block separately.