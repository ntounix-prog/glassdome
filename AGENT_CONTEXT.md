# Glassdome Agent Context

**Last Updated:** 2025-11-27
**Version:** 0.4.1

This file provides context for AI assistants working on Glassdome. Read this first to understand the current state of the project.

---

## What is Glassdome?

Glassdome is a **cyber range automation platform** for creating, deploying, and managing cybersecurity training labs. It deploys VMs across multiple platforms (Proxmox, ESXi, AWS, Azure), injects vulnerabilities for training, and monitors lab health.

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│  React Frontend (port 5174) - Lab Canvas, Deployments, Reaper   │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────┴────────────────────────────────────┐
│                    FastAPI Backend (port 8011)                   │
│  - Lab management        - Platform connections                  │
│  - Reaper missions       - WhiteKnight validation                │
│  - Dispatch API          - Network management                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Distributed Task Queue                        │
│                                                                  │
│  Redis (Docker, port 6379) ──────────────────────────────────┐  │
│                                                               │  │
│  Celery Workers (Native Python):                              │  │
│    orchestrator@agentX ... 8 threads (deploy, configure)     │  │
│    reaper-1@agentX ....... 4 threads (inject, exploit)       │  │
│    reaper-2@agentX ....... 4 threads (inject, exploit)       │  │
│    whiteknight-1@agentX .. 4 threads (validate, test)        │  │
│                                                               │  │
│  Capacity: 20+ parallel tasks                                 │  │
└───────────────────────────────────────────────────────────────┘  │
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                    Platform Abstraction                          │
│  ProxmoxClient | ESXiClient | AWSClient | AzureClient           │
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
│   │   ├── container_dispatch.py # Celery task dispatch
│   │   └── ...
│   ├── workers/            # Celery workers ✨ NEW
│   │   ├── celery_app.py   # Celery configuration
│   │   ├── orchestrator.py # Lab deployment tasks
│   │   ├── reaper.py       # Vulnerability injection
│   │   └── whiteknight.py  # Validation tasks
│   ├── reaper/             # Reaper subsystem
│   │   ├── exploit_library.py # Exploit/Mission models
│   │   └── hot_spare.py    # Hot spare VM pool
│   ├── networking/         # Network management
│   │   ├── models.py       # NetworkDefinition, VMInterface
│   │   └── orchestrator.py # Network orchestration
│   ├── platforms/          # Platform clients
│   │   ├── proxmox_client.py
│   │   ├── esxi_client.py
│   │   ├── aws_client.py
│   │   └── azure_client.py
│   └── core/               # Core utilities
│       ├── config.py       # Settings (Pydantic)
│       ├── database.py     # SQLAlchemy setup
│       └── paths.py        # Centralized path management
├── frontend/               # React frontend
│   └── src/
│       ├── pages/          # Page components
│       │   ├── LabCanvas.jsx    # Visual lab builder
│       │   ├── Deployments.jsx  # Deployment management
│       │   └── ReaperDesign.jsx # Reaper interface
│       └── styles/         # CSS files
├── scripts/
│   └── start_workers.sh    # Worker fleet management ✨ NEW
├── containers/             # Docker definitions ✨ NEW
│   ├── orchestrator/
│   ├── reaper/
│   └── whiteknight/
├── docs/                   # Documentation
│   ├── SESSION_NOTES.md    # Daily progress
│   └── ARCHITECTURE.md     # System design
└── docker-compose.yml      # Container orchestration
```

---

## Key Concepts

### 1. Hot Spare Pool
Pre-provisioned VMs ready for instant deployment. Pool manager maintains 3 ready spares.

```python
# Acquire a spare
pool = get_hot_spare_pool()
spare = await pool.acquire_spare(session, os_type="ubuntu", mission_id="xxx")
# Returns: HotSpare with vmid, ip_address, node
```

### 2. Distributed Workers
Celery workers process tasks from Redis queues in parallel.

```python
# Dispatch lab deployment
from glassdome.workers.orchestrator import deploy_lab
task = deploy_lab.delay(lab_id="xxx", lab_data={...}, platform_id="1")
# Returns: AsyncResult with task_id
```

### 3. VLAN Auto-Assignment
Labs get automatically assigned VLANs from pool 100-170.

```python
VLAN 142 → {
    "cidr": "192.168.142.0/24",
    "gateway": "192.168.142.1",
    "bridge": "vmbr142",
    "vm_ips": [".10", ".11", ".12", ...]
}
```

### 4. Platform Abstraction
All platforms implement the same interface:

```python
# Same code works for all platforms
client = ProxmoxClient(...)  # or ESXiClient, AWSClient, AzureClient
await client.create_vm(config)
await client.start_vm(node, vmid)
await client.configure_vm(node, vmid, settings)
```

---

## Common Tasks

### Start the System
```bash
# Terminal 1: Backend
cd /home/nomad/glassdome
source venv/bin/activate
uvicorn glassdome.main:app --host 0.0.0.0 --port 8011 --reload

# Terminal 2: Frontend
cd /home/nomad/glassdome/frontend
npm run dev

# Terminal 3: Workers
cd /home/nomad/glassdome
./scripts/start_workers.sh start
```

### Check Worker Health
```bash
curl http://localhost:8011/api/dispatch/health | jq
```

### Deploy a Lab
```bash
curl -X POST http://localhost:8011/api/dispatch/lab \
  -H "Content-Type: application/json" \
  -d '{"lab_id": "test", "lab_data": {...}, "platform_id": "1"}'
```

### Check Hot Spare Pool
```bash
curl http://localhost:8011/api/reaper/pool/status | jq
```

---

## Database Models

### Key Tables
- `labs` - Lab definitions with canvas data
- `exploits` - Vulnerability definitions
- `exploit_missions` - Reaper mission tracking
- `mission_logs` - Mission execution logs
- `validation_results` - WhiteKnight test results
- `hot_spares` - Pre-provisioned VM pool
- `network_definitions` - Lab network configurations
- `deployed_vms` - Deployed VM tracking

### Migrations
```bash
cd /home/nomad/glassdome
alembic upgrade head
```

---

## Environment Variables

Key variables in `.env`:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://glassdome:xxx@192.168.3.26:5432/glassdome_dev

# Proxmox
PROXMOX_HOST=192.168.215.78
PROXMOX_USER=apex@pve
PROXMOX_TOKEN_NAME=glassdome-token

# Templates
UBUNTU_2204_TEMPLATE_ID=9000

# Redis (for workers)
REDIS_URL=redis://localhost:6379/0
```

---

## Current Limitations

1. **Windows VMs** - Template-based only (autounattend unreliable)
2. **pfSense** - Template 9020 needs to be created on Proxmox
3. **VLAN Bridges** - Need to be created manually on Proxmox
4. **Docker Workers** - Builds prepared but using native workers for dev

---

## Troubleshooting

### Workers not responding
```bash
./scripts/start_workers.sh stop
./scripts/start_workers.sh start
./scripts/start_workers.sh status
```

### Redis not running
```bash
docker start glassdome-redis
# or
docker run -d --name glassdome-redis -p 6379:6379 redis:7-alpine
```

### Hot spares not provisioning
```bash
curl -X POST http://localhost:8011/api/reaper/pool/start
curl http://localhost:8011/api/reaper/pool/status | jq
```

### Backend not starting
```bash
cd /home/nomad/glassdome
source venv/bin/activate
python -c "from glassdome.main import app; print('OK')"
# Check for import errors
```

---

## Recent Changes (2025-11-27)

1. **Distributed Workers** - Celery + Redis task queue
2. **Simplified Networking** - CIDR-driven auto-configuration
3. **pfSense Support** - Added to Canvas palette
4. **Worker Startup Script** - `./scripts/start_workers.sh`
5. **Dispatch API** - `/api/dispatch/*` endpoints

---

## Contact

This is the **nomad** user's project on the **AgentX** development machine.

- Dev Environment: `/home/nomad/glassdome`
- Production: `/opt/glassdome` (glassdome-prod-app server)
- Database: `192.168.3.26` (PostgreSQL)

