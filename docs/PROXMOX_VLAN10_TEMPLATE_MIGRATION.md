# Proxmox Template Migration via VLAN 10 Network

## Overview

This guide documents the process of migrating template disks from the original Proxmox server (192.168.215.78) to the current Proxmox server via a VLAN 10 network connection. This enables template recovery without disrupting running services.

## Network Architecture

### Original Setup
- **Original Proxmox**: 192.168.215.78 (not accessible from agentX)
- **Current Proxmox**: 192.168.215.77 (accessible)
- **agentX**: 10.0.0.2 (management network)

### New VLAN 10 Network
- **Original Proxmox**: 10.0.0.3 (VLAN 10 on storage network)
- **Current Proxmox**: 10.0.0.77 (VLAN 10 on storage network)
- **agentX**: 10.0.0.2 (can reach 10.0.0.0/24)

### Network Configuration
- **Bridge**: vmbr3 (VLAN-aware)
- **VLAN**: 10
- **Interface**: Storage network (nic4 or nic5)
- **Network**: 10.0.0.0/24

## Phase 1: Network Configuration

### Step 1: Configure Original Proxmox (192.168.215.78 → 10.0.0.3)

**Prerequisites:**
- SSH access to 192.168.215.78
- Root access
- Identify storage network interface (nic4 or nic5)

**Configuration:**

```bash
# 1. Identify storage network interface
ip link show | grep -E "nic4|nic5|ens|enp"

# 2. Backup network configuration
cp /etc/network/interfaces /etc/network/interfaces.backup.$(date +%Y%m%d_%H%M%S)

# 3. Edit /etc/network/interfaces
# Add vmbr3 configuration:
auto vmbr3
iface vmbr3 inet static
    address 10.0.0.3/24
    bridge-ports <storage_nic>  # Replace with actual interface (nic4 or nic5)
    bridge-stp off
    bridge-fd 0
    bridge-vlan-aware yes
    bridge-vids 10

# 4. Apply configuration
ifup vmbr3
# Or restart networking:
systemctl restart networking
```

**Or use the automated script:**

```bash
./scripts/configure_proxmox_vlan10.sh 192.168.215.78 10.0.0.3 nic4
```

### Step 2: Configure Current Proxmox (192.168.215.77 → 10.0.0.77)

**Same process as Step 1, but with different IP:**

```bash
./scripts/configure_proxmox_vlan10.sh 192.168.215.77 10.0.0.77 nic4
```

### Step 3: Verify Network Connectivity

```bash
# From agentX (10.0.0.2)
ping 10.0.0.3   # Original Proxmox
ping 10.0.0.77  # Current Proxmox

# From original Proxmox (10.0.0.3)
ping 10.0.0.2   # agentX
ping 10.0.0.77  # Current Proxmox

# From current Proxmox (10.0.0.77)
ping 10.0.0.2   # agentX
ping 10.0.0.3   # Original Proxmox
```

## Phase 2: Template Discovery

### Templates to Migrate

- **9000**: Ubuntu 22.04 template
- **9100**: Windows Server 2022 template
- **9101**: Windows 11 template

### Discovery Methods

The migration script uses three methods to find templates:

1. **Proxmox API**: Queries VM list and configuration
2. **Filesystem Search**: Searches `/mnt/esxstore/` and `/var/lib/vz/images/`
3. **Storage Pool Search**: Searches all storage pools for template disks

### Manual Discovery Commands

```bash
# Via Proxmox API (from agentX):
pvesh get /nodes/<node>/qemu
pvesh get /nodes/<node>/qemu/9000/config

# Via SSH (on original Proxmox):
find /mnt/esxstore -name "vm-*-disk-*" -type f
find /var/lib/vz/images -name "vm-*-disk-*" -type f
pvesm list local-lvm
```

## Phase 3: Template Migration

### Automated Migration

**Dry Run (Recommended First):**

```bash
cd /home/nomad/glassdome
python3 scripts/migrate_templates_from_original_proxmox.py
```

**Execute Migration:**

```bash
python3 scripts/migrate_templates_from_original_proxmox.py --execute
```

### Migration Process

1. **Network Verification**: Tests connectivity to 10.0.0.3
2. **Template Discovery**: Finds templates via API, filesystem, and storage pools
3. **Disk Download**: Downloads template disks to agentX temporary storage
4. **Disk Import**: Imports disks to current Proxmox using `qm importdisk`
5. **Verification**: Verifies templates are accessible on target Proxmox

### Manual Migration Steps

**Step 1: Download Template Disk**

```bash
# From agentX, download disk from original Proxmox
scp root@10.0.0.3:/mnt/esxstore/vm-9000-disk-0.raw /tmp/vm-9000-disk-0.raw
```

**Step 2: Import to Current Proxmox**

```bash
# From agentX, import to current Proxmox
scp /tmp/vm-9000-disk-0.raw root@10.0.0.77:/tmp/
ssh root@10.0.0.77 "qm importdisk 9000 /tmp/vm-9000-disk-0.raw local-lvm"
```

**Step 3: Attach Disk to VM**

```bash
# If VM exists and is stopped
ssh root@10.0.0.77 "qm set 9000 --scsi0 local-lvm:vm-9000-disk-0"
```

**Step 4: Convert to Template (if needed)**

```bash
ssh root@10.0.0.77 "qm template 9000"
```

## Safety Features

### Low-Impact Operations

- **Dry-run mode**: Default mode shows what would be done without making changes
- **VM status checks**: Only attaches disks if VM is stopped or is a template
- **Non-disruptive**: Uses `qm importdisk` which doesn't require VM shutdown
- **Detailed logging**: All operations are logged for audit

### Error Handling

- Network connectivity verification before operations
- Disk space checks before downloads
- Template verification after import
- Graceful error handling with detailed messages

## Troubleshooting

### Network Issues

**Problem**: Cannot ping 10.0.0.3 from agentX

**Solutions**:
1. Verify VLAN 10 is configured on both Proxmox servers
2. Check bridge configuration: `ip addr show vmbr3`
3. Verify storage network interface is correct
4. Check firewall rules: `iptables -L`

**Problem**: Bridge not coming up

**Solutions**:
1. Check interface name: `ip link show`
2. Verify interface is not in use by another bridge
3. Check for syntax errors in `/etc/network/interfaces`
4. Review logs: `journalctl -u networking`

### Template Discovery Issues

**Problem**: Templates not found via API

**Solutions**:
1. Verify Proxmox API credentials in `.env`
2. Check if templates exist: `pvesh get /nodes/<node>/qemu`
3. Try filesystem search instead
4. Check storage pool names

**Problem**: Disk files not found

**Solutions**:
1. Verify search paths exist: `ls -la /mnt/esxstore`
2. Check file permissions
3. Try different search paths
4. Use manual discovery commands

### Migration Issues

**Problem**: Download fails or times out

**Solutions**:
1. Check disk space on agentX: `df -h /tmp`
2. Verify network connectivity during transfer
3. Try smaller chunks or use `rsync` with resume
4. Check file size: Large files may need more time

**Problem**: Import fails

**Solutions**:
1. Verify disk space on target Proxmox storage pool
2. Check storage pool name: `pvesm status`
3. Verify VM ID doesn't conflict
4. Check Proxmox logs: `journalctl -u pve-cluster`

**Problem**: Disk attachment fails

**Solutions**:
1. Verify VM is stopped: `qm status <vmid>`
2. Check if disk slot is available
3. Verify disk format is compatible
4. Check VM configuration: `qm config <vmid>`

## Files and Scripts

### Scripts

- **`scripts/configure_proxmox_vlan10.sh`**: Network configuration script
- **`scripts/migrate_templates_from_original_proxmox.py`**: Main migration script

### Documentation

- **`docs/PROXMOX_VLAN10_TEMPLATE_MIGRATION.md`**: This file
- **`docs/TEMPLATE_RELOCATION_GUIDE.md`**: General template relocation guide

## Verification

After migration, verify templates are accessible:

```bash
# List templates on current Proxmox
pvesh get /nodes/<node>/qemu | grep template

# Check specific template
pvesh get /nodes/<node>/qemu/9000/config

# Verify disk is attached
qm config 9000 | grep scsi0
```

## Related Documentation

- [Template Relocation Guide](TEMPLATE_RELOCATION_GUIDE.md)
- [Multi-Proxmox Support](MULTI_PROXMOX_SUPPORT.md)
- [Windows Template Guide](WINDOWS_TEMPLATE_GUIDE.md)

---

*Last Updated: November 24, 2024*

