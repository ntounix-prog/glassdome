# Proxmox Template Migration via Direct Network Access

## Overview

Add a secondary network interface to agentX and server VM on the 192.168.215.0/24 network to enable direct access to the original Proxmox server (192.168.215.78) for optimal template migration without VLAN configuration.

## Network Architecture

### Current Setup (✅ COMPLETED)
- **agentX**: 
  - Primary: 192.168.3.227/24 (ens19) - original network
  - Secondary: 192.168.215.228/24 (ens18) - VLAN 215 network with DHCP
- **Current Proxmox**: 192.168.215.77 (accessible via ens18)
- **Original Proxmox**: 192.168.215.78 (accessible via ens18)

### Network Configuration
- **agentX** has direct access to both Proxmox servers on 192.168.215.0/24
- **Interface**: ens18 (192.168.215.228/24) - DHCP assigned
- **Routing**: Default route via 192.168.215.1 (metric 100)
- **Direct Access**: agentX → 192.168.215.78 (original Proxmox) ✅
- **Direct Access**: agentX → 192.168.215.77 (current Proxmox) ✅
- **Note**: 10.0.0.0/24 management network is NOT required for template migration

## Phase 1: Network Interface Configuration

### Step 1: Identify Network Bridge on Current Proxmox

**Find bridge for 192.168.215.0/24 network:**

```bash
# On current Proxmox (192.168.215.77)
ip addr show | grep 192.168.215
# Or check /etc/network/interfaces for bridge configuration
cat /etc/network/interfaces | grep -A 5 192.168.215
```

**Common bridge names:**
- `vmbr0` - Usually main network
- `vmbr1` - Secondary network
- `vmbr2` - Additional network

### Step 2: Add Secondary Interface to agentX VM

**On Current Proxmox (via API or CLI):**

```bash
# Get current agentX VM ID (likely 100 based on management network)
qm config 100

# Add secondary network interface (no gateway, static IP)
qm set 100 --net1 virtio,bridge=<bridge_name>,firewall=0

# Example if bridge is vmbr0:
qm set 100 --net1 virtio,bridge=vmbr0,firewall=0
```

**Or via Proxmox API:**
- Use ProxmoxClient to add network interface
- Configure static IP via cloud-init or manual configuration

### Step 3: Configure Static IP on agentX

**On agentX VM:**

```bash
# Identify new interface
ip addr show
# Look for new interface (usually ens7, ens8, or eth1)

# Configure static IP (example: 192.168.215.10)
sudo ip addr add 192.168.215.10/24 dev <interface_name>
sudo ip link set <interface_name> up

# Or configure via netplan (Ubuntu)
sudo nano /etc/netplan/50-cloud-init.yaml
# Add:
#   network:
#     version: 2
#     ethernets:
#       <interface_name>:
#         addresses:
#           - 192.168.215.10/24
#         # No gateway specified

# Apply:
sudo netplan apply
```

**Important**: Do NOT add a default gateway for this interface to avoid routing conflicts.

### Step 4: Add Secondary Interface to Server VM

**Same process as Step 2-3, but for server VM:**
- Add network interface via Proxmox
- Configure static IP on 192.168.215.0/24
- No default gateway

### Step 5: Verify Connectivity ✅ COMPLETED

```bash
# From agentX (192.168.215.228)
ping 192.168.215.78  # Original Proxmox ✅
ping 192.168.215.77  # Current Proxmox ✅

# Test API access
curl -k https://192.168.215.78:8006/api2/json/version  # Returns 401 (needs auth) ✅
curl -k https://192.168.215.77:8006/api2/json/version  # Returns 401 (needs auth) ✅
```

**Status**: Network connectivity verified. Both Proxmox servers are accessible.

## Phase 2: Template Discovery and Migration

### Discovery

**Direct access to original Proxmox:**

```bash
# From agentX, connect directly to 192.168.215.78
ssh root@192.168.215.78

# Find templates
find /mnt/esxstore -name "vm-*-disk-*" -type f
pvesh get /nodes/<node>/qemu
```

### Migration

**Use existing migration script with updated IP:**

```bash
# Run migration script with original Proxmox IP
python3 scripts/migrate_templates_from_original_proxmox.py --original-ip 192.168.215.78

# Or use default current Proxmox (192.168.215.77) and specify original
python3 scripts/migrate_templates_from_original_proxmox.py \
    --original-ip 192.168.215.78 \
    --original-proxmox-instance 02  # If configured as instance 02
```

## Implementation Script

### File: `scripts/add_secondary_network_interface.py`

**Features:**
1. **Identify Bridge**: Find correct bridge for 192.168.215.0/24
2. **Add Interface**: Add secondary network interface to VM
3. **Configure IP**: Configure static IP on VM (no gateway)
4. **Verify**: Test connectivity to original Proxmox

**Key Functions:**
- `find_network_bridge(proxmox_client, network: str) -> str`: Find bridge for network
- `add_network_interface(proxmox_client, vm_id: int, bridge: str) -> bool`: Add interface
- `configure_static_ip(vm_host: str, interface: str, ip: str) -> bool`: Configure IP
- `verify_connectivity(source_ip: str, target_ip: str) -> bool`: Test connectivity

## Advantages of This Approach

1. **Direct Access**: No VLAN configuration needed
2. **Simpler**: Uses existing network infrastructure
3. **Optimal**: Direct connection, no routing overhead
4. **Flexible**: Can access any host on 192.168.215.0/24
5. **No Gateway Conflicts**: Secondary interface has no gateway

## Safety Considerations

1. **No Default Gateway**: Prevents routing conflicts
2. **Static Routes**: May need static routes for specific subnets
3. **Firewall**: Ensure firewall allows access on new interface
4. **IP Conflicts**: Choose IPs that don't conflict with existing hosts

## Files to Create/Modify

1. **New**: `scripts/add_secondary_network_interface.py` - Network interface configuration
2. **New**: `docs/PROXMOX_DIRECT_NETWORK_TEMPLATE_MIGRATION.md` - This document
3. **Update**: `scripts/migrate_templates_from_original_proxmox.py` - Support 192.168.215.78
4. **Update**: `docs/PROXMOX_VLAN10_TEMPLATE_MIGRATION.md` - Add reference to this approach

---

*Last Updated: November 24, 2024*

