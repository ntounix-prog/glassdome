# Getting Started: From Zero to Working VM

## Current Status: What Works Now

✅ **Framework Complete** - Architecture, APIs, agents, orchestrator
⚠️ **Proxmox Integration** - Code written, needs testing with real Proxmox
❌ **Cloud Providers** - Stubs only (Azure, AWS not implemented)

---

## Step-by-Step: Deploy Your First VM

### Step 1: Prerequisites

You need:
1. **Proxmox VE server** (version 7.x or 8.x)
2. **Network access** to Proxmox API
3. **Ubuntu cloud-init template** in Proxmox

### Step 2: Setup Proxmox Templates

SSH into your Proxmox server and run:

```bash
# Download and run template creation script
curl -o create-template.sh https://raw.githubusercontent.com/ntounix/glassdome/main/scripts/create-template.sh
chmod +x create-template.sh

# Create Ubuntu 22.04 template (ID 9000)
./create-template.sh 9000 22.04
```

Or manually:

```bash
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img

qm create 9000 --name ubuntu-2204-cloudinit-template --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 ubuntu-22.04-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000

echo "✅ Template 9000 created!"
```

### Step 3: Enable Proxmox API Access

**Option A: API Token (Recommended)**

In Proxmox Web UI:
1. Go to `Datacenter` → `Permissions` → `API Tokens`
2. Click `Add`
3. User: `root@pam`
4. Token ID: `glassdome-token`
5. Uncheck "Privilege Separation"
6. Click `Add`
7. **SAVE THE SECRET** (shown only once!)

**Option B: Password**

Just use your root password (less secure).

### Step 4: Configure Glassdome

Create `.env` file in the project root:

```bash
# Proxmox Configuration
PROXMOX_HOST=your-proxmox-ip-or-hostname
PROXMOX_USER=root@pam

# Option A: API Token (recommended)
PROXMOX_TOKEN_NAME=glassdome-token
PROXMOX_TOKEN_VALUE=your-secret-token-here

# Option B: Password
# PROXMOX_PASSWORD=your-password

PROXMOX_VERIFY_SSL=false
PROXMOX_NODE=pve

# Template IDs
UBUNTU_2204_TEMPLATE_ID=9000
UBUNTU_2004_TEMPLATE_ID=9001
```

### Step 5: Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install glassdome package
pip install -e .

# Install Proxmox library
pip install proxmoxer
```

### Step 6: Test Connection

```bash
python3 test_vm_creation.py
```

This will:
1. ✅ Test Proxmox connection
2. ✅ List nodes and templates
3. ✅ Create a test Ubuntu VM
4. ✅ Wait for IP assignment
5. ✅ Show VM details
6. ✅ Optional: Clean up test VM

Expected output:

```
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║            Glassdome VM Creation Test                    ║
║         Testing REAL Proxmox Integration                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

============================================================
TEST 1: Proxmox Connection
============================================================
Host: 192.168.1.100
User: root@pam
Auth: Token
✅ Connected to Proxmox!

Nodes: ['pve']
VMs on pve: 5
Templates: ['ubuntu-2204-cloudinit-template']

============================================================
TEST 2: Create Ubuntu VM
============================================================
Agent initialized: test-agent
Ubuntu versions available: ['22.04', '24.04', '20.04']

Task configuration:
  Node: pve
  Version: 22.04
  Name: glassdome-test-vm
  Resources: 2 cores, 2GB RAM, 20GB disk

Task validation: ✅ Valid

📦 Creating VM...
This may take 1-2 minutes...

------------------------------------------------------------
✅ VM CREATED SUCCESSFULLY!

VM Details:
  VM ID: 123
  Name: glassdome-test-vm
  Node: pve
  Version: 22.04
  IP Address: 192.168.1.123
  Status: created
```

### Step 7: Use the API

Start the backend server:

```bash
glassdome serve
# Or: python -m glassdome.server
```

Create a VM via API:

```bash
curl -X POST http://localhost:8001/api/agents/ubuntu/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-ubuntu-vm",
    "version": "22.04",
    "cores": 2,
    "memory": 4096,
    "disk_size": 30
  }'
```

Expected response:

```json
{
  "success": true,
  "vm_id": 124,
  "name": "my-ubuntu-vm",
  "ip_address": "192.168.1.124",
  "status": "created"
}
```

### Step 8: Use the Frontend (Coming Soon)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5174

Select "Quick Deploy" → Choose OS → Click Deploy!

---

## What Works Right Now

### ✅ Single VM Creation

```bash
POST /api/agents/ubuntu/create
```

Creates ONE Ubuntu VM via agent.

**Status:** Implemented, needs testing with real Proxmox

### ⏳ Lab Orchestration

```bash
POST /api/labs/deploy
```

Creates multiple VMs with users, packages, network config.

**Status:** Code written, needs:
- Cloud-init integration
- SSH operations
- Network management

### ❌ Cloud Providers

Azure and AWS clients exist but are stubs.

**Status:** Not implemented

---

## Troubleshooting

### "Connection refused"

- Check Proxmox is accessible: `ping your-proxmox-host`
- Check API port: `telnet your-proxmox-host 8006`
- Check firewall allows port 8006

### "Authentication failed"

- Verify token/password in `.env`
- Test in Proxmox UI with same credentials
- Check token hasn't expired

### "Template 9000 not found"

- Run: `qm list | grep 9000`
- If missing, create template (Step 2)
- Check template ID in `.env` matches

### "QEMU guest agent not running"

- Template needs QEMU agent installed
- Cloud images have it by default
- Manual install: `apt install qemu-guest-agent`

### "Timeout waiting for IP"

- VM might not have started
- Check Proxmox console
- Verify network bridge exists
- Try DHCP on network

---

## Next Steps

Once you have ONE VM working:

1. ✅ Test with different VM sizes
2. ✅ Test with different Ubuntu versions
3. ⏳ Implement cloud-init user creation
4. ⏳ Implement package installation
5. ⏳ Test 2-VM lab orchestration
6. ⏳ Add Kali, Debian agents
7. ⏳ Add Azure/AWS support

---

## Documentation

- **Proxmox Setup:** `docs/PROXMOX_SETUP.md`
- **Project Status:** `PROJECT_STATUS.md`
- **Architecture:** `docs/ARCHITECTURE.md`
- **API Reference:** `docs/API.md`

---

## Support

Something not working?

1. Check `PROJECT_STATUS.md` for implementation status
2. Check logs: `tail -f glassdome.log`
3. Run test script: `python3 test_vm_creation.py`
4. Check Proxmox task log in Web UI

---

## Summary: Where We Are

```
┌─────────────────────────────────────────────┐
│  Architecture              ████████  100%   │
│  Python Package           ████████  100%   │
│  API Endpoints            ██████░░   75%   │
│  Agent Framework          ████████  100%   │
│  Orchestrator             ██████░░   75%   │
│  Proxmox Client           ████████  100%   │
│  VM Creation Logic        ████████  100%   │
│                                             │
│  ⚠️ NEEDS TESTING WITH REAL PROXMOX        │
│                                             │
│  Cloud-Init               ██░░░░░░   25%   │
│  SSH Operations           ░░░░░░░░    0%   │
│  Database                 ░░░░░░░░    5%   │
│  Frontend Integration     ██░░░░░░   25%   │
│  Azure/AWS                ░░░░░░░░    5%   │
└─────────────────────────────────────────────┘
```

**We have a working foundation. Now we need to test and refine with real Proxmox!** 🚀

