# Securityd Architecture

## High-Level Design

The Glassdome Security Daemon is a long-running process that holds decrypted secrets in memory and serves them to authenticated clients via a secure API.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GLASSDOME-SECURITYD                                 │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │  Auth Manager   │  │ Secrets Store   │  │  Audit Logger   │             │
│  │                 │  │                 │  │                 │             │
│  │ - Validate PID  │  │ - In-memory     │  │ - Access logs   │             │
│  │ - Check certs   │  │ - Encrypted at  │  │ - Rotation logs │             │
│  │ - Issue tokens  │  │   rest (disk)   │  │ - Error logs    │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┼────────────────────┘                       │
│                                │                                            │
│                    ┌───────────┴───────────┐                                │
│                    │    Request Handler    │                                │
│                    │                       │                                │
│                    │  GET /secrets/{key}   │                                │
│                    │  POST /auth/validate  │                                │
│                    │  GET /health          │                                │
│                    └───────────┬───────────┘                                │
│                                │                                            │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                 ┌───────────────┼───────────────┐
                 │               │               │
          Unix Socket      mTLS (HTTPS)    Docker Socket
          (local only)     (remote/containers)  (container sidecar)
                 │               │               │
                 ▼               ▼               ▼
          ┌──────────┐   ┌──────────┐   ┌──────────┐
          │ Local    │   │ Remote   │   │Container │
          │ Agent    │   │ Agent    │   │ Agent    │
          └──────────┘   └──────────┘   └──────────┘
```

## Components

### 1. Daemon Process (`glassdome-securityd`)

**Location:** `glassdome/securityd/daemon.py` (future)

**Responsibilities:**
- Load and decrypt secrets on startup (master password required once)
- Hold decrypted secrets in memory
- Serve secrets to authenticated clients
- Manage session lifecycle (expiration, refresh)
- Log all access attempts

**Lifecycle:**

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   START     │────▶│   INIT      │────▶│   READY     │────▶│   SHUTDOWN  │
│             │     │             │     │             │     │             │
│ Parse args  │     │ Prompt for  │     │ Serve       │     │ Clear       │
│ Load config │     │ master pw   │     │ requests    │     │ secrets     │
│             │     │ Decrypt     │     │             │     │ Close       │
│             │     │ secrets     │     │             │     │ sockets     │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

**Memory Layout:**

```python
class SecuredDaemon:
    def __init__(self):
        self._master_key: bytes = None          # Never written to disk while running
        self._secrets: Dict[str, str] = {}      # Decrypted secrets in memory
        self._sessions: Dict[str, Session] = {} # Active client sessions
        self._audit_log: AuditLogger = None     # Audit trail
```

### 2. Client Library (`glassdome/core/securityd_client.py`)

**Location:** `glassdome/core/securityd_client.py` (future)

**Responsibilities:**
- Connect to daemon (Unix socket or HTTPS)
- Authenticate client process
- Request secrets
- Cache secrets locally (optional, configurable TTL)
- Fallback to file-based approach if daemon unavailable

**Interface:**

```python
class SecuritydClient:
    def __init__(self, socket_path: str = None, url: str = None):
        """
        Connect to securityd daemon.
        
        Args:
            socket_path: Unix socket path (local access)
            url: HTTPS URL (remote access)
        """
        pass
    
    def get_secret(self, key: str) -> Optional[str]:
        """Get a secret from the daemon."""
        pass
    
    def is_available(self) -> bool:
        """Check if daemon is running and accessible."""
        pass
```

**Integration with Existing Code:**

```python
# glassdome/core/security.py (modified)

def ensure_security_context():
    """
    Ensure security context is available.
    
    Priority:
    1. Securityd daemon (if running)
    2. File-based session cache (fallback)
    """
    # Try daemon first
    client = SecuritydClient()
    if client.is_available():
        return _use_daemon_context(client)
    
    # Fallback to current implementation
    return _use_file_based_context()
```

### 3. CLI Tools

**Commands:**

```bash
# Daemon management
glassdome secrets daemon start [--foreground] [--config PATH]
glassdome secrets daemon stop
glassdome secrets daemon status
glassdome secrets daemon logs [--follow]

# Secret management (via daemon)
glassdome secrets get KEY
glassdome secrets set KEY [--value VALUE]
glassdome secrets list
glassdome secrets rotate-master
```

## Communication Patterns

### Local Access (Unix Socket)

For processes on the same host as the daemon:

```
Client Process                    Daemon
     │                              │
     │  connect(/run/glassdome.sock)│
     │─────────────────────────────▶│
     │                              │
     │  {"action": "auth",          │
     │   "pid": 12345,              │
     │   "exe": "/usr/bin/python3"} │
     │─────────────────────────────▶│
     │                              │ Validate process
     │                              │
     │  {"status": "ok",            │
     │   "token": "abc123..."}      │
     │◀─────────────────────────────│
     │                              │
     │  {"action": "get_secret",    │
     │   "token": "abc123...",      │
     │   "key": "proxmox_password"} │
     │─────────────────────────────▶│
     │                              │ Check authorization
     │                              │ Log access
     │                              │
     │  {"status": "ok",            │
     │   "value": "secret123"}      │
     │◀─────────────────────────────│
```

### Remote Access (mTLS)

For processes on different hosts or in containers:

```
Remote Client                     Daemon (HTTPS)
     │                              │
     │  TLS handshake               │
     │  (client cert required)      │
     │─────────────────────────────▶│
     │                              │ Validate cert CN
     │                              │ Check cert fingerprint
     │                              │
     │  POST /auth/validate         │
     │  {"client_id": "agent-01"}   │
     │─────────────────────────────▶│
     │                              │
     │  {"token": "xyz789..."}      │
     │◀─────────────────────────────│
     │                              │
     │  GET /secrets/proxmox_password│
     │  Authorization: Bearer xyz789│
     │─────────────────────────────▶│
     │                              │
     │  {"value": "secret123"}      │
     │◀─────────────────────────────│
```

### Container Sidecar Pattern

For Docker/Kubernetes deployments:

```
┌─────────────────────────────────────────────────────────────┐
│  Pod / Docker Compose Service                               │
│                                                             │
│  ┌─────────────────┐      ┌─────────────────┐              │
│  │  Agent Container │      │ Securityd       │              │
│  │                 │      │ Sidecar         │              │
│  │  GET localhost: │      │                 │              │
│  │  8443/secrets/  │─────▶│ Holds secrets   │              │
│  │  proxmox_pass   │      │ in memory       │              │
│  │                 │      │                 │              │
│  └─────────────────┘      └────────┬────────┘              │
│                                    │                        │
└────────────────────────────────────┼────────────────────────┘
                                     │
                                     │ Mount: secrets volume
                                     │ or init from central daemon
                                     ▼
                            ┌─────────────────┐
                            │ Central Daemon  │
                            │ (optional)      │
                            └─────────────────┘
```

## State Management

### In-Memory Secrets

```python
# Secrets are decrypted once at startup and held in memory
_secrets = {
    "proxmox_password": "decrypted_value",
    "proxmox_token_value": "decrypted_value",
    "openai_api_key": "decrypted_value",
    # ...
}

# Memory is locked to prevent swapping (if supported)
import mmap
mmap.mlock(_secrets_buffer)
```

### Session Tracking

```python
@dataclass
class ClientSession:
    session_id: str
    client_id: str           # Process ID or certificate CN
    created_at: datetime
    expires_at: datetime
    last_access: datetime
    access_count: int
    allowed_secrets: List[str]  # Optional: fine-grained access control
```

### Audit Trail

```python
@dataclass
class AuditEntry:
    timestamp: datetime
    client_id: str
    action: str              # "get_secret", "auth", "rotate"
    secret_key: Optional[str]
    result: str              # "success", "denied", "error"
    details: Dict[str, Any]
```

## Scalability Considerations

### Single Daemon (Recommended for Lab)

```
┌──────────────────────────────────────────┐
│  Lab Network                             │
│                                          │
│  ┌────────────┐                          │
│  │ securityd  │◀──── All hosts connect   │
│  │ (agentX)   │      via Unix socket     │
│  └────────────┘      or mTLS             │
│                                          │
└──────────────────────────────────────────┘
```

**Pros:** Simple, single source of truth
**Cons:** Single point of failure

### Per-Host Daemon

```
┌──────────────────────────────────────────┐
│  Host A                Host B            │
│  ┌────────────┐       ┌────────────┐     │
│  │ securityd  │       │ securityd  │     │
│  │ (local)    │       │ (local)    │     │
│  └────────────┘       └────────────┘     │
│        │                    │            │
│        └────────┬───────────┘            │
│                 ▼                        │
│        ┌────────────────┐                │
│        │ Central Vault  │                │
│        │ (sync secrets) │                │
│        └────────────────┘                │
└──────────────────────────────────────────┘
```

**Pros:** No network dependency for local agents
**Cons:** Secret sync complexity

### Clustered (HA)

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐       │
│  │ securityd  │   │ securityd  │   │ securityd  │       │
│  │ (primary)  │◀─▶│ (replica)  │◀─▶│ (replica)  │       │
│  └────────────┘   └────────────┘   └────────────┘       │
│        │                │                │               │
│        └────────────────┼────────────────┘               │
│                         ▼                                │
│                 ┌────────────────┐                       │
│                 │ Load Balancer  │                       │
│                 └────────────────┘                       │
│                         │                                │
│              ┌──────────┼──────────┐                     │
│              ▼          ▼          ▼                     │
│           Agent A    Agent B    Agent C                  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Pros:** High availability, no single point of failure
**Cons:** Complexity, consensus protocol needed

## File Layout (Future)

```
glassdome/
├── securityd/
│   ├── __init__.py
│   ├── daemon.py           # Main daemon process
│   ├── auth.py             # Authentication handlers
│   ├── protocol.py         # Request/response protocol
│   ├── audit.py            # Audit logging
│   └── config.py           # Daemon configuration
├── core/
│   ├── securityd_client.py # Client library
│   └── security.py         # Updated to use daemon
└── cli.py                  # Updated with daemon commands

/etc/glassdome/
├── securityd.conf          # Daemon configuration
├── certs/
│   ├── server.crt          # Daemon TLS certificate
│   ├── server.key          # Daemon TLS private key
│   └── ca.crt              # CA for client certs

/run/glassdome/
└── securityd.sock          # Unix socket

/var/log/glassdome/
└── securityd.log           # Audit log
```

## Configuration

```yaml
# /etc/glassdome/securityd.conf

daemon:
  socket_path: /run/glassdome/securityd.sock
  socket_permissions: 0660
  socket_group: glassdome

https:
  enabled: true
  bind: 0.0.0.0
  port: 8443
  cert: /etc/glassdome/certs/server.crt
  key: /etc/glassdome/certs/server.key
  client_ca: /etc/glassdome/certs/ca.crt
  require_client_cert: true

auth:
  session_timeout: 8h
  max_sessions_per_client: 10
  
  # Local process validation
  process_validation:
    enabled: true
    allowed_executables:
      - /usr/bin/python3
      - /home/nomad/glassdome/venv/bin/python
    allowed_paths:
      - /home/nomad/glassdome/

  # Remote client validation
  certificate_validation:
    enabled: true
    allowed_cns:
      - agent-*
      - overseer-*

secrets:
  encrypted_file: /home/nomad/.glassdome/secrets.encrypted
  master_key_file: /home/nomad/.glassdome/master_key.enc

audit:
  enabled: true
  log_file: /var/log/glassdome/securityd.log
  log_level: INFO
  include_secret_names: true   # Log which secrets accessed
  include_secret_values: false # Never log actual values
```

