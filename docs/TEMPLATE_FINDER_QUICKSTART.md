# Quick Start: Find Templates in /mnt

Since the Proxmox host at `10.0.0.1` is on the management network (vmbr3) and not directly accessible, run these commands **directly on the Proxmox server**.

---

## Option 1: Run Commands on Proxmox Server

**SSH to Proxmox:**
```bash
# Use the actual Proxmox IP (not 10.0.0.1 - that's management network)
# Check your .env for the real Proxmox host IP
ssh root@<actual-proxmox-ip>
```

**Then run:**
```bash
# Copy the script to Proxmox and run it
# Or run these commands directly:

# Find VM disk images
find /mnt -type f -name "vm-*-disk-*" -size +100M -exec ls -lh {} \; 2>/dev/null

# Find all disk images
find /mnt -type f \( -name "*.qcow2" -o -name "*.raw" -o -name "*.img" \) -size +100M -exec ls -lh {} \; 2>/dev/null

# Find ISOs
find /mnt -type f -name "*.iso" -size +100M -exec ls -lh {} \; 2>/dev/null

# Find Ubuntu cloud images
find /mnt -type f -name "*ubuntu*cloudimg*" -exec ls -lh {} \; 2>/dev/null

# Find Windows ISOs
find /mnt -type f -name "*windows*.iso" -exec ls -lh {} \; 2>/dev/null
```

---

## Option 2: Use the Script File

**Copy script to Proxmox:**
```bash
# From your local machine
scp scripts/find_templates_proxmox_commands.sh root@<proxmox-ip>:/tmp/

# SSH to Proxmox
ssh root@<proxmox-ip>

# Run script
bash /tmp/find_templates_proxmox_commands.sh
```

---

## Option 3: Run from Glassdome VM

If your Glassdome VM is on the management network (vmbr3) and can reach `10.0.0.1`:

```bash
# From Glassdome VM
python3 scripts/find_templates_simple.py /mnt
```

---

## What to Look For

**Template Disk Images:**
- `vm-9000-disk-0.raw` → Ubuntu 22.04 template
- `vm-9100-disk-0.raw` → Windows Server 2022 template
- `vm-9101-disk-0.raw` → Windows 11 template (actually Windows 10)
- `vm-9102-disk-0.raw` → Windows 10 template

**ISOs:**
- `ubuntu-22.04-server-cloudimg-amd64.img`
- `windows-server-2022-eval.iso`
- `windows-11-enterprise-eval.iso`
- `virtio-win.iso`

---

## Relocation Commands

**For ISOs:**
```bash
mv /mnt/path/to/file.iso /var/lib/vz/template/iso/
```

**For VM Disks:**
```bash
# Check if VM exists
qm config 9000

# Import disk to storage pool
qm importdisk 9000 /mnt/path/to/vm-9000-disk-0.raw local-lvm

# Attach to VM
qm set 9000 --scsi0 local-lvm:vm-9000-disk-0
```

---

*Last Updated: November 22, 2024*

