# Glassdome Agent Context

**Last Updated:** 2025-12-02
**Version:** 0.7.7 (API v1 Migration + Vault Security Fix)

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
                             │ REST API (/api/v1/*) + WebSocket
┌────────────────────────────┴────────────────────────────────────┐
│                    FastAPI Backend (port 8000)                   │
│  - Lab management        - Platform connections                  │
│  - Reaper missions       - WhiteKnight validation                │
│  - Registry API          - WebSocket events                      │
│  - Vault secrets (AppRole auth)                                  │
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

## API Versioning (v0.7.7)

**All API endpoints use `/api/v1/` prefix:**

```
GET  /api/v1/health              # Health check
GET  /api/v1/reaper/missions     # Reaper missions
GET  /api/v1/whiteknight/status  # WhiteKnight status
GET  /api/v1/whitepawn/status    # WhitePawn monitoring
GET  /api/v1/labs                # Lab management
GET  /api/v1/networks            # Network definitions
GET  /api/v1/platforms           # Platform connections
GET  /api/v1/registry/status     # Registry health
WS   /api/v1/registry/ws/events  # Real-time events
```

**Old `/api/*` paths return `{"error":"Not found"}`**

---

## Secrets Management

**Backend:** HashiCorp Vault with AppRole authentication

```bash
# .env configuration
SECRETS_BACKEND=vault
VAULT_ADDR=https://192.168.3.7:8200
VAULT_ROLE_ID=xxxxx
VAULT_SECRET_ID=xxxxx
VAULT_MOUNT_POINT=glassdome
VAULT_SKIP_VERIFY=true  # Self-signed cert
```

**Code Usage:**
```python
from glassdome.core.security import get_secret
api_key = get_secret('openai_api_key')  # Uses cached Vault client
```

**Important:** The Vault client is cached globally - never create new instances per request.

---

## Key Directories

```
glassdome/
├── glassdome/              # Main Python package
│   ├── api/                # FastAPI routers (all use /api/v1/)
│   │   ├── v1/__init__.py  # Router aggregation
│   │   ├── reaper.py       # Reaper missions API
│   │   ├── whiteknight.py  # WhiteKnight validation API
│   │   ├── whitepawn.py    # WhitePawn monitoring API
│   │   ├── canvas_deploy.py# Lab deployment from Canvas
│   │   ├── registry.py     # Lab Registry API
│   │   └── ...
│   ├── core/               # Core utilities
│   │   ├── config.py       # Settings (Pydantic)
│   │   ├── security.py     # get_secret() - CACHED Vault
│   │   ├── secrets_backend.py # VaultSecretsBackend
│   │   └── database.py     # SQLAlchemy setup
│   ├── registry/           # Lab Registry system
│   │   ├── core.py         # LabRegistry class (Redis)
│   │   ├── models.py       # Resource, StateChange, Drift
│   │   └── agents/         # Platform polling agents
│   ├── reaper/             # Reaper subsystem
│   │   ├── exploit_library.py # Exploit/Mission models
│   │   └── hot_spare.py    # Hot spare VM pool
│   ├── platforms/          # Platform clients
│   │   ├── proxmox_client.py
│   │   ├── esxi_client.py
│   │   ├── aws_client.py
│   │   └── azure_client.py
│   └── overseer/           # Overseer service
│       ├── health_monitor.py
│       └── state_sync.py
├── frontend/               # React frontend
│   └── src/
│       ├── pages/          # Page components
│       │   ├── LabCanvas.jsx
│       │   ├── ReaperDesign.jsx
│       │   ├── WhiteKnightDesign.jsx
│       │   └── WhitePawnMonitor.jsx
│       ├── hooks/
│       │   └── useRegistry.js  # /api/v1/registry
│       └── components/
│           └── OverseerChat/
├── docs/
│   ├── SESSION_NOTES.md    # Daily progress
│   └── AGENT_CONTEXT.md    # This file
└── .env                    # Environment config
```

---

## Common Tasks

### Start the System
```bash
# Backend runs as systemd service
sudo systemctl start glassdome-backend
sudo systemctl status glassdome-backend

# Frontend
cd /home/nomad/glassdome/frontend
npm run dev &
```

### Check API Health
```bash
curl http://localhost:8000/api/v1/health | jq
```

### Test Reaper Endpoints
```bash
curl http://localhost:8000/api/v1/reaper/missions | jq
curl http://localhost:8000/api/v1/reaper/exploits | jq
curl http://localhost:8000/api/v1/reaper/stats | jq
```

### Check Vault Connection
```bash
# Test Vault directly
curl -k https://192.168.3.7:8200/v1/sys/health | jq

# Test via backend
curl http://localhost:8000/api/v1/secrets/status | jq
```

---

## Environment Variables

Key variables in `.env`:
```bash
# Secrets Backend
SECRETS_BACKEND=vault
VAULT_ADDR=https://192.168.3.7:8200
VAULT_ROLE_ID=xxxxx
VAULT_SECRET_ID=xxxxx
VAULT_MOUNT_POINT=glassdome
VAULT_SKIP_VERIFY=true

# Database
DATABASE_URL=postgresql+asyncpg://glassdome:xxx@192.168.3.7:5432/glassdome

# Proxmox Cluster
PROXMOX_01_HOST=192.168.215.78
PROXMOX_02_HOST=192.168.215.77

# Redis
REDIS_URL=redis://localhost:6379/0

# Hot Spares (disable to prevent clone storms)
HOT_SPARE_ENABLED=false
```

---

## Recent Changes (v0.7.7 - December 2, 2025)

### API v1 Migration
- All 19+ routers migrated from `/api/*` to `/api/v1/*`
- Frontend updated to use `/api/v1/` paths
- Old paths return `{"error":"Not found"}`

### Vault Security Fix
- Fixed infinite Vault auth loop (100%+ CPU → ~18%)
- Cached `_vault_backend` in `security.py`
- Suppressed SSL warnings for self-signed certs

### Security Audit
- Verified Vault is active backend
- No hardcoded secrets in code
- Local .secrets not used with vault backend

---

## Agent Status

| Agent | Status | Description |
|-------|--------|-------------|
| Ubuntu Installer | ✓ Working | Cloud-init deployment across all platforms |
| Windows Installer | ⚠ Partial | Template-based on-prem, AMI on cloud |
| Overseer | ✓ Working | Claude AI chat with tool execution |
| Guest Agent Fixer | ✓ Working | QEMU guest agent repair |
| Reaper | ✓ Working | Exploit injection with hot spares |
| WhiteKnight | ✓ Working | Vulnerability validation |
| WhitePawn | ✓ Working | Continuous monitoring |

---

## Troubleshooting

### High CPU on Backend
- Check if Vault client is being recreated per request
- `security.py` should use cached `_vault_backend`
- Verify `VAULT_SKIP_VERIFY=true` in `.env`

### API Returning 404
- Ensure using `/api/v1/` prefix
- Old `/api/*` paths are deprecated
- Check `glassdome/api/v1/__init__.py` for router mounting

### Vault Connection Failed
```bash
# Check Vault is running
curl -k https://192.168.3.7:8200/v1/sys/health

# Check AppRole credentials
grep VAULT_ .env
```

### Registry Not Connecting
```bash
# Check Redis
docker ps | grep redis
redis-cli ping
```

---

## Contact

- **Dev Environment**: `/home/nomad/glassdome` on AgentX (192.168.215.228)
- **Production**: `/opt/glassdome` on glassdome-prod-app (192.168.3.6)
- **Database**: PostgreSQL at 192.168.3.7
- **Vault**: HashiCorp Vault at 192.168.3.7:8200
- **User**: nomad (dev), ubuntu (prod)
