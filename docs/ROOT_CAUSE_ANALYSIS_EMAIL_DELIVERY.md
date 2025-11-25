# Root Cause Analysis: Email Delivery Failure
## mxwest to mooker Mail Queue Issue
### Incident #001

**Incident ID**: INC-001  
**Date**: November 24, 2024  
**Reported By**: System Administrator  
**Resolved By**: Glassdome AI Agent (AgentX)  
**Duration**: ~4 hours  
**Severity**: High - Complete mail delivery failure  
**Status**: ✅ Resolved

---

## Executive Summary

After migrating the mooker mail server (Mailcow) from VMware ESXi to Proxmox, mail delivery from mxwest (AWS EC2 mail relay) to mooker completely stopped. Mail was queuing on mxwest with TLS handshake timeout errors. The root cause was identified as **WireGuard MTU fragmentation** - the WireGuard tunnel between mxwest and Rome (network gateway) had an MTU of 8920-8921 bytes, but the actual path MTU was only ~1400 bytes, causing TLS handshake packets to fragment and fail.

**Resolution**: Reduced WireGuard MTU to 1400 bytes on both mxwest and Rome, restoring mail delivery within minutes.

---

## Problem Statement

### Initial Symptoms
- Mail queuing on mxwest (AWS EC2 instance)
- All mail to domains hosted on mooker (192.168.3.69) was deferred
- Error messages: "Cannot start TLS: handshake failure"
- Connection timeouts when attempting TLS handshake
- Mail queue growing with messages from November 22-24

### Impact
- **Complete mail delivery failure** for all domains hosted on mooker
- **No inbound mail delivery** from mxwest to mooker
- **User impact**: All email to xisx.org domains was delayed

---

## Network Architecture

### Components Involved
1. **mxwest** (AWS EC2, Oregon datacenter)
   - Public IP: 44.254.59.166
   - Role: Mail relay/outbound SMTP server
   - WireGuard IP: 10.30.0.1

2. **Rome** (Network gateway/router)
   - Internal IP: 192.168.3.99
   - Public IPs: 71.205.42.240 (primary), 174.16.51.110 (secondary)
   - Role: WireGuard peer, routes traffic between mxwest and mooker
   - WireGuard IP: 10.30.0.3
   - **Note**: Rome has dual ISP configuration (two internet providers)

3. **mooker** (Proxmox VM, VM ID 102)
   - IP: 192.168.3.69
   - Hostname: mail.xisx.org
   - Role: Mailcow mail server (Postfix)
   - Recently migrated from VMware ESXi to Proxmox

### Network Path
```
mxwest (10.30.0.1) 
  → WireGuard Tunnel 
  → Rome (10.30.0.3 / 192.168.3.99) 
  → mooker (192.168.3.69)
```

---

## Root Cause Analysis

### Initial Investigation

The investigation began with the assumption that this was a TLS configuration issue, as error messages indicated "Cannot start TLS: handshake failure." However, deeper analysis revealed the actual problem.

#### Phase 1: Network Connectivity Check
- **Finding**: mxwest could not reach mooker at all (ping timeouts)
- **Discovery**: WireGuard service was not running on Rome
- **Action**: Started WireGuard service on Rome
- **Result**: Basic connectivity restored, but mail still failing

#### Phase 2: TLS Handshake Analysis
- **Finding**: TLS handshake would start but never complete
- **Observation**: 
  - mxwest logs showed: "SSL_connect:SSLv3/TLS write client hello" (no response)
  - mooker logs showed: "SSL_accept error: Connection timed out"
- **Discovery**: Both sides were timing out during TLS handshake

#### Phase 3: Path MTU Discovery
- **Test**: Performed path MTU discovery along the entire network path
- **Results**:
  - mxwest → mooker: ~1400 bytes (fails at 1420+)
  - mxwest → Rome (WireGuard): ~1400 bytes (fails at 1420+)
  - Rome → mooker: 9000 bytes (local network, no issue)
- **Critical Finding**: WireGuard MTU was 8920-8921 bytes, but path MTU was only ~1400 bytes

### Root Cause

**WireGuard MTU Fragmentation**

The WireGuard tunnel between mxwest and Rome was configured with an MTU of 8920-8921 bytes (default for high-speed networks). However, the actual network path between these endpoints had a path MTU of only ~1400 bytes. This mismatch caused:

1. **TLS handshake packets** (which contain certificates and are typically 1500+ bytes) to be fragmented
2. **Fragmented packets** to be lost or improperly reassembled
3. **TLS handshake timeouts** on both sides
4. **Complete mail delivery failure**

### Contributing Factors

1. **VMware to Proxmox Migration**: The migration changed the network path, exposing the MTU mismatch
2. **Dual ISP Configuration**: Rome has two internet providers with different source IPs, which may have contributed to path MTU variations
3. **WireGuard Default MTU**: WireGuard defaults to high MTU values assuming optimal network conditions

---

## Resolution Steps

### Step 1: WireGuard Service Recovery
**Issue**: WireGuard was not running on Rome  
**Action**: 
- Connected to Rome via SSH (192.168.3.99)
- Started WireGuard service: `systemctl start wg-quick@wg0`
- Enabled on boot: `systemctl enable wg-quick@wg0`
**Result**: Basic connectivity restored

### Step 2: Network Path Analysis
**Action**: 
- Performed path MTU discovery from mxwest to mooker
- Tested packet sizes: 1300, 1400, 1420, 1450, 1500 bytes
- Identified path MTU bottleneck at ~1400 bytes
**Result**: Confirmed MTU mismatch

### Step 3: WireGuard MTU Configuration
**Action**: 
- Reduced WireGuard MTU to 1400 bytes on Rome:
  ```bash
  # Added to /etc/wireguard/wg0.conf
  MTU = 1400
  systemctl restart wg-quick@wg0
  ```
- Reduced WireGuard MTU to 1400 bytes on mxwest:
  ```bash
  # Added to /etc/wireguard/wg0.conf
  MTU = 1400
  wg-quick down wg0 && wg-quick up wg0
  ```
**Result**: WireGuard MTU now matches path MTU

### Step 4: WireGuard Endpoint Configuration
**Issue**: mxwest WireGuard config was missing Rome's endpoint  
**Action**: Added endpoint to mxwest WireGuard configuration:
  ```
  Endpoint = 71.205.42.240:41926
  ```
**Result**: WireGuard connection stabilized

### Step 5: Postfix TLS Session Cache Clear
**Action**: 
- Cleared Postfix TLS session cache on mxwest
- Reloaded Postfix configuration
**Result**: Removed stale TLS session data

### Step 6: TLS Policy Configuration
**Action**: 
- Verified TLS policy for mail.xisx.org
- Set to "encrypt" (required) for security
**Result**: TLS encryption properly configured

---

## Cloud Access and Tools Used

### AWS Access
- **Purpose**: Access mxwest EC2 instance for diagnostics and configuration
- **Method**: AWS CLI installed and configured on agentx
- **Actions**:
  - Installed AWS CLI v2
  - Configured AWS credentials
  - Used for EC2 instance management (though direct SSH was used for this issue)

### SSH Access
- **mxwest**: SSH key-based access (ubuntu@44.254.59.166)
- **Rome**: SSH key-based access (nomad@192.168.3.99)
- **mooker**: SSH key-based access (nomad@192.168.3.69)
- **Proxmox**: SSH access (root@10.0.0.1) for VM management

### Diagnostic Tools
- **Network**: `ping`, `traceroute`, `telnet`, `openssl s_client`
- **Mail**: `postqueue`, `postconf`, mail log analysis
- **WireGuard**: `wg show`, `wg-quick`, systemctl
- **System**: `ip route`, `ip addr`, `sysctl`

---

## Verification and Testing

### Connectivity Tests
- ✅ mxwest → Rome: Ping successful
- ✅ mxwest → mooker: Ping successful
- ✅ TCP connection to port 25: Successful
- ✅ TLS handshake: Successful (certificate chain received)

### Mail Delivery Tests
- ✅ TLS handshake completes
- ✅ SMTP authentication works
- ✅ Mail delivery resumes
- ✅ Queue processing active

### Final Status
- **Mail Queue**: Reduced from 20+ messages to 1 (processing)
- **Delivery Status**: Multiple messages showing "status=sent (250 2.0.0 Ok)"
- **TLS**: Working with encryption required
- **Network**: Stable with proper MTU configuration

---

## Lessons Learned

### Technical
1. **Path MTU Discovery is Critical**: Always verify path MTU when configuring VPNs/tunnels
2. **Migration Impact**: Network path changes during migrations can expose configuration issues
3. **Dual ISP Considerations**: Multiple internet providers can create path MTU variations
4. **TLS Packet Size**: TLS handshakes with certificates can exceed 1400 bytes, making MTU critical

### Process
1. **Systematic Diagnosis**: Starting with connectivity, then TLS, then MTU was the right approach
2. **Log Analysis**: Both sides' logs were essential to understand the timeout pattern
3. **End-to-End Testing**: Testing the complete path (mxwest → Rome → mooker) revealed the bottleneck

### Prevention
1. **MTU Configuration**: Set WireGuard MTU based on path MTU discovery, not defaults
2. **Post-Migration Testing**: Comprehensive network testing after infrastructure changes
3. **Monitoring**: Implement alerts for mail queue growth and delivery failures

---

## Recommendations

### Immediate
1. ✅ **Completed**: WireGuard MTU set to 1400 bytes on both endpoints
2. ✅ **Completed**: WireGuard service enabled on boot
3. ✅ **Completed**: TLS encryption required for mail.xisx.org

### Short-term
1. **Monitor mail delivery** for 24-48 hours to ensure stability
2. **Document WireGuard configuration** for future reference
3. **Set up mail queue monitoring** alerts

### Long-term
1. **Optimize MTU per path**: If dual ISP paths have different MTUs, configure accordingly
2. **Implement path MTU discovery** in WireGuard configuration
3. **Add network health checks** for critical paths
4. **Create runbook** for similar issues

---

## Conclusion

The mail delivery failure was caused by WireGuard MTU fragmentation due to a mismatch between the configured MTU (8920 bytes) and the actual path MTU (~1400 bytes). This caused TLS handshake packets to fragment and fail, resulting in complete mail delivery failure.

The issue was resolved by:
1. Restoring WireGuard service on Rome
2. Identifying the path MTU through systematic testing
3. Reducing WireGuard MTU to match the path MTU (1400 bytes)
4. Clearing Postfix TLS session cache
5. Verifying end-to-end connectivity and mail delivery

Mail delivery is now functioning normally with TLS encryption properly configured.

---

## Appendix: Key Commands Used

### Path MTU Discovery
```bash
ping -M do -s 1400 -c 1 192.168.3.69  # Success
ping -M do -s 1420 -c 1 192.168.3.69  # Failure
```

### WireGuard MTU Configuration
```bash
# On Rome
echo "MTU = 1400" >> /etc/wireguard/wg0.conf
systemctl restart wg-quick@wg0

# On mxwest
echo "MTU = 1400" >> /etc/wireguard/wg0.conf
wg-quick down wg0 && wg-quick up wg0
```

### Mail Queue Management
```bash
postqueue -p          # View queue
postqueue -f          # Force flush
```

### TLS Testing
```bash
openssl s_client -connect 192.168.3.69:25 -starttls smtp
```

---

**Document Version**: 1.0  
**Last Updated**: November 24, 2024  
**Author**: Glassdome AI Agent (AgentX)  
**Contact**: glassdome-ai@xisx.org

