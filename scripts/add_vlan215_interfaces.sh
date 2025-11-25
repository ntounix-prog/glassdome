#!/bin/bash
# Add VLAN 215 interfaces to Proxmox host and agentX VM
# DHCP will assign IPs automatically

set -e

PROXMOX_HOST="10.0.0.1"
AGENTX_VMID=100  # Adjust if different

echo "=========================================="
echo "Add VLAN 215 Interfaces for Direct Access"
echo "=========================================="
echo "Proxmox Host: $PROXMOX_HOST"
echo "agentX VM ID: $AGENTX_VMID"
echo "VLAN: 215"
echo "Network: 192.168.215.0/24 (DHCP)"
echo ""

# Step 1: Find bridge for 192.168.215.0/24 on Proxmox
echo "Step 1: Finding bridge for 192.168.215.0/24..."
echo "Run on Proxmox host (10.0.0.1):"
echo "  ip addr show | grep 192.168.215"
echo "  cat /etc/network/interfaces | grep -A 5 192.168.215"
echo ""
read -p "Enter bridge name (e.g., vmbr0, vmbr1): " BRIDGE_NAME

if [ -z "$BRIDGE_NAME" ]; then
    echo "❌ Bridge name required"
    exit 1
fi

echo ""
echo "Step 2: Adding network interface to agentX VM..."
echo "Command to run on Proxmox ($PROXMOX_HOST):"
echo "  qm set $AGENTX_VMID --net1 virtio,bridge=$BRIDGE_NAME,tag=215,firewall=0"
echo ""

read -p "Execute this command? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    ssh root@$PROXMOX_HOST "qm set $AGENTX_VMID --net1 virtio,bridge=$BRIDGE_NAME,tag=215,firewall=0"
    echo "✅ Interface added to agentX VM"
else
    echo "Skipped. Run manually:"
    echo "  ssh root@$PROXMOX_HOST 'qm set $AGENTX_VMID --net1 virtio,bridge=$BRIDGE_NAME,tag=215,firewall=0'"
fi

echo ""
echo "Step 3: Restart agentX VM network (or reboot VM)"
echo "The new interface should get an IP via DHCP on VLAN 215"
echo ""

echo "Step 4: Verify connectivity"
echo "After VM gets IP, test:"
echo "  ping 192.168.215.78"
echo "  ssh root@192.168.215.78 'echo Connected'"
echo ""

echo "=========================================="
echo "Configuration Complete"
echo "=========================================="

