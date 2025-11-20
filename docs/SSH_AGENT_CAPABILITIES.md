# SSH Agent Capabilities

## Overview

The Glassdome agentic framework now has **full SSH capabilities**, enabling agents to:
- Execute commands on remote hosts (Proxmox, VMs, cloud instances)
- Transfer files
- Create templates automatically
- Configure infrastructure
- Run post-deployment scripts
- Perform maintenance tasks

This eliminates the need for manual SSH operations - **agents do it all automatically**.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Glassdome Agentic Framework                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Agent (Ubuntu/Kali/etc)                                │
│    ↓                                                    │
│  SSH Client (glassdome/core/ssh_client.py)             │
│    ↓                                                    │
│  ┌───────────────────┐  ┌───────────────────┐         │
│  │  Proxmox Host     │  │  Created VMs      │         │
│  │  (via SSH)        │  │  (via SSH)        │         │
│  ├───────────────────┤  ├───────────────────┤         │
│  │ • Create templates│  │ • Create users    │         │
│  │ • Setup storage   │  │ • Install packages│         │
│  │ • Config network  │  │ • Run scripts     │         │
│  │ • Install tools   │  │ • Configure apps  │         │
│  └───────────────────┘  └───────────────────┘         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Components

### 1. SSHClient (`glassdome/core/ssh_client.py`)

**Core SSH functionality for all agents:**

```python
from glassdome.core.ssh_client import SSHClient

# Connect to remote host
ssh = SSHClient(
    host="192.168.3.2",
    username="root",
    password="password"  # or key_filename="/path/to/key"
)

await ssh.connect()

# Execute commands
result = await ssh.execute("apt update && apt upgrade -y")
print(result["stdout"])

# Transfer files
await ssh.upload_file("/local/script.sh", "/remote/script.sh")
await ssh.download_file("/remote/log.txt", "/local/log.txt")

# Execute scripts
script = """
#!/bin/bash
echo "Setting up environment..."
apt install -y docker.io
systemctl start docker
"""
result = await ssh.execute_script(script)

# File operations
exists = await ssh.file_exists("/etc/config.conf")
content = await ssh.read_file("/etc/config.conf")
await ssh.write_file("/etc/new.conf", "config_value=123")
```

**Features:**
- Password or key-based authentication
- Async/await support
- Command execution
- Script execution
- File transfer (SCP/SFTP)
- File operations (read/write/check)
- Connection pooling
- Error handling

### 2. ProxmoxGateway (`glassdome/platforms/proxmox_gateway.py`)

**High-level API for Proxmox operations:**

```python
from glassdome.platforms.proxmox_gateway import ProxmoxGateway

# Connect to Proxmox
gateway = ProxmoxGateway(
    host="192.168.3.2",
    username="root",
    password="password"
)

await gateway.connect()

# Automatically create Ubuntu template
result = await gateway.create_ubuntu_template(
    template_id=9000,
    ubuntu_version="22.04"
)
# Downloads image, creates VM, configures, converts to template

# List templates
templates = await gateway.list_templates()

# Delete template
await gateway.delete_template(9000)

# Get storage info
storage = await gateway.get_storage_info()

# Create network bridge
await gateway.create_network_bridge("vmbr1", vlan_aware=True)

# Install packages on Proxmox host
await gateway.install_package("qemu-guest-agent")

# Execute custom commands
result = await gateway.execute_custom("pvesh get /nodes")
```

**Capabilities:**
- ✅ Automatic template creation (no manual steps!)
- ✅ Template management
- ✅ Storage configuration
- ✅ Network setup
- ✅ Package installation
- ✅ Backup/restore
- ✅ Custom command execution

---

## Use Cases

### Use Case 1: Automatic Template Creation

**Before (Manual):**
```bash
# User had to SSH and run these commands manually:
ssh root@192.168.3.2
cd /var/lib/vz/template/iso
wget https://cloud-images.ubuntu.com/...
qm create 9000...
# (10+ more commands)
```

**After (Automatic):**
```python
# Agent does it all:
gateway = ProxmoxGateway("192.168.3.2", "root", password)
await gateway.create_ubuntu_template(9000, "22.04")
# Done! Template created.
```

**Or via script:**
```bash
python3 create_template_auto.py
# Interactive wizard, no SSH needed
```

### Use Case 2: Post-Deployment VM Configuration

**Agent creates VM, then configures it via SSH:**

```python
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent

# 1. Create VM via Proxmox API
agent = UbuntuInstallerAgent("agent-001", proxmox_client)
vm_result = await agent.execute({
    "element_type": "ubuntu_vm",
    "config": {"name": "webserver-01", "version": "22.04"}
})

vm_ip = vm_result["ip_address"]

# 2. SSH into newly created VM
vm_ssh = SSHClient(
    host=vm_ip,
    username="ubuntu",  # cloud-init default user
    key_filename="~/.ssh/id_rsa"
)

await vm_ssh.connect()

# 3. Configure VM
await vm_ssh.execute("apt update && apt upgrade -y")
await vm_ssh.execute("apt install -y apache2 mysql-server php")
await vm_ssh.execute("systemctl enable apache2")

# 4. Upload configuration files
await vm_ssh.upload_file("./apache.conf", "/etc/apache2/sites-available/mysite.conf")
await vm_ssh.execute("a2ensite mysite && systemctl reload apache2")

# 5. Create users
await vm_ssh.execute("useradd -m -s /bin/bash webadmin")
await vm_ssh.execute("usermod -aG sudo webadmin")

print(f"✅ Web server configured at {vm_ip}")
```

### Use Case 3: Orchestrated Lab with Post-Config

**Orchestrator deploys multiple VMs and configures them:**

```python
# Orchestrator creates 3 VMs
lab_result = await orchestrator.deploy_lab({
    "vms": [
        {"vm_id": "attacker", "os_type": "kali"},
        {"vm_id": "target", "os_type": "ubuntu"},
        {"vm_id": "monitor", "os_type": "ubuntu"}
    ]
})

# Then SSH into each and configure
for vm_id, vm_data in lab_result["vms"].items():
    ssh = SSHClient(host=vm_data["ip"], username="ubuntu")
    await ssh.connect()
    
    if vm_id == "attacker":
        # Install pentesting tools
        await ssh.execute("apt install -y nmap metasploit-framework")
    elif vm_id == "target":
        # Install vulnerable app
        await ssh.execute("git clone https://github.com/digininja/DVWA.git /var/www/dvwa")
    elif vm_id == "monitor":
        # Install monitoring
        await ssh.execute("apt install -y wireshark tcpdump")
```

### Use Case 4: Infrastructure Maintenance

**Agent performs routine maintenance:**

```python
gateway = ProxmoxGateway("192.168.3.2", "root", password)

# Update Proxmox host
await gateway.execute_custom("apt update && apt upgrade -y")

# Backup configurations
await gateway.backup_config("/backup")

# Check storage
storage = await gateway.get_storage_info()

# Clean up old VMs
vms = await proxmox_client.list_vms("pve01")
for vm in vms:
    if vm.get("tags") == "temp" and age > 7_days:
        await proxmox_client.delete_vm("pve01", vm["vmid"])
```

---

## Security Considerations

### SSH Key Management

**Best Practice: Use SSH Keys**

```python
# Generate key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/glassdome_key

# Use in client
ssh = SSHClient(
    host="192.168.3.2",
    username="root",
    key_filename="~/.ssh/glassdome_key"
)
```

**Store in .env:**
```bash
PROXMOX_SSH_KEY_PATH=/home/user/.ssh/glassdome_key
```

### Password Storage

**Don't hardcode passwords!**

```python
# ❌ BAD
ssh = SSHClient(host="...", password="mysecretpassword")

# ✅ GOOD
import os
password = os.getenv("PROXMOX_SSH_PASSWORD")
ssh = SSHClient(host="...", password=password)
```

### Command Validation

**Validate before executing user input:**

```python
# If allowing user-provided commands
def validate_command(cmd: str) -> bool:
    # Block dangerous commands
    forbidden = ["rm -rf /", "dd if=/dev/zero", "mkfs", "fdisk"]
    return not any(bad in cmd for bad in forbidden)

if validate_command(user_command):
    await ssh.execute(user_command)
else:
    raise ValueError("Dangerous command blocked")
```

### Audit Logging

**Log all SSH operations:**

```python
logger.info(f"SSH: {username}@{host} executing: {command[:50]}...")
# Store in database for audit trail
```

---

## Integration with Agents

### Enhancing Ubuntu Agent

```python
class UbuntuInstallerAgent(DeploymentAgent):
    
    async def _deploy_element(self, element_type, config):
        # 1. Create VM via Proxmox API
        vm_result = await self._create_vm(config)
        
        # 2. Wait for boot and get IP
        ip = vm_result["ip_address"]
        
        # 3. SSH into VM for post-configuration
        ssh = SSHClient(
            host=ip,
            username=config.get("ssh_user", "ubuntu"),
            key_filename=config.get("ssh_key")
        )
        
        await ssh.connect()
        
        # 4. Create users
        for user in config.get("users", []):
            await self._create_user(ssh, user)
        
        # 5. Install packages
        for package in config.get("packages", []):
            await ssh.execute(f"apt install -y {package}")
        
        # 6. Run post-install scripts
        for script in config.get("scripts", []):
            await ssh.execute_script(script)
        
        await ssh.disconnect()
        
        return {
            "success": True,
            "vm_id": vm_result["vm_id"],
            "ip": ip,
            "configured": True
        }
```

---

## API Endpoints

### New Endpoint: Template Management

```python
# glassdome/api/templates.py

@router.post("/templates/create-ubuntu")
async def create_ubuntu_template(
    version: str = "22.04",
    template_id: int = 9000
):
    """
    Automatically create Ubuntu template via SSH
    
    No manual SSH required!
    """
    gateway = ProxmoxGateway(
        host=settings.proxmox_host,
        username=settings.proxmox_ssh_user,
        password=settings.proxmox_ssh_password
    )
    
    result = await gateway.create_ubuntu_template(template_id, version)
    
    return {
        "success": result["success"],
        "template_id": template_id,
        "version": version
    }


@router.get("/templates")
async def list_templates():
    """List all available templates"""
    gateway = ProxmoxGateway(...)
    templates = await gateway.list_templates()
    return {"templates": templates}
```

**Usage:**
```bash
# Create template via API
curl -X POST http://localhost:8001/api/templates/create-ubuntu?version=22.04

# List templates
curl http://localhost:8001/api/templates
```

---

## Configuration

### Add to .env:

```bash
# SSH Configuration for Proxmox Host
PROXMOX_SSH_USER=root
PROXMOX_SSH_PASSWORD=your-password
# OR
PROXMOX_SSH_KEY_PATH=/home/user/.ssh/proxmox_key

# SSH Configuration for Created VMs
VM_SSH_USER=ubuntu
VM_SSH_KEY_PATH=/home/user/.ssh/vm_key
```

### Add to Settings:

```python
# glassdome/core/config.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # SSH Configuration
    proxmox_ssh_user: str = "root"
    proxmox_ssh_password: Optional[str] = None
    proxmox_ssh_key_path: Optional[str] = None
    
    vm_ssh_user: str = "ubuntu"
    vm_ssh_key_path: Optional[str] = None
```

---

## Benefits

### Before SSH Integration:

❌ Manual SSH required for template creation  
❌ Manual SSH for VM configuration  
❌ No automated post-deployment  
❌ Can't validate infrastructure state  
❌ Manual maintenance tasks  

### After SSH Integration:

✅ **Fully autonomous agents**  
✅ **One-click template creation**  
✅ **Automatic VM configuration**  
✅ **Post-deployment automation**  
✅ **Infrastructure validation**  
✅ **Automated maintenance**  
✅ **True agentic behavior**  

---

## Next Steps

1. **Install paramiko:**
   ```bash
   pip install paramiko>=3.4.0
   ```

2. **Configure SSH credentials in .env**

3. **Create template automatically:**
   ```bash
   python3 create_template_auto.py
   ```

4. **Deploy VM with post-configuration:**
   ```python
   # Agent handles everything:
   # - Creates VM
   # - Waits for boot
   # - SSHs in
   # - Configures
   # - Returns ready-to-use VM
   ```

---

## Summary

The agentic framework can now:
- **Execute commands** on any SSH-accessible host
- **Transfer files** to/from remote systems
- **Create infrastructure** automatically (templates, networks, etc.)
- **Configure VMs** post-deployment (users, packages, apps)
- **Perform maintenance** (backups, updates, cleanup)
- **Validate state** (check files, services, configs)

**This makes Glassdome truly autonomous** - agents can do everything a human operator would do via SSH, but automatically!

No more manual SSH sessions. Just tell the agent what you want, and it does it. 🚀

