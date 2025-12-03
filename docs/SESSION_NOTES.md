# Glassdome Session Notes

## Session: 2025-12-02 (API v1 Migration & Vault Security Fix)

### Summary
Major refactoring session implementing proper API versioning (`/api/v1/`) across all endpoints and fixing a critical Vault authentication bug that was causing 100%+ CPU usage. All 19+ API routers migrated to `/api/v1/` prefix.

---

## Completed Work

### 1. API v1 Migration ✨ NEW
**All endpoints now use `/api/v1/` prefix for sustainable versioning**

**Routers Migrated (19 total):**
- `reaper.py` - `/api/v1/reaper/*`
- `whiteknight.py` - `/api/v1/whiteknight/*`
- `whitepawn.py` - `/api/v1/whitepawn/*`
- `labs.py` - `/api/v1/labs/*`
- `networks.py` - `/api/v1/networks/*`
- `platforms.py` - `/api/v1/platforms/*`
- `templates.py` - `/api/v1/templates/*`
- `ansible.py` - `/api/v1/ansible/*`
- `auth.py` - `/api/v1/auth/*`
- `chat.py` - `/api/v1/chat/*`
- `canvas_deploy.py` - `/api/v1/deployments/*`
- `container_dispatch.py` - `/api/v1/dispatch/*`
- `registry.py` - `/api/v1/registry/*`
- `secrets.py` - `/api/v1/secrets/*`
- `network_probes.py` - `/api/v1/probes/*`
- `agents_status.py` - `/api/v1/agents/*`
- `elements.py` - `/api/v1/elements/*`
- `ubuntu.py` - `/api/v1/ubuntu/*`
- `reconciler.py` - `/api/v1/reconciler/*`
- `logs.py` - `/api/v1/logs/*`
- `overseer.py` - `/api/v1/overseer/*`

**Architecture:**
```
Before: router = APIRouter(prefix="/api/reaper", ...)
After:  router = APIRouter(prefix="/reaper", ...)
        # Mounted at /api/v1/ by v1/__init__.py
```

**Frontend Updates:**
- `useRegistry.js` - `/api/v1/registry`
- `ChatModal.jsx` - `/api/v1/chat`
- `FeatureDetail.jsx` - Documentation updated

### 2. Vault Security Fix ✨ CRITICAL
**Fixed infinite Vault authentication loop causing 100%+ CPU**

**Root Cause:**
In `glassdome/core/security.py`, every call to `get_secret()` was creating a new `VaultSecretsBackend()` instance, which re-authenticated with Vault each time. During startup, dozens of secrets are read, causing hundreds of authentication requests.

**Fix:**
```python
# Before (BUG)
def get_secret(key: str) -> Optional[str]:
    if backend_type == "vault":
        vault = VaultSecretsBackend()  # NEW instance every call!
        return vault.get(key)

# After (FIXED)
_vault_backend: Optional[Any] = None  # Cached instance

def get_secret(key: str) -> Optional[str]:
    global _vault_backend
    if backend_type == "vault":
        if _vault_backend is None:
            _vault_backend = VaultSecretsBackend()  # Cached!
        return _vault_backend.get(key)
```

**Result:**
- CPU: 100%+ → ~18% (stable)
- Vault requests: Hundreds → Single auth
- SSL warnings suppressed for self-signed certs

### 3. Security Audit ✨ NEW
**Comprehensive compliance verification**

**Checks Performed:**
- ✅ SECRETS_BACKEND=vault (active)
- ✅ Vault client caching implemented
- ✅ No hardcoded secrets in code
- ✅ Local .secrets directory NOT used with vault backend
- ✅ Keyring NOT used with vault backend
- ✅ All API endpoints using /api/v1/ prefix
- ✅ Frontend using /api/v1/ paths
- ✅ Old /api/* paths return {"error":"Not found"}

---

## Previous Session: 2025-12-02 (Overseer Service & Instant Chat)

### Summary
Implemented Overseer as a standalone service with health monitoring, state synchronization, and instant chat initialization. Fixed stale DB records issue by adding automatic reconciliation with Proxmox.

---

## Completed Work

### 1. Overseer Service
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

### 2. Instant Chat
**Chat modal now opens instantly**

**Problem:** Chat took 5-10 seconds to initialize (lazy loading)
**Solution:** Pre-warm chat agent on backend startup

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

## Current State

### Services
| Service | Port | Status |
|---------|------|--------|
| Backend API | 8000 | ✅ Running |
| Frontend | 5174 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running (192.168.3.7) |
| Redis | 6379 | ✅ Running |
| Vault | 8200 | ✅ Running (192.168.3.7) |

### API Endpoints (v1)
| Endpoint | Status | Data |
|----------|--------|------|
| /api/v1/health | ✅ | healthy |
| /api/v1/reaper/missions | ✅ | 10 missions |
| /api/v1/reaper/exploits | ✅ | 6 exploits |
| /api/v1/whiteknight/status | ✅ | running |
| /api/v1/whitepawn/status | ✅ | running |
| /api/v1/labs | ✅ | 2 labs |
| /api/v1/networks | ✅ | 2 networks |
| /api/v1/platforms | ✅ | 4 platforms |

### Platform Connections
| Platform | Status | Details |
|----------|--------|---------|
| Proxmox | ✅ Connected | pve01 + pve02 |
| AWS | ✅ Connected | us-east-1, us-west-2 |
| ESXi | ✅ Connected | 192.168.215.76 |
| Azure | ✅ Connected | glassdome-rg |
| Vault | ✅ Connected | AppRole auth |

---

## Files Modified This Session

```
# Backend - API v1 Migration
glassdome/api/v1/__init__.py           # Router aggregation at /api/v1/
glassdome/api/reaper.py                # prefix="/reaper"
glassdome/api/whiteknight.py           # prefix="/whiteknight"
glassdome/api/whitepawn.py             # prefix="/whitepawn"
glassdome/api/labs.py                  # prefix="/labs"
glassdome/api/networks.py              # prefix="/networks"
glassdome/api/platforms.py             # prefix="/platforms"
glassdome/api/templates.py             # prefix="/templates"
glassdome/api/ansible.py               # prefix="/ansible"
glassdome/api/auth.py                  # prefix="/auth"
glassdome/api/chat.py                  # prefix="/chat"
glassdome/api/canvas_deploy.py         # prefix="/deployments"
glassdome/api/container_dispatch.py    # prefix="/dispatch"
glassdome/api/registry.py              # prefix="/registry"
glassdome/api/secrets.py               # prefix="/secrets"
glassdome/api/network_probes.py        # prefix="/probes"
glassdome/api/agents_status.py         # prefix="/agents"
glassdome/api/elements.py              # prefix="/elements"
glassdome/api/ubuntu.py                # prefix="/ubuntu"
glassdome/api/reconciler.py            # prefix="/reconciler"
glassdome/api/logs.py                  # prefix="/logs"
glassdome/api/overseer.py              # prefix="/overseer"

# Backend - Vault Fix
glassdome/core/security.py             # Cached _vault_backend
glassdome/core/secrets_backend.py      # SSL warning suppression

# Frontend
frontend/src/hooks/useRegistry.js      # /api/v1/registry
frontend/src/components/OverseerChat/ChatModal.jsx  # /api/v1/chat
frontend/src/pages/FeatureDetail.jsx   # Documentation
```

---

## Version Plan

| Version | Features |
|---------|----------|
| v0.3.0 | MVP - Protected on main |
| v0.4.0 | Hot Spare Pool + WhiteKnight + Mission History |
| v0.4.1 | Distributed Workers + Simplified Networking |
| v0.5.0 | Network orchestration + pfSense integration |
| v0.6.0 | Cross-platform migration |
| v0.6.3 | Contextual Help + Demo Showcase |
| v0.7.6 | Overseer Service + Instant Chat |
| v0.7.7 | **API v1 Migration + Vault Security Fix** ← CURRENT |
| v1.0.0 | Production with auth |

---

## Next Steps

1. [x] Migrate all API endpoints to /api/v1/
2. [x] Fix Vault authentication caching
3. [x] Update frontend API calls
4. [x] Security audit
5. [ ] Deploy to production
6. [ ] Test demo readiness
