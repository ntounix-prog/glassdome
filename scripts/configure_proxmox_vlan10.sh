#!/bin/bash
# Proxmox VLAN 10 Network Configuration Script
# Configures vmbr3 with VLAN 10 on storage network for template migration

set -e

PROXMOX_IP=$1
PROXMOX_IP_NEW=$2  # New IP in 10.0.0.0/24 (e.g., 10.0.0.3 or 10.0.0.77)
STORAGE_NIC=$3      # Storage network interface (nic4 or nic5)

if [ -z "$PROXMOX_IP" ] || [ -z "$PROXMOX_IP_NEW" ] || [ -z "$STORAGE_NIC" ]; then
    echo "Usage: $0 <current_proxmox_ip> <new_ip_10.0.0.x> <storage_nic>"
    echo "Example: $0 192.168.215.78 10.0.0.3 nic4"
    echo "Example: $0 192.168.215.77 10.0.0.77 nic4"
    exit 1
fi

echo "=========================================="
echo "Proxmox VLAN 10 Network Configuration"
echo "=========================================="
echo "Proxmox IP: $PROXMOX_IP"
echo "New IP: $PROXMOX_IP_NEW"
echo "Storage NIC: $STORAGE_NIC"
echo ""

# Step 1: Identify storage network interface
echo "Step 1: Verifying storage network interface..."
ssh root@$PROXMOX_IP "ip link show | grep -E 'nic4|nic5|ens|enp' | head -5"
echo ""

# Step 2: Backup current network configuration
echo "Step 2: Backing up /etc/network/interfaces..."
ssh root@$PROXMOX_IP "cp /etc/network/interfaces /etc/network/interfaces.backup.\$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup created"
echo ""

# Step 3: Check if vmbr3 already exists
echo "Step 3: Checking for existing vmbr3..."
if ssh root@$PROXMOX_IP "grep -q '^auto vmbr3' /etc/network/interfaces"; then
    echo "⚠️  vmbr3 already exists in /etc/network/interfaces"
    echo "   Please review and update manually if needed"
else
    echo "✅ vmbr3 not found, will add configuration"
fi
echo ""

# Step 4: Generate network configuration
echo "Step 4: Generating vmbr3 configuration..."
cat > /tmp/vmbr3_config.txt <<EOF
# VLAN 10 bridge for template migration network
auto vmbr3
iface vmbr3 inet static
    address $PROXMOX_IP_NEW/24
    bridge-ports $STORAGE_NIC
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 10
EOF

echo "Configuration to add:"
cat /tmp/vmbr3_config.txt
echo ""

# Step 5: Add configuration to Proxmox
echo "Step 5: Adding configuration to /etc/network/interfaces..."
echo "   (This will append the configuration to the file)"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

ssh root@$PROXMOX_IP "cat >> /etc/network/interfaces" < /tmp/vmbr3_config.txt
echo "✅ Configuration added"
echo ""

# Step 6: Apply configuration
echo "Step 6: Applying network configuration..."
echo "   Bringing up vmbr3..."
ssh root@$PROXMOX_IP "ifup vmbr3" || {
    echo "⚠️  ifup failed, trying alternative method..."
    ssh root@$PROXMOX_IP "systemctl restart networking"
}
echo ""

# Step 7: Verify configuration
echo "Step 7: Verifying configuration..."
echo "Checking vmbr3 interface:"
ssh root@$PROXMOX_IP "ip addr show vmbr3"
echo ""

echo "Checking bridge status:"
ssh root@$PROXMOX_IP "bridge link show vmbr3"
echo ""

echo "Testing connectivity from agentX..."
if ping -c 2 -W 2 $PROXMOX_IP_NEW > /dev/null 2>&1; then
    echo "✅ Successfully pinged $PROXMOX_IP_NEW"
else
    echo "⚠️  Cannot ping $PROXMOX_IP_NEW yet (may need time to establish)"
fi
echo ""

echo "=========================================="
echo "Configuration Complete"
echo "=========================================="
echo "Proxmox is now accessible at: $PROXMOX_IP_NEW"
echo "Verify connectivity: ping $PROXMOX_IP_NEW"
echo ""

