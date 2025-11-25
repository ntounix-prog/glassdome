# Migration from File-Based to Daemon-Based Secrets

## Current State

The current Glassdome secrets implementation uses a file-based approach:

```
~/.glassdome/
├── secrets.encrypted      # AES-256-GCM encrypted secrets
├── master_key.enc         # Master key encrypted with password
├── session_cache.json     # Session metadata (authenticated_at, expires_at)
└── session_key.bin        # Decrypted master key (for headless access)
```

**Flow:**
1. User runs `./glassdome_start`
2. Prompted for master password
3. Master key decrypted and cached in `session_key.bin`
4. Session metadata saved to `session_cache.json`
5. Agents call `ensure_security_context()` which reads cached key
6. Secrets decrypted in each process's memory

**Limitations:**
- Each process decrypts secrets independently
- No centralized audit trail
- No process-level access control
- Doesn't work across hosts without copying files

## Migration Strategy

### Guiding Principles

1. **Backward compatibility:** File-based approach remains functional
2. **Incremental adoption:** Daemon is optional, then preferred, then required
3. **Zero downtime:** Agents continue working during migration
4. **Rollback capability:** Can revert to file-based at any time

### Migration Phases

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MIGRATION TIMELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 0          Phase 1          Phase 2          Phase 3                 │
│  (Current)        (Parallel)       (Preferred)      (Required)              │
│                                                                             │
│  File-based ──▶  File + Daemon ──▶ Daemon-first ──▶ Daemon-only            │
│  only            (optional)        (file fallback)  (file deprecated)       │
│                                                                             │
│  ────────────────────────────────────────────────────────────────────────▶  │
│                                                                             │
│  Now             +2 weeks          +1 month         +3 months               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Phase 0: Current State (Now)

No changes. Document current implementation and prepare for migration.

**Files involved:**
- `glassdome/core/session.py` - Session management
- `glassdome/core/secrets.py` - Secrets encryption/decryption
- `glassdome/core/security.py` - Security context helpers

## Phase 1: Parallel Operation

Daemon runs alongside file-based system. Agents can use either.

### Changes

#### 1. Add Daemon Detection to Security Context

```python
# glassdome/core/security.py (modified)

def ensure_security_context() -> None:
    """
    Ensure security context is available.
    
    Priority:
    1. Securityd daemon (if running and reachable)
    2. File-based session cache (fallback)
    """
    session = get_session()
    
    # Try daemon first (if enabled)
    if _daemon_enabled():
        client = get_securityd_client()
        if client.is_available():
            logger.debug("Using securityd daemon for secrets")
            return _use_daemon_context(client)
        else:
            logger.warning("Securityd daemon not available, falling back to file-based")
    
    # Fallback to file-based
    if not session.is_initialized():
        logger.info("Using file-based session cache")
        success = session.initialize(interactive=False, use_cache=True)
        if not success or not session.is_initialized():
            raise RuntimeError(
                "Security context not initialized.\n"
                "Run ./glassdome_start or start securityd daemon."
            )

def _daemon_enabled() -> bool:
    """Check if daemon mode is enabled in config."""
    return os.environ.get('GLASSDOME_USE_DAEMON', 'false').lower() == 'true'

def _use_daemon_context(client: 'SecuritydClient') -> None:
    """Use daemon for secrets."""
    # Authenticate with daemon
    if not client.authenticate():
        raise RuntimeError("Failed to authenticate with securityd daemon")
    
    # Store client for later use
    _set_daemon_client(client)
```

#### 2. Add Daemon Client

```python
# glassdome/core/securityd_client.py (new)

import socket
import json
import os
from typing import Optional, Dict
from pathlib import Path

class SecuritydClient:
    DEFAULT_SOCKET = '/run/glassdome/securityd.sock'
    
    def __init__(self, socket_path: str = None, url: str = None):
        self.socket_path = socket_path or os.environ.get(
            'GLASSDOME_SECURITYD_SOCKET', self.DEFAULT_SOCKET
        )
        self.url = url or os.environ.get('GLASSDOME_SECURITYD_URL')
        self.token: Optional[str] = None
        self._secrets_cache: Dict[str, str] = {}
    
    def is_available(self) -> bool:
        """Check if daemon is running."""
        if self.url:
            return self._check_https_available()
        return Path(self.socket_path).exists()
    
    def authenticate(self) -> bool:
        """Authenticate with daemon."""
        response = self._send({
            'action': 'auth',
            'params': {
                'pid': os.getpid(),
                'exe': self._get_executable()
            }
        })
        if response.get('status') == 'ok':
            self.token = response['data']['token']
            return True
        return False
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get secret from daemon."""
        # Check cache first
        if key in self._secrets_cache:
            return self._secrets_cache[key]
        
        # Request from daemon
        response = self._send({
            'action': 'get_secret',
            'token': self.token,
            'params': {'key': key}
        })
        
        if response.get('status') == 'ok':
            value = response['data']['value']
            self._secrets_cache[key] = value
            return value
        return None
    
    def _send(self, message: dict) -> dict:
        """Send message to daemon."""
        if self.url:
            return self._send_https(message)
        return self._send_socket(message)
    
    def _send_socket(self, message: dict) -> dict:
        """Send via Unix socket."""
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        sock.sendall(json.dumps(message).encode() + b'\n')
        
        data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk or b'\n' in data:
                break
            data += chunk
        
        sock.close()
        return json.loads(data.decode().strip())
    
    def _get_executable(self) -> str:
        """Get current executable path."""
        import sys
        return sys.executable
```

#### 3. Update Settings to Use Daemon Client

```python
# glassdome/core/config.py (modified)

from glassdome.core.securityd_client import SecuritydClient

class Settings(BaseSettings):
    @model_validator(mode='after')
    def _load_secrets_from_manager(self) -> 'Settings':
        """Load secrets from daemon or file-based manager."""
        
        # Try daemon first
        if os.environ.get('GLASSDOME_USE_DAEMON', 'false').lower() == 'true':
            client = SecuritydClient()
            if client.is_available() and client.authenticate():
                return self._load_from_daemon(client)
        
        # Fall back to file-based
        return self._load_from_file_manager()
    
    def _load_from_daemon(self, client: SecuritydClient) -> 'Settings':
        """Load secrets from securityd daemon."""
        secret_mappings = {
            'proxmox_password': 'proxmox_password',
            'proxmox_token_value': 'proxmox_token_value',
            # ... all mappings
        }
        
        for field, secret_key in secret_mappings.items():
            if hasattr(self, field):
                value = client.get_secret(secret_key)
                if value:
                    setattr(self, field, value)
        
        return self
```

### Testing Phase 1

```bash
# Test 1: File-based still works
./glassdome_start
python scripts/test_platform_connections.py
# Expected: PASS

# Test 2: Daemon works when enabled
export GLASSDOME_USE_DAEMON=true
glassdome secrets daemon start
python scripts/test_platform_connections.py
# Expected: PASS (using daemon)

# Test 3: Fallback works when daemon down
glassdome secrets daemon stop
python scripts/test_platform_connections.py
# Expected: PASS (fell back to file-based)
```

## Phase 2: Daemon Preferred

Daemon is the default, file-based is fallback.

### Changes

#### 1. Change Default

```python
# glassdome/core/security.py

def _daemon_enabled() -> bool:
    """Check if daemon mode is enabled."""
    # Changed: Default is now 'true'
    return os.environ.get('GLASSDOME_USE_DAEMON', 'true').lower() != 'false'
```

#### 2. Add Migration Warning

```python
# glassdome/core/session.py

def initialize(self, ...):
    """Initialize session."""
    # Add deprecation warning
    import warnings
    warnings.warn(
        "File-based session management will be deprecated in v2.0. "
        "Consider migrating to securityd daemon. "
        "See: docs/securityd/MIGRATION.md",
        DeprecationWarning
    )
    # ... rest of initialization
```

#### 3. Update Documentation

- Update README to recommend daemon
- Update QUICKSTART to use daemon
- Add migration guide link to all secret-related docs

### Testing Phase 2

```bash
# Test 1: Daemon is default
python scripts/test_platform_connections.py
# Expected: Uses daemon, shows deprecation warning if falling back

# Test 2: Can explicitly disable daemon
export GLASSDOME_USE_DAEMON=false
python scripts/test_platform_connections.py
# Expected: Uses file-based, shows deprecation warning
```

## Phase 3: Daemon Required

File-based is removed (or hidden behind flag).

### Changes

#### 1. Remove File-Based Fallback

```python
# glassdome/core/security.py

def ensure_security_context() -> None:
    """Ensure security context via securityd daemon."""
    client = get_securityd_client()
    
    if not client.is_available():
        raise RuntimeError(
            "Securityd daemon not running.\n"
            "Start with: glassdome secrets daemon start"
        )
    
    if not client.authenticate():
        raise RuntimeError("Failed to authenticate with securityd daemon")
    
    _set_daemon_client(client)
```

#### 2. Keep File-Based for Emergency

```python
# glassdome/core/security.py

def ensure_security_context() -> None:
    """Ensure security context via securityd daemon."""
    # Emergency escape hatch
    if os.environ.get('GLASSDOME_LEGACY_MODE') == 'true':
        logger.warning("Using legacy file-based mode (not recommended)")
        return _legacy_file_based_context()
    
    # Normal daemon-based flow
    # ...
```

#### 3. Update All Scripts

Remove `./glassdome_start` references, replace with daemon commands.

### Testing Phase 3

```bash
# Test 1: Daemon required
python scripts/test_platform_connections.py
# Expected: Error if daemon not running

# Test 2: Works with daemon
glassdome secrets daemon start
python scripts/test_platform_connections.py
# Expected: PASS

# Test 3: Emergency legacy mode
export GLASSDOME_LEGACY_MODE=true
python scripts/test_platform_connections.py
# Expected: PASS with warning
```

## Rollback Procedure

If issues arise during migration, rollback to previous phase:

### From Phase 1 to Phase 0

```bash
# Stop daemon
glassdome secrets daemon stop

# Disable daemon mode
export GLASSDOME_USE_DAEMON=false

# Or unset entirely
unset GLASSDOME_USE_DAEMON

# Verify file-based works
./glassdome_start
python scripts/test_platform_connections.py
```

### From Phase 2 to Phase 1

```bash
# Explicitly disable daemon default
export GLASSDOME_USE_DAEMON=false

# Add to ~/.bashrc for persistence
echo 'export GLASSDOME_USE_DAEMON=false' >> ~/.bashrc
```

### From Phase 3 to Phase 2

```bash
# Enable legacy mode
export GLASSDOME_LEGACY_MODE=true

# Or downgrade to previous version
git checkout v1.x
pip install -e .
```

## Data Migration

No data migration required - both approaches use the same encrypted secrets file:

```
~/.glassdome/secrets.encrypted  # Used by both file-based and daemon
```

The daemon simply reads this file at startup instead of each process reading it independently.

## Compatibility Matrix

| Component | Phase 0 | Phase 1 | Phase 2 | Phase 3 |
|-----------|---------|---------|---------|---------|
| `./glassdome_start` | Required | Optional | Deprecated | Removed |
| `glassdome secrets daemon start` | N/A | Optional | Default | Required |
| File-based session | Default | Fallback | Fallback (warn) | Emergency only |
| Daemon session | N/A | Optional | Default | Required |
| `session_key.bin` | Used | Used (fallback) | Deprecated | Removed |
| `session_cache.json` | Used | Used (fallback) | Deprecated | Removed |

## Timeline

| Phase | Target Date | Criteria to Proceed |
|-------|-------------|---------------------|
| Phase 0 | Now | Documentation complete |
| Phase 1 | +2 weeks | Daemon implementation tested |
| Phase 2 | +1 month | No critical bugs in Phase 1 |
| Phase 3 | +3 months | All agents migrated, no fallback usage |

## Checklist

### Pre-Migration

- [ ] Document current secrets and their usage
- [ ] Verify all agents use `ensure_security_context()`
- [ ] Test file-based approach works reliably
- [ ] Generate SSL certificates for daemon

### Phase 1

- [ ] Implement daemon (see IMPLEMENTATION_CHECKLIST.md)
- [ ] Implement client library
- [ ] Add daemon detection to security.py
- [ ] Test parallel operation
- [ ] Document daemon usage

### Phase 2

- [ ] Change default to daemon
- [ ] Add deprecation warnings
- [ ] Update all documentation
- [ ] Monitor fallback usage
- [ ] Train team on daemon operations

### Phase 3

- [ ] Remove file-based code (or hide)
- [ ] Update all scripts
- [ ] Final documentation update
- [ ] Archive legacy code

