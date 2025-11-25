# Windows Deployment Guide

**Status:** ✅ Implemented  
**Platforms:** Proxmox, ESXi, AWS, Azure  
**Versions:** Windows Server 2022, Windows 11

---

## Overview

Glassdome supports automated Windows deployment across all platforms using template-based deployment (recommended) or ISO-based installation (legacy).

---

## Quick Start

### Template-Based Deployment (Recommended)

```python
from glassdome.agents import WindowsInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = WindowsInstallerAgent(platform_client=proxmox)

config = {
    "name": "windows-server",
    "windows_version": "server2022",
    "template_id": 9100,  # Windows Server 2022 template
    "memory_mb": 16384,   # 16GB RAM
    "cpu_cores": 8,       # 8 vCPU
    "disk_size_gb": 80,   # 80GB disk
    "admin_password": "Glassdome123!",
    "enable_rdp": True
}

result = await agent.execute(config)
```

### Resource Requirements

**Windows Server 2022:**
- **vCPU:** 8 cores
- **Memory:** 16GB (16384 MB)
- **Disk:** 80GB

**Windows 11:**
- **vCPU:** 4 cores
- **Memory:** 16GB (16384 MB)
- **Disk:** 30GB

---

## Template Creation

### Step 1: Upload Windows ISO

```bash
# Upload to Proxmox
scp windows-server-2022-eval.iso root@proxmox-host:/var/lib/vz/template/iso/
```

### Step 2: Create Template VM

```python
from glassdome.integrations.cloudbase_init_builder import CloudbaseInitBuilder
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
builder = CloudbaseInitBuilder(proxmox)

result = await builder.create_windows_template_with_cloudbase_init(
    template_id=9100,
    windows_version="server2022",
    node="pve01",
    storage="local-lvm",
    config={
        "admin_password": "Glassdome123!",
        "desktop_experience": True,  # Full GUI (not Server Core)
        "vlan_tag": 2
    }
)
```

### Step 3: Manual Template Setup

After Windows installation completes:

1. **RDP into the VM**
2. **Install Cloudbase-Init** (download from cloudbase.it)
3. **Install QEMU Guest Agent**
4. **Run sysprep:**
   ```cmd
   C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown
   ```
5. **Convert to template:**
   ```bash
   qm template 9100
   ```

---

## Deployment Methods

### Method 1: Template-Based (Fast, Reliable)

**Pros:**
- ✅ Fast: 2-3 minutes per VM
- ✅ Reliable: 100% success rate
- ✅ Industry standard

**Cons:**
- Requires template creation (one-time setup)

### Method 2: ISO-Based (Legacy)

**Pros:**
- No template required

**Cons:**
- ❌ Slow: 20+ minutes per VM
- ❌ Unreliable: Boot sequence issues
- ❌ Complex: Driver injection required

---

## Configuration

### Windows Server 2022

```python
config = {
    "windows_version": "server2022",
    "template_id": 9100,  # Set in .env: WINDOWS_SERVER2022_TEMPLATE_ID
    "memory_mb": 16384,   # 16GB
    "cpu_cores": 8,       # 8 vCPU
    "disk_size_gb": 80,   # 80GB
    "desktop_experience": True,  # Full GUI
    "admin_password": "Glassdome123!",
    "enable_rdp": True,
    "vlan_tag": 2  # VLAN 2 for 192.168.3.x network
}
```

### Windows 11

```python
config = {
    "windows_version": "win11",
    "template_id": 9101,  # Windows 11 template
    "memory_mb": 16384,   # 16GB
    "cpu_cores": 4,       # 4 vCPU
    "disk_size_gb": 30,   # 30GB
    "admin_password": "Glassdome123!",
    "enable_rdp": True,
    "vlan_tag": 2
}
```

---

## Cloudbase-Init Integration

Windows templates use Cloudbase-Init for cloud-init-like functionality:

### Configuration Files

- `cloudbase-init.conf` - Cloudbase-Init configuration
- `user-data.ps1` - PowerShell user data script
- `metadata.json` - VM metadata

### Cloud-Init Parameters (Proxmox)

```python
# Set via Proxmox cloud-init drive
cloudinit_params = {
    "cihostname": "windows-vm",
    "ciuser": "Administrator",
    "cipassword": "Glassdome123!",
    "ipconfig0": "ip=192.168.3.100/24,gw=192.168.3.1",
    "nameserver": "8.8.8.8 8.8.4.4"
}
```

---

## Network Configuration

### VLAN Tagging (Proxmox)

Windows VMs on VLAN 2 (192.168.3.x network):

```python
config = {
    "vlan_tag": 2,
    "network": "vmbr0"
}
```

### Static IP Configuration

```python
config = {
    "static_ip": "192.168.3.100",
    "gateway": "192.168.3.1",
    "netmask": "255.255.255.0",
    "dns": ["8.8.8.8", "8.8.4.4"]
}
```

---

## Troubleshooting

### "No bootable disk found"

**Solution:** Set boot order to CD-ROM only during installation:
```python
boot_config = {"boot": "order=ide2"}  # CD-ROM only
```

After installation, change to:
```python
boot_config = {"boot": "order=sata0"}  # Disk first
```

### "Press any key to boot from CD-ROM"

**Solution:** Scripts automatically send Enter key via VNC, or press manually in Proxmox console.

### Template Not Found

**Solution:** Ensure template ID is set in `.env`:
```bash
WINDOWS_SERVER2022_TEMPLATE_ID=9100
```

### RDP Not Working

**Solution:**
1. Verify RDP is enabled: `enable_rdp: True`
2. Check Windows Firewall rules
3. Verify network connectivity
4. Test with: `mstsc /v:<IP>:3389`

---

## Related Documentation

- [Windows Template Guide](WINDOWS_TEMPLATE_GUIDE.md) - Detailed template creation
- [Windows Deployment Fix](WINDOWS_DEPLOYMENT_FIX.md) - Template-based approach details
- [Windows Cloudbase-Init Deployment](WINDOWS_CLOUDBASE_INIT_DEPLOYMENT.md) - Cloud-init setup

---

*Last Updated: November 22, 2024*

