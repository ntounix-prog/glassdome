# Code Migration Reference Guide

## Purpose
This document serves as a reference when encountering code that needs to be updated to use the new session-based authentication and secrets management system.

## Important: Session Persistence

**⚠️ Sessions are per-process and do NOT persist across different Python processes.**

- When you run `./glassdome_start`, it initializes the session in that process
- When that process exits, the session is gone
- Each new Python process (script, API server, etc.) needs its own session initialization
- This is by design for security - sessions are in-memory only

**What this means:**
- If you run a script after `./glassdome_start`, the script needs to initialize its own session
- The API server needs to initialize its own session when it starts
- Each agent execution in a separate process needs its own session

**Solution:** Each script/process should check if session is initialized and initialize if needed:
```python
from glassdome.core.session import get_session

session = get_session()
if not session.is_initialized():
    session.initialize(interactive=True)  # Will prompt for password
```

## Quick Reference: What Needs Updating

### ❌ OLD PATTERNS (Need to Update)

#### 1. Direct Environment Variable Access
```python
# ❌ BAD - Direct os.getenv()
password = os.getenv('PROXMOX_PASSWORD')
api_key = os.getenv('OPENAI_API_KEY')
```

#### 2. Direct .env File Reading
```python
# ❌ BAD - Reading .env directly
from dotenv import load_dotenv
load_dotenv()
password = os.getenv('PROXMOX_PASSWORD')
```

#### 3. Settings Without Session Check
```python
# ❌ BAD - Using Settings() without session (will prompt for password)
from glassdome.core.config import Settings
settings = Settings()
password = settings.proxmox_password
```

### ✅ NEW PATTERNS (Correct Usage)

#### 1. Using Session (Recommended for Agents/Scripts)
```python
# ✅ GOOD - Use session (requires initialization first)
from glassdome.core.session import get_session, require_session

# Option A: Check if session exists, initialize if needed
session = get_session()
if not session.is_initialized():
    session.initialize(interactive=True)

settings = session.get_settings()
password = session.get_secret('proxmox_password')
api_key = session.get_secret('openai_api_key')

# Option B: Require session (raises error if not initialized)
session = require_session()  # Raises RuntimeError if not authenticated
settings = session.get_settings()
password = session.get_secret('proxmox_password')
```

#### 2. Using Settings Directly (For Backward Compatibility)
```python
# ✅ ACCEPTABLE - Settings() will work but may prompt for password
# Use this only if you're sure session is initialized OR
# you want to allow password prompt as fallback
from glassdome.core.config import Settings

settings = Settings()  # Will use secrets manager if available
password = settings.proxmox_password
api_key = settings.openai_api_key
```

#### 3. Direct Secrets Manager Access (Advanced)
```python
# ✅ GOOD - Direct access to secrets manager (for admin tools)
from glassdome.core.secrets import get_secrets_manager

secrets = get_secrets_manager()
# Note: This requires master key to be loaded (via session or explicit call)
password = secrets.get_secret('proxmox_password')
```

## Migration Patterns by Code Type

### Pattern 1: Agent Classes
**Location**: `glassdome/agents/*.py`

**Before:**
```python
from glassdome.core.config import settings

class MyAgent(BaseAgent):
    def run(self, task):
        password = settings.proxmox_password  # May prompt
        # ... use password
```

**After:**
```python
from glassdome.core.session import require_session

class MyAgent(BaseAgent):
    def run(self, task):
        # BaseAgent already checks session in _check_session()
        # But if you need secrets directly:
        session = require_session()
        password = session.get_secret('proxmox_password')
        # ... use password
```

**Note**: `BaseAgent` already implements `_check_session()`, so agents automatically require authentication.

### Pattern 2: Scripts
**Location**: `scripts/*.py`

**Before:**
```python
import os
password = os.getenv('PROXMOX_PASSWORD')
```

**After:**
```python
from glassdome.core.session import get_session

# At start of script
session = get_session()
if not session.is_initialized():
    print("Please run: ./glassdome_start")
    sys.exit(1)

settings = session.get_settings()
password = settings.proxmox_password
# or
password = session.get_secret('proxmox_password')
```

### Pattern 3: API Endpoints
**Location**: `glassdome/api/*.py`

**Before:**
```python
from glassdome.core.config import settings

@router.post("/endpoint")
async def my_endpoint():
    password = settings.proxmox_password
```

**After:**
```python
from glassdome.core.session import require_session

@router.post("/endpoint")
async def my_endpoint():
    session = require_session()  # Ensures session is initialized
    password = session.get_secret('proxmox_password')
    # or use settings
    settings = session.get_settings()
    password = settings.proxmox_password
```

### Pattern 4: Platform Clients
**Location**: `glassdome/platforms/*.py`

**Before:**
```python
import os
password = os.getenv('PROXMOX_PASSWORD')
```

**After:**
```python
from glassdome.core.config import Settings

# Platform clients typically receive config from Settings
# They should use Settings() which will use secrets manager
settings = Settings()
password = settings.proxmox_password
```

**Note**: Platform clients are usually instantiated with config from Settings, so they automatically benefit from secrets manager.

## Common Issues and Solutions

### Issue 1: "Session not authenticated" Error
**Error**: `RuntimeError: Session not authenticated or expired. Call initialize() first.`

**Solution**:
```python
# Option A: Initialize session first
from glassdome.core.session import get_session
session = get_session()
session.initialize(interactive=True)

# Option B: Check if initialized
if not session.is_initialized():
    session.initialize(interactive=True)
```

### Issue 2: Password Prompted Multiple Times
**Problem**: Password is being prompted multiple times.

**Solution**: 
- Ensure session is initialized ONCE at application startup
- Use `session.get_secret()` instead of creating new Settings() instances
- Master key is cached after first load

### Issue 3: Secrets Not Found
**Problem**: `get_secret()` returns `None`.

**Possible Causes**:
1. Secret not migrated to secrets manager
2. Session not initialized (master key not loaded)
3. Secret key name mismatch

**Solution**:
```python
# Check if secret exists
from glassdome.core.secrets import get_secrets_manager
secrets = get_secrets_manager()
all_secrets = secrets.list_secrets()
print(f"Available secrets: {all_secrets}")

# Verify secret key name matches
# Common mappings:
# - PROXMOX_PASSWORD → proxmox_password
# - OPENAI_API_KEY → openai_api_key
```

## Testing Checklist

When updating code, verify:

- [ ] Code uses session or Settings (not direct os.getenv)
- [ ] Session is initialized before accessing secrets
- [ ] No direct .env file reading
- [ ] Agents use `require_session()` or inherit from BaseAgent
- [ ] Scripts check for session initialization
- [ ] API endpoints use `require_session()` dependency
- [ ] Platform clients use Settings() for config

## Files Already Updated

These files have been migrated and serve as reference examples:

- ✅ `glassdome/core/config.py` - Settings class with secrets integration
- ✅ `glassdome/core/session.py` - Session management
- ✅ `glassdome/agents/base.py` - BaseAgent with session check
- ✅ `glassdome/platforms/proxmox_client.py` - Uses Settings
- ✅ `scripts/add_secondary_network_interface.py` - Uses Settings
- ✅ `scripts/auto_boot_windows_vms.py` - Uses Settings
- ✅ `scripts/setup_windows10_complete.py` - Uses Settings
- ✅ `scripts/setup_windows11_complete.py` - Uses Settings

## Secret Key Mappings

When migrating, use these standard key names:

| Environment Variable | Secret Key Name |
|---------------------|----------------|
| `PROXMOX_PASSWORD` | `proxmox_password` |
| `PROXMOX_TOKEN_VALUE` | `proxmox_token_value` |
| `PROXMOX_TOKEN_VALUE_02` | `proxmox_token_value_02` |
| `PROXMOX_ROOT_PASSWORD` | `proxmox_root_password` |
| `OPENAI_API_KEY` | `openai_api_key` |
| `ANTHROPIC_API_KEY` | `anthropic_api_key` |
| `XAI_API_KEY` | `xai_api_key` |
| `PERPLEXITY_API_KEY` | `perplexity_api_key` |
| `RAPIDAPI_KEY` | `rapidapi_key` |
| `GOOGLE_SEARCH_API_KEY` | `google_search_api_key` |
| `GOOGLE_SEARCH_API` | `google_search_api_key` |
| `GOOGLE_ENGINE_ID` | `google_engine_id` |
| `ESXI_PASSWORD` | `esxi_password` |
| `AZURE_CLIENT_SECRET` | `azure_client_secret` |
| `AWS_SECRET_ACCESS_KEY` | `aws_secret_access_key` |
| `MAIL_API` | `mail_api` |
| `SECRET_KEY` | `secret_key` |

## Quick Migration Template

```python
# ============================================
# BEFORE (Old Pattern)
# ============================================
import os
password = os.getenv('PROXMOX_PASSWORD')

# ============================================
# AFTER (New Pattern - Option 1: Session)
# ============================================
from glassdome.core.session import require_session

session = require_session()
password = session.get_secret('proxmox_password')

# ============================================
# AFTER (New Pattern - Option 2: Settings)
# ============================================
from glassdome.core.config import Settings

settings = Settings()  # Uses secrets manager automatically
password = settings.proxmox_password
```

## Questions?

If you encounter code that needs updating:
1. Check this reference guide
2. Look at the "Files Already Updated" section for examples
3. Use the migration patterns above
4. Test that session is initialized before accessing secrets

