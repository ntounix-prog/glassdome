# Ubuntu Agent Quick Start 🚀

## What We Built

A **fully autonomous agent** that listens for API calls and creates Ubuntu VMs on Proxmox!

## Quick Test (Without Proxmox)

### 1. Start the Server

```bash
cd /home/nomad/glassdome
source venv/bin/activate
glassdome serve
```

Server starts on **http://localhost:8001**

### 2. Check Available Versions

```bash
curl http://localhost:8001/api/ubuntu/versions
```

Response:
```json
{
  "versions": {
    "22.04": {"name": "Ubuntu 22.04 LTS (Jammy)", ...},
    "24.04": {"name": "Ubuntu 24.04 LTS (Noble)", ...},
    "20.04": {"name": "Ubuntu 20.04 LTS (Focal)", ...}
  }
}
```

### 3. Check Agent Status

```bash
curl http://localhost:8001/api/ubuntu/agent/status
```

### 4. API Documentation

Visit: **http://localhost:8001/docs**

You'll see all Ubuntu endpoints with interactive testing!

## With Proxmox Configuration

### 1. Configure Proxmox

Edit `.env`:
```bash
PROXMOX_HOST=192.168.1.100
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your-password
PROXMOX_VERIFY_SSL=false
```

### 2. Create Ubuntu VM

```bash
curl -X POST http://localhost:8001/api/ubuntu/create-sync \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ubuntu-test",
    "node": "pve",
    "ubuntu_version": "22.04",
    "cores": 2,
    "memory": 2048
  }'
```

### 3. The Agent Does Everything

The agent will:
1. ✅ Validate request
2. ✅ Get next available VM ID
3. ✅ Clone from template (or create from ISO)
4. ✅ Configure resources
5. ✅ Start VM
6. ✅ Wait for IP address
7. ✅ Return VM details

**All autonomous! No manual intervention!**

## Using Python

```python
import requests

# Create VM
response = requests.post(
    "http://localhost:8001/api/ubuntu/create-sync",
    json={
        "name": "my-ubuntu-vm",
        "node": "pve",
        "ubuntu_version": "22.04",
        "cores": 4,
        "memory": 4096
    }
)

result = response.json()
print(f"VM ID: {result['vm_details']['resource_id']}")
print(f"IP: {result['vm_details']['ip_address']}")
```

## Using the Package Directly

```python
from glassdome import ProxmoxClient
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
import asyncio

async def create_vm():
    # Create client
    proxmox = ProxmoxClient(
        host="192.168.1.100",
        user="root@pam",
        password="secret"
    )
    
    # Create agent
    agent = UbuntuInstallerAgent("ubuntu_1", proxmox)
    
    # Create VM
    task = {
        "element_type": "ubuntu_vm",
        "config": {
            "name": "my-vm",
            "node": "pve",
            "ubuntu_version": "22.04"
        }
    }
    
    result = await agent.run(task)
    print(result)

asyncio.run(create_vm())
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/ubuntu/create` | POST | Create VM (async) |
| `/api/ubuntu/create-sync` | POST | Create VM (wait) |
| `/api/ubuntu/versions` | GET | List versions |
| `/api/ubuntu/agent/status` | GET | Agent status |
| `/api/ubuntu/defaults` | GET | Default config |
| `/api/ubuntu/template/create` | POST | Create template |

## Example Requests

### Async (Returns Immediately)

```bash
curl -X POST http://localhost:8001/api/ubuntu/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ubuntu-web-01",
    "node": "pve",
    "ubuntu_version": "22.04"
  }'
```

Returns task ID immediately. Check status later.

### Sync (Waits for Completion)

```bash
curl -X POST http://localhost:8001/api/ubuntu/create-sync \
  -H "Content-Type: application/json" \
  -d '{
    "name": "ubuntu-web-01",
    "node": "pve",
    "ubuntu_version": "22.04"
  }'
```

Waits for VM to be created (may take 1-2 minutes).

## Configuration Options

```json
{
  "name": "my-ubuntu-vm",           // Required
  "node": "pve",                    // Required
  "ubuntu_version": "22.04",        // Optional (default: 22.04)
  "use_template": true,             // Optional (default: true)
  "cores": 2,                       // Optional (default: 2)
  "memory": 2048,                   // Optional (default: 2048)
  "disk_size": 20,                  // Optional (default: 20)
  "network": "vmbr0",               // Optional (default: vmbr0)
  "storage": "local-lvm"            // Optional (default: local-lvm)
}
```

## What Makes This Special

### 1. Autonomous Agent ✨
- Not just a script - it's an **intelligent agent**
- Makes decisions (template vs ISO)
- Handles errors autonomously
- Self-managing lifecycle

### 2. API-Driven 🔌
- RESTful endpoints
- Clean separation of concerns
- Easy integration

### 3. Production-Ready 🚀
- Error handling
- Async operations
- Validation
- Logging
- Documentation

### 4. Extensible 🔧
- Base classes for other agents
- Easy to add more VM types
- Platform-agnostic design

## Next Steps

### Create More Agents

Now that you have one agent working, create more:

- **Kali Linux Agent** - For penetration testing VMs
- **DVWA Agent** - For vulnerable web applications
- **Windows Agent** - For Windows VMs
- **Network Agent** - For virtual networks
- **Docker Agent** - For containerized services

### Add Intelligence

Enhance agents with:
- AI-powered configuration selection
- Cost optimization
- Resource prediction
- Automated testing

### Build the Dashboard

Create React components for:
- Visual VM creation
- Drag-and-drop lab designer
- Real-time deployment monitoring
- Agent status dashboard

## Architecture

```
API Request → FastAPI Endpoint → Ubuntu Agent → Proxmox API
                                      ↓
                               Agent Manager
                                      ↓
                            Orchestration Engine
```

## Files

- `glassdome/agents/ubuntu_installer.py` - Agent code
- `glassdome/api/ubuntu.py` - API endpoints
- `examples/create_ubuntu_vm.py` - Usage examples
- `docs/UBUNTU_AGENT.md` - Full documentation

## Documentation

- **Full docs:** `docs/UBUNTU_AGENT.md`
- **API docs:** http://localhost:8001/docs
- **Examples:** `examples/create_ubuntu_vm.py`

---

## 🎉 You Now Have

✅ A working autonomous agent  
✅ REST API for VM creation  
✅ Package structure for more agents  
✅ Example code and documentation  
✅ Foundation for full cyber range system  

**Start creating Ubuntu VMs autonomously!** 🚀

```bash
glassdome serve
# Then visit http://localhost:8001/docs
```

