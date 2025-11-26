# Glassdome Session Notes

## Session: 2025-11-26 (Portability Refactor)

### Summary
Major refactor to make the codebase fully portable - can now run from any directory (e.g., `/opt/glassdome`) without hardcoded paths.

---

## Completed Work

### 1. Centralized Path Management
**New file: `glassdome/core/paths.py`**

All paths in the application now derive from a single source of truth:
- `PROJECT_ROOT` - Auto-detected from module location
- `GLASSDOME_DATA_DIR` - Overridable via environment variable
- `SECRETS_DIR` - Now in `PROJECT_ROOT/.secrets/` (not `~/.glassdome/`)
- `LOGS_DIR`, `RAG_INDEX_DIR`, `ENV_FILE` - All centralized

**Environment Variable Override:**
```bash
export GLASSDOME_ROOT=/opt/glassdome
export GLASSDOME_DATA_DIR=/opt/glassdome
```

### 2. Files Updated
| File | Change |
|------|--------|
| `glassdome/core/secrets.py` | Use `SECRETS_DIR`, `MASTER_KEY_PATH` |
| `glassdome/core/session.py` | Use `SESSION_CACHE_PATH`, `SESSION_KEY_PATH` |
| `glassdome/core/config.py` | Use `ENV_FILE` for .env loading |
| `glassdome/api/secrets_web.py` | Replace all `Path.home()` references |
| `glassdome/knowledge/*.py` | Use `PROJECT_ROOT`, `RAG_INDEX_DIR` |
| `glassdome/overseer/state.py` | Use `OVERSEER_STATE_FILE` |
| `scripts/network_discovery/*.py` | Use `PROJECT_ROOT` for output files |

### 3. Migration Steps Completed
1. Created `.secrets/` directory in project root
2. Migrated existing secrets from `~/.glassdome/`
3. Added `.secrets/` to `.gitignore`
4. Tested running from `/opt/glassdome` - **SUCCESS**

### 4. Validation
```
/opt/glassdome$ source venv/bin/activate
$ python -c "from glassdome.core.paths import print_paths; print_paths()"

============================================================
GLASSDOME PATH CONFIGURATION
============================================================
PROJECT_ROOT:        /opt/glassdome
GLASSDOME_DATA_DIR:  /opt/glassdome
SECRETS_DIR:         /opt/glassdome/.secrets
LOGS_DIR:            /opt/glassdome/logs
RAG_INDEX_DIR:       /opt/glassdome/.rag_index
ENV_FILE:            /opt/glassdome/.env
============================================================
```

---

## Previous Session: 2025-11-25–26 (Full Feature Session)

### Summary
Major feature session implementing Overseer chat interface, Reaper vulnerability injection system, multi-platform dashboard connections, and VP demo showcase.

---

## Completed Work

### 1. Overseer Chat Interface
**Core conversational AI for operations**

**Features:**
- Real-time WebSocket chat with tool calling
- LLM integration (OpenAI GPT-4o, Anthropic Claude)
- 12 available tools for operations
- Confirmation workflow for destructive actions
- Recursive tool call handling
- **Draggable floating button** (saves position to localStorage)

**Tools Available:**
| Tool | Description |
|------|-------------|
| `deploy_vm` | Deploy single VM to AWS/Proxmox |
| `terminate_vm` | Destroy/delete a VM |
| `deploy_lab` | Deploy multi-VM lab environment |
| `get_platform_status` | Check AWS/Proxmox/Azure status |
| `get_status` | System/mission/deployment status |
| `create_reaper_mission` | Create vulnerability injection mission |
| `send_email` | Send email notifications via Mailcow |
| `search_knowledge` | Search knowledge base |
| `list_resources` | List VMs/hosts/deployments |
| `stop_resource` | Stop a running resource |
| `ask_clarification` | Ask for more details |
| `confirm_action` | Generic confirmation |

### 2. Reaper Vulnerability Injection System ✨ NEW
**Full exploit library and mission management UI**

**Architecture:**
```
Reaper (owns exploits)  ←─────  Architect designs/manages
       │
       └── /missions/{id}/start  ←──  Overseer can ONLY call this
```

**Features:**
- **Exploit Library Browser** - Grid view with filters (type, severity, OS)
- **Mission Builder** - 3-step wizard (Configure → Select Exploits → Launch)
- **Active Missions Tracker** - Progress bars, status updates
- **Mission History** - Completed/failed missions table
- **Live Log Viewer** - Semi-transparent panel with WebSocket streaming
- 6 default exploits pre-loaded (SQL injection, XSS, weak SSH, sudo privesc, SMB anon, DVWA)

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reaper/exploits` | GET | List all exploits |
| `/api/reaper/exploits` | POST | Create new exploit |
| `/api/reaper/exploits/{id}` | GET/PUT/DELETE | CRUD operations |
| `/api/reaper/exploits/seed` | POST | Load default exploits |
| `/api/reaper/missions` | GET/POST | List/create missions |
| `/api/reaper/missions/{id}/start` | POST | Start mission (Overseer access) |
| `/api/reaper/stats` | GET | Dashboard statistics |
| `/api/reaper/logs` | GET | Recent log entries |
| `/api/reaper/logs/stream` | WS | Live log streaming |

**Database Tables:**
- `exploits` - Exploit definitions (CVE, type, severity, scripts, etc.)
- `exploit_missions` - Mission tracking (target, exploits, status, results)

**Log File:** `logs/reaper.log`

**Files Created:**
- `glassdome/reaper/exploit_library.py` - DB models + default exploits
- `glassdome/api/reaper.py` - REST API + WebSocket endpoints
- `frontend/src/pages/ReaperDesign.jsx` - Full React UI
- `frontend/src/styles/ReaperDesign.css` - Dark theme styling

### 3. Platform Status Pages
**Dashboard → Platform → Status View**

**Routes:**
- `/platform/proxmox` - Proxmox VE status
- `/platform/aws` - AWS EC2 instances  
- `/platform/esxi` - VMware ESXi VMs
- `/platform/azure` - Azure VMs

**Features:**
- Summary cards (Total VMs, Running, Stopped, Templates)
- Filter buttons (All, Running, Stopped, Templates)
- Search by VM name or ID
- VM table with status, resources, and actions
- Auto-refresh every 30 seconds
- **Multi-Proxmox support:** pve01 + pve02 shown as distinct servers
- Clickable **Proxmox Servers** cards to filter VMs

### 4. ESXi and Azure Connections
**Added platform client methods and API integration**

| Platform | Host | Status | VMs |
|----------|------|--------|-----|
| ESXi | 192.168.215.76 | ✅ Connected | 11 VMs |
| Azure | Subscription c93088a4-... | ✅ Connected | 0 VMs |

### 5. Email Integration
**Overseer can send email notifications**

- Mailbox: `glassdome-ai@xisx.org`
- SMTP: mail.xisx.org:587
- Usage: "Send a status email to user@example.com"

### 6. VP Demo Showcase
**30-second animated demo for presentations**

- Accessible via "▶ Demo" button on Dashboard only
- Synthwave music with Web Audio API
- Custom audio upload support
- Cyberpunk animations

### 7. Version Management
**Protected MVP with branch strategy**

```
main (v0.3.0) ← Protected, tagged MVP
  └── develop ← All new work
```

**Version:** `0.3.0` (tagged)

---

## Current State

### Services
| Service | Port | Status |
|---------|------|--------|
| Backend API | 8011 | ✅ Running |
| Frontend | 5174 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running (192.168.3.26) |
| Mailcow | 587 | ✅ Connected |

### Platform Connections
| Platform | Status | Details |
|----------|--------|---------|
| Proxmox | ✅ Connected | pve01 (7 VMs) + pve02 (8 VMs) |
| AWS | ✅ Connected | 2 instances (us-east-1, us-west-2) |
| ESXi | ✅ Connected | 11 VMs |
| Azure | ✅ Connected | 0 VMs (glassdome-rg) |

### LLM Providers
- OpenAI (gpt-4o) ✅
- Anthropic (claude-sonnet-4) ✅

---

## Files Created This Session

```
# Reaper System
glassdome/reaper/exploit_library.py
glassdome/api/reaper.py
frontend/src/pages/ReaperDesign.jsx
frontend/src/styles/ReaperDesign.css
logs/reaper.log

# Chat System
glassdome/chat/__init__.py
glassdome/chat/agent.py
glassdome/chat/llm_service.py
glassdome/chat/tools.py
glassdome/chat/workflow_engine.py
glassdome/api/chat.py
frontend/src/components/OverseerChat/

# Platform Status
glassdome/api/platforms.py
frontend/src/pages/PlatformStatus.jsx
frontend/src/styles/PlatformStatus.css

# Demo
frontend/src/components/DemoShowcase/
```

## Files Modified This Session

```
glassdome/main.py                    # Router registration
glassdome/core/database.py           # Reaper tables
glassdome/platforms/esxi_client.py   # list_vms()
glassdome/platforms/azure_client.py  # list_vms()
frontend/src/App.jsx                 # Routes + Reaper
frontend/src/pages/Dashboard.jsx     # Tools section
frontend/src/styles/Dashboard.css    # Tools styling
frontend/src/components/OverseerChat/ChatToggle.jsx  # Draggable
frontend/src/components/OverseerChat/ChatToggle.css
```

---

## Git Commits (develop branch)

```
feat: Reaper Vulnerability Injection System UI
feat: Add comprehensive Reaper logging
feat: Add live log viewer panel to Reaper UI
feat: Make Overseer chat button draggable
chore: Bump version to 0.3.0
feat: Add ESXi and Azure dashboard connections
fix: Demo button only shows on dashboard page
```

---

## Testing Commands

### Reaper API
```bash
# Get stats
curl http://localhost:8011/api/reaper/stats

# List exploits
curl http://localhost:8011/api/reaper/exploits

# Seed default exploits
curl -X POST http://localhost:8011/api/reaper/exploits/seed

# Get recent logs
curl http://localhost:8011/api/reaper/logs
```

### Platform APIs
```bash
curl http://localhost:8011/api/platforms/proxmox/all-instances
curl http://localhost:8011/api/platforms/esxi
curl http://localhost:8011/api/platforms/azure
curl http://localhost:8011/api/platforms/aws/all-regions
```

---

## Next Steps (Roadmap)

1. **GitHub Issues Integration** - Track tickets via GitHub API
2. **Network Architecture** - VM interfaces, bridges, cross-platform mapping
3. **Cross-Platform Migration** - Move labs between ESXi/AWS/Azure
4. **User Authentication** - Roles (observer, architect, engineer, admin)
5. **Enhanced Canvas** - Platform-agnostic lab templates

---

## Version Plan

| Version | Features |
|---------|----------|
| v0.3.0 | MVP - Current (protected on main) |
| v0.4.0 | Reaper UI + GitHub Issues |
| v0.5.0 | Network tracking |
| v0.6.0 | Cross-platform migration |
| v1.0.0 | Production with auth |
