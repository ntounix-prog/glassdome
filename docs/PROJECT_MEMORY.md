# Glassdome Project Memory

**Last Updated:** November 24, 2024  
**Purpose:** Centralized knowledge base for agent context and summaries

---

## Platform Integrations

### Azure Integration
- **Status:** ✅ Fully Implemented
- **File:** `glassdome/platforms/azure_client.py` (799 lines)
- **Capabilities:**
  - VM creation (Linux and Windows)
  - Resource group management
  - 101 Azure regions globally supported
  - Dynamic region selection
  - Cloud-init support
  - Auto image lookup
  - Provider registration
- **Tested:** 2024-11-20
- **Credentials:** Service principal (client_id, client_secret, tenant_id, subscription_id)
- **Default Region:** eastus
- **Resource Group:** glassdome-rg (creates if doesn't exist)

### AWS Integration
- **Status:** ✅ Fully Implemented
- **File:** `glassdome/platforms/aws_client.py`
- **Capabilities:**
  - EC2 instance deployment
  - Dynamic AMI selection
  - ARM64 support
  - VPC and subnet creation
  - Security group configuration
  - Cloud-init support
- **Regions:** Flexible (tested us-east-1, us-west-2)
- **Credentials:** AWS access keys

### Proxmox Integration
- **Status:** ✅ Fully Implemented (Multi-Instance Support)
- **File:** `glassdome/platforms/proxmox_client.py`
- **Capabilities:**
  - Full CRUD operations
  - Template cloning
  - Cloud-init support
  - Windows template-based deployment
  - Multi-instance support (pve01, pve02)
  - Template migration tools
  - VM management (create, start, stop, delete)
  - IP detection via QEMU guest agent
- **Instances:**
  - Original Proxmox: 192.168.215.78 (pve01)
  - Current Proxmox: 192.168.215.77 (pve02)
- **Authentication:** API tokens or password

### ESXi Integration
- **Status:** ✅ Fully Implemented
- **File:** `glassdome/platforms/esxi_client.py`
- **Capabilities:**
  - VM creation
  - Template builder
  - Cloud-init support
  - Standalone host support
- **Status:** VMware infrastructure currently offline (needs validation)

---

## Package Structure

### Python Package
- **Structure:** Proper Python package with `pyproject.toml`
- **Package Name:** `glassdome`
- **Version:** 0.1.0
- **Installation:**
  ```bash
  pip install -e /home/nomad/glassdome
  ```
- **CLI Commands:**
  - `glassdome serve` - Start API server
  - `glassdome init` - Initialize system
  - `glassdome status` - System status
- **Ports:**
  - Backend: 8001 (changed from 8000)
  - Frontend: 5174 (changed from 5173)
- **Documentation:** `docs/PACKAGE_GUIDE.md`

### Debian Package (Vulnerability Packages)
- **Concept:** Vulnerabilities packaged as `.deb` files
- **Purpose:** Fast, reliable vulnerability deployment
- **Status:** Planned (not yet implemented)
- **Location:** `docs/_archive/NETWORK_ARCHITECTURE.md`
- **Example:** `glassdome-vuln-sql-injection-dvwa_1.0_all.deb`

---

## Git Operations

### Repository
- **URL:** https://github.com/ntounix-prog/glassdome
- **Status:** Active, regularly updated
- **Branch:** main
- **Documentation:** `docs/GIT_SETUP.md`

### Workflow
- **Commit Conventions:** Conventional commits (feat:, fix:, docs:, etc.)
- **Branch Strategy:** Feature branches
- **Recent Activity:** Regular commits for incidents, features, documentation

### Recent Commits (Last 7 Days)
- Documentation updates
- RAG index rebuilds
- Incident resolutions
- Network discovery
- Template migration

---

## Project History

### Project Start
- **Date:** November 19, 2024
- **Initial Focus:** Agentic cyber range deployment framework

### Major Milestones

**Week 1 (Nov 19-20):**
- Project structure and architecture
- Backend framework (FastAPI)
- Agent architecture
- Proxmox integration
- SSH capabilities

**Week 2 (Nov 21-27):**
- Windows deployment (template-based)
- Multi-platform support
- OS agent expansion (Rocky, Kali, Parrot, RHEL)
- Template migration tools

**Week 3 (Nov 18-24):**
- Incident #001: Email delivery failure (MTU fragmentation)
- Incident #002: mxeast WireGuard endpoint
- Incident #003: Network device routing
- Cisco switch discovery
- Port labeling
- Security assessment planning
- VLAN cleanup proposal
- RAG system rebuild (5,005 documents indexed)

---

## Recent Accomplishments (Last 7 Days)

### Incidents Resolved
1. **Incident #001:** Email delivery failure
   - Root cause: WireGuard MTU fragmentation
   - Resolution: Reduced MTU to 1400 bytes
   - Impact: Restored critical mail services

2. **Incident #002:** mxeast WireGuard endpoint
   - Added missing endpoint to mxeast WireGuard config
   - Validated security

3. **Incident #003:** Network device routing
   - Fixed default gateways on Cisco switches
   - Enabled network discovery

### Network Infrastructure
- Discovered 2 Cisco switches (3850, Nexus 3064)
- Mapped 16 connected interfaces
- Labeled 6 unlabeled ports
- Identified 57 VLANs
- Created VLAN cleanup proposal
- Created security assessment plan

### Documentation
- Consolidated 100+ files into organized structure
- Rebuilt RAG index (5,005 documents)
- Created 30+ new documentation files
- Updated core documentation (AGENT_CONTEXT.md, INCIDENTS.md)

---

## Key Technical Details

### Multi-Platform Support
- **Platforms:** Proxmox, ESXi, AWS, Azure
- **OS Support:** Ubuntu, Windows Server 2022, Windows 11, Windows 10, Rocky Linux, Kali Linux, Parrot Security, RHEL
- **Deployment Method:** Template-based (fast, reliable)

### Agent Framework
- **Base Class:** `OSInstallerAgentBase`
- **Factory:** `OSInstallerFactory`
- **Agents:** Ubuntu, Windows, Rocky, Kali, Parrot, RHEL
- **Purpose:** OS-specific deployment logic

### Orchestration
- **Engine:** `OrchestrationEngine`
- **Lab Orchestrator:** `LabOrchestrator`
- **Features:** Dependency management, parallel deployment, task graphs

### Network Management
- **Cisco Switches:** 3850 (corefc), Nexus 3064 (core3k)
- **UniFi Gateway:** API integration for device identification
- **VLAN Management:** Planned (VLAN cleanup proposal created)

---

## Current Status

### Completed (60-70%)
- Multi-platform deployment (Proxmox, ESXi, AWS, Azure)
- Agent framework with OS-specific agents
- Template-based deployment
- Windows deployment (Server 2022, Windows 11, Windows 10)
- Mailcow integration
- SSH automation
- Network discovery tools
- Documentation system

### In Progress (20%)
- Multi-VM orchestration
- Network orchestration (VLAN management)
- React frontend (25% complete)
- Template migration (from Proxmox 01 to Proxmox 02)

### Planned (20%)
- Reaper Agent (vulnerability injection)
- Research Agent (AI-powered CVE research)
- Security assessment execution
- VLAN cleanup implementation

---

## Key Files and Locations

### Core Code
- `glassdome/platforms/` - Platform clients (Azure, AWS, Proxmox, ESXi)
- `glassdome/agents/` - OS installer agents
- `glassdome/orchestration/` - Orchestration engine
- `glassdome/integrations/` - External integrations (Mailcow, etc.)

### Documentation
- `docs/` - Main documentation directory
- `docs/AGENT_CONTEXT.md` - Agent identity and capabilities
- `docs/INCIDENTS.md` - Incident log
- `docs/PACKAGE_GUIDE.md` - Package usage guide
- `docs/GIT_SETUP.md` - Git workflows

### Configuration
- `.env` - Environment variables
- `pyproject.toml` - Python package configuration
- `glassdome/core/config.py` - Settings management

---

## Important Notes

1. **Glassdome is a Python package** - Installable with `pip install -e .`
2. **Multi-instance Proxmox support** - Can manage multiple Proxmox servers
3. **Template-based deployment** - Fast, reliable (2-3 min vs 20+ min from ISO)
4. **RAG system** - 5,005 documents indexed for knowledge retrieval
5. **Git repository** - Active on GitHub, regular commits

---

*This document should be updated weekly or after major changes to maintain accurate project memory.*

