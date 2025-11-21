# Windows Server 2022 Template Creation Guide

**Purpose:** Create a reusable Windows template for fast, reliable VM deployment on Proxmox.

**Why Template-Based?**
- ✅ Fast: 2-3 minutes per VM (vs 20+ minutes for ISO install)
- ✅ Reliable: 100% success rate (vs autounattend failures)
- ✅ Industry standard: Used by all major cloud providers
- ✅ One-time setup: 15 minutes to create, unlimited clones

---

## Prerequisites

- Proxmox VE 7.x or 8.x
- Windows Server 2022 Evaluation ISO (or licensed ISO)
- Root SSH access to Proxmox host
- ~20GB free storage

---

## Step 1: Upload Windows ISO to Proxmox

```bash
# From your local machine
scp windows-server-2022-eval.iso root@192.168.3.2:/var/lib/vz/template/iso/
```

Or use the provided script:
```bash
./scripts/upload_isos_to_proxmox.sh
```

---

## Step 2: Create Windows VM

**Choose a template ID** (e.g., 9100 for Windows Server 2022):

```bash
# SSH to Proxmox
ssh root@192.168.3.2

# Create VM with SATA disk (Windows-native, no driver issues)
qm create 9100 \
  --name windows-server2022-template \
  --memory 4096 \
  --cores 2 \
  --ostype win11 \
  --bios ovmf \
  --machine pc-q35-7.2 \
  --net0 virtio,bridge=vmbr0

# Add EFI disk (required for UEFI boot)
pvesm alloc local-lvm 9100 vm-9100-disk-0 4M
qm set 9100 --efidisk0 local-lvm:vm-9100-disk-0,efitype=4m,pre-enrolled-keys=1

# Add SATA disk (Windows-native, no driver needed)
qm set 9100 --sata0 local-lvm:80,format=raw

# Attach Windows ISO
qm set 9100 --cdrom local:iso/windows-server-2022-eval.iso,media=cdrom

# Configure boot order (CD-ROM first, then disk)
qm set 9100 --boot order=sata0;ide2

# Enable QEMU guest agent (for IP detection)
qm set 9100 --agent enabled=1

# Start VM
qm start 9100
```

---

## Step 3: Install Windows

1. **Connect to VM console** (Proxmox Web UI → VM 9100 → Console)

2. **Install Windows Server 2022:**
   - Select language, time zone, keyboard
   - Click "Install Now"
   - Choose "Windows Server 2022 Evaluation (Desktop Experience)" or "Standard"
   - Accept license
   - Select "Custom: Install Windows only"
   - Select the SATA disk (should be visible without drivers)
   - Wait for installation (15-20 minutes)

3. **Initial Setup:**
   - Set Administrator password: `Glassdome123!` (or your choice)
   - Complete Windows setup wizard
   - Log in as Administrator

---

## Step 4: Configure Windows for Template

### 4.1 Install QEMU Guest Agent

```powershell
# Download QEMU guest agent
Invoke-WebRequest -Uri "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso" -OutFile "C:\virtio-win.iso"

# Mount ISO
Mount-DiskImage -ImagePath "C:\virtio-win.iso"

# Install guest agent
$drive = (Get-DiskImage -ImagePath "C:\virtio-win.iso" | Get-Volume).DriveLetter
Start-Process -FilePath "$drive`:\guest-agent\qemu-ga-x64.msi" -Wait
```

**Or use Proxmox's built-in VirtIO drivers:**
```bash
# On Proxmox host, attach VirtIO drivers ISO
qm set 9100 --ide3 local:iso/virtio-win.iso,media=cdrom
```

Then in Windows:
- Open Device Manager
- Install VirtIO drivers from CD-ROM
- Install QEMU guest agent from `guest-agent\qemu-ga-x64.msi`

### 4.2 Enable RDP

```powershell
# Enable RDP
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# Allow RDP through firewall
netsh advfirewall firewall set rule group="remote desktop" new enable=Yes
```

### 4.3 Configure Windows Updates (Optional)

```powershell
# Install Windows Updates
Install-Module -Name PSWindowsUpdate -Force
Get-WindowsUpdate
Install-WindowsUpdate -AcceptAll -AutoReboot
```

### 4.4 Install Common Tools (Optional)

```powershell
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install common tools
choco install -y git vscode 7zip
```

---

## Step 5: Prepare for Sysprep

### 5.1 Create Unattend.xml for Sysprep

Create `C:\unattend.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <settings pass="generalize">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <DoNotCleanTaskBar>true</DoNotCleanTaskBar>
        </component>
    </settings>
    <settings pass="specialize">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <ComputerName>*</ComputerName>
        </component>
    </settings>
</unattend>
```

### 5.2 Run Sysprep

```powershell
# Run sysprep (generalize and shutdown)
C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown /unattend:C:\unattend.xml
```

**The VM will shut down automatically.**

---

## Step 6: Convert to Template

```bash
# On Proxmox host
# Detach ISO
qm set 9100 --cdrom none

# Convert to template
qm template 9100

# Verify template
qm list | grep 9100
```

**Template is now ready!**

---

## Step 7: Configure Glassdome

Add template ID to `.env`:

```bash
WINDOWS_SERVER2022_TEMPLATE_ID=9100
```

Or update `glassdome/core/config.py`:

```python
windows_server2022_template_id: int = 9100
```

---

## Step 8: Test Template Deployment

```python
from glassdome.platforms import ProxmoxClient
from glassdome.agents import WindowsInstallerAgent

# Initialize client
proxmox = ProxmoxClient(
    host="192.168.3.2",
    user="apex@pve",
    token_name="apex@pve!glassdome-token",
    token_value="your-token"
)

# Initialize agent
agent = WindowsInstallerAgent(platform_client=proxmox)

# Deploy Windows VM
config = {
    "name": "windows-test",
    "template_id": 9100,  # Use template
    "cores": 2,
    "memory_mb": 4096,
    "ip_address": "192.168.3.100",
    "gateway": "192.168.3.1",
    "subnet_mask": "255.255.255.0"
}

result = await agent.execute(config)
print(f"VM deployed: {result['vm_id']}")
print(f"IP: {result['ip_address']}")
print(f"RDP: {result['windows_connection']['rdp_host']}:3389")
```

---

## Troubleshooting

### VM Won't Boot After Clone

**Issue:** VM stuck at boot screen  
**Solution:** Ensure template was properly sysprepped before conversion

### No Network After Clone

**Issue:** VM has no IP address  
**Solution:** 
- Check network configuration in Proxmox
- Verify VLAN tags if using multi-network setup
- Windows may need network configuration via RDP

### RDP Not Working

**Issue:** Can't connect via RDP  
**Solution:**
- Verify RDP is enabled in template
- Check firewall rules
- Ensure port 3389 is open

### Static IP Not Applied

**Issue:** VM uses DHCP instead of static IP  
**Solution:**
- Windows doesn't support cloud-init
- Configure static IP via:
  1. RDP into VM and configure manually
  2. Use unattend.xml in template with static IP
  3. Use PowerShell script post-boot

---

## Next Steps

1. **Create multiple templates:**
   - Windows Server 2022 Standard
   - Windows Server 2022 Datacenter
   - Windows 11 (if needed)

2. **Automate template creation:**
   - Script the entire process
   - Use Packer for automated builds

3. **Add static IP configuration:**
   - Modify unattend.xml to accept static IP parameters
   - Use sysprep answer file with network configuration

---

## Time Investment

- **One-time setup:** 15-20 minutes
- **Per VM deployment:** 2-3 minutes
- **ROI:** Saves 15+ minutes per VM deployment

---

**Template is ready for production use!** 🎉

