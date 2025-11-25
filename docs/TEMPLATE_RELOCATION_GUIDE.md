# Proxmox Template Relocation Guide

**Purpose:** After SAN rebuild, find and relocate unlinked template files to proper Proxmox storage locations.

---

## Quick Start

```bash
# Run the template finder script
python scripts/find_and_relocate_templates.py
```

This will:
1. Connect to Proxmox
2. Search `/mnt` for template files
3. Identify file types and VM IDs
4. Suggest proper relocation locations
5. Generate relocation commands

---

## Proxmox Storage Locations

### Template Disk Images

**Location:** Storage pools (local-lvm, TrueNAS, etc.)
- Format: `STORAGE_POOL:vm-XXXX-disk-0`
- Example: `local-lvm:vm-9000-disk-0`

**Common Storage Pools:**
- `local-lvm` - Local LVM thin pool (default)
- `TrueNAS` - NFS storage (if configured)
- `local` - Local directory storage

### ISO Files

**Location:** `/var/lib/vz/template/iso/`
- Ubuntu cloud images: `ubuntu-22.04-server-cloudimg-amd64.img`
- Windows ISOs: `windows-server-2022-eval.iso`
- VirtIO drivers: `virtio-win.iso`

---

## File Patterns

The script identifies:

1. **VM Disk Images:**
   - `vm-9000-disk-0.raw` → VM ID 9000
   - `vm-9100-disk-0.qcow2` → VM ID 9100
   - `9000.raw` → VM ID 9000

2. **Ubuntu Cloud Images:**
   - `ubuntu-22.04-server-cloudimg-amd64.img`
   - `ubuntu-20.04-server-cloudimg-amd64.img`

3. **Windows ISOs:**
   - `windows-server-2022-eval.iso`
   - `windows-11-enterprise-eval.iso`

4. **VirtIO ISOs:**
   - `virtio-win.iso`

---

## Manual Relocation

### Step 1: Find Files

```bash
# Search for VM disk images
find /mnt -name "vm-*-disk-*" -type f

# Search for ISOs
find /mnt -name "*.iso" -o -name "*.img" -type f

# Search for specific VM ID
find /mnt -name "*9000*" -type f
```

### Step 2: Identify VM/Template

```bash
# On Proxmox host, check if VM exists
qm config 9000

# List all VMs and templates
qm list
```

### Step 3: Relocate Files

**For ISO Files:**
```bash
# Move to ISO directory
mv /mnt/path/to/file.iso /var/lib/vz/template/iso/
```

**For VM Disk Images:**
```bash
# If VM exists, import disk to storage pool
qm importdisk 9000 /mnt/path/to/vm-9000-disk-0.raw local-lvm

# Then attach to VM
qm set 9000 --scsi0 local-lvm:vm-9000-disk-0
```

**For Orphaned Disks (VM doesn't exist):**
```bash
# Option 1: Create new VM and import
qm create 9000 --name template-name --memory 2048 --cores 2
qm importdisk 9000 /mnt/path/to/vm-9000-disk-0.raw local-lvm
qm set 9000 --scsi0 local-lvm:vm-9000-disk-0

# Option 2: Move to storage pool manually (advanced)
# Requires understanding of Proxmox storage structure
```

---

## Common Template IDs

Based on your setup:

- **9000** - Ubuntu 22.04 template
- **9001** - Ubuntu 20.04 template
- **9100** - Windows Server 2022 template
- **9101** - Windows 11 template (actually Windows 10)
- **9102** - Windows 10 template

---

## Verification

After relocation:

```bash
# Check VM config
qm config 9000

# Check storage
pvesm list local-lvm

# List ISOs
ls -lh /var/lib/vz/template/iso/
```

---

## Troubleshooting

### "VM not found"

If VM ID doesn't exist in Proxmox:
- File might be orphaned from deleted VM
- Check if you need to recreate the VM
- Or file might belong to a different Proxmox instance

### "Storage pool not found"

Check available storage:
```bash
pvesm status
```

Use the correct storage pool name from the list.

### "Permission denied"

Ensure you're running as root on Proxmox host:
```bash
ssh root@proxmox-host
```

## Template Migration from Original Proxmox

If templates need to be migrated from the original Proxmox server (192.168.215.78) via VLAN 10 network, see:

- **[PROXMOX_VLAN10_TEMPLATE_MIGRATION.md](PROXMOX_VLAN10_TEMPLATE_MIGRATION.md)** - Complete migration guide with network setup

This process:
1. Configures VLAN 10 network on both Proxmox servers
2. Discovers templates on original Proxmox (10.0.0.3)
3. Downloads and migrates template disks to current Proxmox
4. Verifies templates are accessible

---

*Last Updated: November 24, 2024*

