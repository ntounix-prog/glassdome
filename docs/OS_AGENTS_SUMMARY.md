# OS Agents Summary

**Date:** 2024-11-22  
**Status:** ✅ Implemented (Ready for Testing)

---

## Overview

Four new OS installer agents have been implemented following the same platform-agnostic architecture as Ubuntu and Windows agents.

---

## New OS Agents

### 1. RockyInstallerAgent
**File:** `glassdome/agents/rocky_installer.py`  
**Template IDs:** 9200 (Rocky 9), 9201 (Rocky 8)

**Supported Versions:**
- Rocky Linux 9 (default)
- Rocky Linux 8

**Default Configuration:**
- Cores: 2
- Memory: 2048 MB
- Disk: 20 GB
- SSH User: `rocky`

**Usage:**
```python
from glassdome.agents import RockyInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = RockyInstallerAgent("rocky-agent-1", proxmox)

result = await agent.execute({
    "element_type": "rocky_vm",
    "config": {
        "name": "rocky-server-01",
        "rocky_version": "9",
        "cores": 4,
        "memory": 4096,
        "template_id": 9200
    }
})
```

---

### 2. KaliInstallerAgent
**File:** `glassdome/agents/kali_installer.py`  
**Template IDs:** 9300 (2024.1), 9301 (2024.2), 9302 (2023.4)

**Supported Versions:**
- Kali Linux 2024.1 (default)
- Kali Linux 2024.2
- Kali Linux 2023.4

**Default Configuration:**
- Cores: 4 (Kali needs more CPU for tools)
- Memory: 4096 MB (Kali needs more RAM)
- Disk: 50 GB (Kali is larger)
- SSH User: `kali`

**Usage:**
```python
from glassdome.agents import KaliInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = KaliInstallerAgent("kali-agent-1", proxmox)

result = await agent.execute({
    "element_type": "kali_vm",
    "config": {
        "name": "kali-attack-01",
        "kali_version": "2024.1",
        "template_id": 9300
    }
})
```

---

### 3. ParrotInstallerAgent
**File:** `glassdome/agents/parrot_installer.py`  
**Template IDs:** 9400 (6.0), 9401 (5.3)

**Supported Versions:**
- Parrot Security 6.0 (default)
- Parrot Security 5.3

**Default Configuration:**
- Cores: 4 (Parrot needs more CPU for tools)
- Memory: 4096 MB (Parrot needs more RAM)
- Disk: 40 GB (Parrot is larger than Ubuntu)
- SSH User: `parrot`

**Usage:**
```python
from glassdome.agents import ParrotInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = ParrotInstallerAgent("parrot-agent-1", proxmox)

result = await agent.execute({
    "element_type": "parrot_vm",
    "config": {
        "name": "parrot-attack-01",
        "parrot_version": "6.0",
        "template_id": 9400
    }
})
```

---

### 4. RHELInstallerAgent
**File:** `glassdome/agents/rhel_installer.py`  
**Template IDs:** 9500 (RHEL 9), 9501 (RHEL 8)

**Supported Versions:**
- Red Hat Enterprise Linux 9 (default)
- Red Hat Enterprise Linux 8

**Default Configuration:**
- Cores: 2
- Memory: 2048 MB
- Disk: 20 GB
- SSH User: `cloud-user`

**⚠️ Important:** RHEL requires a valid subscription. Ensure subscription is configured in templates or cloud-init.

**Usage:**
```python
from glassdome.agents import RHELInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = RHELInstallerAgent("rhel-agent-1", proxmox)

result = await agent.execute({
    "element_type": "rhel_vm",
    "config": {
        "name": "rhel-server-01",
        "rhel_version": "9",
        "template_id": 9500,
        "subscription_user": "your-rhel-user",  # Optional
        "subscription_password": "your-rhel-pass"  # Optional
    }
})
```

---

## Using OSInstallerFactory

All agents are registered in the factory for easy access:

```python
from glassdome.agents.os_installer_factory import OSInstallerFactory
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)

# Get agent for any OS type
rocky_agent = OSInstallerFactory.get_agent("rocky", proxmox)
kali_agent = OSInstallerFactory.get_agent("kali", proxmox)
parrot_agent = OSInstallerFactory.get_agent("parrot", proxmox)
rhel_agent = OSInstallerFactory.get_agent("rhel", proxmox)

# List all supported OS types
supported = OSInstallerFactory.get_supported_os_types()
# Returns: ['ubuntu', 'windows', 'rocky', 'kali', 'parrot', 'rhel']
```

---

## Template ID Convention

| OS | Version | Template ID | Notes |
|----|---------|-------------|-------|
| Ubuntu | 22.04 | 9000 | Existing |
| Ubuntu | 20.04 | 9001 | Existing |
| Windows Server 2022 | - | 9100 | Existing |
| Windows 11 | - | 9101 | Existing |
| Rocky Linux | 9 | 9200 | **New** |
| Rocky Linux | 8 | 9201 | **New** |
| Kali Linux | 2024.1 | 9300 | **New** |
| Kali Linux | 2024.2 | 9301 | **New** |
| Kali Linux | 2023.4 | 9302 | **New** |
| Parrot Security | 6.0 | 9400 | **New** |
| Parrot Security | 5.3 | 9401 | **New** |
| RHEL | 9 | 9500 | **New** |
| RHEL | 8 | 9501 | **New** |

---

## Architecture

All agents follow the same platform-agnostic architecture:

```
OS Agent (Rocky, Kali, Parrot, RHEL)
    ↓ calls
Platform Client (Proxmox, AWS, Azure, ESXi)
    ↓ implements
PlatformClient Interface (ABC)
```

**Key Benefits:**
- ✅ Same agent code works across all platforms
- ✅ No platform-specific logic in OS agents
- ✅ Easy to add new platforms (just implement PlatformClient)
- ✅ Easy to add new OS types (just create agent + register)

---

## Testing Status

**Current Status:** ✅ Code Complete, ⏳ Testing Pending

**Next Steps:**
1. Create templates for each OS on Proxmox
2. Test deployment on Proxmox
3. Test deployment on ESXi
4. Test deployment on AWS/Azure (if cloud images available)

---

## Notes

- **Kali & Parrot:** Require more resources (4 cores, 4GB RAM, 40-50GB disk) due to pre-installed security tools
- **RHEL:** Requires subscription management - templates should be pre-configured with subscription
- **Rocky Linux:** RHEL-compatible alternative that doesn't require subscription
- All agents support both template-based (fast) and ISO-based (slow) deployment

---

## Files Created

- `glassdome/agents/rocky_installer.py`
- `glassdome/agents/kali_installer.py`
- `glassdome/agents/parrot_installer.py`
- `glassdome/agents/rhel_installer.py`
- Updated: `glassdome/agents/os_installer_factory.py`
- Updated: `glassdome/agents/__init__.py`




