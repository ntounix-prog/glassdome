# Glassdome Session Management

## Overview

Glassdome requires authentication **once per session** (8 hours). After initialization, agents can execute without re-authentication. This ensures that:
1. Secrets are only decrypted when authorized (once per day)
2. Agents cannot run without proper initialization
3. All secrets are loaded into memory for efficient access
4. Session timeout prevents indefinite access (8 hours)
5. **No password prompts during agent execution** - authentication happens once

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              GlassdomeSession (Singleton)                   │
│  - Authenticated: bool                                      │
│  - Secrets: Dict[str, str] (decrypted in memory)          │
│  - Settings: Settings instance                             │
│  - Session timeout: 8 hours                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ require_auth()
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              BaseAgent                                       │
│  - _check_session() before execution                        │
│  - Raises RuntimeError if not authenticated                 │
└─────────────────────────────────────────────────────────────┘
```

## Usage

### 1. Command Line Initialization (Recommended)

**Quick Start:**
```bash
# Initialize session (will prompt for master password)
./glassdome_start
# or
./scripts/start_glassdome.sh

# Initialize and start API server on port 8010
./glassdome_start --serve
# or
./scripts/start_glassdome.sh --serve
```

**Alternative (direct script):**
```bash
# Initialize session only
python scripts/glassdome_init.py
```

**What the startup script does:**
1. ✅ Checks for virtual environment
2. ✅ Activates venv automatically
3. ✅ Initializes Glassdome session (prompts for master password once)
4. ✅ Optionally starts FastAPI server on port 8010

### 2. Programmatic Initialization

```python
from glassdome.core.session import get_session

session = get_session()
success = session.initialize(interactive=True)

if success:
    # Now agents can execute
    settings = session.get_settings()
    secret = session.get_secret('openai_api_key')
```

### 3. API Initialization

```bash
# Login via API (server must be running on port 8010)
curl -X POST http://localhost:8010/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"master_password": "your-master-password"}'

# Check status
curl http://localhost:8010/api/auth/status

# Logout
curl -X POST http://localhost:8010/api/auth/logout
```

## Agent Execution

Agents automatically check for authentication before execution. **This is a fast check - no password prompt**:

```python
from glassdome.agents.ubuntu import UbuntuInstallerAgent

# Morning: Initialize session once
session = get_session()
session.initialize()  # Enter password ONCE

# Throughout the day: Agents run without re-auth
agent = UbuntuInstallerAgent(...)
result = await agent.run(task)  # ✅ Fast check, session valid
result2 = await agent.run(task2)  # ✅ Fast check, session still valid
# ... many more agent executions ...
# All work without re-authentication for 8 hours
```

## Session Lifecycle

1. **Initialization**: User provides master password
2. **Decryption**: All secrets are decrypted and loaded into memory
3. **Validation**: Session is marked as authenticated
4. **Execution**: Agents can execute (they check session on each run)
5. **Timeout**: Session expires after 8 hours
6. **Refresh**: User can refresh session with master password

## Security Features

- **Master Password Required**: Cannot access secrets without password (once per session)
- **Session Timeout**: Sessions expire after 8 hours (then re-authenticate)
- **In-Memory Storage**: Secrets decrypted only in memory (not on disk)
- **Agent Gating**: Agents cannot execute without valid session
- **Fast Checks**: Every agent execution checks session validity (no password prompt)
- **One-Time Auth**: Authenticate once, use all day (8 hours)

## Memory Persistence

Yes, secrets stay in memory for the session duration:

- Secrets are decrypted once during initialization
- Stored in `session.secrets` dictionary (in memory)
- Available for entire session lifetime (8 hours)
- Cleared on logout or session expiration
- Never written to disk in decrypted form

## Integration with Existing Code

### Before (Direct Settings Access)
```python
from glassdome.core.config import settings
api_key = settings.openai_api_key  # Works but no auth check
```

### After (Session-Based)
```python
from glassdome.core.session import require_session

session = require_session()  # Raises if not authenticated
settings = session.get_settings()
api_key = settings.openai_api_key  # Safe access
```

### Agent Code (Automatic)
```python
# Agents automatically check session
class MyAgent(BaseAgent):
    async def execute(self, task):
        # Session already checked by BaseAgent.run()
        # Just use settings/secrets normally
        settings = self.get_settings()  # Or use session
```

## Migration Path

1. **Initialize session** before running agents
2. **Agents automatically check** - no code changes needed
3. **Settings access** still works (but requires session)
4. **API endpoints** can check session status

## Example Workflow

```python
# 1. Initialize session (ONCE per day - morning startup)
from glassdome.core.session import get_session
session = get_session()
session.initialize(interactive=True)  # Enter password ONCE

# 2. Use agents throughout the day (NO re-authentication needed)
from glassdome.agents.ubuntu import UbuntuInstallerAgent
agent = UbuntuInstallerAgent(...)

# All these work without re-authentication (session valid for 8 hours)
result1 = await agent.run(task1)  # ✅ Fast check, works
result2 = await agent.run(task2)  # ✅ Fast check, works
result3 = await agent.run(task3)  # ✅ Fast check, works
# ... many more executions ...

# 3. Access secrets (no password needed, already decrypted)
secret = session.get_secret('proxmox_password')  # ✅ Instant access

# 4. Next day or after 8 hours: Re-authenticate if needed
# session.refresh()  # Only if session expired
```

## Troubleshooting

### "Session not authenticated" Error

**Cause**: Session not initialized or expired

**Solution**:
```python
session = get_session()
session.initialize(interactive=True)
```

### "Agents cannot execute" Error

**Cause**: Session check failed

**Solution**: Initialize session first (see above)

### Session Expired

**Cause**: Session timeout (8 hours)

**Solution**:
```python
session.refresh()  # Re-authenticate
```

