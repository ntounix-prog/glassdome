# Ubuntu Installer Agent

## Overview

The Ubuntu Installer Agent is a specialized autonomous agent that listens for API calls and creates base Ubuntu installation images on Proxmox.

## Features

- ✅ **Autonomous Operation** - Agent handles entire VM creation process
- ✅ **Multiple Ubuntu Versions** - Supports 20.04, 22.04, and 24.04 LTS
- ✅ **Template Support** - Fast cloning from pre-built templates
- ✅ **ISO Installation** - Create from scratch when templates don't exist
- ✅ **Configurable Resources** - CPU, memory, disk, network
- ✅ **API-Driven** - REST API for triggering deployments
- ✅ **Async & Sync** - Both async (background) and sync (wait) modes

## Supported Ubuntu Versions

| Version | Name | Template ID | Status |
|---------|------|-------------|--------|
| 22.04 | Ubuntu 22.04 LTS (Jammy) | 9000 | ✅ Default |
| 24.04 | Ubuntu 24.04 LTS (Noble) | 9001 | ✅ Supported |
| 20.04 | Ubuntu 20.04 LTS (Focal) | 9002 | ✅ Supported |

## Default Configuration

```python
{
    "cores": 2,
    "memory": 2048,  # MB
    "disk_size": 20,  # GB
    "network": "vmbr0",
    "storage": "local-lvm",
}
```

## API Endpoints

### 1. Create Ubuntu VM (Async)

```http
POST /api/ubuntu/create
```

**Request:**
```json
{
    "name": "ubuntu-web-server",
    "node": "pve",
    "ubuntu_version": "22.04",
    "use_template": true,
    "cores": 2,
    "memory": 2048,
    "disk_size": 20
}
```

**Response:**
```json
{
    "success": true,
    "message": "Ubuntu VM creation task submitted: ubuntu_vm_ubuntu-web-server",
    "task_id": "ubuntu_vm_ubuntu-web-server"
}
```

Returns immediately with a task ID. Check task status separately.

### 2. Create Ubuntu VM (Sync)

```http
POST /api/ubuntu/create-sync
```

**Request:** Same as async

**Response:**
```json
{
    "success": true,
    "message": "Ubuntu VM created successfully",
    "vm_details": {
        "resource_id": 101,
        "vm_name": "ubuntu-web-server",
        "node": "pve",
        "ubuntu_version": "22.04",
        "ip_address": "10.0.0.101",
        "status": "created"
    }
}
```

Waits for completion before responding (may take several minutes).

### 3. List Ubuntu Versions

```http
GET /api/ubuntu/versions
```

**Response:**
```json
{
    "versions": {
        "22.04": {
            "name": "Ubuntu 22.04 LTS (Jammy)",
            "iso": "ubuntu-22.04.3-live-server-amd64.iso",
            "template_id": 9000
        },
        ...
    },
    "default_version": "22.04"
}
```

### 4. Get Agent Status

```http
GET /api/ubuntu/agent/status
```

**Response:**
```json
{
    "agent_id": "ubuntu_installer_1",
    "agent_type": "deployment",
    "status": "idle",
    "error": null
}
```

### 5. Get Default Config

```http
GET /api/ubuntu/defaults
```

**Response:**
```json
{
    "default_config": {
        "cores": 2,
        "memory": 2048,
        "disk_size": 20,
        "network": "vmbr0",
        "storage": "local-lvm"
    }
}
```

### 6. Create Template

```http
POST /api/ubuntu/template/create
```

**Request:**
```json
{
    "node": "pve",
    "ubuntu_version": "22.04",
    "template_vmid": 9000
}
```

Creates a base template for faster future deployments.

## Usage Examples

### Using cURL

```bash
# Create Ubuntu VM
curl -X POST http://localhost:8001/api/ubuntu/create-sync \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ubuntu-test",
    "node": "pve",
    "ubuntu_version": "22.04",
    "cores": 2,
    "memory": 2048
  }'

# List available versions
curl http://localhost:8001/api/ubuntu/versions

# Check agent status
curl http://localhost:8001/api/ubuntu/agent/status
```

### Using Python Requests

```python
import requests

# Create VM
response = requests.post(
    "http://localhost:8001/api/ubuntu/create-sync",
    json={
        "name": "ubuntu-web-server",
        "node": "pve",
        "ubuntu_version": "22.04",
        "cores": 4,
        "memory": 4096,
        "disk_size": 50
    }
)

result = response.json()
print(f"VM created: {result['vm_details']['resource_id']}")
```

### Using Glassdome Package

```python
from glassdome import ProxmoxClient
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent

# Create agent
proxmox = ProxmoxClient(host="...", user="...", password="...")
agent = UbuntuInstallerAgent("ubuntu_1", proxmox)

# Create VM
task = {
    "element_type": "ubuntu_vm",
    "config": {
        "name": "my-ubuntu-vm",
        "node": "pve",
        "ubuntu_version": "22.04",
        "use_template": True
    }
}

result = await agent.run(task)
```

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Proxmox Configuration (required for Ubuntu agent)
PROXMOX_HOST=your-proxmox-host
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your-password
PROXMOX_VERIFY_SSL=false
```

### Using Templates vs ISO

**Templates (Recommended):**
- ✅ Fast (cloning takes ~30 seconds)
- ✅ Consistent configuration
- ✅ Ready to use immediately
- ⚠️ Requires template to be created first

**ISO Installation:**
- ✅ No dependencies
- ✅ Full customization
- ⚠️ Slower (requires manual/automated installation)
- ⚠️ VM created but not started

## How It Works

### Template Clone Method (Fast)

1. Agent receives API request
2. Validates configuration
3. Gets next available VM ID
4. Clones from template (VM 9000, 9001, or 9002)
5. Configures resources (CPU, memory)
6. Starts VM
7. Waits for IP address assignment
8. Returns VM details

### ISO Installation Method (Slower)

1. Agent receives API request
2. Validates configuration
3. Gets next available VM ID
4. Creates new VM with specified resources
5. Attaches Ubuntu ISO to virtual CD-ROM
6. Returns VM details (not started)
7. Manual or automated installation required

## Agent Architecture

```python
class UbuntuInstallerAgent(DeploymentAgent):
    """
    Specialized agent for Ubuntu deployments
    
    Inherits from DeploymentAgent base class
    Implements autonomous VM creation logic
    """
    
    async def validate(task):
        """Validate task can be executed"""
        
    async def execute(task):
        """Execute the deployment"""
        
    async def _deploy_element(element_type, config):
        """Core deployment logic"""
```

## Creating Templates

For best performance, create templates once:

```bash
# Via API
curl -X POST http://localhost:8001/api/ubuntu/template/create \
  -H "Content-Type: application/json" \
  -d '{
    "node": "pve",
    "ubuntu_version": "22.04"
  }'

# Via Glassdome CLI
glassdome ubuntu create-template --node pve --version 22.04
```

## Error Handling

The agent handles various error conditions:

- **Proxmox not configured:** Returns 503 error
- **Invalid Ubuntu version:** Returns validation error
- **VM creation fails:** Returns detailed error message
- **Template not found:** Falls back to ISO installation
- **Timeout waiting for IP:** Returns VM details without IP

## Monitoring

Check agent status:

```python
from glassdome import agent_manager

status = agent_manager.get_status()
print(status['agents']['ubuntu_installer_1'])
```

Or via API:
```bash
curl http://localhost:8001/api/ubuntu/agent/status
```

## Best Practices

1. **Use Templates** - Much faster than ISO installation
2. **Create Templates Once** - Per Ubuntu version, per node
3. **Async for Multiple VMs** - Use async endpoint for parallel creation
4. **Sync for Single VMs** - Use sync endpoint for immediate feedback
5. **Configure Proxmox First** - Set environment variables before using
6. **Check Agent Status** - Verify agent is ready before submitting tasks

## Troubleshooting

### Agent Not Initialized

```
Error: "Proxmox not configured"
```

**Solution:** Set Proxmox credentials in `.env`:
```bash
PROXMOX_HOST=192.168.1.100
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your-password
```

### Template Not Found

```
Error: "Template 9000 not found"
```

**Solution:** Create template or use `use_template: false` in request.

### VM Creation Timeout

```
Error: "Timeout waiting for IP"
```

**Solution:** Check if QEMU guest agent is installed in template, or ignore IP field.

## Next Steps

- Add more specialized agents (Kali, DVWA, Metasploitable)
- Implement cloud-init for automated configuration
- Add post-installation scripts
- Create agent for template management
- Implement multi-node deployment

## Example Script

See `examples/create_ubuntu_vm.py` for complete working examples.

---

**The Ubuntu Installer Agent demonstrates the power of the agentic framework - autonomous, API-driven infrastructure deployment!**

