# Cisco Switch Network Discovery Report

**Date:** November 24, 2024  
**Project:** Cisco Switch VLAN Cleanup and Network Discovery  
**Status:** Phase 3 Complete - Discovery Successful

---

## Executive Summary

Successfully completed comprehensive network discovery on both Cisco switches in the environment. Resolved connectivity issues, established SSH access, and collected detailed configuration data from both the Cisco 3850 (corefc) and Nexus 3064 (core3k) switches.

---

## Switches Discovered

### 1. Cisco 3850-48 POE Switch (corefc)
- **IP Address:** 192.168.2.253
- **Hostname:** corefc
- **Status:** ✅ Fully Accessible
- **Connected Interfaces:** 16 active ports
- **CDP Neighbors:** 4 devices discovered

### 2. Nexus 3064 Datacenter Switch (core3k)
- **IP Address:** 192.168.2.244
- **Hostname:** core3k
- **Status:** ✅ Fully Accessible
- **VRF Configuration:** Management interface in dedicated VRF
- **VLANs Configured:** 57 VLANs
- **CDP Neighbors:** 2 devices discovered

---

## Issues Resolved

### 1. Network Routing Issues
**Problem:** Switches could not route traffic back to agentX (192.168.3.227)

**Root Cause:**
- Cisco 3850 had default gateway set to 192.168.2.95 (incorrect)
- Nexus 3064 management VRF had default route to 192.168.2.2 (incorrect)

**Resolution:**
- Updated Cisco 3850 default gateway to 192.168.2.1 (UniFi gateway)
- Updated Nexus 3064 management VRF default route to 192.168.2.1
- Both switches now properly route to agentX network

### 2. SSH Connectivity
**Problem:** SSH authentication failures and algorithm compatibility issues

**Resolution:**
- Fixed SSHClient to disable agent/key lookup for password authentication
- Created Nexus-specific discovery script using legacy SSH algorithms (ssh-rsa)
- Both switches now fully accessible via SSH

---

## Key Findings

### Cisco 3850 (corefc)

**Connected Interfaces (16 total):**
- **VLAN 215 (Management):** 
  - Gi1/0/3: SAN MGMT
  - Gi1/0/36: ESX OBS01 MGMT
  - Gi1/0/37: PROXMOX 02 mgmt
  - Gi1/0/40: proxmox01 mgmt
- **VLAN 1 (Default):** 8 unlabeled ports
- **VLAN 11:** 1 unlabeled port
- **Trunk Ports:**
  - Gi1/0/35: Extreme. maybe
  - Gi1/0/38: proxmox 01 ilo
  - Te1/1/3: Gateway (UniFi)
  - Te1/1/4: Fiber CORE (Nexus 3064)

**CDP Neighbors:**
- Nexus 3064 (core3k) - Connected on Gi1/0/23 and Te1/1/4
- UniFi Gateway - Connected on Te1/1/3

### Nexus 3064 (core3k)

**Configuration Highlights:**
- **VRFs:** default, management
- **VLANs:** 1 (default), 2 (Servers), 11, 211 (SAN A), 212 (SAN B), 100-150
- **Primary Role:** Core datacenter switch with trunk connections
- **Key Connections:**
  - Multiple trunk links to obs01, obs02, obs03, obs04, obs05
  - SAN networks on dedicated VLANs (211, 212)
  - Server network (VLAN 2)

**Interface Configuration:**
- Most interfaces configured as trunk ports
- SAN connections on dedicated access ports (Eth1/17, Eth1/29)
- Trunk restrictions on specific ports (Eth1/13, Eth1/23, Eth1/35)

---

## Network Topology Overview

```
UniFi Gateway (192.168.2.1)
    │
    ├── Te1/1/3 ── Cisco 3850 (corefc) ── 192.168.2.253
    │                   │
    │                   ├── Gi1/0/23 ── Nexus 3064 (core3k) ── 192.168.2.244
    │                   │
    │                   └── Te1/1/4 ── Nexus 3064 (10G fiber)
    │
    └── Management Network (VLAN 215)
            ├── Proxmox 01
            ├── Proxmox 02
            ├── ESXi OBS01
            └── SAN Management
```

---

## Data Collected

### Cisco 3850
- ✅ Interface status and descriptions
- ✅ MAC address table
- ✅ CDP neighbor details
- ✅ LLDP neighbor details
- ✅ VLAN configuration
- ✅ Routing table

### Nexus 3064
- ✅ Interface status and descriptions
- ✅ MAC address table
- ✅ CDP neighbor details
- ✅ LLDP neighbor details
- ✅ VLAN configuration
- ✅ VRF configuration
- ✅ Routing tables (global and VRF)

---

## Identified Issues

1. **Unlabeled Ports:** Multiple ports on Cisco 3850 lack descriptions
   - 8 ports on VLAN 1 with no description
   - 1 port on VLAN 11 with no description

2. **VLAN Assignment Review Needed:**
   - Several ports on default VLAN (1) that may need reassignment
   - Trunk port configurations need verification

3. **Documentation Gaps:**
   - Some interface descriptions are unclear ("Extreme. maybe")
   - Need to map MAC addresses to devices for unlabeled ports

---

## Next Steps

### Phase 4: Topology Mapping (In Progress)
- [ ] Combine discovery data from both switches
- [ ] Map physical connections using CDP/LLDP
- [ ] Correlate MAC addresses with DHCP leases from UniFi
- [ ] Create complete network topology diagram

### Phase 5: VLAN Cleanup
- [ ] Review VLAN assignments
- [ ] Label unlabeled ports based on MAC address mapping
- [ ] Restrict VLANs on access ports
- [ ] Verify trunk port configurations

### Phase 6: Verification and Documentation
- [ ] Test connectivity after changes
- [ ] Generate final network documentation
- [ ] Create switch configuration backups
- [ ] Document port assignments and VLAN structure

---

## Tools and Scripts Created

1. **discover_cisco_3850.py** - Automated discovery for Cisco 3850
2. **discover_nexus_3064.py** - Automated discovery for Nexus 3064 (legacy SSH support)
3. **SSHClient Updates** - Enhanced to support Cisco device authentication
4. **Discovery Data Files:**
   - `/home/nomad/glassdome/docs/cisco_3850_discovery.json`
   - `/home/nomad/glassdome/docs/nexus_3064_discovery.json`

---

## Recommendations

1. **Immediate Actions:**
   - Update .env file with correct Nexus IP (already done: 192.168.2.244)
   - Review and label unlabeled ports on Cisco 3850
   - Document trunk port purposes

2. **Short-term:**
   - Complete topology mapping with MAC address correlation
   - Implement VLAN restrictions on access ports
   - Create network documentation

3. **Long-term:**
   - Regular network audits
   - Automated port monitoring
   - Network diagram updates

---

## Conclusion

Network discovery phase completed successfully. Both switches are now accessible, routing is properly configured, and comprehensive configuration data has been collected. The foundation is in place for topology mapping and VLAN cleanup activities.

**Status:** ✅ Ready to proceed with Phase 4 (Topology Mapping)

---

*Report generated by AgentX - Glassdome Automation System*

