# Changelog

All notable changes to Glassdome will be documented in this file.

## [0.7.4] - 2025-11-30

### Test Suite Expansion & Code Quality

Comprehensive test coverage for critical monitoring and infrastructure modules.

### Deprecation Fixes
- **69 occurrences** of `datetime.utcnow()` replaced with `datetime.now(timezone.utc)`
- Fixed across 19 files in the codebase
- Warnings reduced from 72 to 20 (remaining are SQLAlchemy internals)

### New Test Coverage

#### WhitePawn Monitor (31 tests)
- MonitoringResult creation and validation
- Configuration and initial state tests
- Ping success/failure/timeout handling with async mocks
- Monitor lifecycle (start/stop)
- Alert cooldown mechanism
- Target management
- Latency analysis and threshold detection
- Database integration tests

#### WhitePawn Orchestrator (23 tests)
- Initialization and state management
- Lifecycle start/stop operations
- Multi-monitor management
- Deployment operations
- Alert aggregation and resolution
- Guardian loop functionality
- Configuration propagation

#### Reaper Engine (36 tests)
- Task model creation and serialization
- ResultEvent with success/error states
- HostState tracking (failures, locking, vulnerabilities)
- MissionState lifecycle and task tracking
- MissionEngine initialization and scheduling
- Mission completion and failure scenarios
- Mission types (web-security, network-defense, incident-response)

#### Registry Core (42 tests)
- ResourceType, ResourceState, DriftType, EventType enums
- Resource model CRUD operations
- StateChange event tracking
- Drift detection and resolution
- LabRegistry connection management
- Resource registration and retrieval
- Lab deployment workflows
- LabSnapshot creation

### Test Statistics
- **Previous**: 78 tests
- **Current**: 210 tests
- **Added**: 132 new tests (+169%)

---

## [0.7.3] - 2025-11-30

### Centralized Logging System

Implemented enterprise-grade logging with JSON output for SIEM integration.

### New Features
- **Centralized logging configuration** in `glassdome/core/logging.py`
- **JSON log output** for Filebeat/Logstash/ELK ingestion (`logs/glassdome.json`)
- **Rotating file handlers** with configurable size limits
- **Colored console output** for development
- **Log level control** via `LOG_LEVEL` environment variable

### CLI Commands
- `glassdome logs tail` - Tail log files (with `-f` follow mode)
- `glassdome logs level` - Show/change log level
- `glassdome logs clear` - Clear old log files
- `glassdome logs status` - Show logging configuration and file sizes

### Configuration
New settings in `.env`:
```bash
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_DIR=logs                # Log directory
LOG_MAX_SIZE_MB=10          # Max file size before rotation
LOG_BACKUP_COUNT=5          # Rotated files to keep
LOG_JSON_ENABLED=true       # Enable JSON output for SIEM
```

### Files Changed
- `glassdome/core/config.py` - Added 7 logging settings
- `glassdome/core/logging.py` - **New** centralized logging module
- `glassdome/server.py` - Simplified to use centralized logging
- `glassdome/api/reaper.py` - Removed ad-hoc file handler
- `glassdome/workers/whitepawn_monitor.py` - Uses centralized logging
- `glassdome/cli.py` - Added `logs` command group

### Documentation
- `docs/LOGGING.md` - Comprehensive logging guide
- `deploy/filebeat.yml` - Sample Filebeat config for ELK

---

## [0.7.2] - 2025-11-30

### Wiring & Integration Release

Wired up stub implementations to use actual database and platform operations.
Reduced TODO count from 32 to 16.

### CLI Commands (Now Functional)
- `glassdome init` - Initializes database, creates admin user, tests platform connections
- `glassdome status` - Shows agent manager, platform connectivity, deployment stats
- `glassdome lab list` - Lists all labs from database (supports --format json)
- `glassdome lab create` - Creates lab in database
- `glassdome lab show <id>` - Shows lab details
- `glassdome lab delete <id>` - Deletes lab from database
- `glassdome deploy list` - Lists deployed VMs from database
- `glassdome deploy create` - Queues lab deployment
- `glassdome deploy destroy` - Destroys VMs on platform and removes from database
- `glassdome deploy status` - Shows real deployment progress

### API Improvements
- `GET /api/templates` - Now queries database, falls back to built-in templates
- `GET /api/templates/{id}` - Full template retrieval with template_data
- `POST /api/templates` - Creates templates in database
- `DELETE /api/templates/{id}` - Deletes templates
- `GET /api/labs/{id}/status` - Real deployment status from database

### Chat Agent Operations
- `_terminate_proxmox_vm` - Now calls proxmox_client.stop_vm() and delete_vm()
- `_deploy_to_proxmox` - Now clones from templates via proxmox_client

### Technical
- All 78 tests passing
- 16 TODOs remaining (down from 32)
- No breaking changes

---

## [0.7.1] - 2025-11-30

### Code Cleanup Release

Minor cleanup release removing deprecated code and improving codebase hygiene.

### Removed
- **`_deprecated/` folder** - Deleted 9 unused files:
  - `cloudbase_init_builder.py` - Unused Windows cloud-init builder
  - `os_installer_base.py` - Abstract base never implemented
  - `proxmox_gateway.py` - Experimental gateway code
  - `secrets_web.py` - Duplicate of CLI secrets functionality
  - `logging_config.py` - Unused worker logging config
  - `frontend/LabTemplates.jsx` - Old component
  - `frontend/LabTemplates.css` - Old styles
  - `frontend/QuickDeploy.jsx` - Old component
  - `frontend/QuickDeploy.css` - Old styles

### Technical Notes
- 32 TODO markers remain for future feature work
- All tests still passing (78/81)
- No breaking changes

---

## [0.7.0] - 2025-11-30

### 🚀 Major Release: API v1 Refactor

This release introduces comprehensive API versioning, a full test suite, and improved 
platform connectivity through enhanced Vault secret mappings.

### Added
- **API Versioning**: All endpoints now use `/api/v1/` prefix
- **Test Suite**: 78 integration tests covering API smoke tests, auth flows, and deployment logic
- **Test Infrastructure**: pytest fixtures with mocked DB, Redis, and Proxmox client
- **API Config**: `frontend/src/config/api.js` centralizing API_BASE and WS_BASE constants
- **Vault Secret Mappings**: Added missing mappings for:
  - `esxi_host` - ESXi host configuration
  - `proxmox_host` → `proxmox_01_host` - Proxmox host configuration
  - `azure_subscription_id`, `azure_tenant_id`, `azure_client_id` - Azure credentials

### Changed
- **Backend**: Extracted inline endpoints from `main.py` into modular routers:
  - `api/templates.py` - Template CRUD
  - `api/agents_status.py` - Agent status endpoints
  - `api/elements.py` - Element library and stats
  - `api/v1/__init__.py` - V1 router aggregation with legacy redirect
- **Frontend**: Updated all 50+ fetch calls across 18 files to use `/api/v1/` prefix
- **main.py**: Slimmed from ~800 lines to ~238 lines (app init, middleware, startup/shutdown)
- **docker-compose.yml**: Updated healthcheck to `/api/v1/health`
- **deploy/deploy-prod.sh**: Updated verification curl to `/api/v1/health`
- **config.py**: Fixed secret mappings for multi-platform connectivity

### Documentation
- **docs/API.md**: Complete rewrite with v1 paths, JWT auth, RBAC, all endpoints
- **docs/REQUEST_FLOW.md**: Updated all API path examples

### Platform Connectivity (Verified Working)
- ✅ Proxmox: 2 nodes, 25 VMs
- ✅ ESXi: 11 VMs
- ✅ AWS: 1 instance
- ✅ Azure: Connected
- ✅ Overseer AI: OpenAI + Anthropic providers

### Backward Compatibility
- Legacy `/api/*` requests redirect (307) to `/api/v1/*` for backward compatibility
- Existing integrations continue to work during transition

### Technical Details
- Tests: 78 passed, 3 skipped (WhitePawn requires real DB)
- No breaking changes to API response formats

---

## [0.6.4] - 2025-11-25

### Added
- Email infrastructure & MX server monitoring
