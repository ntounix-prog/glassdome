#!/bin/bash
# Add VLAN 215 to storage network (nic4/nic5) without disrupting traffic
# These interfaces are VLAN-aware and can handle multiple VLANs

set -e

PROXMOX_HOST="10.0.0.1"
AGENTX_VMID=100

echo "=========================================="
echo "Add VLAN 215 to Storage Network (nic4/nic5)"
echo "=========================================="
echo "This will add VLAN 215 to existing storage network bridge"
echo "Storage network interfaces (nic4/nic5) are VLAN-aware"
echo "No traffic disruption - VLANs are isolated"
echo ""

# Step 1: Identify which bridge uses nic4/nic5
echo "Step 1: Identifying storage network bridge..."
echo ""
echo "Run on Proxmox host to find bridge:"
echo "  ssh root@$PROXMOX_HOST"
echo "  cat /etc/network/interfaces | grep -E 'nic4|nic5' -B 2 -A 5"
echo "  ip addr show | grep -E 'vmbr.*192.168'"
echo ""

# Common scenario: vmbr0 or vmbr1 uses nic4/nic5 for storage
# We'll add VLAN 215 tag to the VM interface, bridge handles it

echo "Step 2: Add VLAN 215 interface to agentX VM"
echo "The bridge (vmbr0/vmbr1) that uses nic4/nic5 is VLAN-aware"
echo "We just need to tag the VM interface with VLAN 215"
echo ""
echo "Command to run on Proxmox:"
echo "  qm set $AGENTX_VMID --net1 virtio,bridge=<bridge_name>,tag=215,firewall=0"
echo ""
echo "Where <bridge_name> is the bridge that uses nic4 or nic5"
echo ""
echo "Example (if vmbr0 uses nic4/nic5):"
echo "  qm set $AGENTX_VMID --net1 virtio,bridge=vmbr0,tag=215,firewall=0"
echo ""
echo "Example (if vmbr1 uses nic4/nic5):"
echo "  qm set $AGENTX_VMID --net1 virtio,bridge=vmbr1,tag=215,firewall=0"
echo ""

echo "=========================================="
echo "Important Notes"
echo "=========================================="
echo "1. nic4/nic5 are VLAN-aware - they handle all VLANs automatically"
echo "2. Adding VLAN 215 tag to VM interface won't disrupt existing traffic"
echo "3. VLANs are isolated - traffic on VLAN 215 won't affect other VLANs"
echo "4. DHCP on VLAN 215 will assign IP automatically"
echo "5. No changes needed to Proxmox host network config"
echo ""

echo "After adding interface, agentX will get IP via DHCP on VLAN 215"
echo "Then you can access 192.168.215.78 directly"

