# VLAN 215 Setup on Storage Network (nic4/nic5)

## Overview

Add VLAN 215 interface to agentX VM using the storage network bridge (nic4/nic5). These interfaces are VLAN-aware and handle multiple VLANs without disrupting existing traffic.

## Key Points

- **nic4/nic5 are VLAN-aware**: They automatically handle all VLANs
- **No traffic disruption**: VLANs are isolated, adding VLAN 215 won't affect existing traffic
- **No bridge changes needed**: Just tag the VM interface with VLAN 215
- **DHCP active**: Interface will get IP automatically on VLAN 215

## Setup Steps

### Step 1: Identify Storage Network Bridge

**On Proxmox host (10.0.0.1):**

```bash
# Find which bridge uses nic4/nic5
cat /etc/network/interfaces | grep -E 'nic4|nic5' -B 2 -A 5

# Or check bridge ports
ip addr show | grep -E 'vmbr.*192.168'
bridge link show | grep -E 'nic4|nic5'
```

**Common configurations:**
- `vmbr0` uses `nic4` or `nic5` for storage network
- `vmbr1` uses `nic4` or `nic5` for storage network
- Bridge is already VLAN-aware (configured with `bridge-vlan-aware yes`)

### Step 2: Add VLAN 215 Interface to agentX VM

**On Proxmox host (10.0.0.1):**

```bash
# Replace <bridge_name> with actual bridge (vmbr0, vmbr1, etc.)
qm set 100 --net1 virtio,bridge=<bridge_name>,tag=215,firewall=0
```

**Example if vmbr0 uses nic4/nic5:**
```bash
qm set 100 --net1 virtio,bridge=vmbr0,tag=215,firewall=0
```

**Example if vmbr1 uses nic4/nic5:**
```bash
qm set 100 --net1 virtio,bridge=vmbr1,tag=215,firewall=0
```

### Step 3: Verify Interface Added

```bash
qm config 100 | grep net
```

Should show:
```
net0: virtio,bridge=vmbr3
net1: virtio,bridge=vmbr0,tag=215,firewall=0
```

### Step 4: Check IP Assignment on agentX

**On agentX VM (10.0.0.2):**

```bash
# Check for new interface
ip link show | tail -5

# Check if IP assigned via DHCP
ip addr show | grep 192.168.215

# If not assigned, wait a moment or trigger DHCP
sudo dhclient <interface_name>
```

### Step 5: Verify Connectivity

**On agentX:**

```bash
# Test connectivity to original Proxmox
ping 192.168.215.78

# Test SSH access
ssh root@192.168.215.78 "echo 'Connected to original Proxmox!' && hostname"
```

## How It Works

1. **VLAN-aware Bridge**: The bridge (vmbr0/vmbr1) that uses nic4/nic5 is configured as VLAN-aware
2. **VLAN Tagging**: Adding `tag=215` to the VM interface tells Proxmox to tag traffic with VLAN 215
3. **Automatic Handling**: nic4/nic5 automatically handle the VLAN tag - no bridge configuration changes needed
4. **Traffic Isolation**: VLAN 215 traffic is isolated from other VLANs on the same physical interface
5. **DHCP**: DHCP server on VLAN 215 assigns IP automatically

## Why This Works Without Disruption

- **VLAN Isolation**: Each VLAN is isolated at Layer 2
- **VLAN-aware Bridges**: Proxmox bridges handle multiple VLANs simultaneously
- **No Bridge Changes**: We're not modifying the bridge, just adding a tagged interface
- **Physical Interface Unchanged**: nic4/nic5 continue handling all VLANs as before

## Troubleshooting

**Interface not appearing:**
- Restart agentX VM: `qm reboot 100`
- Or wait a few seconds for interface initialization

**No IP assigned:**
- Verify DHCP is active on VLAN 215
- Check VLAN 215 is configured on network switch
- Manually request: `sudo dhclient <interface_name>`

**Cannot ping 192.168.215.78:**
- Verify original Proxmox is on 192.168.215.78
- Check VLAN 215 is configured on network switch/router
- Verify bridge is VLAN-aware: `bridge vlan show`

**Traffic disruption concerns:**
- VLANs are isolated - VLAN 215 won't affect other VLANs
- No changes to bridge configuration
- Only VM interface is modified
- Existing traffic on other VLANs continues normally

---

*Last Updated: November 24, 2024*

