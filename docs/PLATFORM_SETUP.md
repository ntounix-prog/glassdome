# Platform Setup Guide

Complete setup instructions for all supported platforms: Proxmox, ESXi, AWS, Azure.

**Quick Reference:**
- **Proxmox:** API token, Ubuntu templates
- **ESXi:** Root access, cloud-init VMDK conversion
- **AWS:** IAM user, programmatic access
- **Azure:** Service principal, Contributor role

---

## Proxmox Setup

### Prerequisites
- Proxmox VE 7.x or 8.x
- Network access to port 8006
- Root or user with Administrator role

### API Token Creation

**Method 1: Web UI (Recommended)**
1. Navigate to `Datacenter` → `Permissions` → `API Tokens`
2. Click `Add`
3. User: `apex@pve` (or your user)
4. Token ID: `glassdome-token`
5. **Uncheck** "Privilege Separation"
6. Click `Add`
7. **SAVE THE SECRET** (shown only once!)

**Method 2: CLI**
```bash
pveum user token add apex@pve glassdome-token --privsep 0
```

**`.env` Configuration:**
```bash
PROXMOX_HOST=192.168.3.2
PROXMOX_USER=apex@pve
PROXMOX_TOKEN_NAME=apex@pve!glassdome-token
PROXMOX_TOKEN_VALUE=44fa1891-0b3f-487a-b1ea-0800284f79d9
PROXMOX_NODE=pve01
```

### Ubuntu Template Creation

**Automated Script:**
```bash
python scripts/proxmox_create_template.py \
  --host 192.168.3.2 \
  --version 22.04 \
  --template-id 9000
```

**Manual Steps:**
```bash
# SSH to Proxmox
ssh root@192.168.3.2

# Download cloud image
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img

# Create VM
qm create 9000 \
  --name ubuntu-2204-template \
  --memory 2048 \
  --cores 2 \
  --net0 virtio,bridge=vmbr0

# Import disk
qm importdisk 9000 ubuntu-22.04-server-cloudimg-amd64.img local-lvm

# Configure VM
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1

# Convert to template
qm template 9000
```

### Windows Template (SATA Controller)

**Key Lesson:** Use SATA, not SCSI, for Windows VMs (no driver injection needed)

```bash
# Create VM with SATA disk
qm create 113 \
  --name windows-template \
  --memory 4096 \
  --cores 2 \
  --ostype win11 \
  --bios ovmf \
  --machine pc-q35-7.2

# Add EFI disk
pvesm alloc local-lvm 113 vm-113-disk-0 4M
qm set 113 --efidisk0 local-lvm:vm-113-disk-0,efitype=4m,pre-enrolled-keys=1

# Add SATA disk (Windows-native)
qm set 113 --sata0 local-lvm:80,cache=writeback,discard=on

# Attach ISOs
qm set 113 --ide2 local:iso/windows-server-2022-eval.iso,media=cdrom
qm set 113 --ide0 local:iso/virtio-win.iso,media=cdrom

# Set boot order
qm set 113 --boot order=ide2
```

**Note:** Autounattend.xml approach has reliability issues. Template-based deployment recommended.

### Troubleshooting

**"Authentication failed":**
- Verify token in Web UI (Datacenter → Permissions → API Tokens)
- Check token hasn't expired
- Ensure "Privilege Separation" is disabled

**"Template not found":**
```bash
# List all VMs/templates
qm list

# Check specific ID
qm config 9000
```

**"Timeout waiting for IP":**
- Check DHCP on network
- Verify bridge exists: `ip link show vmbr0`
- Check QEMU guest agent: VM console → `systemctl status qemu-guest-agent`

---

## ESXi Setup

### Prerequisites
- ESXi 7.0+ (standalone, no vCenter required)
- SSH enabled
- Root access
- Datastore with sufficient space

### Enable SSH (if disabled)

**From ESXi console:**
1. Press `F2` for System Customization
2. Navigate to `Troubleshooting Options`
3. Enable `ESXi Shell` and `SSH`
4. Press `ESC` to save

**Via CLI:**
```bash
# Start SSH
/etc/init.d/SSH start

# Enable on boot
chkconfig SSH on

# Verify
/etc/init.d/SSH status
```

### Management Services (If Locked Out)

**Symptoms:** Can't SSH or access Web UI, but console works

**Root Cause:** Auth services desync (often from multiple failed logins)

**Fix from Console:**
```bash
# Restart management daemon
/etc/init.d/hostd restart

# Restart SSH
/etc/init.d/SSH restart

# Enable on boot
chkconfig hostd on
chkconfig SSH on

# Verify
ps | grep hostd
ps | grep sshd
```

### Ubuntu Template Creation

**Critical:** ESXi 7.0 standalone doesn't support OVA cloud images natively. Must convert VMDK.

**Automated Script:**
```bash
python scripts/esxi_create_template.py \
  --host 192.168.3.3 \
  --user root \
  --password H-3a-7YP \
  --datastore NFSSTORE \
  --template-name ubuntu-2204-template
```

**Manual Steps:**
```bash
# 1. Download Ubuntu cloud image (on glassdome host)
cd /home/nomad/glassdome/isos/linux
wget https://cloud-images.ubuntu.com/releases/22.04/release/jammy-server-cloudimg-amd64.img

# 2. Convert to monolithicFlat VMDK
qemu-img convert -f qcow2 -O vmdk \
  -o subformat=monolithicFlat \
  jammy-server-cloudimg-amd64.img \
  ubuntu-2204-flat.vmdk

# 3. Create NoCloud ISO for cloud-init
mkdir -p nocloud
cat > nocloud/user-data << 'EOF'
#cloud-config
password: glassdome123
chpasswd: { expire: False }
ssh_pwauth: True
EOF

echo "instance-id: ubuntu-template" > nocloud/meta-data
genisoimage -output seed.iso -volid cidata -joliet -rock nocloud/

# 4. Upload to ESXi
scp ubuntu-2204-flat.vmdk root@192.168.3.3:/vmfs/volumes/NFSSTORE/ubuntu-2204/
scp ubuntu-2204.vmdk root@192.168.3.3:/vmfs/volumes/NFSSTORE/ubuntu-2204/
scp seed.iso root@192.168.3.3:/vmfs/volumes/NFSSTORE/ubuntu-2204/

# 5. Convert VMDK to ESXi-native format (via SSH to ESXi)
ssh root@192.168.3.3
cd /vmfs/volumes/NFSSTORE/ubuntu-2204/
vmkfstools -i ubuntu-2204-flat.vmdk -d thin ubuntu-2204-esxi.vmdk

# 6. Create VM and attach converted VMDK (via Python or govc)
```

**Key Learnings:**
- `monolithicFlat` format required (not `streamOptimized`)
- Must run `vmkfstools -i` on ESXi host to convert
- `lsilogic` adapter for SCSI controller
- NoCloud ISO for cloud-init configuration
- Default credentials: `ubuntu/glassdome123`

**`.env` Configuration:**
```bash
ESXI_HOST=192.168.3.3
ESXI_USER=root
ESXI_PASSWORD=H-3a-7YP
ESXI_DATASTORE=NFSSTORE
ESXI_NETWORK=VM Network
```

### ISO Storage

**Upload ISOs to ESXi:**
```bash
# Create ISO directory
ssh root@192.168.3.3 "mkdir -p /vmfs/volumes/NFSSTORE/iso"

# Upload via SCP
scp windows-server-2022-eval.iso root@192.168.3.3:/vmfs/volumes/NFSSTORE/iso/
scp virtio-win.iso root@192.168.3.3:/vmfs/volumes/NFSSTORE/iso/
```

### Troubleshooting

**"InvalidLogin" despite correct password:**
- Check from console first
- Restart auth services (see above)
- Verify PAM isn't locked (too many failed attempts)

**"No operating system" after VM creation:**
- Check VMDK descriptor matches controller type
- Verify VMDK is ESXi-native format (run `vmkfstools -i`)
- Ensure boot order is correct

**"Unsupported disk type":**
- VMDK not converted to ESXi format
- Run: `vmkfstools -i source.vmdk -d thin output.vmdk`

---

## AWS Setup

### Prerequisites
- AWS account with billing enabled
- Ability to create IAM users
- Credit card on file

### IAM User Creation

**1. Create User:**
```bash
# Via AWS CLI
aws iam create-user --user-name glassdome-deploy

# Via Console: IAM → Users → Add User
# - User name: glassdome-deploy
# - Access type: Programmatic access
```

**2. Create Access Key:**
```bash
aws iam create-access-key --user-name glassdome-deploy

# Save output:
# - AccessKeyId → AWS_ACCESS_KEY_ID
# - SecretAccessKey → AWS_SECRET_ACCESS_KEY
```

**3. Attach Policy:**

**Recommended Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:*",
        "vpc:*"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::*:role/*"
    }
  ]
}
```

**Apply Policy:**
```bash
# Save above JSON to glassdome-policy.json
aws iam put-user-policy \
  --user-name glassdome-deploy \
  --policy-name glassdome-deployment \
  --policy-document file://glassdome-policy.json
```

**`.env` Configuration:**
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

### Testing

```bash
# Test credentials
python scripts/testing/test_aws_quick.py

# Expected: Creates t4g.nano instance, shows IP, auto-deletes
```

### Instance Types

**Recommended for Testing:**
- `t4g.nano` - ARM64, $0.0042/hr
- `t3.micro` - x86_64, $0.0104/hr (Free Tier eligible)

**Note:** Glassdome auto-detects architecture and selects appropriate AMI.

### Troubleshooting

**"InvalidClientTokenId":**
- Verify credentials in `.env`
- Test: `aws sts get-caller-identity`

**"UnauthorizedOperation":**
- Check IAM policy attached
- Verify permissions include `ec2:*`

**"UnsupportedOperation: The requested configuration is currently not supported":**
- Instance type not available in selected AZ
- Solution: Don't specify subnet, let AWS choose

---

## Azure Setup

### Prerequisites
- Azure subscription
- Owner or Contributor role on subscription
- Azure CLI installed (optional)

### Service Principal Creation

**Method 1: Azure CLI (Easiest)**
```bash
# Login
az login

# Create service principal
az ad sp create-for-rbac \
  --name glassdome-deploy-azure \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Output:
# {
#   "appId": "xxx",          → AZURE_CLIENT_ID
#   "password": "yyy",       → AZURE_CLIENT_SECRET
#   "tenant": "zzz"          → AZURE_TENANT_ID
# }
```

**Method 2: Azure Portal**
1. Navigate to **Microsoft Entra ID** (formerly Azure Active Directory)
2. Click **App registrations** → **New registration**
3. Name: `glassdome-deploy-azure`
4. Click **Register**
5. Copy **Application (client) ID** → `AZURE_CLIENT_ID`
6. Copy **Directory (tenant) ID** → `AZURE_TENANT_ID`
7. Click **Certificates & secrets** → **New client secret**
8. Copy **Secret Value** (not Secret ID!) → `AZURE_CLIENT_SECRET`
9. Navigate to **Subscriptions** → Your subscription
10. Click **Access control (IAM)** → **Add role assignment**
11. Role: **Contributor**
12. Assign access to: **User, group, or service principal**
13. Select: `glassdome-deploy-azure`

**`.env` Configuration:**
```bash
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-secret-value
AZURE_REGION=eastus
AZURE_RESOURCE_GROUP=glassdome-rg
```

### Resource Provider Registration

**Required providers:**
- `Microsoft.Compute`
- `Microsoft.Network`

**Auto-registration** (handled by Glassdome):
```python
# Automatic on first use
client = AzureClient(...)  # Registers providers if needed
```

**Manual registration:**
```bash
az provider register --namespace Microsoft.Compute
az provider register --namespace Microsoft.Network
```

### Testing

```bash
# Test credentials
python scripts/testing/test_azure_quick.py

# Expected: Creates Standard_B1s VM, shows IP, auto-deletes
```

### VM Sizes

**Recommended for Testing:**
- `Standard_B1s` - 1 core, 1GB RAM, $0.0104/hr
- `Standard_B2s` - 2 cores, 4GB RAM, $0.0416/hr

### Troubleshooting

**"AuthorizationFailed":**
- Verify service principal has Contributor role
- Wait 60 seconds after role assignment (propagation delay)

**"MissingSubscriptionRegistration":**
- Resource providers not registered
- Run: `az provider register --namespace Microsoft.Compute`

**"400 Contributor roles":**
- Select **Contributor** under "Privileged administrator roles" tab
- Not custom contributor roles

---

## Windows Deployment

### Cloud Platforms (AWS/Azure)

**Status:** ✅ Working (pre-built AMIs/images)

**AWS:**
- Image: Windows Server 2022 (auto-detected)
- Configuration: EC2Launch via UserData
- Default user: `Administrator`
- RDP: Port 3389 auto-configured

**Azure:**
- Image: Windows Server 2022 Datacenter
- Configuration: Custom Data (PowerShell)
- Default user: `gdadmin` (not Administrator - reserved by Azure)
- RDP: Port 3389 auto-configured

### On-Premise Platforms (Proxmox/ESXi)

**Status:** ⚠️ In Progress

**Current Blocker:** Autounattend.xml approach unreliable

**Attempts:**
1. CD-ROM placement → Windows Setup doesn't check secondary drives
2. Floppy + VirtIO SCSI → Drivers not visible
3. Floppy + SATA → Setup not starting
4. VNC automation → Connection refused

**Recommendation:** Template-based approach
1. Manual Windows install (15 min, one-time)
2. Sysprep and convert to template
3. Clone for future deployments (2-3 min each, 100% reliable)

**Key Insight:** Use SATA controller (not SCSI) for Windows VMs
- SATA is Windows-native (no driver injection needed)
- SCSI requires VirtIO drivers during Setup
- Change: `scsihw` → `sata0` in Proxmox

---

## Summary

| Platform | Setup Time | Complexity | Status |
|----------|------------|------------|--------|
| Proxmox  | 15 min     | Low        | ✅ Working |
| ESXi     | 30 min     | Medium     | ✅ Working |
| AWS      | 5 min      | Low        | ✅ Working |
| Azure    | 10 min     | Medium     | ✅ Working |

**Next:** See `docs/QUICKSTART.md` for first VM deployment.

