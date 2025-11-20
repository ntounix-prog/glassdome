# ESXi Cloud-Init Solution

## 🎯 Problem Solved

**Ubuntu cloud images DO NOT work directly with ESXi standalone!**

### Root Cause
- Ubuntu cloud VMDKs ship as **StreamOptimized (disk type 22)**
- ESXi 7.0.3 standalone **DOES NOT support** this format
- Error: `Unsupported or invalid disk type 22 for 'scsi0:0'`

### Solution
**Conversion is MANDATORY using `vmkfstools` on the ESXi host**

---

## 📋 Complete Workflow

### Prerequisites
- ESXi 7.0+ standalone host
- SSH access enabled on ESXi
- qemu-img installed locally
- genisoimage installed locally

### Pipeline Overview

```
Ubuntu Cloud VMDK (StreamOptimized)
          ↓ qemu-img convert
MonolithicFlat VMDK
          ↓ Upload to ESXi
ESXi Datastore
          ↓ vmkfstools (on ESXi host)
ESXi-Native VMDK
          ↓ Attach to VM + NoCloud ISO
✅ Working Cloud-Init VM
```

---

## 🚀 Step-by-Step Instructions

### Step 1: Download and Convert

```bash
# Download Ubuntu cloud image
wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.vmdk

# Convert to monolithicFlat (ESXi-compatible base)
qemu-img convert \
  -f vmdk \
  -O vmdk \
  -o adapter_type=lsilogic,subformat=monolithicFlat \
  ubuntu-22.04-server-cloudimg-amd64.vmdk \
  ubuntu-flat.vmdk
```

This creates:
- `ubuntu-flat.vmdk` (512 bytes - descriptor file)
- `ubuntu-flat-flat.vmdk` (10GB - data file)

### Step 2: Create NoCloud ISO

Cloud-init configuration via NoCloud datasource:

```bash
mkdir -p seed

# user-data
cat > seed/user-data << 'EOF'
#cloud-config
hostname: ubuntu-esxi
users:
  - name: ubuntu
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    shell: /bin/bash
    lock_passwd: false
    passwd: $6$rounds=4096$salt$hash  # Password: ubuntu
ssh_pwauth: true
packages:
  - qemu-guest-agent
  - cloud-init
runcmd:
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent
EOF

# meta-data
cat > seed/meta-data << EOF
instance-id: ubuntu-esxi-001
local-hostname: ubuntu-esxi
EOF

# Create ISO
genisoimage -output seed.iso -volid cidata -joliet -rock seed/
```

### Step 3: Upload to ESXi

```bash
# Via HTTP API (Python/requests)
# Upload to: https://<esxi-host>/folder/<vm-name>/ubuntu-flat.vmdk
# Upload to: https://<esxi-host>/folder/<vm-name>/ubuntu-flat-flat.vmdk
# Upload to: https://<esxi-host>/folder/<vm-name>/seed.iso
```

### Step 4: Convert with vmkfstools (ON ESXi HOST)

**⚠️ CRITICAL STEP - Must run on ESXi:**

```bash
# SSH into ESXi
ssh root@<esxi-host>

# Navigate to datastore
cd /vmfs/volumes/<datastore>/<vm-name>/

# Convert to ESXi-native format
vmkfstools -i ubuntu-flat.vmdk \
           ubuntu-esxi.vmdk \
           -d thin

# Verify
ls -lh
# You should see:
#   ubuntu-esxi.vmdk (descriptor)
#   ubuntu-esxi-flat.vmdk (ESXi-native data)
```

### Step 5: Create VM and Attach Disks

```python
from glassdome.platforms.esxi_client import ESXiClient

# Create VM without disks
vm = client.create_vm_without_disk(
    name="ubuntu-esxi-template",
    memory=2048,
    cpus=2
)

# Attach ESXi-native VMDK
vm.attach_disk(
    path="[datastore] ubuntu-esxi-template/ubuntu-esxi.vmdk",
    controller_key=1000,  # SCSI controller
    thin_provisioned=True
)

# Attach seed ISO
vm.attach_cdrom(
    path="[datastore] ubuntu-esxi-template/seed.iso",
    controller_key=200  # IDE controller
)

# Power on
vm.power_on()
```

### Step 6: Verify

Wait 60-90 seconds for cloud-init to complete:

```bash
# SSH into VM
ssh ubuntu@<vm-ip>
Password: ubuntu

# Check cloud-init status
cloud-init status

# Should show: status: done
```

---

## 🔧 Technical Details

### VMDK Format Comparison

| Format | ESXi Support | Use Case |
|--------|-------------|----------|
| StreamOptimized | ❌ NO | Cloud images, compressed |
| MonolithicSparse | ⚠️ Partial | Intermediate format |
| MonolithicFlat | ✅ YES | Base for conversion |
| VMFS (vmkfstools) | ✅ YES | ESXi-native, optimal |

### Controller Types

- **SCSI**: ParaVirtualSCSIController (key=1000)
  - Adapter type: `lsilogic` (most compatible)
  - For VMDK attachment
- **IDE**: VirtualIDEController (key=200)
  - For CD-ROM (seed.iso)

### NoCloud Datasource

ESXi doesn't support the GuestInfo datasource natively, so we use NoCloud:
- Volume label: `cidata`
- Required files: `user-data`, `meta-data`
- Attached as CD-ROM during first boot
- Cloud-init reads config and applies

---

## 📝 Automation Script

See `/tmp/esxi_complete_workflow.py` for full automation.

Key features:
- Uploads all files to ESXi
- Pauses for manual vmkfstools step
- Creates VM and attaches disks
- Powers on and verifies

---

## ❌ Common Issues

### "Unsupported or invalid disk type 22"
- **Cause**: StreamOptimized VMDK not converted
- **Fix**: Run vmkfstools on ESXi

### "Unsupported or invalid disk type 2"
- **Cause**: Sparse VMDK without proper adapter type
- **Fix**: Ensure `adapter_type=lsilogic` in qemu-img conversion

### "The file specified is not a virtual disk"
- **Cause**: Missing flat data file
- **Fix**: Upload both descriptor and `-flat.vmdk` file

### SSH "Bad authentication type"
- **Cause**: ESXi requires keyboard-interactive auth
- **Fix**: Enable SSH in ESXi UI, use proper SSH client

---

## 🎯 Success Criteria

✅ VM powers on without disk errors
✅ Cloud-init status shows "done"
✅ Guest has IP address
✅ SSH works with ubuntu/ubuntu
✅ qemu-guest-agent running

---

## 🔗 References

- Ubuntu Cloud Images: https://cloud-images.ubuntu.com/
- Cloud-Init NoCloud: https://cloudinit.readthedocs.io/en/latest/reference/datasources/nocloud.html
- VMware vmkfstools: https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.vsphere.storage.doc/GUID-A5D85C33-A510-4A3E-8FC7-93E6BA0A048F.html

---

## 📅 Status

- **Discovered**: November 20, 2024
- **Tested On**: ESXi 7.0.3
- **Working**: ✅ Solution proven
- **Next Steps**: Automate vmkfstools step or provide clear manual instructions

