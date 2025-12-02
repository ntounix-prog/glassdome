# Glassdome Session Notes

## Session: 2025-12-02 (Overseer Service & Instant Chat)

### Summary
Implemented Overseer as a standalone service with health monitoring, state synchronization, and instant chat initialization. Fixed stale DB records issue by adding automatic reconciliation with Proxmox.

---

## Completed Work

### 1. Overseer Service ✨ NEW
**Central control plane for Glassdome infrastructure**

**New Files:**
- `glassdome/overseer/health_monitor.py` - Service health monitoring
- `glassdome/overseer/state_sync.py` - DB ↔ Proxmox reconciliation
- `glassdome/overseer/service.py` - FastAPI service (port 8001)
- `docker-compose.overseer.yml` - Container deployment

**Features:**
- Health checks for frontend/backend/whitepawn/proxmox
- Automatic cleanup of orphaned DB records (every 5 min)
- State sync between `deployed_vms`/`hot_spares` tables and Proxmox
- Configurable intervals via environment variables

**Endpoints (port 8001):**
| Endpoint | Description |
|----------|-------------|
| `GET /health` | All service health status |
| `GET /health/{service}` | Single service health |
| `POST /sync` | Trigger state sync (background) |
| `POST /sync/now` | Trigger sync (blocking) |
| `GET /sync/status` | Sync history |

### 2. Instant Chat ✨ NEW
**Chat modal now opens instantly**

**Problem:** Chat took 5-10 seconds to initialize (lazy loading)
**Solution:** Pre-warm chat agent on backend startup

**Changes to `main.py`:**
- Chat agent initialized during `_start_background_services()`
- LLM providers (OpenAI, Anthropic) ready immediately
- State sync scheduler starts automatically

**Performance:**
| Before | After |
|--------|-------|
| ~5-10 seconds | **23ms** |

### 3. Windows 11 Template
**VMID 9012 converted to template**

- Installed Windows 11 Enterprise on pve01
- Converted to template for cloning
- Added to TEMPLATE_MAPPING in canvas_deploy.py

---

## Previous Session: 2025-11-27 (Distributed Worker Architecture & Simplified Networking)

### Summary
Major architecture session implementing distributed Celery workers, simplified lab networking (CIDR-driven auto-configuration), and pfSense integration planning. Pivoted from complex Docker container builds to simpler native Python workers.

---

## Completed Work

### 1. Distributed Worker Architecture ✨ NEW
**Celery + Redis task queue for parallel lab deployments**

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    Glassdome Distributed System                  │
│                                                                  │
│  ┌─────────────────┐                                            │
│  │  Redis (Docker) │ ← Task Queue (localhost:6379)             │
│  └────────┬────────┘                                            │
│           │                                                      │
│  ┌────────┴────────────────────────────────────────────────┐    │
│  │              Python Celery Workers                       │    │
│  │                                                          │    │
│  │  orchestrator@agentX .... 8 threads (deploy/config)     │    │
│  │  reaper-1@agentX ........ 4 threads (inject/exploit)    │    │
│  │  reaper-2@agentX ........ 4 threads (inject/exploit)    │    │
│  │  whiteknight-1@agentX ... 4 threads (validate/test)     │    │
│  │                                                          │    │
│  │  Total Capacity: 20+ parallel tasks                      │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features:**
- Native Python workers (no Docker build required!)
- Celery task queue with Redis backend
- Parallel VM deployments via `celery group()`
- Automatic VLAN attachment for isolated network access
- JSON structured logging for debugging

**Files Created:**
- `glassdome/workers/__init__.py` - Worker package init
- `glassdome/workers/celery_app.py` - Celery configuration
- `glassdome/workers/orchestrator.py` - Lab deployment tasks
- `glassdome/workers/reaper.py` - Vulnerability injection tasks  
- `glassdome/workers/whiteknight.py` - Validation tasks
- `glassdome/workers/whitepawn_monitor.py` - Continuous monitoring
- `glassdome/workers/logging_config.py` - Structured JSON logging
- `glassdome/api/container_dispatch.py` - Dispatch API
- `scripts/start_workers.sh` - Worker fleet management

**Startup Script:**
```bash
./scripts/start_workers.sh start   # Start all workers
./scripts/start_workers.sh status  # Check worker status
./scripts/start_workers.sh stop    # Stop all workers
```

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dispatch/health` | GET | Worker fleet health check |
| `/api/dispatch/lab` | POST | Dispatch lab deployment |
| `/api/dispatch/mission` | POST | Dispatch Reaper mission |
| `/api/dispatch/validate` | POST | Dispatch WhiteKnight validation |
| `/api/dispatch/task/{id}` | GET | Get task status |

### 2. Simplified Lab Networking ✨ NEW
**CIDR-driven auto-configuration for lab networks**

**User Experience:**
```
User: Drag 3 Ubuntu + 1 Network Hub → Click Deploy

System automatically:
1. Picks available VLAN (100-170)
2. Creates bridge vmbr{vlan}
3. Assigns 192.168.{vlan}.0/24 CIDR
4. Configures gateway at .1
5. Assigns VM IPs: .10, .11, .12...
```

**Key Changes:**
- Removed manual CIDR/VLAN configuration from Canvas UI
- Single "Lab Network" element - system handles the rest
- VLAN pool: 100-170 (70 possible isolated labs)
- VMs get only lab network (no management NIC)

**Network Derivation:**
```python
VLAN 142 → {
    "cidr": "192.168.142.0/24",
    "gateway": "192.168.142.1", 
    "bridge": "vmbr142",
    "vm_ips": ["192.168.142.10", ".11", ".12", ...]
}
```

### 3. pfSense Integration (Planned) ✨ NEW
**Firewall/DHCP at the edge of each lab**

**Architecture:**
```
┌────────────────────────────────────────────┐
│              Lab VLAN 142                  │
│                                            │
│   ┌────────┐  ┌────────┐  ┌────────┐      │
│   │Ubuntu  │  │Ubuntu  │  │ Kali   │      │
│   │  .10   │  │  .11   │  │  .12   │      │
│   └───┬────┘  └───┬────┘  └───┬────┘      │
│       └───────────┼───────────┘            │
│                   │                        │
│            ┌──────┴──────┐                 │
│            │   pfSense   │ ← Gateway       │
│            │     .1      │   DHCP          │
│            │             │   Firewall      │
│            └──────┬──────┘                 │
└───────────────────┼────────────────────────┘
                    │ BLOCKED (no escape!)
```

**Features Added:**
- pfSense added to Canvas palette (🛡️)
- pfSense gets gateway IP (.1) automatically
- Deployed first in lab sequence
- Template ID 9020 (needs creation on Proxmox)

### 4. Docker Compose Infrastructure (Prepared)
**Container definitions ready for production**

**Files Created:**
- `docker-compose.yml` - Full 16-container fleet
- `docker-compose.minimal.yml` - Redis + orchestrator only
- `containers/orchestrator/Dockerfile` - Base worker image
- `containers/orchestrator/entrypoint.sh` - Mode switching
- `containers/reaper/Dockerfile` - Reaper worker
- `containers/whiteknight/Dockerfile` - WhiteKnight worker
- `containers/whitepawn/Dockerfile` - WhitePawn monitor
- `containers/env.template` - Environment template

**Note:** Docker builds were complex; pivoted to native Python workers for dev. Docker containers ready for production deployment.

---

## Previous Session: 2025-11-26 (Hot Spare Pool & WhiteKnight)

### Summary
Implemented Hot Spare VM Pool, WhiteKnight validation engine, mission history with SQL storage, and VM destroy functionality.

### Key Features:
- Hot Spare Pool with 3 pre-provisioned VMs
- WhiteKnight container for vulnerability validation
- Mission logs stored in SQL (2-week retention)
- VM destroy from Deployments page
- Pool manager auto-starts on backend startup

---

## Current State

### Services
| Service | Port | Status |
|---------|------|--------|
| Backend API | 8011 | ✅ Running |
| Frontend | 5174 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running (192.168.3.26) |
| Redis | 6379 | ✅ Running (Docker) |
| Celery Workers | - | ✅ 5 workers online |

### Worker Fleet
| Worker | Concurrency | Queues |
|--------|-------------|--------|
| orchestrator@agentX | 8 | deploy, configure, network |
| reaper-1@agentX | 4 | inject, exploit |
| reaper-2@agentX | 4 | inject, exploit |
| whiteknight-1@agentX | 4 | validate, test |

### Platform Connections
| Platform | Status | Details |
|----------|--------|---------|
| Proxmox | ✅ Connected | pve01 + pve02 |
| AWS | ✅ Connected | us-east-1, us-west-2 |
| ESXi | ✅ Connected | 192.168.215.76 |
| Azure | ✅ Connected | glassdome-rg |

---

## Files Created This Session

```
# Distributed Workers
glassdome/workers/__init__.py
glassdome/workers/celery_app.py
glassdome/workers/orchestrator.py
glassdome/workers/reaper.py
glassdome/workers/whiteknight.py
glassdome/workers/whitepawn_monitor.py
glassdome/workers/logging_config.py

# API
glassdome/api/container_dispatch.py

# Scripts
scripts/start_workers.sh

# Docker (prepared for production)
docker-compose.yml
docker-compose.minimal.yml
containers/orchestrator/Dockerfile
containers/orchestrator/entrypoint.sh
containers/reaper/Dockerfile
containers/whiteknight/Dockerfile
containers/whitepawn/Dockerfile
containers/env.template
```

## Files Modified This Session

```
glassdome/main.py                    # Added dispatch_router
glassdome/api/canvas_deploy.py       # VLAN auto-allocation, pfSense support
frontend/src/pages/LabCanvas.jsx     # Simplified networking, pfSense palette
```

---

## Testing Commands

### Worker Fleet
```bash
# Start all workers
./scripts/start_workers.sh start

# Check status
./scripts/start_workers.sh status

# Stop all workers
./scripts/start_workers.sh stop

# Health check via API
curl http://localhost:8011/api/dispatch/health | jq
```

### Deploy Lab via Dispatch
```bash
# Queue lab deployment
curl -X POST http://localhost:8011/api/dispatch/lab \
  -H "Content-Type: application/json" \
  -d '{
    "lab_id": "test-lab-001",
    "lab_data": {"nodes": [...], "edges": [...]},
    "platform_id": "1"
  }'

# Check task status
curl http://localhost:8011/api/dispatch/task/{task_id}
```

---

## Architecture Decisions

### Why Native Workers vs Docker Containers?

| Approach | Pros | Cons |
|----------|------|------|
| **Native Workers** | No build time, easy debug, same code | Less isolation |
| **Docker Containers** | Isolated, production-ready | Build complexity, 16 containers |

**Decision:** Use native workers for development, Docker for production.

### Why CIDR-Driven Networking?

| Approach | Pros | Cons |
|----------|------|------|
| **Manual Config** | Full control | Error-prone, slow |
| **CIDR-Driven** | Zero config, fast | Less flexibility |

**Decision:** Auto-derive everything from CIDR for 90% use case. Manual config can be added later.

---

## Version Plan

| Version | Features |
|---------|----------|
| v0.3.0 | MVP - Protected on main |
| v0.4.0 | Hot Spare Pool + WhiteKnight + Mission History |
| v0.4.1 | Distributed Workers + Simplified Networking ← **CURRENT** |
| v0.5.0 | Network orchestration + pfSense integration |
| v0.6.0 | Cross-platform migration |
| v1.0.0 | Production with auth |

---

## Next Steps

1. [ ] Create pfSense template on Proxmox (VMID 9020)
2. [ ] Test full lab deployment with distributed workers
3. [ ] Implement VLAN bridge creation on Proxmox
4. [ ] Add WhitePawn continuous monitoring to worker fleet
5. [ ] Merge to main and tag v0.4.1
