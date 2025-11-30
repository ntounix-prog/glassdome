# Glassdome Agent Context

**Version:** 0.7.0  
**Last Updated:** November 30, 2025

---

## Project Overview

Glassdome is an **Agentic Cyber Range Deployment Framework** for automated deployment and management of cybersecurity training environments across multiple virtualization platforms.

### Core Capabilities
- Multi-platform VM deployment (Proxmox, ESXi, AWS, Azure)
- Canvas-based visual lab design
- Automated network configuration
- Reaper exploit framework integration
- WhiteKnight defensive monitoring
- WhitePawn network connectivity monitoring
- Overseer AI assistant (Claude/GPT-powered)

---

## Architecture

### Technology Stack
| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL (async via asyncpg) |
| Cache/Queue | Redis |
| Task Queue | Celery |
| Frontend | React |
| Secrets | HashiCorp Vault |
| Auth | JWT tokens with RBAC |

### API Structure (v0.7.0+)
All API endpoints use the `/api/v1/` prefix:
```
/api/v1/health          - Health check
/api/v1/auth/*          - Authentication
/api/v1/labs/*          - Lab management
/api/v1/platforms/*     - Platform status
/api/v1/registry/*      - Resource registry
/api/v1/reaper/*        - Exploit framework
/api/v1/whiteknight/*   - Defensive monitoring
/api/v1/whitepawn/*     - Network monitoring
/api/v1/chat/*          - Overseer AI chat
```

Legacy `/api/*` requests redirect (307) to `/api/v1/*` for backward compatibility.

---

## Key Directories

```
glassdome/
├── api/              # API route handlers
│   ├── v1/           # V1 router aggregator
│   ├── auth.py       # Authentication
│   ├── labs.py       # Lab CRUD
│   ├── platforms.py  # Platform status
│   ├── reaper.py     # Exploit framework
│   └── chat.py       # Overseer AI
├── core/
│   ├── config.py     # Settings & Vault mappings
│   ├── database.py   # Async DB connection
│   └── session.py    # Session management
├── chat/
│   ├── agent.py      # OverseerChatAgent
│   └── llm_service.py # LLM provider abstraction
├── platforms/        # Platform clients
│   ├── proxmox_client.py
│   ├── esxi_client.py
│   ├── aws_client.py
│   └── azure_client.py
├── reaper/           # Exploit framework
├── whiteknight/      # Defensive monitoring
└── whitepawn/        # Network monitoring
```

---

## Configuration

### Environment Variables (.env)
```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/glassdome
SECRET_KEY=your-secret-key

# Vault Integration
SECRETS_BACKEND=vault
VAULT_ADDR=https://192.168.3.7:8200
VAULT_ROLE_ID=...
VAULT_SECRET_ID=...
VAULT_SKIP_VERIFY=true

# API Keys (if not in Vault)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...

# Azure (if not in Vault)
AZURE_SUBSCRIPTION_ID=...
AZURE_TENANT_ID=...
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
```

### Server Startup
```bash
cd /home/nomad/glassdome
export $(grep -v '^#' .env | xargs)  # CRITICAL: Export env vars
source venv/bin/activate
python -m uvicorn glassdome.main:app --host 0.0.0.0 --port 8011
```

### Vault Secret Mappings
Platform credentials are mapped in `glassdome/core/config.py`:
```python
secret_mappings = {
    'proxmox_host': 'proxmox_01_host',
    'proxmox_password': 'proxmox_01_password',
    'esxi_host': 'esxi_host',
    'esxi_password': 'esxi_password',
    'aws_access_key_id': 'aws_access_key_id',
    'azure_subscription_id': 'azure_subscription_id',
    'anthropic_api_key': 'anthropic_api_key',
    # ... etc
}
```

---

## Testing

### Run Tests
```bash
cd /home/nomad/glassdome
source venv/bin/activate
python -m pytest tests/ -v
```

### Test Coverage
- **78 tests passing** (3 skipped)
- API smoke tests
- Authentication flows
- Deployment validation
- RBAC permissions

### Test Environment
Tests use isolated fixtures:
- In-memory SQLite (not real PostgreSQL)
- Mock Redis
- Mock platform clients
- No Vault dependency

---

## Platform Status Endpoints

Check platform connectivity:
```bash
# All platforms
curl http://localhost:8011/api/v1/platforms

# Individual status
curl http://localhost:8011/api/v1/platforms/proxmox
curl http://localhost:8011/api/v1/platforms/esxi
curl http://localhost:8011/api/v1/platforms/aws
curl http://localhost:8011/api/v1/platforms/azure

# Overseer AI
curl http://localhost:8011/api/chat/providers
```

---

## Common Issues & Solutions

### Platforms Show "Not Configured"
**Cause:** Missing Vault secret mappings or env vars not exported
**Solution:** 
1. Check `config.py` has mapping for the secret key
2. Ensure server started with `export $(grep -v '^#' .env | xargs)`
3. Verify secret exists in Vault

### LLM Providers Empty
**Cause:** API keys not in environment
**Solution:** Add `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` to `.env`

### Database Connection Failed
**Cause:** `DATABASE_URL` not set or incorrect
**Solution:** Verify `.env` has correct PostgreSQL connection string

---

## Recent Changes (v0.7.0)

1. **API Versioning** - All endpoints now `/api/v1/*`
2. **Backend Refactor** - `main.py` slimmed from 800→238 lines
3. **Test Suite** - 78 integration tests
4. **Platform Fixes** - All platforms now connecting
5. **Overseer AI** - OpenAI + Anthropic providers working

---

## Related Documentation

- [CHANGELOG.md](/CHANGELOG.md)
- [docs/API.md](/docs/API.md)
- [docs/AGENTS.md](/docs/AGENTS.md)
- [docs/session_logs/](/docs/session_logs/)

---

*For AI agents: This context provides essential project information. Always use `/api/v1/` prefix for API calls. Check platform status before deployment operations.*
