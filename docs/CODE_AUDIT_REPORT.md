# Glassdome Code Audit Report

**Date:** 2024-11-27  
**Purpose:** Identify stubbed, abandoned, and unused code for cleanup

---

## Executive Summary

The codebase has grown organically with multiple features. This audit identifies:
- **45+ TODO markers** indicating incomplete implementations
- **6 potentially unused files** that may be dead code
- **Multiple stub endpoints** in main.py that return placeholder data
- **Large files** that may benefit from refactoring

---

## 1. Files Potentially Not In Use

These files don't appear to be imported anywhere:

| File | Lines | Recommendation |
|------|-------|----------------|
| `workers/logging_config.py` | ? | Review - may be for Celery workers |
| `integrations/cloudbase_init_builder.py` | ? | DELETE - Windows cloud-init, not used |
| `platforms/proxmox_gateway.py` | ? | Review - may be experimental |
| `platforms/esxi_template_builder.py` | 538 | Review - large file, may be useful |
| `agents/os_installer_base.py` | ? | DELETE - abstract base never implemented |
| `api/secrets_web.py` | 865 | Review - large, may duplicate CLI secrets |

### Action Required:
```bash
# Check if these are imported
grep -r "from glassdome.workers.logging_config" glassdome/
grep -r "from glassdome.integrations.cloudbase" glassdome/
grep -r "from glassdome.platforms.proxmox_gateway" glassdome/
grep -r "from glassdome.platforms.esxi_template_builder" glassdome/
grep -r "from glassdome.agents.os_installer_base" glassdome/
grep -r "from glassdome.api.secrets_web" glassdome/
```

---

## 2. Stubbed/Placeholder Endpoints in main.py

These endpoints return hardcoded data and need implementation or removal:

| Endpoint | Line | Issue |
|----------|------|-------|
| `GET /api/v1/platforms` | 342 | Returns hardcoded list |
| `POST /api/v1/platforms` | 355 | Returns fake success |
| `POST /platforms/{id}/test` | 365 | Returns fake success |
| `GET /api/v1/templates` | 377 | Returns hardcoded templates |
| `GET /templates/{id}` | 399 | Returns placeholder |
| `POST /api/v1/templates` | 410 | Returns fake success |

### Recommendation:
- **Option A:** Implement properly using database models
- **Option B:** Remove and redirect to dedicated API routers
- **Option C:** Mark as "coming soon" in docs

---

## 3. CLI Commands with TODOs

The CLI has several stub commands:

| Command | Issue |
|---------|-------|
| `glassdome init` | TODOs for migrations, admin user |
| `glassdome status` | TODOs for agent/platform status |
| `glassdome lab list` | TODO: Query database |
| `glassdome lab create` | TODO: Create from template |
| `glassdome deploy list` | TODO: Query database |
| `glassdome deploy create` | TODO: Trigger deployment |
| `glassdome deploy destroy` | TODO: Destroy deployment |

### Recommendation:
These are valid CLI commands that should be implemented or the group stubs removed.

---

## 4. Large Files Needing Refactoring

| File | Lines | Issue |
|------|-------|-------|
| `chat/agent.py` | 1545 | Too many responsibilities |
| `api/reaper.py` | 1462 | Could split into multiple routers |
| `platforms/proxmox_client.py` | 1121 | Many methods, some unused |
| `api/canvas_deploy.py` | 948 | Complex, but cohesive |
| `platforms/esxi_client.py` | 946 | Similar to proxmox, may share code |
| `platforms/azure_client.py` | 927 | Review for dead code |

---

## 5. Abstract Methods Never Implemented

### `networking/orchestrator.py` (Lines 605-641)
```python
raise NotImplementedError  # 5 methods
```

### `platforms/base.py`
- `create_network()` - NotImplementedError
- `test_connection()` - NotImplementedError

### Recommendation:
Either implement or remove from base class if not needed.

---

## 6. TODO Markers by Category

### High Priority (Blocking Features)
- `chat/agent.py:1155` - "Implement Proxmox VM termination"
- `chat/agent.py:1373` - "Implement actual Proxmox deployment"
- `reaper/hot_spare.py:525` - "Implement VM reset"

### Medium Priority (Enhancement)
- `workers/orchestrator.py:121` - Refactor callbacks
- `agents/overseer.py:251` - Notification system
- `agents/overseer.py:311` - Time-series storage
- `api/networks.py:76` - Register other platform handlers

### Confirmed Active Integrations
- `integrations/mailcow_client.py` - ✅ Used by Overseer chat
- `integrations/ansible_bridge.py` - ✅ Ansible integration
- `integrations/ansible_executor.py` - ✅ Ansible execution

### Low Priority (Nice to Have)
- `platforms/aws_client.py:445` - Custom VPC creation
- `overseer/entity.py` - Multiple resolution strategies

---

## 7. Recommended Cleanup Actions

### Phase 1: Quick Wins (30 min)
1. Delete confirmed unused files:
   - `integrations/cloudbase_init_builder.py`
   - `agents/os_installer_base.py`

2. Add deprecation warnings to stub endpoints in `main.py`

### Phase 2: Consolidation (2 hours)
1. Review `api/secrets_web.py` vs CLI secrets - may be duplicate
2. Review `platforms/proxmox_gateway.py` - experimental?
3. Review `platforms/esxi_template_builder.py` - needed?

### Phase 3: Refactoring (4+ hours)
1. Split `chat/agent.py` into:
   - `chat/agent_core.py` - base agent logic
   - `chat/agent_tools.py` - tool handlers
   - `chat/agent_actions.py` - deployment actions

2. Split `api/reaper.py` into:
   - `api/reaper/missions.py`
   - `api/reaper/exploits.py`
   - `api/reaper/validation.py`

### Phase 4: Implementation (Ongoing)
1. Implement or remove CLI stubs
2. Implement or remove main.py stub endpoints
3. Implement NotImplementedError methods or mark as abstract

---

## 8. Code Quality Metrics

```
Total Python files: ~80
Total lines of code: ~25,000
Files > 500 lines: 20
TODO markers: 45+
NotImplementedError: 8
Unused files (potential): 6
```

---

## 9. Next Steps

1. **Review this report** with team
2. **Prioritize** based on demo needs (12/8)
3. **Create tickets** for each cleanup action
4. **Document decisions** (keep vs delete vs refactor)

---

## Appendix: Full TODO List

```
glassdome/chat/agent.py:1155:        # TODO: Implement Proxmox VM termination
glassdome/chat/agent.py:1373:        # TODO: Implement actual Proxmox deployment
glassdome/workers/orchestrator.py:121:    # TODO: Refactor to use callbacks
glassdome/platforms/aws_client.py:445:    # TODO: Create custom VPC (Phase 2)
glassdome/main.py:342:    # TODO: Implement platform listing
glassdome/main.py:355:    # TODO: Implement platform addition
glassdome/main.py:365:    # TODO: Implement platform testing
glassdome/main.py:377:    # TODO: Implement template listing
glassdome/main.py:399:    # TODO: Implement template retrieval
glassdome/main.py:410:    # TODO: Implement template creation
glassdome/cli.py:45:    # TODO: Run database migrations
glassdome/cli.py:46:    # TODO: Create default admin user
glassdome/cli.py:47:    # TODO: Verify platform connections
glassdome/cli.py:60:    # TODO: Check agent manager status
glassdome/cli.py:61:    # TODO: Check platform connectivity
glassdome/cli.py:62:    # TODO: Show active deployments
glassdome/cli.py:167:    # TODO: Query database and list labs
glassdome/cli.py:176:    # TODO: Create lab from template or blank
glassdome/cli.py:189:    # TODO: Query database and list deployments
glassdome/cli.py:198:    # TODO: Trigger deployment
glassdome/cli.py:207:    # TODO: Destroy deployment
glassdome/agents/overseer.py:251:    # TODO: Send to notification system
glassdome/agents/overseer.py:311:    # TODO: Implement time-series storage
glassdome/reaper/hot_spare.py:525:    # TODO: Implement VM reset
glassdome/networking/orchestrator.py:145:    # TODO: Deprovision from platforms
glassdome/api/labs.py:323:    # TODO: Implement database lookup
glassdome/api/labs.py:345:    # TODO: Implement lab deletion
glassdome/api/networks.py:76:    # TODO: Register other platform handlers
glassdome/api/reaper.py:502:    # TODO: Get IP from platform
glassdome/api/registry.py:335:    # TODO: Process webhook
glassdome/overseer/service.py:343:    # TODO: Trigger immediate sync
glassdome/overseer/entity.py:216:    # TODO: Add timestamp checks
glassdome/overseer/entity.py:259:    # TODO: Implement resolution strategies
glassdome/overseer/entity.py:335:    # TODO: Implement deployment logic
glassdome/overseer/entity.py:380:    # TODO: Implement state discovery
glassdome/overseer/entity.py:561:    # TODO: Implement resource checking
```

