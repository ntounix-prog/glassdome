# Glassdome Agent Context

**Last Updated:** 2024-11-28
**Version:** 0.6.3 (Contextual Help)

This file provides context for AI assistants working on Glassdome. Read this first to understand the current state of the project.

---

## What is Glassdome?

Glassdome is a **cyber range automation platform** for creating, deploying, and managing cybersecurity training labs. It deploys VMs across multiple platforms (Proxmox, ESXi, AWS, Azure), injects vulnerabilities for training, and monitors lab health with a central registry.

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│  React Frontend (port 5174) - Lab Canvas, Monitor, Deployments   │
│  - Overseer Chat (Claude AI)  - Integrated SomaFM Radio         │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API + WebSocket
┌────────────────────────────┴────────────────────────────────────┐
│                    FastAPI Backend (port 8011)                   │
│  - Lab management        - Platform connections                  │
│  - Reaper missions       - WhiteKnight validation                │
│  - Registry API          - WebSocket events                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Lab Registry (Redis)                          │
│  - Real-time resource state    - Tiered polling (1-60s)         │
│  - Pub/Sub event streaming     - Drift detection                 │
│  - Self-healing reconciliation - WebSocket broadcast             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Platform Agents                               │
│  ProxmoxAgent (10s) | UnifiAgent (15s) | TrueNAS (planned)      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Infrastructure                                │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │ Proxmox 01  │   │ Proxmox 02  │   │  TrueNAS    │            │
│  │ (Production)│   │   (Labs)    │   │ (29TB NFS)  │            │
│  │192.168.215.78   │192.168.215.77   │192.168.215.75│            │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘            │
│         └────────── 10G Cluster ─────────────┘                   │
│                   Nexus 3064X Switch                             │
│               VLANs 211/212 (SAN A/B)                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Directories

```
glassdome/
├── glassdome/              # Main Python package
│   ├── api/                # FastAPI routers
│   │   ├── reaper.py       # Reaper missions API
│   │   ├── whiteknight.py  # WhiteKnight validation API
│   │   ├── canvas_deploy.py# Lab deployment from Canvas
│   │   ├── registry.py     # Lab Registry API ✨ NEW
│   │   └── ...
│   ├── registry/           # Lab Registry system ✨ NEW
│   │   ├── core.py         # LabRegistry class (Redis)
│   │   ├── models.py       # Resource, StateChange, Drift
│   │   ├── agents/         # Platform polling agents
│   │   │   ├── base.py     # BaseAgent framework
│   │   │   ├── proxmox_agent.py
│   │   │   └── unifi_agent.py
│   │   └── controllers/    # Reconciliation controllers
│   │       └── lab_controller.py
│   ├── workers/            # Celery workers
│   │   ├── celery_app.py   # Celery configuration
│   │   ├── orchestrator.py # Lab deployment tasks
│   │   ├── reaper.py       # Vulnerability injection
│   │   └── whiteknight.py  # Validation tasks
│   ├── reaper/             # Reaper subsystem
│   │   ├── exploit_library.py # Exploit/Mission models
│   │   └── hot_spare.py    # Hot spare VM pool
│   ├── platforms/          # Platform clients
│   │   ├── proxmox_client.py
│   │   ├── esxi_client.py
│   │   ├── aws_client.py
│   │   └── azure_client.py
│   └── core/               # Core utilities
│       ├── config.py       # Settings (Pydantic)
│       ├── database.py     # SQLAlchemy setup
│       └── ssh_client.py   # SSH utilities
├── frontend/               # React frontend
│   └── src/
│       ├── pages/          # Page components
│       │   ├── LabCanvas.jsx    # Visual lab builder
│       │   ├── LabMonitor.jsx   # Registry monitor ✨ NEW
│       │   ├── FeatureDetail.jsx# Feature descriptions ✨ NEW
│       │   ├── Deployments.jsx  # Deployment management
│       │   └── WhitePawnMonitor.jsx
│       ├── hooks/          # React hooks ✨ NEW
│       │   └── useRegistry.js   # Registry API hooks
│       ├── components/
│       │   └── OverseerChat/    # AI Chat + Radio ✨ UPDATED
│       └── styles/
├── scripts/
│   ├── start_workers.sh    # Worker fleet management
│   └── network_discovery/  # Switch configuration
├── docs/
│   ├── session_logs/       # Daily progress logs
│   ├── CODE_AUDIT_REPORT.md
│   └── CODEBASE_INVENTORY.md
├── _deprecated/            # Deprecated code ✨ NEW
└── docker-compose.yml
```

---

## Key Concepts

### 1. Lab Registry (Central Source of Truth)
Real-time infrastructure monitoring with tiered polling:

```python
# Registry API endpoints
GET  /api/registry/status           # Health check
GET  /api/registry/resources        # List resources (filterable)
GET  /api/registry/labs/{id}        # Lab snapshot
WS   /api/registry/ws/events        # Real-time events

# Tier structure
Tier 1: Lab VMs, Networks  → 1s polling (webhook-ready)
Tier 2: All VMs, Templates → 10s polling
Tier 3: Hosts, Storage     → 30-60s polling
```

### 2. Hot Spare Pool
Pre-provisioned VMs ready for instant deployment:

```python
pool = get_hot_spare_pool()
spare = await pool.acquire_spare(session, os_type="ubuntu", mission_id="xxx")
```

### 3. Platform Abstraction
All platforms implement the same interface:

```python
client = ProxmoxClient(...)  # or ESXiClient, AWSClient, AzureClient
await client.create_vm(config)
await client.clone_vm(template_id, new_vm_id, config)
await client.start_vm(node, vmid)
```

### 4. Canvas Lab Deployment
pfSense-as-gateway architecture for isolated lab networks:

```
┌─────────────────────────────────────────┐
│              Management (VLAN 2)         │
│           192.168.2.x (DHCP)            │
└──────────────────┬──────────────────────┘
                   │ net0 (WAN)
              ┌────┴────┐
              │ pfSense │
              │ Gateway │
              └────┬────┘
                   │ net1 (LAN)
┌──────────────────┴──────────────────────┐
│           Lab Network (10.X.0.0/24)      │
│         VLAN 100-170, DHCP via pfSense  │
│   ┌─────┐    ┌─────┐    ┌─────┐         │
│   │Kali │    │ MS3 │    │ Win │         │
│   └─────┘    └─────┘    └─────┘         │
└─────────────────────────────────────────┘
```

---

## Common Tasks

### Start the System
```bash
# Terminal 1: Backend
cd /home/nomad/glassdome
source venv/bin/activate
uvicorn glassdome.main:app --host 0.0.0.0 --port 8011 &

# Terminal 2: Frontend
cd /home/nomad/glassdome/frontend
npm run dev &

# Terminal 3: Workers (optional)
cd /home/nomad/glassdome
./scripts/start_workers.sh start
```

### Check Registry Status
```bash
curl http://localhost:8011/api/registry/status | jq
```

### List Proxmox Resources
```bash
curl "http://localhost:8011/api/registry/resources?platform=proxmox" | jq
```

### Deploy a Lab from Canvas
```bash
curl -X POST http://localhost:8011/api/deployments \
  -H "Content-Type: application/json" \
  -d '{"nodes": [...], "edges": [...], "platform": "proxmox"}'
```

---

## Environment Variables

Key variables in `.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://glassdome:xxx@192.168.3.26:5432/glassdome_dev

# Proxmox Cluster
PROXMOX_HOST=192.168.215.78      # pve01 (production)
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=xxxxx

PROXMOX_02_HOST=192.168.215.77   # pve02 (labs)
PROXMOX_02_USER=root@pam
PROXMOX_02_PASSWORD=xxxxx

# Templates
UBUNTU_2204_TEMPLATE_ID=9000
PFSENSE_TEMPLATE_ID=9020

# Redis
REDIS_URL=redis://localhost:6379/0

# Unifi (for IP discovery)
UBIQUITI_GATEWAY_HOST=192.168.2.1
UBIQUITI_API_KEY=xxxxx

# DNS (local resolver)
DNS_SERVERS=192.168.3.1,8.8.8.8
```

---

## Infrastructure

### Proxmox Cluster
- **pve01** (192.168.215.78): Production VMs - mooker, rome, scribe, agentx, prod-app, prod-db
- **pve02** (192.168.215.77): Lab deployments, templates
- **Shared Storage**: `truenas-nfs-labs` (29TB NFS)
- **Cluster Communication**: 10G SAN interfaces (VLANs 211/212)
- **HA & Live Migration**: Enabled

### TrueNAS (192.168.215.75)
- 29TB ZFS pool with SLOG (NVMe) and L2ARC (4TB SSD)
- NFS share: `/mnt/PROXMOX/proxmox-vms`
- Dual 10G paths for redundancy

### Nexus 3064X Switch (192.168.2.244)
- Core SAN switch for 10G traffic
- VLANs: 211 (SAN-A), 212 (SAN-B), 215 (Mgmt)
- Documented in `docs/NEXUS_3064_SAN_SWITCH.md`

---

## Agent Status

| Agent | Status | Description |
|-------|--------|-------------|
| Ubuntu Installer | ✓ Working | Cloud-init deployment across all platforms |
| Windows Installer | ⚠ Partial | Template-based on-prem, AMI on cloud |
| Overseer | ✓ Working | Claude AI chat with tool execution |
| Guest Agent Fixer | ✓ Working | QEMU guest agent repair |
| Mailcow | ✓ Working | Email integration |
| Reaper | ⚠ Partial | WEAK SSH injection, seed patterns |
| Research | ⚠ Partial | GPT-4o via Overseer, Range AI |

---

## Recent Changes (2024-11-28 - Player Portal MVP)

### Player Access Pipeline ✨ NEW
1. **Player Portal** (`/player`) - Lab code entry with particle effects
2. **Player Lobby** (`/player/:labId`) - Machine cards, mission brief, network info
3. **Player Session** (`/player/:labId/:vmName`) - RDP/SSH via Guacamole

### Updock (Guacamole) Server ✨ NEW
- **Host**: 192.168.3.8 (Docker on pve02)
- **Services**: PostgreSQL + guacd + Guacamole web
- **Access**: http://192.168.3.8:8080/guacamole
- **Credentials**: guacadmin / guacadmin

### Lab Network (brettlab) ✨ WORKING
- **pfSense Gateway**: WAN 192.168.3.242, LAN 10.101.0.1/24
- **Kali Attack Box**: 10.101.0.10 (xRDP + SSH)
- **Ubuntu Target**: 10.101.0.11 (xRDP + SSH)
- **VM Credentials**: ubuntu / Password123!

### Previous (MVP 2.0)
1. **Lab Registry** - Real-time monitoring with Redis + WebSocket
2. **Proxmox Cluster** - 2-node cluster with shared NFS storage
3. **Frontend Overhaul** - Design/Monitor dropdowns, LabMonitor page
4. **Integrated Radio** - SomaFM in Overseer chat modal
5. **Feature Pages** - Dynamic detail pages for capabilities
6. **Code Cleanup** - Deprecated code moved to `_deprecated/`
7. **DNS Update** - Local resolver (192.168.3.1) as primary

---

## TODO: Create Templates from Configured VMs

**ACTION REQUIRED:** Convert both lab VMs to templates - they're fully configured!

### VM 115 → Kali Template (9002)
### VM 116 → Ubuntu Template (9003)

Both VMs are configured with:
- ✅ xRDP + XFCE desktop environment
- ✅ SSH password authentication enabled
- ✅ DNS configured (8.8.8.8)
- ✅ Ready for DHCP on any lab network
- ✅ User: ubuntu / Password123!

```bash
# On pve02 - Create templates from the configured VMs
ssh root@192.168.215.77

# Shutdown VMs first
qm shutdown 115
qm shutdown 116

# Option A: Convert in-place to templates
qm template 115
qm template 116

# Option B: Clone to new template IDs (preserves originals)
qm clone 115 9002 --name kali-xrdp-template --full
qm clone 116 9003 --name ubuntu-xrdp-template --full
qm template 9002
qm template 9003
```

These replace the basic cloud-init templates (9000/9001) for labs needing RDP access.

---

## Troubleshooting

### Registry not connecting
```bash
# Check Redis
docker ps | grep redis
redis-cli ping

# Restart backend
pkill -f uvicorn
uvicorn glassdome.main:app --host 0.0.0.0 --port 8011 &
```

### Frontend proxy issues
```bash
# Check Vite is running
lsof -i :5174

# Restart frontend
cd /home/nomad/glassdome/frontend
npm run dev &
```

### Proxmox agents not reporting
- Check `.env` credentials (PROXMOX_USER, PROXMOX_PASSWORD)
- Verify network connectivity to Proxmox hosts
- Check backend logs for timeout errors

---

## Contact

- **Dev Environment**: `/home/nomad/glassdome` on AgentX
- **Production**: `/opt/glassdome` on glassdome-prod-app
- **Database**: PostgreSQL at 192.168.3.26
- **User**: nomad

## v0.6.3 Changes (November 29, 2025)
- Contextual help system in Overseer modal
- Help tab shows page-specific documentation
- "Ask" button to query Overseer about topics
- Page context injected into all chat messages
- Extended demo showcase (12 slides, presenter mode)
- Feature cards for Updock, WhiteKnight, WhitePawn, Overseer
- Fixed WebSocket message handling for chat
