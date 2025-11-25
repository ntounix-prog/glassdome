# Multi-Proxmox Platform Support

**Date:** November 22, 2024  
**Status:** ✅ Implemented

---

## Overview

Glassdome now supports multiple Proxmox platforms with instance selection. You can deploy VMs to different Proxmox hosts by specifying the instance ID.

---

## Configuration

### Environment Variables

**Instance 01 (Default/Backward Compatible):**
```bash
PROXMOX_HOST=192.168.3.2
PROXMOX_USER=apex@pve
PROXMOX_TOKEN_NAME=glassdome-token
PROXMOX_TOKEN_VALUE=your-token-secret-here
PROXMOX_NODE=pve
PROXMOX_VERIFY_SSL=false
```

**Instance 02:**
```bash
PROXMOX_02_HOST=192.168.3.10
PROXMOX_02_USER=apex@pve
PROXMOX_02_TOKEN_NAME=glassdome-token
PROXMOX_TOKEN_VALUE_02=your-second-token-secret-here
PROXMOX_02_NODE=pve
PROXMOX_02_VERIFY_SSL=false
```

**Instance 03+ (Future):**
```bash
PROXMOX_03_HOST=192.168.3.11
PROXMOX_03_USER=apex@pve
PROXMOX_TOKEN_VALUE_03=your-third-token-secret-here
# etc.
```

**Note:** Token value uses `PROXMOX_TOKEN_VALUE_XX` format (not `PROXMOX_XX_TOKEN_VALUE`) for consistency.

---

## Usage

### Python API

**Get Proxmox Client for Specific Instance:**
```python
from glassdome.platforms.proxmox_factory import get_proxmox_client

# Instance 01 (default)
client_01 = get_proxmox_client(instance_id="01")

# Instance 02
client_02 = get_proxmox_client(instance_id="02")

# Use client to deploy VMs
result = await client_02.create_vm({
    "name": "test-vm",
    "template_id": 9000,
    "memory_mb": 2048
})
```

**Get Configuration:**
```python
from glassdome.core.config import settings

# Get config for instance 01
config_01 = settings.get_proxmox_config("01")

# Get config for instance 02
config_02 = settings.get_proxmox_config("02")

# List all configured instances
instances = settings.list_proxmox_instances()
# Returns: ["01", "02"]
```

**List Available Instances:**
```python
from glassdome.platforms.proxmox_factory import list_available_proxmox_instances

instances = list_available_proxmox_instances()
# Returns: ["01", "02", "03", ...]
```

### REST API

**Create Ubuntu VM on Specific Instance:**
```json
POST /api/ubuntu/create
{
    "name": "test-vm",
    "node": "pve",
    "ubuntu_version": "22.04",
    "proxmox_instance": "02",  // ← Specify instance
    "cores": 2,
    "memory": 2048
}
```

**Default Behavior:**
- If `proxmox_instance` is not specified, uses instance "01" (backward compatible)
- All existing code continues to work without changes

---

## Agent Usage

**Windows Installer Agent:**
```python
from glassdome.agents import WindowsInstallerAgent
from glassdome.platforms.proxmox_factory import get_proxmox_client

# Get client for instance 02
proxmox = get_proxmox_client(instance_id="02")

# Create agent with specific client
agent = WindowsInstallerAgent(platform_client=proxmox)

# Deploy Windows VM
result = await agent.execute({
    "name": "windows-server",
    "windows_version": "server2022",
    "template_id": 9100
})
```

**Ubuntu Installer Agent:**
```python
from glassdome.agents import UbuntuInstallerAgent
from glassdome.platforms.proxmox_factory import get_proxmox_client

# Get client for instance 02
proxmox = get_proxmox_client(instance_id="02")

# Create agent
agent = UbuntuInstallerAgent(platform_client=proxmox)

# Deploy Ubuntu VM
result = await agent.execute({
    "name": "ubuntu-vm",
    "template_id": 9000
})
```

---

## Implementation Details

### Configuration Loading

The `Settings` class now includes:
- `get_proxmox_config(instance_id)` - Get config for specific instance
- `list_proxmox_instances()` - List all configured instances

### Factory Pattern

New `proxmox_factory.py` module provides:
- `get_proxmox_client(instance_id)` - Create ProxmoxClient for instance
- `list_available_proxmox_instances()` - List configured instances

### Backward Compatibility

- All existing code using `settings.proxmox_host` continues to work
- Instance "01" is the default and uses existing variables
- No breaking changes to existing APIs

---

## Example: Deploying to Multiple Platforms

```python
from glassdome.platforms.proxmox_factory import get_proxmox_client
from glassdome.agents import UbuntuInstallerAgent

# Deploy to first Proxmox
proxmox_01 = get_proxmox_client("01")
agent_01 = UbuntuInstallerAgent(platform_client=proxmox_01)
result_01 = await agent_01.execute({
    "name": "vm-on-proxmox-01",
    "template_id": 9000
})

# Deploy to second Proxmox
proxmox_02 = get_proxmox_client("02")
agent_02 = UbuntuInstallerAgent(platform_client=proxmox_02)
result_02 = await agent_02.execute({
    "name": "vm-on-proxmox-02",
    "template_id": 9000
})
```

---

## Environment Variable Patterns

### Supported Formats

**Instance 02:**
- `PROXMOX_02_HOST` ✅
- `PROXMOX_02_USER` ✅
- `PROXMOX_02_TOKEN_NAME` ✅
- `PROXMOX_TOKEN_VALUE_02` ✅ (special format)
- `PROXMOX_02_PASSWORD` ✅
- `PROXMOX_02_NODE` ✅
- `PROXMOX_02_VERIFY_SSL` ✅

**Instance 03:**
- `PROXMOX_03_HOST` ✅
- `PROXMOX_03_USER` ✅
- `PROXMOX_TOKEN_VALUE_03` ✅
- etc.

---

## Migration Guide

### From Single to Multi-Instance

**Before:**
```python
proxmox = ProxmoxClient(
    host=settings.proxmox_host,
    user=settings.proxmox_user,
    token_value=settings.proxmox_token_value
)
```

**After (Still Works):**
```python
# Option 1: Still works (uses instance 01)
proxmox = ProxmoxClient(
    host=settings.proxmox_host,
    user=settings.proxmox_user,
    token_value=settings.proxmox_token_value
)

# Option 2: Use factory (recommended)
from glassdome.platforms.proxmox_factory import get_proxmox_client
proxmox = get_proxmox_client("01")  # or "02", "03", etc.
```

---

## Future Enhancements

- [ ] Instance selection in web UI
- [ ] Instance health monitoring
- [ ] Load balancing across instances
- [ ] Instance-specific template management
- [ ] Instance metadata (name, description, tags)

---

## Troubleshooting

### "Proxmox instance XX not configured"

**Check:**
1. Environment variable exists: `PROXMOX_XX_HOST`
2. User is set: `PROXMOX_XX_USER`
3. Token is set: `PROXMOX_TOKEN_VALUE_XX` (note the format)

**Verify:**
```python
from glassdome.core.config import settings

config = settings.get_proxmox_config("02")
print(config)  # Should show all config values
```

### "Missing credentials"

**Check:**
- Either `PROXMOX_TOKEN_VALUE_XX` OR `PROXMOX_XX_PASSWORD` must be set
- Token name: `PROXMOX_XX_TOKEN_NAME` (can reuse from instance 01)

---

*Last Updated: November 22, 2024*

