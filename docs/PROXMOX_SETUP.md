# Proxmox Setup for Glassdome

## Getting Ubuntu Images: The Practical Guide

### Where Do Ubuntu Images Come From?

You have **3 options** for getting Ubuntu images into Proxmox:

---

## Option 1: Cloud Images (RECOMMENDED) ⭐

Cloud images are pre-built, cloud-init ready, and optimized for automation.

### Step 1: Download Ubuntu Cloud Image

```bash
# SSH into your Proxmox host
ssh root@your-proxmox-host

# Go to template storage
cd /var/lib/vz/template/iso

# Download Ubuntu 22.04 cloud image
wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img

# Download Ubuntu 20.04 cloud image
wget https://cloud-images.ubuntu.com/releases/20.04/release/ubuntu-20.04-server-cloudimg-amd64.img
```

**Available versions:**
- https://cloud-images.ubuntu.com/releases/22.04/release/
- https://cloud-images.ubuntu.com/releases/20.04/release/
- https://cloud-images.ubuntu.com/releases/24.04/release/

### Step 2: Create Proxmox Template from Cloud Image

```bash
# Create VM template (ID 9000 for Ubuntu 22.04)
qm create 9000 \
  --name ubuntu-2204-cloudinit-template \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0

# Import cloud image as disk
qm importdisk 9000 ubuntu-22.04-server-cloudimg-amd64.img local-lvm

# Attach disk to VM
qm set 9000 \
  --scsihw virtio-scsi-pci \
  --scsi0 local-lvm:vm-9000-disk-0

# Add cloud-init drive
qm set 9000 --ide2 local-lvm:cloudinit

# Set boot disk
qm set 9000 --boot c --bootdisk scsi0

# Add serial console
qm set 9000 --serial0 socket --vga serial0

# Enable QEMU guest agent
qm set 9000 --agent enabled=1

# Convert to template
qm template 9000
```

**Now you have:** Template ID 9000 ready to clone!

### Step 3: Test Template

```bash
# Clone template to create a VM
qm clone 9000 100 --name test-ubuntu-vm --full

# Set cloud-init credentials
qm set 100 \
  --ciuser ubuntu \
  --cipassword mysecretpassword \
  --ipconfig0 ip=dhcp

# Start VM
qm start 100

# Wait for boot (30 seconds)
sleep 30

# Get IP address
qm guest exec 100 -- ip -4 addr show | grep inet

# SSH into VM
ssh ubuntu@<ip-address>
# Password: mysecretpassword
```

---

## Option 2: ISO Installation (Traditional)

Download regular Ubuntu ISO and install manually (then convert to template).

### Step 1: Download ISO

```bash
# SSH into Proxmox
cd /var/lib/vz/template/iso

# Download Ubuntu Server ISO
wget https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso
```

### Step 2: Create VM and Install

```bash
# Create VM
qm create 9001 \
  --name ubuntu-2204-template \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0 \
  --cdrom local:iso/ubuntu-22.04.3-live-server-amd64.iso \
  --scsi0 local-lvm:32

# Start VM
qm start 9001

# Open VNC console and manually install Ubuntu
# Proxmox Web UI → VM 9001 → Console
```

### Step 3: Prepare for Template

After installation, clean up the VM:

```bash
# SSH into the VM
ssh ubuntu@vm-ip

# Remove machine-specific files
sudo apt clean
sudo rm -rf /var/lib/cloud/instances/*
sudo rm /etc/machine-id /var/lib/dbus/machine-id
sudo touch /etc/machine-id
sudo truncate -s 0 /etc/hostname
sudo rm /etc/netplan/*.yaml
sudo cloud-init clean

# Shutdown
sudo poweroff
```

Convert to template:

```bash
# Back on Proxmox host
qm template 9001
```

---

## Option 3: Pre-built Proxmox Templates

Some Proxmox installations have pre-configured templates available.

Check your Proxmox storage:

```bash
# List available templates
pveam available | grep ubuntu

# Download template (if available)
pveam download local ubuntu-22.04-standard_22.04-1_amd64.tar.zst
```

---

## Automated Template Creation Script

Let's make this easier:

```bash
#!/bin/bash
# create-ubuntu-template.sh

# Configuration
TEMPLATE_ID=${1:-9000}
UBUNTU_VERSION=${2:-22.04}
TEMPLATE_NAME="ubuntu-${UBUNTU_VERSION//.}-cloudinit-template"
STORAGE="local-lvm"

echo "Creating Ubuntu ${UBUNTU_VERSION} template (ID: ${TEMPLATE_ID})..."

# Download cloud image
cd /tmp
IMAGE_FILE="ubuntu-${UBUNTU_VERSION}-server-cloudimg-amd64.img"
wget -q "https://cloud-images.ubuntu.com/releases/${UBUNTU_VERSION}/release/${IMAGE_FILE}" \
  -O "${IMAGE_FILE}" || { echo "Download failed"; exit 1; }

echo "✅ Downloaded cloud image"

# Create VM
qm create ${TEMPLATE_ID} \
  --name ${TEMPLATE_NAME} \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0 \
  > /dev/null

echo "✅ Created VM ${TEMPLATE_ID}"

# Import disk
qm importdisk ${TEMPLATE_ID} ${IMAGE_FILE} ${STORAGE} > /dev/null

echo "✅ Imported disk"

# Configure VM
qm set ${TEMPLATE_ID} \
  --scsihw virtio-scsi-pci \
  --scsi0 ${STORAGE}:vm-${TEMPLATE_ID}-disk-0 \
  --ide2 ${STORAGE}:cloudinit \
  --boot c \
  --bootdisk scsi0 \
  --serial0 socket \
  --vga serial0 \
  --agent enabled=1 \
  > /dev/null

echo "✅ Configured VM"

# Convert to template
qm template ${TEMPLATE_ID} > /dev/null

echo "✅ Converted to template"
echo ""
echo "Template created: ${TEMPLATE_NAME} (ID: ${TEMPLATE_ID})"
echo "Clone with: qm clone ${TEMPLATE_ID} <new-vm-id> --name <vm-name> --full"

# Cleanup
rm -f ${IMAGE_FILE}
```

Save and run:

```bash
chmod +x create-ubuntu-template.sh

# Create Ubuntu 22.04 template (ID 9000)
./create-ubuntu-template.sh 9000 22.04

# Create Ubuntu 20.04 template (ID 9001)
./create-ubuntu-template.sh 9001 20.04
```

---

## Verify Templates Exist

```bash
# List all templates
qm list | grep template

# Should see:
# 9000  ubuntu-2204-cloudinit-template  stopped
# 9001  ubuntu-2004-cloudinit-template  stopped
```

---

## Template ID Convention

We'll use this convention in Glassdome:

| OS | Version | Template ID | Template Name |
|----|---------|-------------|---------------|
| Ubuntu | 22.04 | 9000 | `ubuntu-2204-cloudinit-template` |
| Ubuntu | 20.04 | 9001 | `ubuntu-2004-cloudinit-template` |
| Kali | 2024.1 | 9100 | `kali-2024-cloudinit-template` |
| Debian | 12 | 9200 | `debian-12-cloudinit-template` |
| CentOS | 9 | 9300 | `centos-9-cloudinit-template` |

---

## Proxmox API Access

Enable API access for Glassdome:

### Step 1: Create API Token

```bash
# In Proxmox Web UI:
# Datacenter → Permissions → API Tokens → Add

# Or via CLI:
pveum user token add glassdome@pam glassdome-token \
  --privsep 0 \
  --expire 0
  
# Save the token secret (only shown once!)
```

### Step 2: Set Permissions

```bash
# Grant VM admin permissions
pveum aclmod / -user glassdome@pam -role Administrator
```

### Step 3: Test API Access

```bash
# Install proxmoxer
pip install proxmoxer requests

# Test connection
python3 << EOF
from proxmoxer import ProxmoxAPI

proxmox = ProxmoxAPI(
    'your-proxmox-host',
    user='glassdome@pam',
    token_name='glassdome-token',
    token_value='your-secret-token',
    verify_ssl=False
)

# List nodes
nodes = proxmox.nodes.get()
print("Proxmox nodes:", [n['node'] for n in nodes])

# List templates
templates = [vm for vm in proxmox.nodes('pve').qemu.get() if vm.get('template')]
print("Templates:", [t['name'] for t in templates])
EOF
```

---

## Environment Configuration for Glassdome

Update your `.env` file:

```bash
# Proxmox Configuration
PROXMOX_HOST=your-proxmox-host.local
PROXMOX_USER=glassdome@pam
PROXMOX_TOKEN_NAME=glassdome-token
PROXMOX_TOKEN_VALUE=your-secret-token
PROXMOX_VERIFY_SSL=false
PROXMOX_NODE=pve

# Ubuntu Template IDs
UBUNTU_2204_TEMPLATE_ID=9000
UBUNTU_2004_TEMPLATE_ID=9001
KALI_2024_TEMPLATE_ID=9100
```

---

## Summary

**To get Ubuntu images working in Glassdome:**

1. ✅ **Create cloud-init templates in Proxmox** (use the script above)
2. ✅ **Enable API access** (create token)
3. ✅ **Configure `.env`** (add Proxmox credentials)
4. ✅ **Verify templates exist** (template IDs 9000, 9001, etc.)

**Now we can implement the actual VM creation in the agents!**

---

## Next: Implement ProxmoxClient

See `docs/PROXMOX_INTEGRATION.md` for the actual implementation.

