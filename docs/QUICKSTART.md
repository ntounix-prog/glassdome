# Glassdome Quick Start

**Goal:** Deploy your first VM in 5 minutes

---

## Prerequisites

1. **Proxmox VE** (7.x or 8.x) or **ESXi** (7.0+)
2. Network access to management interface
3. For cloud: AWS/Azure credentials

---

## Installation

```bash
# Clone repository
git clone https://github.com/ntounix/glassdome.git
cd glassdome

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install package
pip install -e .
```

---

## Configuration

Create `.env` file in project root:

```bash
# === Proxmox ===
PROXMOX_HOST=192.168.3.2
PROXMOX_USER=apex@pve
PROXMOX_TOKEN_NAME=apex@pve!glassdome-token
PROXMOX_TOKEN_VALUE=your-token-secret
PROXMOX_VERIFY_SSL=false
PROXMOX_NODE=pve01

# === ESXi ===
ESXI_HOST=192.168.3.3
ESXI_USER=root
ESXI_PASSWORD=your-password
ESXI_DATASTORE=datastore1

# === AWS ===
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1

# === Azure ===
AZURE_SUBSCRIPTION_ID=your-sub-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-secret
AZURE_REGION=eastus
AZURE_RESOURCE_GROUP=glassdome-rg

# === Template IDs ===
UBUNTU_2204_TEMPLATE_ID=9000
UBUNTU_2004_TEMPLATE_ID=9001
```

---

## Platform Setup

### Proxmox

Create Ubuntu template:

```bash
# SSH to Proxmox
ssh root@192.168.3.2

# Download cloud image
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img

# Create template
qm create 9000 --name ubuntu-2204-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 ubuntu-22.04-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

**API Token Setup:**
1. Proxmox Web UI → Datacenter → Permissions → API Tokens
2. Click "Add"
3. User: `apex@pve`, Token ID: `glassdome-token`
4. Uncheck "Privilege Separation"
5. Save the secret (shown only once!)

### ESXi

Create Ubuntu template using automated script:

```bash
# From Glassdome project root
python scripts/esxi_create_template.py \
  --host 192.168.3.3 \
  --user root \
  --password your-password \
  --datastore NFSSTORE \
  --template-name ubuntu-2204-template
```

**Manual SSH Setup** (if needed):
```bash
# On ESXi host
/etc/init.d/SSH restart
chkconfig SSH on
```

### AWS

Create IAM user with programmatic access:

```bash
# Required IAM permissions:
# - ec2:*
# - vpc:*
# - iam:PassRole (for instance profiles)
```

**Recommended policy:** See `docs/platform_setup/AWS_IAM_POLICY.json`

### Azure

Create service principal:

```bash
# Via Azure CLI
az login
az ad sp create-for-rbac --name glassdome-deploy-azure \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Copy output to .env:
# AZURE_CLIENT_ID = appId
# AZURE_CLIENT_SECRET = password
# AZURE_TENANT_ID = tenant
```

---

## First VM Deployment

### Test Connection

```bash
# Test Proxmox
python scripts/testing/test_proxmox_quick.py

# Test ESXi
python scripts/testing/test_esxi_quick.py

# Test AWS
python scripts/testing/test_aws_quick.py

# Test Azure
python scripts/testing/test_azure_quick.py
```

### Deploy Ubuntu VM

```bash
# Via CLI
glassdome deploy ubuntu \
  --platform proxmox \
  --name my-ubuntu-vm \
  --version 22.04 \
  --cores 2 \
  --memory 4096 \
  --disk 20

# Via Python
python -c "
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
from glassdome.platforms.proxmox_client import ProxmoxClient
import asyncio

async def deploy():
    client = ProxmoxClient(...)
    agent = UbuntuInstallerAgent(client)
    result = await agent.execute({
        'name': 'test-vm',
        'version': '22.04',
        'cores': 2,
        'memory': 2048,
        'disk_size_gb': 20
    })
    print(result)

asyncio.run(deploy())
"
```

---

## Troubleshooting

**Connection refused:**
- Check host is reachable: `ping 192.168.3.2`
- Check port: `telnet 192.168.3.2 8006`
- Check firewall

**Authentication failed:**
- Verify credentials in `.env`
- For Proxmox: Test token in Web UI
- For ESXi: Try console login first

**Template not found:**
- List templates: `qm list | grep template` (Proxmox)
- Verify template ID in `.env` matches

**VM creation fails:**
- Check Proxmox/ESXi logs
- Verify sufficient storage
- Check network bridge exists

**ESXi "InvalidLogin":**
- Check services: `/etc/init.d/hostd status`
- Restart if needed: `/etc/init.d/hostd restart`
- Enable SSH: `chkconfig SSH on`

---

## Next Steps

1. **Deploy multiple VMs** - Test different OS versions
2. **Multi-network scenarios** - See `docs/NETWORK_SCENARIOS.md`
3. **Dashboard** - Launch React UI: `cd frontend && npm run dev`
4. **Research Agent** - See `docs/AGENTS.md`

---

## Documentation

- **Architecture:** `docs/ARCHITECTURE.md`
- **Platform Setup:** `docs/PLATFORM_SETUP.md`
- **Agents:** `docs/AGENTS.md`
- **API Reference:** `docs/API_REFERENCE.md`
- **Project Status:** `docs/PROJECT_STATUS.md`

---

**Ready to build cyber ranges!** 🚀
