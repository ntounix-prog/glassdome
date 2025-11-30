# Changelog

All notable changes to Glassdome will be documented in this file.

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
