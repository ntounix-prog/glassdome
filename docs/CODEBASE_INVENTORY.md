# Glassdome Codebase Inventory

**Last Updated:** 2024-11-27  
**Purpose:** Define the function and use of every component

---

## Project Root Structure

```
glassdome/
├── glassdome/          # Main Python package (CORE)
├── frontend/           # React frontend (ACTIVE)
├── containers/         # Docker containers (REVIEW NEEDED)
├── scripts/            # Utility scripts (ACTIVE)
├── docs/               # Documentation (ACTIVE)
├── configs/            # Configuration templates (ACTIVE)
├── isos/               # ISO images for VMs (ACTIVE)
├── whiteknight/        # WhiteKnight standalone (DEPRECATED?)
├── tests/              # Test files (MINIMAL)
├── alembic/            # Database migrations (ACTIVE)
├── _deprecated/        # Deprecated code (ARCHIVE)
├── agent_context/      # Agent memory/context (ACTIVE)
├── deploy/             # Deployment scripts (ACTIVE)
├── examples/           # Example configurations (REFERENCE)
└── logs/               # Log files (RUNTIME)
```

---

## Core Package: `glassdome/`

### Root Level Files

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `__init__.py` | ~20 | Package version | ACTIVE |
| `main.py` | ~450 | FastAPI app, routes | ACTIVE - has stub endpoints |
| `cli.py` | ~315 | CLI commands | ACTIVE - has TODOs |
| `server.py` | ? | Uvicorn server | ACTIVE |

---

### `glassdome/agents/` - Deployment Agents

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `base.py` | Base agent class | ACTIVE |
| `manager.py` | Agent lifecycle manager | ACTIVE |
| `overseer.py` | Master orchestration agent | ACTIVE |
| `ubuntu_installer.py` | Ubuntu VM deployment | ACTIVE |
| `windows_installer.py` | Windows VM deployment | ACTIVE |
| `kali_installer.py` | Kali VM deployment | ACTIVE |
| `parrot_installer.py` | Parrot OS deployment | ACTIVE |
| `rhel_installer.py` | RHEL deployment | ACTIVE |
| `rocky_installer.py` | Rocky Linux deployment | ACTIVE |
| `os_installer_factory.py` | Installer factory | ACTIVE |
| `mailcow_agent.py` | Mailcow management | ACTIVE |
| `guest_agent_fixer.py` | QEMU guest agent fix | ACTIVE |

---

### `glassdome/api/` - REST API Endpoints

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `ansible.py` | Ansible playbook API | ACTIVE |
| `auth.py` | Authentication | ACTIVE |
| `canvas_deploy.py` | Canvas lab deployment | ACTIVE - core feature |
| `chat.py` | Overseer chat API | ACTIVE |
| `container_dispatch.py` | Container worker dispatch | REVIEW |
| `labs.py` | Lab management | ACTIVE - has TODOs |
| `networks.py` | Network management | ACTIVE |
| `platforms.py` | Platform status API | ACTIVE |
| `reaper.py` | Reaper missions API | ACTIVE - large, needs split |
| `registry.py` | Lab Registry API | ACTIVE - NEW |
| `ubuntu.py` | Ubuntu deployment API | ACTIVE |
| `whiteknight.py` | Validation API | ACTIVE |
| `whitepawn.py` | Monitoring API | ACTIVE |

---

### `glassdome/chat/` - Overseer Chat System

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `agent.py` | Chat agent with tools | ACTIVE - large, needs split |
| `llm_service.py` | LLM providers (Claude, OpenAI) | ACTIVE |
| `memory.py` | Conversation memory | ACTIVE |
| `tools.py` | Tool definitions | ACTIVE |

---

### `glassdome/core/` - Core Infrastructure

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `config.py` | Settings management | ACTIVE |
| `database.py` | SQLAlchemy async setup | ACTIVE |
| `paths.py` | Path constants | ACTIVE |
| `secrets.py` | Secrets management | ACTIVE |
| `secrets_backend.py` | Secrets backend interface | ACTIVE |
| `security.py` | Security context | ACTIVE |
| `session.py` | Session management | ACTIVE |

---

### `glassdome/integrations/` - External Integrations

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `ansible_bridge.py` | Ansible integration | ACTIVE |
| `ansible_executor.py` | Ansible execution | ACTIVE |
| `mailcow_client.py` | Mailcow email server | ACTIVE - used by Overseer |

---

### `glassdome/knowledge/` - Knowledge Base

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `index_builder.py` | RAG index builder | ACTIVE |
| `rag_engine.py` | RAG query engine | ACTIVE |
| `code_analyzer.py` | Code analysis | ACTIVE |
| `types.py` | Type definitions | ACTIVE |

---

### `glassdome/models/` - Database Models

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `lab.py` | Lab model | ACTIVE |
| `templates.py` | Template models | ACTIVE |
| `deployment.py` | Deployment models | ACTIVE |

---

### `glassdome/networking/` - Network Management

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `models.py` | Network/VM models | ACTIVE |
| `orchestrator.py` | Network orchestration | ACTIVE - has NotImplemented |
| `proxmox_handler.py` | Proxmox networking | ACTIVE |
| `reconciler.py` | State reconciliation | ACTIVE |

---

### `glassdome/orchestration/` - Lab Orchestration

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `engine.py` | Orchestration engine | ACTIVE |
| `lab_orchestrator.py` | Lab deployment | ACTIVE |

---

### `glassdome/overseer/` - Overseer System

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `entity.py` | Entity state management | ACTIVE - many TODOs |
| `service.py` | Overseer service | ACTIVE |
| `types.py` | Type definitions | ACTIVE |

---

### `glassdome/platforms/` - Platform Clients

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `base.py` | Base platform interface | ACTIVE |
| `proxmox_client.py` | Proxmox VE client | ACTIVE - primary |
| `esxi_client.py` | VMware ESXi client | ACTIVE |
| `esxi_template_builder.py` | ESXi templates | KEEP - needed soon |
| `aws_client.py` | AWS EC2 client | ACTIVE |
| `azure_client.py` | Azure VM client | ACTIVE |

---

### `glassdome/reaper/` - Vulnerability Injection

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `hot_spare.py` | Hot spare VM pool | ACTIVE |
| `injector.py` | Vulnerability injector | ACTIVE |
| `library.py` | Exploit library | ACTIVE |
| `mission.py` | Mission management | ACTIVE |
| `validator.py` | Validation engine | ACTIVE |
| `agents/` | Reaper agents | ACTIVE |

---

### `glassdome/registry/` - Lab Registry (NEW)

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `core.py` | Registry core | ACTIVE |
| `models.py` | Registry models | ACTIVE |
| `agents/` | Platform agents | ACTIVE |
| `controllers/` | Reconciliation | ACTIVE |

---

### `glassdome/utils/` - Utilities

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `ip_pool.py` | IP address pool | ACTIVE |
| `cloudinit.py` | Cloud-init templates | ACTIVE |
| `windows_autounattend.py` | Windows unattend | ACTIVE |

---

### `glassdome/vulnerabilities/` - Vulnerability Definitions

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `playbooks/` | Ansible playbooks | ACTIVE |
| `terraform/` | IaC definitions | REVIEW |

---

### `glassdome/whiteknight/` - Validation Engine

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `engine.py` | Validation engine | ACTIVE |

---

### `glassdome/whitepawn/` - Network Monitoring

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `monitor.py` | Network monitor | ACTIVE |
| `orchestrator.py` | Monitoring orchestrator | ACTIVE |
| `models.py` | WhitePawn models | ACTIVE |

---

### `glassdome/workers/` - Celery Workers

| File | Purpose | Status |
|------|---------|--------|
| `__init__.py` | Package init | ACTIVE |
| `celery_app.py` | Celery configuration | ACTIVE |
| `orchestrator.py` | Orchestrator tasks | ACTIVE |
| `build_tasks.py` | Build worker tasks | ACTIVE |
| `reaper_tasks.py` | Reaper worker tasks | ACTIVE |

---

## Containers: `containers/`

| Container | Purpose | Status | Decision |
|-----------|---------|--------|----------|
| `orchestrator/` | Lab deployment worker | NOT USED | KEEP - for future scaling |
| `reaper/` | Vulnerability injection | NOT USED | KEEP - for future scaling |
| `whiteknight/` | Validation worker | NOT USED | KEEP - for future scaling |
| `whitepawn/` | Monitoring worker | NOT USED | KEEP - for future scaling |

**Current State:**
- Only `glassdome-redis` container is running
- All worker functionality runs directly on the host via uvicorn
- Worker containers exist for future horizontal scaling
- Exited containers cleaned up (94MB reclaimed)

**docker-compose.yml** defines:
- 1x orchestrator
- 8x reaper workers (parallelized)
- 1x whiteknight
- 4x whitepawn monitors

**Decision:** Keep container definitions for future use when scaling is needed. Currently not blocking.

---

## Frontend: `frontend/`

| Path | Purpose | Status |
|------|---------|--------|
| `src/pages/Dashboard.jsx` | Main dashboard | ACTIVE |
| `src/pages/LabCanvas.jsx` | Lab designer | ACTIVE |
| `src/pages/LabMonitor.jsx` | Registry monitor | ACTIVE - NEW |
| `src/pages/PlatformStatus.jsx` | Platform VMs | ACTIVE |
| `src/pages/Deployments.jsx` | Deployment list | ACTIVE |
| `src/pages/ReaperDesign.jsx` | Reaper UI | ACTIVE |
| `src/pages/WhiteKnightDesign.jsx` | Validation UI | ACTIVE |
| `src/pages/WhitePawnMonitor.jsx` | Monitoring UI | ACTIVE |
| `src/hooks/useRegistry.js` | Registry hooks | ACTIVE - NEW |
| `src/components/OverseerChat/` | Chat interface | ACTIVE |
| `src/components/NetworkMap.jsx` | Network visualization | ACTIVE |

---

## Scripts: `scripts/`

| Script | Purpose | Status |
|--------|---------|--------|
| `network_discovery/` | Switch/network discovery | ACTIVE |
| `truenas_api_test.py` | TrueNAS testing | ACTIVE |
| Various shell scripts | Automation | REVIEW |

---

## Deprecated: `_deprecated/`

| File | Original Location | Why Deprecated |
|------|------------------|----------------|
| `logging_config.py` | `workers/` | Celery logging not used |
| `cloudbase_init_builder.py` | `integrations/` | Windows cloud-init unused |
| `proxmox_gateway.py` | `platforms/` | Experimental, superseded |
| `os_installer_base.py` | `agents/` | Abstract never implemented |
| `secrets_web.py` | `api/` | Not registered, CLI preferred |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| **Python Files** | ~95 |
| **Lines of Code** | ~25,000 |
| **API Endpoints** | ~15 routers |
| **Platform Clients** | 4 (Proxmox, ESXi, AWS, Azure) |
| **Frontend Pages** | 8 |
| **Deprecated Files** | 5 |

---

## Recommended Actions

### High Priority
1. ✅ Move unused files to `_deprecated/`
2. Review `containers/` - decide: use or remove
3. Clean up stub endpoints in `main.py`

### Medium Priority
1. Split large files (`chat/agent.py`, `api/reaper.py`)
2. Implement or remove NotImplementedError methods

### Low Priority
1. Add comprehensive tests
2. Improve documentation
3. Consolidate duplicate code

