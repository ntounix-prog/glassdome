# VLAN Cleanup and Security Proposal

**Date:** November 24, 2024  
**Prepared By:** AgentX - Glassdome Automation System  
**Status:** Proposal for Review

---

## Executive Summary

This proposal outlines a comprehensive VLAN cleanup and security hardening plan for both Cisco switches. Based on network discovery and device mapping, we've identified several security concerns and optimization opportunities in the current VLAN configuration.

**Key Issues Identified:**
- Excessive use of default VLAN (1) for production devices
- Trunk ports allowing all VLANs (security risk)
- Unused VLANs consuming resources
- Access ports not properly restricted
- Missing VLAN restrictions on trunk ports

**Proposed Changes:**
- Restrict access ports to single VLANs
- Limit trunk ports to required VLANs only
- Move devices off default VLAN where appropriate
- Remove unused VLANs
- Implement VLAN access restrictions

---

## 1. Current VLAN Analysis

### Cisco 3850 (corefc) - Current State

#### VLAN Inventory
| VLAN ID | Name | Status | Ports | Purpose |
|---------|------|--------|-------|---------|
| 1 | default | Active | 35+ ports | **SECURITY RISK** - Too many devices |
| 2 | Servers | Active | 2 ports (Gi1/0/47, Gi1/0/48) | Server network |
| 11 | DMZ | Active | 1 port (Gi1/0/4) | DMZ network |
| 20 | WLAN20 | Active | 0 ports | **UNUSED** |
| 30 | Automation | Active | 0 ports | **UNUSED** |
| 40 | DRM | Active | 0 ports | **UNUSED** |
| 215 | MGMT | Active | 4 ports | Management network |
| 1002-1005 | Legacy | Active | N/A | **OBSOLETE** |

#### Security Concerns

1. **VLAN 1 (Default) - Critical Security Issue**
   - 35+ ports assigned to default VLAN
   - Many production devices on default VLAN
   - Default VLAN should be reserved for unused ports only
   - **Risk:** VLAN 1 is often targeted in attacks, no isolation

2. **Trunk Ports - Security Risk**
   - Gi1/0/35: "Extreme. maybe" - Trunk allowing all VLANs
   - Gi1/0/38: "proxmox 01 ilo" - Trunk allowing all VLANs
   - Te1/1/3: "Gateway" - Trunk allowing all VLANs
   - Te1/1/4: "Fiber CORE" - Trunk allowing all VLANs
   - **Risk:** Unrestricted trunk ports allow VLAN hopping attacks

3. **Unused VLANs**
   - VLAN 20 (WLAN20) - No ports assigned
   - VLAN 30 (Automation) - No ports assigned
   - VLAN 40 (DRM) - No ports assigned
   - **Impact:** Resource consumption, confusion

4. **Legacy VLANs**
   - VLANs 1002-1005 (FDDI, Token Ring) - Obsolete protocols
   - **Impact:** Configuration clutter

### Nexus 3064 (core3k) - Current State

#### VLAN Inventory
| VLAN ID | Name | Status | Ports | Purpose |
|---------|------|--------|-------|---------|
| 1 | default | Active | 48+ ports | **SECURITY RISK** - Trunk default |
| 2 | Servers | Active | 48+ ports | Server network (trunk) |
| 11 | (from config) | Active | Trunk restricted | Unknown purpose |
| 211 | VLAN0211 | Active | 48+ ports | SAN A side |
| 212 | VLAN0212 | Active | 48+ ports | SAN B side |
| 100-150 | (from config) | Active | Eth1/35 only | Range for obs05 |

#### Security Concerns

1. **Excessive Trunk Ports**
   - Most ports configured as trunks with all VLANs
   - Only specific ports have restrictions (Eth1/13, Eth1/23, Eth1/35)
   - **Risk:** VLAN hopping, unauthorized access

2. **Trunk Port Restrictions**
   - Eth1/13: Allows VLANs 2, 11, 212
   - Eth1/23: Allows VLANs 2, 11, 211
   - Eth1/35: Allows VLANs 1, 100-150
   - **Good:** Some restrictions exist, but more needed

3. **Access Ports**
   - Eth1/10: Access VLAN 212 (SAN B)
   - Eth1/17: Access VLAN 211 (SAN A)
   - Eth1/29: Access VLAN 212 (SAN B)
   - **Good:** SAN ports properly configured as access

---

## 2. Proposed VLAN Structure

### Recommended VLAN Assignments

#### Cisco 3850

| VLAN ID | Name | Purpose | Ports | Type |
|---------|------|---------|-------|------|
| 1 | default | Unused ports only | Unused ports | Access |
| 2 | Servers | Server network | Gi1/0/47, Gi1/0/48 | Access |
| 11 | DMZ | DMZ network | Gi1/0/4 | Access |
| 215 | MGMT | Management network | Gi1/0/3, Gi1/0/36, Gi1/0/37, Gi1/0/40 | Access |
| Trunk | - | Inter-switch links | Gi1/0/23, Te1/1/4 | Trunk (restricted) |
| Trunk | - | Gateway connection | Te1/1/3 | Trunk (restricted) |

#### Device-to-VLAN Mapping (Cisco 3850)

Based on device discovery:

| Port | Device | Current VLAN | Proposed VLAN | Reason |
|------|--------|-------------|---------------|--------|
| Gi1/0/3 | truenas | 215 | 215 | ✅ Correct (Management) |
| Gi1/0/4 | Unknown | 11 | 11 | ✅ Correct (DMZ) |
| Gi1/0/5 | MyCloud-GWHRKK | 1 | **2** | Move to Servers VLAN |
| Gi1/0/7 | rh01.summit.local | 1 | **2** | Move to Servers VLAN |
| Gi1/0/9 | Unknown | 1 | **Investigate** | Identify device first |
| Gi1/0/11 | hubv3-03011107833 | 1 | **2** | Move to Servers VLAN |
| Gi1/0/13 | Unknown | 1 | **Investigate** | Identify device first |
| Gi1/0/17 | Unknown | 1 | **Investigate** | Identify device first |
| Gi1/0/23 | Nexus-3064-mgmt | 1 | **Trunk** | Should be trunk with restrictions |
| Gi1/0/35 | Extreme. maybe | Trunk | **Trunk (restricted)** | Restrict allowed VLANs |
| Gi1/0/36 | ESX OBS01 MGMT | 215 | 215 | ✅ Correct |
| Gi1/0/37 | agentX | 215 | 215 | ✅ Correct |
| Gi1/0/38 | proxmox 01 ilo | Trunk | **Trunk (restricted)** | Restrict allowed VLANs |
| Gi1/0/40 | proxmox01 mgmt | 215 | 215 | ✅ Correct |
| Te1/1/3 | Gateway | Trunk | **Trunk (restricted)** | Restrict to required VLANs |
| Te1/1/4 | Nexus-3064-fiber | Trunk | **Trunk (restricted)** | Restrict to required VLANs |

---

## 3. Security Hardening Recommendations

### 3.1 Access Port Restrictions

**Current Issue:** Access ports may allow multiple VLANs or have no restrictions.

**Recommendation:** Configure all access ports with explicit VLAN assignment and disable trunk negotiation.

**Cisco 3850 Configuration:**
```cisco
interface GigabitEthernet1/0/5
  description MyCloud-GWHRKK (192.168.2.111)
  switchport mode access
  switchport access vlan 2
  switchport nonegotiate
  spanning-tree portfast
```

### 3.2 Trunk Port Restrictions

**Current Issue:** Trunk ports allow all VLANs by default.

**Recommendation:** Restrict trunk ports to only required VLANs.

**Cisco 3850 Configuration:**
```cisco
interface TenGigabitEthernet1/1/3
  description Gateway (UniFi)
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215
  switchport trunk native vlan 1
  switchport nonegotiate

interface TenGigabitEthernet1/1/4
  description Nexus-3064-core3k-fiber-10G
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215,211,212
  switchport trunk native vlan 1
  switchport nonegotiate

interface GigabitEthernet1/0/23
  description Nexus-3064-core3k-mgmt
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215
  switchport trunk native vlan 1
  switchport nonegotiate
```

### 3.3 Unused Port Security

**Current Issue:** Unused ports remain on default VLAN with no restrictions.

**Recommendation:** Disable unused ports or configure port security.

**Cisco 3850 Configuration:**
```cisco
interface GigabitEthernet1/0/6
  description Unused
  switchport mode access
  switchport access vlan 1
  shutdown
```

### 3.4 VLAN Cleanup

**Remove Unused VLANs:**
- VLAN 20 (WLAN20) - No ports assigned
- VLAN 30 (Automation) - No ports assigned
- VLAN 40 (DRM) - No ports assigned
- VLANs 1002-1005 (Legacy protocols) - Obsolete

**Cisco 3850 Configuration:**
```cisco
no vlan 20
no vlan 30
no vlan 40
no vlan 1002
no vlan 1003
no vlan 1004
no vlan 1005
```

### 3.5 Nexus 3064 Trunk Restrictions

**Current Issue:** Most trunk ports allow all VLANs.

**Recommendation:** Apply VLAN restrictions to all trunk ports based on actual requirements.

**Nexus 3064 Configuration:**
```cisco
interface Ethernet1/5
  description Cisco-3850-fiber-10G
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215,211,212
  switchport trunk native vlan 1
```

---

## 4. Implementation Plan

### Phase 1: Preparation (Week 1)

1. **Backup Current Configuration**
   - Backup Cisco 3850 configuration
   - Backup Nexus 3064 configuration
   - Document current state

2. **Device Identification**
   - Identify devices on ports Gi1/0/9, Gi1/0/13, Gi1/0/17
   - Verify device requirements for VLAN assignments
   - Confirm device IP addresses and network requirements

3. **Change Window Planning**
   - Schedule maintenance window
   - Notify stakeholders
   - Prepare rollback plan

### Phase 2: VLAN Cleanup (Week 1-2)

1. **Remove Unused VLANs**
   - Remove VLANs 20, 30, 40
   - Remove legacy VLANs 1002-1005
   - Verify no dependencies

2. **Move Devices to Appropriate VLANs**
   - Move Gi1/0/5 (MyCloud) to VLAN 2
   - Move Gi1/0/7 (rh01) to VLAN 2
   - Move Gi1/0/11 (hubv3) to VLAN 2
   - Verify connectivity after each move

3. **Configure Access Ports**
   - Set explicit access mode on all access ports
   - Add `switchport nonegotiate` to prevent trunk negotiation
   - Enable `spanning-tree portfast` on access ports

### Phase 3: Trunk Port Hardening (Week 2)

1. **Restrict Trunk Ports**
   - Apply VLAN restrictions to Te1/1/3 (Gateway)
   - Apply VLAN restrictions to Te1/1/4 (Nexus fiber)
   - Apply VLAN restrictions to Gi1/0/23 (Nexus mgmt)
   - Apply VLAN restrictions to Gi1/0/35 (Extreme)
   - Apply VLAN restrictions to Gi1/0/38 (Proxmox iLO)

2. **Verify Connectivity**
   - Test inter-VLAN routing
   - Verify gateway connectivity
   - Test management network access

### Phase 4: Unused Port Security (Week 2)

1. **Disable Unused Ports**
   - Identify all unused ports
   - Shutdown unused ports
   - Add descriptions for future reference

2. **Port Security (Optional)**
   - Configure port security on access ports
   - Limit MAC addresses per port
   - Configure violation actions

### Phase 5: Verification and Documentation (Week 2-3)

1. **Connectivity Testing**
   - Test all device connectivity
   - Verify VLAN isolation
   - Test inter-VLAN routing
   - Verify management access

2. **Documentation**
   - Update network diagrams
   - Document VLAN assignments
   - Create port assignment matrix
   - Update change log

---

## 5. Risk Assessment

### Implementation Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|------------|------------|
| Service disruption during changes | High | Medium | Change window, gradual rollout, rollback plan |
| Incorrect VLAN assignment | Medium | Low | Pre-change verification, testing after each change |
| Trunk port misconfiguration | High | Low | Careful VLAN list verification, connectivity testing |
| Device connectivity loss | High | Medium | Immediate rollback capability, device-by-device changes |

### Security Risks (If Not Implemented)

| Risk | Impact | Probability | Current State |
|------|--------|------------|---------------|
| VLAN hopping attacks | High | Medium | Trunk ports allow all VLANs |
| Unauthorized network access | High | Medium | Default VLAN used for production |
| Network reconnaissance | Medium | High | Unrestricted trunk ports |
| Configuration drift | Medium | High | No VLAN restrictions enforced |

---

## 6. Configuration Examples

### Cisco 3850 - Complete Access Port Configuration

```cisco
! Access port for server on VLAN 2
interface GigabitEthernet1/0/5
  description MyCloud-GWHRKK (192.168.2.111)
  switchport mode access
  switchport access vlan 2
  switchport nonegotiate
  spanning-tree portfast
  no shutdown

! Access port for management on VLAN 215
interface GigabitEthernet1/0/37
  description agentX (192.168.215.228)
  switchport mode access
  switchport access vlan 215
  switchport nonegotiate
  spanning-tree portfast
  no shutdown
```

### Cisco 3850 - Restricted Trunk Port Configuration

```cisco
! Trunk to UniFi Gateway - restricted VLANs
interface TenGigabitEthernet1/1/3
  description Gateway (UniFi)
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215
  switchport trunk native vlan 1
  switchport nonegotiate
  no shutdown

! Trunk to Nexus 3064 - restricted VLANs
interface TenGigabitEthernet1/1/4
  description Nexus-3064-core3k-fiber-10G
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215,211,212
  switchport trunk native vlan 1
  switchport nonegotiate
  no shutdown
```

### Nexus 3064 - Trunk Port Restrictions

```cisco
! Trunk to Cisco 3850 - restricted VLANs
interface Ethernet1/5
  description Cisco-3850-fiber-10G
  switchport mode trunk
  switchport trunk allowed vlan 1,2,11,215,211,212
  switchport trunk native vlan 1
  no shutdown
```

---

## 7. Success Criteria

### Security Improvements

- ✅ All access ports restricted to single VLAN
- ✅ All trunk ports restricted to required VLANs only
- ✅ Production devices moved off default VLAN
- ✅ Unused VLANs removed
- ✅ Unused ports disabled

### Operational Improvements

- ✅ Clear VLAN structure and purpose
- ✅ Complete port documentation
- ✅ Reduced attack surface
- ✅ Improved network isolation
- ✅ Easier troubleshooting

### Verification

- ✅ All devices can reach intended networks
- ✅ Inter-VLAN routing works correctly
- ✅ Management network accessible
- ✅ No service disruptions
- ✅ Configuration backed up

---

## 8. Timeline

### Week 1: Preparation and Planning
- **Days 1-2:** Device identification and verification
- **Days 3-4:** Configuration backup and change window scheduling
- **Day 5:** Final review and approval

### Week 2: Implementation
- **Days 1-2:** VLAN cleanup (remove unused VLANs)
- **Days 3-4:** Device migration and access port configuration
- **Day 5:** Trunk port restrictions

### Week 3: Verification
- **Days 1-2:** Connectivity testing
- **Days 3-4:** Documentation updates
- **Day 5:** Final verification and sign-off

**Total Duration:** 3 weeks

---

## 9. Approval and Next Steps

### Required Approvals

- [ ] Network team approval
- [ ] Security team approval
- [ ] Change management approval
- [ ] Stakeholder notification

### Immediate Next Steps

1. **Review and Approve Proposal**
   - Review VLAN assignments
   - Verify device requirements
   - Approve implementation timeline

2. **Schedule Change Window**
   - Coordinate with stakeholders
   - Schedule maintenance window
   - Prepare rollback procedures

3. **Begin Phase 1**
   - Start device identification
   - Begin configuration backups
   - Prepare change documentation

---

## 10. Conclusion

This VLAN cleanup proposal addresses critical security concerns while improving network organization and maintainability. The proposed changes will:

- **Enhance Security:** Restrict VLAN access, prevent VLAN hopping
- **Improve Organization:** Clear VLAN structure, proper device placement
- **Reduce Risk:** Eliminate unused VLANs, secure trunk ports
- **Facilitate Maintenance:** Better documentation, easier troubleshooting

**Recommendation:** Approve and proceed with implementation following the phased approach outlined in this proposal.

---

*Proposal prepared by AgentX - Glassdome Automation System*  
*For questions or clarifications, please contact the network team.*

