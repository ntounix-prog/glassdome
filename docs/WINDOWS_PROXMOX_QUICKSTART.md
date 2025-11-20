# Windows Server 2022 on Proxmox - Quick Start

## Overview
Deploy Windows Server 2022 VMs on Proxmox with:
- ✅ **Automated installation** via autounattend.xml
- ✅ **Static IP assignment** from IP pool (192.168.3.30-40)
- ✅ **VirtIO drivers** pre-configured
- ✅ **RDP enabled** automatically
- ✅ **Firewall disabled** for cyber range

## Prerequisites

### 1. Download ISOs
```bash
cd /home/nomad/glassdome
source venv/bin/activate

# Download Windows Server 2022 (4.7 GB)
python scripts/iso_manager.py download windows-server-2022

# Download VirtIO drivers (753 MB)
python scripts/iso_manager.py download virtio-win
```

**Status:** ✅ Already downloaded!

### 2. Upload ISOs to Proxmox
```bash
# Upload both ISOs to Proxmox storage
./scripts/upload_isos_to_proxmox.sh
```

**This will:**
- Upload `windows-server-2022-eval.iso` to `/var/lib/vz/template/iso/`
- Upload `virtio-win.iso` to `/var/lib/vz/template/iso/`
- Make them available for VM creation

## Deployment

### Test Deployment
```bash
cd /home/nomad/glassdome
source venv/bin/activate

python scripts/testing/test_proxmox_windows.py
```

### What Happens

1. **IP Allocation**: Static IP assigned from pool (e.g., 192.168.3.30)
2. **Autounattend Generation**: Creates answer file with:
   - Hostname
   - Administrator password
   - Static IP configuration
   - VirtIO driver paths
   - RDP enablement
3. **VM Creation**: Creates UEFI VM with:
   - 4 GB RAM, 2 CPU cores, 80 GB disk
   - Windows ISO attached as primary CD-ROM
   - VirtIO drivers ISO attached as secondary CD-ROM
   - Autounattend ISO attached as third CD-ROM
4. **Auto-Install**: Windows installs automatically (~15-20 minutes)
   - Detects and loads VirtIO drivers
   - Configures static IP
   - Enables RDP
   - Disables Windows Firewall

### Monitor Installation

**Option 1: Proxmox Web Console**
1. Open: https://192.168.3.2:8006
2. Navigate to VM
3. Click "Console" tab
4. Watch Windows installation progress

**Option 2: SSH to Proxmox**
```bash
ssh root@192.168.3.2
qm status <vmid>
```

### After Installation

**Test RDP Connection:**
```bash
# Linux
rdesktop 192.168.3.30 -u Administrator -p Glassdome123!

# Windows
mstsc /v:192.168.3.30
```

**Credentials:**
- Username: `Administrator`
- Password: `Glassdome123!`

## IP Pool Management

### View IP Allocations
```python
from glassdome.utils.ip_pool import get_ip_pool_manager

ip_manager = get_ip_pool_manager()
allocations = ip_manager.list_allocations()
print(allocations)
```

### Release IP
```python
ip_manager.release_ip("192.168.3.0/24", "vm-id")
```

### Configuration
Edit: `config/ip_pools.json`

```json
{
  "pools": {
    "192.168.3.0/24": {
      "name": "Proxmox Lab Network",
      "gateway": "192.168.3.1",
      "netmask": "255.255.255.0",
      "dns": ["8.8.8.8", "8.8.4.4"],
      "range_start": "192.168.3.30",
      "range_end": "192.168.3.40",
      "allocated": {}
    }
  }
}
```

## Troubleshooting

### ISOs Not Found in Proxmox
```bash
# Verify ISOs exist locally
ls -lh isos/windows/windows-server-2022-eval.iso
ls -lh isos/drivers/virtio-win.iso

# Re-upload to Proxmox
./scripts/upload_isos_to_proxmox.sh
```

### VM Fails to Boot
1. Check Proxmox console for errors
2. Verify UEFI/OVMF is supported
3. Check ISOs are attached correctly

### Windows Installation Hangs
1. Check VirtIO drivers ISO is attached as IDE0
2. Verify autounattend.xml ISO is attached
3. Restart VM

### Static IP Not Working
1. Check network is `vmbr0` (or configured network)
2. Verify gateway is reachable
3. Check autounattend.xml was applied (look for `C:\glassdome-init.log`)

## Next Steps

### Create Windows Template
After first successful install:
1. Let Windows complete installation
2. Install updates (optional)
3. Run Sysprep
4. Convert to template
5. **Future deployments clone from template** (~2 minutes instead of 15-20)

### Deploy Multiple Windows VMs
```python
for i in range(5):
    await agent.execute({
        "name": f"glassdome-win-{i}",
        "windows_version": "server2022",
        "network_cidr": "192.168.3.0/24"
    })
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Glassdome                                               │
│  ├─ ISOs Downloaded                                     │
│  ├─ Autounattend.xml Generated (static IP)             │
│  └─ IP Pool Manager (tracks allocations)               │
└────────────────────┬────────────────────────────────────┘
                     │ SSH/SCP
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Proxmox (192.168.3.2)                                   │
│  ├─ ISOs in /var/lib/vz/template/iso/                  │
│  │   ├─ windows-server-2022-eval.iso                   │
│  │   ├─ virtio-win.iso                                 │
│  │   └─ autounattend-<vmid>.iso                        │
│  └─ VM Created                                          │
│      ├─ UEFI/OVMF BIOS                                 │
│      ├─ VirtIO SCSI controller                         │
│      └─ Windows auto-installs                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Windows VM (192.168.3.30)                               │
│  ├─ Static IP configured                               │
│  ├─ RDP enabled on port 3389                           │
│  ├─ Firewall disabled                                  │
│  └─ Ready for cyber range use                          │
└─────────────────────────────────────────────────────────┘
```

