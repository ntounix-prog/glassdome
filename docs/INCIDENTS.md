# Incident Log - AgentX

## Incident #001: Email Delivery Failure
**Date**: November 24, 2024  
**Status**: ✅ Resolved  
**Severity**: High  
**First incident successfully handled**

### Problem
Complete mail delivery failure from mxwest (AWS EC2, us-west-2) to mooker (Mailcow on Proxmox) after VMware-to-Proxmox migration. Mail queuing on mxwest with TLS handshake errors.

### Symptoms
- `SSL_connect error to mail.xisx.org[192.168.3.69]:25: Connection timed out`
- `Cannot start TLS: handshake failure`
- Mail stuck in queue on mxwest

### Root Cause
WireGuard MTU fragmentation:
- WireGuard configured with MTU 8920-8921 bytes
- Path MTU between mxwest and Rome was ~1400 bytes
- TLS handshake packets fragmented and failed
- WireGuard service initially not running on Rome

### Resolution Steps
1. Started WireGuard service on Rome
2. Performed path MTU discovery (ping with DF flag)
3. Reduced WireGuard MTU to 1400 bytes on both mxwest and Rome
4. Cleared Postfix TLS session cache
5. Verified end-to-end connectivity and mail delivery

### Documentation
- `docs/ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md`
- `docs/MAIL_TLS_MTU_ISSUE.md`
- `docs/ROME_WIREGUARD_FIX.md`
- `docs/EMAIL_NETWORK_ISSUE_DIAGNOSIS.md`

### Lessons Learned
- Always verify path MTU for VPNs/tunnels
- Infrastructure migrations can expose hidden issues
- Systematic diagnosis: Connectivity → TLS → MTU

---

## Incident #002: mxeast WireGuard Endpoint Missing
**Date**: November 24, 2024  
**Status**: ✅ Resolved  
**Severity**: Medium

### Problem
mxeast (secondary mail exchanger in AWS us-east-1, Virginia) missing WireGuard endpoint configuration, preventing proper VPN connectivity.

### Symptoms
- mxeast not properly connected to WireGuard network
- Missing endpoint in WireGuard configuration

### Root Cause
WireGuard configuration on mxeast was missing the Rome endpoint (71.205.42.240:41926).

### Resolution Steps
1. Discovered mxeast from Rome's WireGuard configuration
2. Gained AWS console access (us-east-1 region)
3. Added SSH key to mxeast instance
4. Connected via SSH and reviewed WireGuard configuration
5. Added missing endpoint: `Endpoint = 71.205.42.240:41926`
6. Corrected duplicated endpoint entries
7. Validated security and connectivity

### Documentation
- `docs/INCIDENT_002_MXEAST_ENDPOINT.md`

### Lessons Learned
- Secondary systems need same attention as primary
- Configuration consistency across regions important
- Security validation after changes critical

---

## Incident #003: Network Device Routing Issues
**Date**: November 24, 2024  
**Status**: ✅ Resolved  
**Severity**: Medium

### Problem
Cisco switches (3850 and Nexus 3064) could not route traffic back to agentX network (192.168.3.0/24), preventing network discovery and management.

### Symptoms
- "Destination Host Unreachable" from gateway
- Switches not accessible from agentX
- Network discovery blocked

### Root Cause
- Cisco 3850 had default gateway set to 192.168.2.95 (incorrect)
- Nexus 3064 management VRF had default route to 192.168.2.2 (incorrect)
- Both should point to 192.168.2.1 (UniFi gateway)

### Resolution Steps
1. Identified incorrect default gateway on Cisco 3850
2. Updated Cisco 3850 default gateway to 192.168.2.1
3. Updated Nexus 3064 management VRF default route to 192.168.2.1
4. Verified connectivity from agentX

### Documentation
- `docs/SWITCH_DEFAULT_GATEWAY_SETUP.md`
- `docs/CISCO_SWITCH_DISCOVERY_REPORT.md`

### Lessons Learned
- Network devices need proper default gateway configuration
- VRF routing requires separate configuration
- Always verify routing after network changes

---

*Last Updated: November 24, 2024*  
*Total Incidents: 3*  
*Resolved: 3*
