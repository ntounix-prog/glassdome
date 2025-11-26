# Glassdome Session Notes

## Session: 2025-11-26 (Hot Spare Pool & WhiteKnight)

### Summary
Major feature session implementing Hot Spare VM Pool, WhiteKnight validation engine, mission history with SQL storage, and VM destroy functionality.

---

## Completed Work

### 1. Hot Spare Pool System ✨ NEW
**Pre-provisioned VM pool for instant Reaper missions**

**Architecture:**
```
Pool Manager (Guardian Process)
       │
       ├── Maintains min 3 ready spares
       ├── Auto-provisions replacements
       ├── Health checks every 30 seconds
       └── Auto-starts on backend startup
```

**Features:**
- Atomic spare acquisition (`SELECT FOR UPDATE SKIP LOCKED`)
- Immediate replacement dispatch when spare acquired
- Configurable pool size (min: 3, max: 6)
- IP range: 192.168.3.100 - 192.168.3.120
- Ubuntu cloud-init templates with qemu-guest-agent
- VM renaming to `reaper-{hash}` on acquisition

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reaper/pool/status` | GET | Pool statistics and spare list |
| `/api/reaper/pool/start` | POST | Start pool manager |
| `/api/reaper/pool/stop` | POST | Stop pool manager |
| `/api/reaper/pool/provision` | POST | Manually provision spare |

**Database Table:** `hot_spares`

**Files Created:**
- `glassdome/reaper/hot_spare.py` - HotSpare model + HotSparePoolManager

### 2. WhiteKnight Validation Engine ✨ NEW
**Automated post-injection vulnerability verification**

**Architecture:**
```
WhiteKnight Container (Docker)
       │
       ├── SSH credential tests
       ├── Network scans
       ├── Web vulnerability checks
       └── Privilege escalation detection
```

**Security Control:**
- **ONLY targets deployed Reaper missions**
- Validates mission_id + IP match before testing
- Prevents misuse as attack tool

**Test Categories:**
| Category | Tests |
|----------|-------|
| Connectivity | ping, port scan |
| Credentials | SSH, MySQL, PostgreSQL, Redis, SMB |
| Network | SMB anonymous, SNMP public, Redis open |
| Web | HTTP methods, directory listing, security headers |
| Privilege Escalation | sudo NOPASSWD, SUID binaries, docker group |

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/whiteknight/status` | GET | Container status |
| `/api/whiteknight/tests` | GET | Available tests by category |
| `/api/whiteknight/validate` | POST | Run validation tests |
| `/api/whiteknight/logs` | GET | Container logs |

**UI Features:**
- Test Runner with mission selector dropdown
- Only shows deployed Reaper missions
- Real-time test results with evidence
- Validation history tab (stored in SQL)

**Files Created:**
- `glassdome/api/whiteknight.py` - WhiteKnight API router
- `glassdome/whiteknight/client.py` - Docker integration
- `frontend/src/pages/WhiteKnightDesign.jsx` - Full React UI
- `frontend/src/styles/WhiteKnightDesign.css` - Dark theme styling
- `whiteknight/Dockerfile` - Ubuntu-based container with tools
- `whiteknight/agent/main.py` - Container entry point

### 3. Mission History & Logs (SQL Storage) ✨ NEW
**Persistent mission tracking with 2-week retention**

**New Database Tables:**

**`mission_logs`:**
- mission_id (FK)
- level (DEBUG, INFO, WARNING, ERROR)
- message, details (JSON)
- step, exploit_id
- timestamp

**`validation_results`:**
- mission_id (FK)
- test_name, test_type
- status (success, failed, error)
- message, evidence
- target_ip, duration_ms
- validated_at

**API Endpoints:**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reaper/missions/{id}/logs` | GET | Mission log entries |
| `/api/reaper/missions/{id}/validations` | GET | WhiteKnight results |
| `/api/reaper/history` | GET | Mission history with summaries |
| `/api/reaper/history/cleanup` | DELETE | Purge old missions (14 days) |

### 4. VM Destroy Functionality ✨ NEW
**Destroy mission VMs from Deployments page**

**Features:**
- Confirmation dialog before destroy
- Stops VM, waits 5 seconds, then deletes
- Updates mission status to "destroyed"
- Works with Proxmox API

**API Endpoint:**
```
DELETE /api/reaper/missions/{mission_id}/destroy
```

### 5. Exploit Script Fixes
**Ubuntu 22.04 cloud-init compatibility**

**Issue:** Cloud images have `/etc/ssh/sshd_config.d/60-cloudimg-settings.conf` that sets `PasswordAuthentication no`

**Fix:** Updated weak-ssh-password exploit to:
- Overwrite `60-cloudimg-settings.conf` instead of adding new file
- Create vulnuser with password authentication
- Properly restart SSH service

### 6. Auto-Start Pool Manager
**Guardian process starts on backend startup**

Added to `glassdome/main.py`:
- `startup_event()` - Starts HotSparePoolManager
- `shutdown_event()` - Stops HotSparePoolManager gracefully

---

## Previous Session: 2025-11-26 (Portability Refactor)

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

---

## Current State

### Services
| Service | Port | Status |
|---------|------|--------|
| Backend API | 8011 | ✅ Running |
| Frontend | 5174 | ✅ Running |
| PostgreSQL | 5432 | ✅ Running (192.168.3.26) |
| WhiteKnight | Docker | ✅ Available |

### Platform Connections
| Platform | Status | Details |
|----------|--------|---------|
| Proxmox | ✅ Connected | pve01 + pve02 |
| AWS | ✅ Connected | us-east-1, us-west-2 |
| ESXi | ✅ Connected | 192.168.215.76 |
| Azure | ✅ Connected | glassdome-rg |

### Hot Spare Pool
| Status | Count |
|--------|-------|
| Ready | 3 |
| In Use | 0 |
| Provisioning | 0 |

---

## Files Created This Session

```
# Hot Spare Pool
glassdome/reaper/hot_spare.py

# WhiteKnight System
glassdome/api/whiteknight.py
glassdome/whiteknight/__init__.py
glassdome/whiteknight/client.py
frontend/src/pages/WhiteKnightDesign.jsx
frontend/src/styles/WhiteKnightDesign.css
whiteknight/Dockerfile
whiteknight/docker-compose.yml
whiteknight/requirements.txt
whiteknight/agent/__init__.py
whiteknight/agent/main.py
whiteknight/TOOLS.md
```

## Files Modified This Session

```
glassdome/main.py                    # Auto-start pool manager
glassdome/core/database.py           # MissionLog, ValidationResult tables
glassdome/reaper/exploit_library.py  # MissionLog, ValidationResult models
glassdome/api/reaper.py              # Destroy endpoint, history endpoints
glassdome/platforms/proxmox_client.py # VM rename support
frontend/src/App.jsx                 # WhiteKnight route
frontend/src/pages/Dashboard.jsx     # WhiteKnight link
frontend/src/pages/Deployments.jsx   # Destroy button
frontend/src/pages/ReaperDesign.jsx  # Template ID support
frontend/src/styles/Dashboard.css    # WhiteKnight styling
frontend/src/styles/Deployments.css  # Compact cards
requirements.txt                     # asyncssh dependency
```

---

## Testing Commands

### Hot Spare Pool
```bash
# Pool status
curl http://localhost:8011/api/reaper/pool/status

# Start pool manager
curl -X POST http://localhost:8011/api/reaper/pool/start

# Manually provision spare
curl -X POST http://localhost:8011/api/reaper/pool/provision
```

### WhiteKnight
```bash
# Container status
curl http://localhost:8011/api/whiteknight/status

# Available tests
curl http://localhost:8011/api/whiteknight/tests

# Run validation (requires valid mission)
curl -X POST http://localhost:8011/api/whiteknight/validate \
  -H "Content-Type: application/json" \
  -d '{"mission_id": "mission-xxx", "target_ip": "192.168.3.100", "tests": ["ssh_creds"]}'
```

### Mission Management
```bash
# Mission history
curl http://localhost:8011/api/reaper/history

# Mission logs
curl http://localhost:8011/api/reaper/missions/{id}/logs

# Destroy mission VM
curl -X DELETE http://localhost:8011/api/reaper/missions/{id}/destroy
```

---

## Version Plan

| Version | Features |
|---------|----------|
| v0.3.0 | MVP - Protected on main |
| v0.4.0 | Hot Spare Pool + WhiteKnight + Mission History ← **CURRENT** |
| v0.5.0 | Network tracking |
| v0.6.0 | Cross-platform migration |
| v1.0.0 | Production with auth |

---

## Merge Checklist

- [x] Hot Spare Pool working
- [x] WhiteKnight validation working
- [x] Mission history stored in SQL
- [x] VM destroy functionality
- [x] Pool manager auto-starts
- [x] Exploit scripts fixed for Ubuntu 22.04
- [x] All tests passing
- [ ] Merge develop → main
- [ ] Tag v0.4.0
- [ ] Deploy to production
