# Securityd Implementation Checklist

## Overview

This checklist provides a phased implementation plan for the Glassdome Security Daemon. Each phase builds on the previous, allowing incremental delivery and testing.

**Total Estimated Effort:** 40-60 hours
**Recommended Team Size:** 1-2 developers

## Phase 1: Core Daemon (Unix Socket)

**Goal:** Basic daemon that serves secrets to local processes via Unix socket.
**Estimated Effort:** 12-16 hours
**Priority:** P0 (Required)

### 1.1 Daemon Framework

- [ ] Create `glassdome/securityd/` package directory
- [ ] Create `glassdome/securityd/__init__.py`
- [ ] Create `glassdome/securityd/daemon.py` with main daemon class
  - [ ] Signal handling (SIGTERM, SIGHUP, SIGINT)
  - [ ] PID file management
  - [ ] Graceful shutdown
  - [ ] Logging setup

**File:** `glassdome/securityd/daemon.py`
```python
class SecurityDaemon:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.secrets: Dict[str, str] = {}
        self.sessions: Dict[str, Session] = {}
        self._running = False
    
    def start(self):
        """Start the daemon."""
        self._setup_signals()
        self._load_secrets()
        self._start_socket_server()
        self._running = True
        self._main_loop()
    
    def stop(self):
        """Stop the daemon gracefully."""
        self._running = False
        self._close_sockets()
        self._clear_secrets()
```

### 1.2 Secrets Loading

- [ ] Create `glassdome/securityd/secrets_store.py`
  - [ ] Load encrypted secrets from file
  - [ ] Decrypt with master key
  - [ ] Store in memory (dict)
  - [ ] Memory locking (mlock) if available

**File:** `glassdome/securityd/secrets_store.py`
```python
class SecretsStore:
    def __init__(self, secrets_file: Path, master_key: bytes):
        self._secrets: Dict[str, str] = {}
        self._load(secrets_file, master_key)
    
    def get(self, key: str) -> Optional[str]:
        return self._secrets.get(key)
    
    def list_keys(self) -> List[str]:
        return list(self._secrets.keys())
    
    def clear(self):
        """Securely clear secrets from memory."""
        for key in self._secrets:
            self._secrets[key] = '\x00' * len(self._secrets[key])
        self._secrets.clear()
```

### 1.3 Unix Socket Server

- [ ] Create `glassdome/securityd/socket_server.py`
  - [ ] Create Unix socket at configured path
  - [ ] Set socket permissions (0660)
  - [ ] Accept connections
  - [ ] Handle concurrent clients (asyncio or threading)
  - [ ] Parse JSON requests
  - [ ] Send JSON responses

**File:** `glassdome/securityd/socket_server.py`
```python
class UnixSocketServer:
    def __init__(self, socket_path: str, handler: RequestHandler):
        self.socket_path = socket_path
        self.handler = handler
    
    async def start(self):
        """Start listening for connections."""
        server = await asyncio.start_unix_server(
            self._handle_client,
            path=self.socket_path
        )
        os.chmod(self.socket_path, 0o660)
        async with server:
            await server.serve_forever()
    
    async def _handle_client(self, reader, writer):
        """Handle a single client connection."""
        data = await reader.readline()
        request = json.loads(data.decode())
        response = await self.handler.handle(request)
        writer.write(json.dumps(response).encode() + b'\n')
        await writer.drain()
        writer.close()
```

### 1.4 Request Handler

- [ ] Create `glassdome/securityd/handler.py`
  - [ ] Route requests by action
  - [ ] Implement `auth` action
  - [ ] Implement `get_secret` action
  - [ ] Implement `list_secrets` action
  - [ ] Implement `health` action
  - [ ] Error handling and responses

**File:** `glassdome/securityd/handler.py`
```python
class RequestHandler:
    def __init__(self, secrets_store: SecretsStore, auth_manager: AuthManager):
        self.secrets = secrets_store
        self.auth = auth_manager
    
    async def handle(self, request: dict) -> dict:
        action = request.get('action')
        
        if action == 'health':
            return self._handle_health()
        
        if action == 'auth':
            return await self._handle_auth(request)
        
        # All other actions require auth
        token = request.get('token')
        if not self.auth.validate_token(token):
            return {'status': 'error', 'error': {'code': 'AUTH_REQUIRED'}}
        
        if action == 'get_secret':
            return self._handle_get_secret(request, token)
        
        if action == 'list_secrets':
            return self._handle_list_secrets(token)
        
        return {'status': 'error', 'error': {'code': 'UNKNOWN_ACTION'}}
```

### 1.5 Authentication Manager

- [ ] Create `glassdome/securityd/auth.py`
  - [ ] Process validation (PID, executable path)
  - [ ] Session/token generation
  - [ ] Token validation
  - [ ] Session expiration

**File:** `glassdome/securityd/auth.py`
```python
class AuthManager:
    def __init__(self, config: dict):
        self.config = config
        self.sessions: Dict[str, Session] = {}
    
    def authenticate_process(self, pid: int, exe: str) -> Optional[str]:
        """Authenticate a local process and return token."""
        if not self._validate_process(pid, exe):
            return None
        
        token = self._generate_token()
        self.sessions[token] = Session(
            client_id=f"pid:{pid}",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=8)
        )
        return token
    
    def validate_token(self, token: str) -> bool:
        """Check if token is valid and not expired."""
        session = self.sessions.get(token)
        if not session:
            return False
        if datetime.utcnow() > session.expires_at:
            del self.sessions[token]
            return False
        return True
```

### 1.6 CLI Commands

- [ ] Add daemon commands to `glassdome/cli.py`
  - [ ] `glassdome secrets daemon start [--foreground]`
  - [ ] `glassdome secrets daemon stop`
  - [ ] `glassdome secrets daemon status`
  - [ ] `glassdome secrets daemon logs`

### 1.7 Testing

- [ ] Unit tests for SecretsStore
- [ ] Unit tests for AuthManager
- [ ] Unit tests for RequestHandler
- [ ] Integration test: start daemon, request secret
- [ ] Test socket permissions
- [ ] Test concurrent clients

**Acceptance Criteria:**
- Daemon starts and prompts for master password
- Secrets loaded into memory
- Local process can authenticate via Unix socket
- Local process can retrieve secrets
- Daemon stops gracefully on SIGTERM

---

## Phase 2: Client Library Integration

**Goal:** Client library that agents use to access secrets from daemon.
**Estimated Effort:** 8-10 hours
**Priority:** P0 (Required)

### 2.1 Client Library

- [ ] Create `glassdome/core/securityd_client.py`
  - [ ] Unix socket connection
  - [ ] Authentication
  - [ ] Secret retrieval
  - [ ] Connection pooling (optional)
  - [ ] Retry logic

### 2.2 Security Context Integration

- [ ] Modify `glassdome/core/security.py`
  - [ ] Add daemon detection
  - [ ] Add daemon client initialization
  - [ ] Add fallback to file-based
  - [ ] Add `GLASSDOME_USE_DAEMON` env var check

### 2.3 Settings Integration

- [ ] Modify `glassdome/core/config.py`
  - [ ] Add daemon-aware secret loading
  - [ ] Maintain backward compatibility

### 2.4 Testing

- [ ] Test client connects to daemon
- [ ] Test client authenticates
- [ ] Test client retrieves secrets
- [ ] Test fallback when daemon unavailable
- [ ] Test `ensure_security_context()` uses daemon

**Acceptance Criteria:**
- `ensure_security_context()` uses daemon when available
- Falls back to file-based when daemon unavailable
- All existing tests pass
- `test_platform_connections.py` works with daemon

---

## Phase 3: Remote Access (mTLS)

**Goal:** Secure remote access for agents on other hosts or in containers.
**Estimated Effort:** 10-12 hours
**Priority:** P1 (Important)

### 3.1 HTTPS Server

- [ ] Create `glassdome/securityd/https_server.py`
  - [ ] TLS configuration
  - [ ] Client certificate validation
  - [ ] REST API endpoints
  - [ ] Rate limiting

### 3.2 Certificate Management

- [ ] Create `scripts/generate_securityd_certs.sh`
  - [ ] CA generation
  - [ ] Server certificate generation
  - [ ] Client certificate generation
- [ ] Document certificate rotation procedure

### 3.3 Client Library HTTPS Support

- [ ] Update `glassdome/core/securityd_client.py`
  - [ ] HTTPS connection support
  - [ ] Client certificate loading
  - [ ] Server certificate validation

### 3.4 Configuration

- [ ] Add HTTPS configuration to `securityd.conf`
- [ ] Add certificate paths
- [ ] Add allowed CNs list

### 3.5 Testing

- [ ] Test HTTPS server starts
- [ ] Test client cert validation
- [ ] Test secret retrieval over HTTPS
- [ ] Test from remote host
- [ ] Test invalid cert rejection

**Acceptance Criteria:**
- Daemon serves HTTPS on configurable port
- Client certificates required and validated
- Remote agents can retrieve secrets
- Invalid certificates rejected

---

## Phase 4: Container Support

**Goal:** Containers can access secrets via daemon or sidecar.
**Estimated Effort:** 6-8 hours
**Priority:** P1 (Important)

### 4.1 Docker Sidecar

- [ ] Create `Dockerfile.securityd`
- [ ] Create `docker-compose.securityd.yml`
- [ ] Create sidecar pattern example
- [ ] Document volume mounts for socket sharing

### 4.2 Kubernetes Support

- [ ] Create `k8s/securityd-daemonset.yaml`
- [ ] Create `k8s/securityd-service.yaml`
- [ ] Create example pod spec with sidecar
- [ ] Document Kubernetes secrets for master key

### 4.3 Testing

- [ ] Test Docker sidecar pattern
- [ ] Test container-to-daemon communication
- [ ] Test socket volume sharing

**Acceptance Criteria:**
- Docker container can access secrets via sidecar
- Kubernetes DaemonSet deploys successfully
- Pods can access secrets from DaemonSet

---

## Phase 5: Audit and Compliance

**Goal:** Full audit trail and compliance features.
**Estimated Effort:** 6-8 hours
**Priority:** P2 (Nice to have)

### 5.1 Audit Logging

- [ ] Create `glassdome/securityd/audit.py`
  - [ ] Structured log format (JSON)
  - [ ] All access logged
  - [ ] Rotation support
  - [ ] Remote syslog support (optional)

### 5.2 Metrics

- [ ] Add Prometheus metrics endpoint
  - [ ] Request counts
  - [ ] Error rates
  - [ ] Active sessions
  - [ ] Latency histograms

### 5.3 Authorization

- [ ] Implement secret-level access control
- [ ] Add authorization rules to config
- [ ] Log authorization decisions

### 5.4 Testing

- [ ] Test audit logs generated
- [ ] Test log rotation
- [ ] Test Prometheus metrics
- [ ] Test authorization rules

**Acceptance Criteria:**
- All secret access logged with client identity
- Prometheus metrics available
- Authorization rules enforced

---

## Summary

| Phase | Effort | Priority | Dependencies |
|-------|--------|----------|--------------|
| Phase 1: Core Daemon | 12-16h | P0 | None |
| Phase 2: Client Integration | 8-10h | P0 | Phase 1 |
| Phase 3: Remote Access | 10-12h | P1 | Phase 2 |
| Phase 4: Container Support | 6-8h | P1 | Phase 3 |
| Phase 5: Audit & Compliance | 6-8h | P2 | Phase 2 |

**Minimum Viable Product (MVP):** Phases 1-2 (20-26 hours)
**Full Implementation:** Phases 1-5 (42-54 hours)

## File Structure (Final)

```
glassdome/
├── securityd/
│   ├── __init__.py
│   ├── daemon.py           # Main daemon process
│   ├── socket_server.py    # Unix socket server
│   ├── https_server.py     # HTTPS server (Phase 3)
│   ├── handler.py          # Request handler
│   ├── auth.py             # Authentication manager
│   ├── secrets_store.py    # In-memory secrets
│   ├── audit.py            # Audit logging (Phase 5)
│   └── config.py           # Daemon configuration
├── core/
│   ├── securityd_client.py # Client library (Phase 2)
│   └── security.py         # Updated for daemon support

etc/
├── securityd.conf.example  # Example configuration

scripts/
├── generate_securityd_certs.sh  # Certificate generation (Phase 3)

docker/
├── Dockerfile.securityd    # Docker image (Phase 4)
├── docker-compose.securityd.yml

k8s/
├── securityd-daemonset.yaml  # Kubernetes DaemonSet (Phase 4)
├── securityd-service.yaml

tests/
├── securityd/
│   ├── test_daemon.py
│   ├── test_auth.py
│   ├── test_handler.py
│   ├── test_client.py
│   └── test_integration.py
```

## Next Steps

1. **Review this plan** with stakeholders
2. **Set timeline** based on priorities
3. **Start Phase 1** implementation
4. **Test thoroughly** before proceeding to next phase
5. **Document** as you go

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2024-11-25 | Use asyncio for daemon | Better performance for concurrent clients |
| 2024-11-25 | JWT for session tokens | Standard, stateless validation |
| 2024-11-25 | Unix socket for local | Lower latency, no TLS overhead |
| 2024-11-25 | mTLS for remote | Strong client authentication |

