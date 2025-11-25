# Windows 11 Deployment Status

**Date:** November 22, 2024  
**Status:** ✅ Ready for Deployment

---

## Current State

### VM 9101 (Windows 11 Template)

**Configuration:**
- **Status:** Configured and ready
- **Memory:** 16GB (16384 MB) ✅
- **CPU:** 4 vCPU ✅
- **Disk:** 30GB ✅
- **Network:** VLAN 2 (192.168.3.x) ✅
- **ISO:** windows-11-enterprise-eval.iso attached ✅
- **Boot Order:** CD-ROM (ide2) ✅

**Location:** Proxmox node `pve01`

---

## Deployment Methods

### Method 1: Automated Script (Recommended)

```bash
python scripts/setup_windows11_complete.py
```

This script will:
1. ✅ Find/upload Windows 11 ISO (if needed)
2. ✅ Configure VM with correct specs (4 vCPU, 16GB RAM, 30GB disk)
3. ✅ Generate autounattend.xml for Windows 11
4. ✅ Upload autounattend floppy
5. ✅ Attach ISOs (Windows 11 + VirtIO drivers)
6. ✅ Set boot order
7. ✅ Start VM and send Enter key

### Method 2: Using WindowsInstallerAgent

```python
from glassdome.agents import WindowsInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = WindowsInstallerAgent(platform_client=proxmox)

config = {
    "name": "windows11-vm",
    "windows_version": "win11",
    "memory_mb": 16384,   # 16GB
    "cpu_cores": 4,       # 4 vCPU
    "disk_size_gb": 30,   # 30GB
    "admin_password": "Glassdome123!",
    "enable_rdp": True,
    "vlan_tag": 2
}

result = await agent.execute(config)
```

---

## Resource Requirements

**Windows 11:**
- **vCPU:** 4 cores (required)
- **Memory:** 16GB (16384 MB) - required
- **Disk:** 30GB - minimum (Windows 11 requires at least 11GB)

---

## Configuration Details

### Autounattend.xml

Windows 11 uses:
- **Image Index:** 1 (Windows 11 Enterprise)
- **Image Name:** Windows 11 Enterprise
- **Desktop Experience:** Always enabled (Windows 11 is GUI-only)

### Network

- **VLAN:** 2 (for 192.168.3.x network)
- **Static IP:** Allocated via IP pool manager
- **Gateway:** 192.168.3.1
- **DNS:** 8.8.8.8, 8.8.4.4

---

## Troubleshooting

### VM Won't Boot

**Check:**
1. Boot order is set to `order=ide2` (CD-ROM)
2. Windows 11 ISO is attached to ide2
3. VM has sufficient resources (4 vCPU, 16GB RAM)

**Fix:**
```bash
# Check boot order
qm config 9101 | grep boot

# Set boot order if needed
qm set 9101 --boot order=ide2
```

### Installation Hangs

**Check:**
1. Autounattend floppy is attached
2. VirtIO drivers ISO is attached (ide3)
3. Disk is large enough (30GB minimum)

**Fix:**
- Monitor in Proxmox console
- Check if "Press any key" prompt appears
- Script automatically sends Enter key via VNC

### Wrong Windows Version Installs

**Issue:** Windows Server 2022 installs instead of Windows 11

**Solution:**
- Verify correct ISO is attached: `windows-11-enterprise-eval.iso`
- Check autounattend.xml uses `windows_version: "win11"`
- Verify image_index is "1" for Windows 11

---

## Next Steps

### For Template Creation

After Windows 11 installation completes:

1. **RDP into VM** (use allocated IP)
2. **Install Cloudbase-Init** (download from cloudbase.it)
3. **Install QEMU Guest Agent**
4. **Run sysprep:**
   ```cmd
   C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown
   ```
5. **Convert to template:**
   ```bash
   qm template 9101
   ```

### For Deployment

Once template is created:

```python
config = {
    "name": "windows11-vm",
    "windows_version": "win11",
    "template_id": 9101,  # Use template
    "memory_mb": 16384,
    "cpu_cores": 4,
    "disk_size_gb": 30
}

result = await agent.execute(config)
```

---

## Verification

Run the test script to verify everything is ready:

```bash
python scripts/test_windows11_deployment.py
```

This will check:
- ✅ autounattend.xml generation
- ✅ Windows 11 defaults
- ✅ ISO availability
- ✅ VM 9101 configuration

---

## Related Documentation

- [Windows Deployment Guide](WINDOWS_DEPLOYMENT.md) - Complete Windows deployment guide
- [Windows Template Guide](WINDOWS_TEMPLATE_GUIDE.md) - Template creation details

---

*Last Updated: November 22, 2024*

