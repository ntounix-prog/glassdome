# Glassdome Session Notes

## Session: 2025-11-25–26 (Overseer Chat, Email, Platform Status, Multi-Proxmox)

### Summary
Major feature session implementing Overseer chat interface with LLM integration, email notifications, platform status pages, and VM deployment/termination via chat.

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

**Files Created:**
- `glassdome/chat/__init__.py`
- `glassdome/chat/agent.py` - Main chat agent
- `glassdome/chat/llm_service.py` - LLM provider abstraction
- `glassdome/chat/tools.py` - Tool definitions
- `glassdome/chat/workflow_engine.py` - Multi-step workflows
- `glassdome/api/chat.py` - WebSocket/REST endpoints
- `frontend/src/components/OverseerChat/` - React components

### 2. Email Integration
**Overseer can send email notifications**

**Setup:**
- Created/reset `glassdome-ai@xisx.org` mailbox on Mailcow
- Password stored in secrets as `overseer_mail_password`
- Uses SMTP via mail.xisx.org:587

**Usage:**
Ask Overseer: "Send a status email to user@example.com"

**Files Modified:**
- `glassdome/chat/agent.py` - Added `_execute_send_email()`
- `glassdome/chat/tools.py` - Added `send_email` tool

### 3. VM Deployment via Chat
**Deploy and terminate VMs through Overseer**

**Examples:**
- "Deploy a t2.nano Ubuntu to AWS us-east-1 called test-vm"
- "Terminate the AWS instance named glassdome-92ff57"

**Features:**
- Automatic platform detection
- Region selection for AWS
- Instance type configuration
- Confirmation before destructive actions

### 4. Platform Status Pages
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
- Clickable **Proxmox Servers** cards (All / pve01 / pve02) to filter VMs
- Combined view shows all VMs with a `Server` column

### 5. AWS Multi-Region Support
**Endpoint:** `/api/platforms/aws/all-regions`

- Queries `us-east-1` (Virginia) and `us-west-2` (Oregon)
- Aggregates instances from all regions
- Shows region in instance name

### 6. Creator Lab Deployment
**Fixed lab deployment from Creator canvas**

- Wired up `/api/deployments` endpoint to actually deploy
- Added platform selector (AWS/Proxmox)
- Fixed node type detection for canvas elements
- Real deployment feedback

### 7. Startup Script Updated
**`./glassdome_start` now supports:**

```bash
./glassdome_start              # Initialize session only
./glassdome_start --backend    # Start backend (port 8011)
./glassdome_start --frontend   # Start frontend (port 5174)
./glassdome_start --all        # Start both services
```

---

## Current State

### Services
| Service | Port | Status |
|---------|------|--------|
| Backend API | 8011 | ✅ Running |
| Frontend | 5174 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running (192.168.3.26) |
| Mailcow | 587 | ✅ Connected |

### Authenticated Secrets (22 total)
- `openai_api_key` ✅
- `anthropic_api_key` ✅
- `aws_access_key_id` ✅
- `aws_secret_access_key` ✅
- `mail_api` ✅
- `overseer_mail_password` ✅ (NEW)
- `proxmox_password` ✅
- And 15 others...

### Platform Connections
| Platform | Status | Instances / Notes |
|----------|--------|-------------------|
| Proxmox | ✅ Connected | **pve01** (192.168.215.78), **pve02** (192.168.215.77) – 15 VMs total |
| AWS | ✅ Connected | 2 instances (mx-east, mx-west) |
| ESXi | ⚠️ Not configured | - |
| Azure | ⚠️ Not configured | - |

### LLM Providers
- OpenAI (gpt-4o) ✅
- Anthropic (claude-sonnet-4) ✅

---

## Bug Fixes This Session

1. **Streaming mode doesn't support tools**
   - Changed default to non-streaming for chat
   - Tools now execute properly

2. **Tool message format for OpenAI**
   - Fixed assistant message with tool_calls before tool results
   - Proper conversation history format

3. **Recursive tool calls**
   - Follow-up LLM responses with tool_calls now processed
   - Multi-step operations work (e.g., get status → send email)

4. **Email configuration**
   - Fixed `api_key` → `api_token` for MailcowClient
   - Added `mail_api` as fallback key name
   - Force sender to configured mailbox

5. **VM serialization error**
   - Fixed JSON serialization of VM objects in tool results

6. **Proxmox multi-instance + token bug**
   - Implemented multi-instance Proxmox config (`get_proxmox_config(instance_id)`) and discovery (`list_proxmox_instances()`)
   - Added `/api/platforms/proxmox/all-instances` to aggregate **pve01 + pve02**
   - Found a stale `proxmox_token_value_02` with limited permissions that caused pve02 to return 0 VMs
   - Removed the bad token from the secrets manager so password auth is used and all 8 pve02 VMs are visible

---

## Files Created This Session

```
glassdome/chat/__init__.py
glassdome/chat/agent.py
glassdome/chat/llm_service.py
glassdome/chat/tools.py
glassdome/chat/workflow_engine.py
glassdome/api/chat.py
glassdome/api/platforms.py
glassdome/reaper/                    # Full Reaper system
frontend/src/components/OverseerChat/
frontend/src/pages/PlatformStatus.jsx
frontend/src/styles/PlatformStatus.css
docs/REAPER_SYSTEM.md
```

## Files Modified This Session

```
glassdome/main.py                    # Deployment endpoint, session loading
glassdome/server.py                  # Logging configuration
glassdome/overseer/entity.py         # Reaper integration
frontend/src/App.jsx                 # Chat + platform routes
frontend/src/pages/Dashboard.jsx     # Platform links
frontend/src/pages/LabCanvas.jsx     # Platform selector, deployment
frontend/src/styles/Dashboard.css    # Link styling
frontend/src/styles/LabCanvas.css    # Platform selector styling
scripts/start_glassdome.sh           # Updated with --frontend, --all
```

---

## Testing Commands

### Check Services
```bash
curl http://localhost:8011/api/health
curl http://localhost:8011/api/platforms/aws/all-regions
```

### Test Chat
```bash
curl -X POST http://localhost:8011/api/chat/conversations/test/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "What AWS instances do I have?"}'
```

### Test Email
```bash
# Via Overseer chat:
"Send a status email to user@example.com"
```

---

## Next Steps

1. **Proxmox Integration:** Wire up VM actions (start/stop)
2. **Reaper Testing:** Test vulnerability injection via chat
3. **ESXi/Azure:** Add credentials to secrets
4. **Monitoring:** Add Overseer background monitoring
5. **Lab Templates:** Pre-built lab configurations

---

## Git Commits This Session

```
feat: Overseer Chat Interface + Reaper System + Platform Status
feat: Add email tool to Overseer + fix Creator deployment
```

