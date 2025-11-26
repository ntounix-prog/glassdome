#!/bin/bash
#
# Create Ubuntu 22.04 Cloud-Init Template on Proxmox
# Run this ON the Proxmox host (pve01) via SSH
#
# Usage: ssh root@192.168.215.78 'bash -s' < scripts/create_ubuntu_template.sh
#

set -e

# Configuration
VMID=9001
VM_NAME="ubuntu-2204-cloudinit-local"
STORAGE="local-lvm"
CLOUD_IMAGE_URL="https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img"
CLOUD_IMAGE_FILE="/var/lib/vz/template/iso/jammy-server-cloudimg-amd64.img"

echo "========================================"
echo "Creating Ubuntu 22.04 Cloud-Init Template"
echo "========================================"
echo "  VMID:    $VMID"
echo "  Name:    $VM_NAME"
echo "  Storage: $STORAGE"
echo "========================================"

# Check if VM already exists
if qm status $VMID &>/dev/null; then
    echo "WARNING: VM $VMID already exists"
    read -p "Delete and recreate? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting existing VM..."
        qm destroy $VMID --purge
    else
        echo "Aborting."
        exit 1
    fi
fi

# Download cloud image if not exists
if [ ! -f "$CLOUD_IMAGE_FILE" ]; then
    echo "Downloading Ubuntu cloud image..."
    wget -O "$CLOUD_IMAGE_FILE" "$CLOUD_IMAGE_URL"
else
    echo "Cloud image already exists: $CLOUD_IMAGE_FILE"
fi

# Create VM
echo "Creating VM $VMID..."
qm create $VMID --name "$VM_NAME" --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0

# Import disk to local-lvm
echo "Importing disk to $STORAGE..."
qm importdisk $VMID "$CLOUD_IMAGE_FILE" $STORAGE

# Attach disk
echo "Attaching disk..."
qm set $VMID --scsihw virtio-scsi-pci --scsi0 $STORAGE:vm-$VMID-disk-0

# Add cloud-init drive
echo "Adding cloud-init drive..."
qm set $VMID --ide2 $STORAGE:cloudinit

# Set boot order
echo "Setting boot order..."
qm set $VMID --boot c --bootdisk scsi0

# Enable serial console (for cloud-init output)
echo "Enabling serial console..."
qm set $VMID --serial0 socket --vga serial0

# Enable QEMU guest agent
echo "Enabling QEMU guest agent..."
qm set $VMID --agent enabled=1

# Convert to template
echo "Converting to template..."
qm template $VMID

echo ""
echo "========================================"
echo "Template created successfully!"
echo "========================================"
echo "  VMID:    $VMID"
echo "  Name:    $VM_NAME"
echo "  Storage: $STORAGE (local)"
echo ""
echo "You can now clone this template for new VMs."
echo "Update TEMPLATE_ID in deploy_prod_server.py to: $VMID"
echo "========================================"

