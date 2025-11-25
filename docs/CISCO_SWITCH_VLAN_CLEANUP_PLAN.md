# Cisco Switch VLAN Cleanup and Network Discovery - Implementation Plan

## Overview
This plan outlines the comprehensive approach to discover network topology, map physical connections, analyze traffic patterns, and implement proper VLAN assignments on Cisco Nexus 3064 (datacenter) and Cisco 3850-48 (POE) switches. The plan integrates with Ubiquiti gateway to build a complete network topology map.

## Phase 1: Environment Setup

### 1.1 Add Network Device Credentials to .env
Add placeholders to env.example and .env for:
- Nexus 3064: SSH host, username, password
- Cisco 3850: SSH host, username, password  
- Ubiquiti Gateway: Access method (SSH/API), host, credentials

**Placeholders needed:**
```
# Cisco Nexus 3064 (Datacenter Switch)
NEXUS_3064_HOST=your-nexus-3064-ip
NEXUS_3064_USER=admin
NEXUS_3064_PASSWORD=your-nexus-password
NEXUS_3064_SSH_PORT=22

# Cisco 3850-48 (POE Switch)
CISCO_3850_HOST=your-cisco-3850-ip
CISCO_3850_USER=admin
CISCO_3850_PASSWORD=your-cisco-3850-password
CISCO_3850_SSH_PORT=22

# Ubiquiti Gateway
UBIQUITI_GATEWAY_HOST=your-ubiquiti-gateway-ip
UBIQUITI_GATEWAY_USER=ubnt
UBIQUITI_GATEWAY_PASSWORD=your-ubiquiti-password
UBIQUITI_ACCESS_METHOD=ssh  # or 'api' if using UniFi API
UBIQUITI_SSH_PORT=22
```

## Phase 2: Network Discovery Infrastructure

### 2.1 Create Network Device Client Classes
**File**: `glassdome/network/cisco_client.py`
- `CiscoSwitchClient` - Base class for Cisco switch operations
- `Nexus3064Client` - Specialized for Nexus 3064 (NX-OS)
- `Cisco3850Client` - Specialized for Cisco 3850 (IOS-XE)
- Methods: `get_port_status()`, `get_mac_address_table()`, `get_interface_config()`, `get_vlan_config()`, `get_cdp_neighbors()`, `get_lldp_neighbors()`

**File**: `glassdome/network/ubiquiti_client.py`
- `UbiquitiGatewayClient` - For Ubiquiti gateway access
- Methods: `get_routing_table()`, `get_dhcp_leases()`, `get_interface_status()`, `get_firewall_rules()`

### 2.2 Create Discovery Scripts
**File**: `scripts/network_discovery/discover_switch_ports.py`
- Connect to switches via SSH
- Collect: port status, MAC addresses, CDP/LLDP neighbors, VLAN assignments
- Output: JSON mapping of ports to devices/MACs

**File**: `scripts/network_discovery/analyze_traffic.py`
- Monitor switch port statistics (bytes in/out, packet counts)
- Capture traffic patterns over time period (e.g., 5-15 minutes)
- Identify active vs inactive ports
- Correlate traffic with VLANs

**File**: `scripts/network_discovery/map_topology.py`
- Combine switch data with Ubiquiti gateway data
- Map IP addresses to MAC addresses (DHCP leases)
- Build complete topology: Switch Port → MAC → IP → Device Name
- Generate network diagram data

## Phase 3: Network Discovery Execution

### 3.1 Port Discovery
**Commands to execute on switches:**

**Nexus 3064 (NX-OS):**
```bash
show interface status          # Port status
show mac address-table        # MAC to port mapping
show cdp neighbors detail     # Connected devices
show lldp neighbors detail    # LLDP neighbors
show vlan                     # VLAN configuration
show interface ethernet X/Y   # Per-port details
```

**Cisco 3850 (IOS-XE):**
```bash
show interfaces status        # Port status
show mac address-table        # MAC to port mapping
show cdp neighbors detail     # Connected devices
show lldp neighbors detail    # LLDP neighbors
show vlan brief               # VLAN configuration
show interfaces gigabitEthernet X/Y/X  # Per-port details
```

### 3.2 Traffic Monitoring
- Enable port statistics collection
- Monitor for 5-15 minutes to capture traffic patterns
- Identify which ports are actively used
- Correlate traffic with VLAN assignments

### 3.3 Gateway Integration
- Query Ubiquiti gateway for DHCP leases
- Map IP addresses to MAC addresses
- Get routing table and interface status
- Identify VLAN-to-subnet mappings

## Phase 4: Topology Mapping and Analysis

### 4.1 Build Network Map
**File**: `scripts/network_discovery/build_topology.py`
- Combine all discovery data
- Create mapping: Switch → Port → MAC → IP → Device
- Identify unknown/unlabeled devices
- Generate topology visualization data

### 4.2 VLAN Analysis
- Identify current VLAN assignments per port
- Detect misconfigured VLANs (ports in wrong VLANs)
- Identify untagged vs tagged ports
- Find ports that should be trunk vs access

### 4.3 Generate Discovery Report
**File**: `scripts/network_discovery/generate_report.py`
- Create comprehensive discovery report
- Include: port mappings, VLAN assignments, traffic patterns
- Highlight issues and recommendations
- Export to JSON/CSV for review

## Phase 5: VLAN Cleanup and Configuration

### 5.1 Create VLAN Configuration Plan
Based on discovery:
- Define proper VLAN assignments per port
- Identify which ports should be access vs trunk
- Determine VLAN restrictions needed
- Plan for minimal disruption

### 5.2 Implement VLAN Changes
**File**: `scripts/network_discovery/configure_vlans.py`
- Apply VLAN assignments to ports
- Configure access ports (single VLAN)
- Configure trunk ports (multiple VLANs with tagging)
- Set up VLAN restrictions
- Add port descriptions/labels

**Nexus 3064 Configuration:**
```bash
interface ethernet X/Y
  description Device-Name-or-Purpose
  switchport mode access
  switchport access vlan XXX
  # OR for trunk:
  switchport mode trunk
  switchport trunk allowed vlan XXX,YYY,ZZZ
```

**Cisco 3850 Configuration:**
```bash
interface GigabitEthernet X/Y/X
  description Device-Name-or-Purpose
  switchport mode access
  switchport access vlan XXX
  # OR for trunk:
  switchport mode trunk
  switchport trunk allowed vlan XXX,YYY,ZZZ
```

### 5.3 Port Labeling
- Add descriptions to all ports based on discovered devices
- Document in switch configuration
- Update network documentation

## Phase 6: Verification and Documentation

### 6.1 Verify Configuration
- Test connectivity after VLAN changes
- Verify devices can reach intended networks
- Check for connectivity issues
- Monitor for errors

### 6.2 Generate Final Documentation
**File**: `docs/NETWORK_TOPOLOGY.md`
- Complete network topology map
- Port assignments and descriptions
- VLAN configuration
- Device inventory

**File**: `docs/SWITCH_CONFIGURATION.md`
- Switch configurations
- VLAN assignments
- Port descriptions
- Backup of configurations

## Implementation Files

**New files to create:**
1. `glassdome/network/__init__.py`
2. `glassdome/network/cisco_client.py` - Cisco switch client
3. `glassdome/network/ubiquiti_client.py` - Ubiquiti gateway client
4. `scripts/network_discovery/discover_switch_ports.py`
5. `scripts/network_discovery/analyze_traffic.py`
6. `scripts/network_discovery/map_topology.py`
7. `scripts/network_discovery/build_topology.py`
8. `scripts/network_discovery/generate_report.py`
9. `scripts/network_discovery/configure_vlans.py`
10. `docs/NETWORK_TOPOLOGY.md`
11. `docs/SWITCH_CONFIGURATION.md`

**Files to modify:**
1. `env.example` - Add network device credentials section
2. `glassdome/core/config.py` - Add network device config loading

## Safety Considerations

1. **Dry-run mode**: All configuration changes should support `--dry-run` flag
2. **Backup configurations**: Save switch configs before making changes
3. **Gradual rollout**: Apply changes port-by-port or VLAN-by-VLAN
4. **Rollback plan**: Keep original configs for quick rollback
5. **Monitoring**: Monitor for errors after each change
6. **Documentation**: Document all changes made

## Dependencies

- `paramiko` - Already available for SSH
- `netmiko` - May need to add for better Cisco device support
- `textfsm` - For parsing Cisco command output (optional but helpful)

## Questions for Clarification

1. **Ubiquiti Gateway Model**: What model is the Ubiquiti gateway? (UniFi, EdgeRouter, etc.) This determines API vs SSH access.
2. **VLAN Strategy**: Do you have a target VLAN structure in mind, or should we discover and recommend based on traffic patterns?
3. **Discovery Duration**: How long should we monitor traffic? (5-15 minutes recommended)
4. **Change Approval**: Should changes require manual approval, or can we apply them automatically after review?

---

**Status**: Plan ready for review. Implementation will begin once credentials are added to .env and any clarifications are provided.

**Next Steps**:
1. Add network device credentials to .env file
2. Answer clarification questions (if any)
3. Begin Phase 1 implementation