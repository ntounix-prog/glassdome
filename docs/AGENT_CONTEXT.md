# Agent Context and Capabilities

## Agent Identity

**Name**: AgentX (Glassdome AI Agent)  
**Email**: glassdome-ai@xisx.org  
**Host**: agentX (192.168.215.228)  
**Platform**: Proxmox VM 100  
**Network**: 192.168.215.0/24 (Management), 192.168.3.0/24 (Servers)

## Incident Handling

### Incident #001: Email Delivery Failure
**Date**: November 24, 2024  
**Status**: ✅ Resolved  
**First incident successfully handled**

**Problem**: Complete mail delivery failure from mxwest to mooker after VMware-to-Proxmox migration.

**Root Cause**: WireGuard MTU fragmentation - configured MTU (8920 bytes) exceeded path MTU (~1400 bytes), causing TLS handshake packets to fragment and fail.

**Resolution**:
1. Restored WireGuard service on Rome
2. Performed path MTU discovery
3. Reduced WireGuard MTU to 1400 bytes on both endpoints
4. Cleared Postfix TLS session cache
5. Verified end-to-end connectivity

**Key Skills Demonstrated**:
- Systematic problem diagnosis
- Network troubleshooting (connectivity, TLS, MTU)
- Cloud infrastructure access (AWS CLI, SSH)
- Multi-system coordination (mxwest, Rome, mooker, Proxmox)
- Documentation and root cause analysis

### Incident #002: mxeast WireGuard Endpoint
**Date**: November 24, 2024  
**Status**: ✅ Resolved

**Problem**: mxeast (secondary mail exchanger) missing WireGuard endpoint configuration.

**Resolution**:
1. Discovered mxeast from Rome's WireGuard config
2. Gained AWS console access (us-east-1, Virginia)
3. Added SSH key and connected to instance
4. Added missing endpoint to WireGuard configuration
5. Corrected duplicated endpoint entries
6. Validated security and connectivity

**Key Skills Demonstrated**:
- AWS EC2 instance management
- WireGuard VPN configuration
- Security validation
- Multi-region infrastructure access

## Network Infrastructure Management

### Cisco Switch Discovery and Cleanup
**Date**: November 24, 2024  
**Status**: ✅ Discovery Complete, Cleanup Proposed

**Switches Managed**:
- **Cisco 3850 (corefc)**: 192.168.2.253 - 48-port POE switch
- **Nexus 3064 (core3k)**: 192.168.2.244 - Datacenter switch

**Accomplishments**:
1. Resolved routing issues (default gateway configuration)
2. Established SSH connectivity to both switches
3. Discovered 16 connected interfaces on Cisco 3850
4. Discovered 57 VLANs on Nexus 3064
5. Mapped devices to ports using MAC address tables and DHCP leases
6. Labeled 6 previously unlabeled ports
7. Created comprehensive VLAN cleanup proposal

**Key Findings**:
- 35+ ports on default VLAN (security risk)
- Trunk ports allowing all VLANs (VLAN hopping risk)
- Unused VLANs consuming resources
- Missing VLAN restrictions on access ports

**Deliverables**:
- Network discovery reports
- Port-to-device mapping
- VLAN cleanup proposal
- Security assessment plan

### UniFi Gateway Integration
- **Gateway**: 192.168.2.1 (UniFi Dream Router)
- **API Access**: Configured and working
- **Firewall Rules**: Managed via API
- **DHCP Integration**: Used for device identification

## Access and Credentials

### SSH Access
- **mxwest**: ubuntu@44.254.59.166 (AWS us-west-2)
- **mxeast**: ubuntu@<ip> (AWS us-east-1)
- **Rome**: nomad@192.168.3.99
- **mooker**: nomad@192.168.3.69
- **Proxmox 01**: root@192.168.215.78 (pve01)
- **Proxmox 02**: root@192.168.215.77 (pve02)
- **Cisco 3850**: admin@192.168.2.253
- **Nexus 3064**: admin@192.168.2.244 (legacy SSH algorithms)

### Email Access
- **Mailbox**: glassdome-ai@xisx.org
- **Password**: Stored securely
- **SMTP**: 192.168.3.69:587 (TLS)
- **IMAP**: 192.168.3.69 (for monitoring)

### Cloud Access
- **AWS CLI**: Configured on agentX
- **AWS Regions**: us-west-2 (Oregon), us-east-1 (Virginia)
- **EC2 Access**: Via SSH keys

### Network Device Access
- **Cisco Switches**: SSH with password authentication
- **UniFi Gateway**: API access (X-API-KEY header)
- **Proxmox**: API and SSH access

## Network Knowledge

### Key Network Paths
- **Management Network**: 192.168.215.0/24 (Proxmox management)
- **Server Network**: 192.168.2.0/24 (Default network)
- **Mail Network**: 192.168.3.0/24 (mooker, Rome)
- **WireGuard Network**: 10.30.0.0/24 (mxwest ↔ Rome)

### VLAN Structure
- **VLAN 1**: Default (should be unused ports only)
- **VLAN 2**: Servers
- **VLAN 11**: DMZ
- **VLAN 215**: Management (Proxmox, ESXi, SAN)
- **VLAN 211**: SAN A side
- **VLAN 212**: SAN B side

### Critical Infrastructure
- **Proxmox 01**: 192.168.215.78 (pve01)
- **Proxmox 02**: 192.168.215.77 (pve02)
- **mooker**: 192.168.3.69 (Mailcow mail server)
- **Rome**: 192.168.3.99 (network gateway, dual ISP)
- **mxwest**: 44.254.59.166 (AWS EC2 mail relay, us-west-2)
- **mxeast**: <ip> (AWS EC2 mail relay, us-east-1)
- **Cisco 3850**: 192.168.2.253 (corefc)
- **Nexus 3064**: 192.168.2.244 (core3k)
- **UniFi Gateway**: 192.168.2.1
- **agentX**: 192.168.215.228

## Capabilities

### Network Management
- Cisco switch configuration (IOS-XE and NX-OS)
- VLAN management and security
- Port labeling and documentation
- MAC address table analysis
- CDP/LLDP neighbor discovery
- Network topology mapping
- Inter-VLAN routing configuration

### Infrastructure Management
- Proxmox VM management (multi-instance)
- WireGuard VPN configuration
- Postfix mail server configuration
- SSH key management
- Cloud infrastructure access (AWS)
- Network device automation

### Security Assessment
- Network security analysis
- VLAN security hardening
- Access control review
- Configuration compliance checking
- Security documentation

### Communication
- Email composition and sending
- Technical documentation
- Root cause analysis
- Incident reporting
- Team collaboration
- Proposal creation

### Troubleshooting
- Network connectivity diagnosis
- TLS/SSL handshake analysis
- Path MTU discovery
- Mail server queue management
- Service status monitoring
- Device identification and mapping

## Recent Accomplishments

### November 24, 2024
1. ✅ Resolved Incident #001 (Email delivery failure)
2. ✅ Resolved Incident #002 (mxeast WireGuard endpoint)
3. ✅ Discovered and documented Cisco switch infrastructure
4. ✅ Mapped devices to switch ports
5. ✅ Labeled unlabeled switch ports
6. ✅ Created VLAN cleanup proposal
7. ✅ Created security assessment plan
8. ✅ Established network device access

## Current Projects

### Active
- **VLAN Cleanup**: Proposal created, awaiting approval
- **Security Assessment**: Plan created, ready for execution
- **Network Documentation**: Ongoing updates

### Pending
- Template migration from Proxmox 01 to Proxmox 02
- VLAN cleanup implementation (after approval)
- Security assessment execution

## Lessons Learned

1. **Path MTU Discovery**: Always verify path MTU for VPNs/tunnels
2. **Migration Impact**: Infrastructure changes can expose hidden issues
3. **Dual ISP**: Multiple internet providers require careful routing
4. **Systematic Diagnosis**: Connectivity → TLS → MTU approach works
5. **Network Device Access**: Legacy devices may require special SSH algorithms
6. **VLAN Security**: Default VLAN should not be used for production devices
7. **Trunk Port Security**: Always restrict trunk ports to required VLANs only
8. **Device Mapping**: MAC address tables + DHCP leases = effective device identification

## Current Status

**Active Systems**:
- ✅ Mail delivery: Working (INC-001 resolved)
- ✅ WireGuard: Configured with proper MTU (mxwest, mxeast, Rome)
- ✅ TLS: Required and working
- ✅ Network connectivity: Stable
- ✅ Cisco switches: Accessible and documented
- ✅ Network discovery: Complete

**Monitoring**:
- Mail queue on mxwest and mxeast
- WireGuard connectivity
- TLS handshake success rate
- Network path MTU
- Switch port status
- VLAN assignments

---

*Last Updated: November 24, 2024*  
*Incidents Handled: 2*  
*Switches Managed: 2*  
*Ports Labeled: 6*
