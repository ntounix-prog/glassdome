# TODO: Daemon Approach for Session Management

## Status: Future Consideration

**Current Implementation:** Cross-process session sharing via OS keyring + cache file  
**Future Enhancement:** Daemon-based session management for improved security

## Why Daemon Approach?

### Current Limitations

1. **OS Keyring Security**: If keyring is unlocked, any same-user process can access master key
2. **No Process Validation**: Can't verify which processes are "trusted"
3. **No Audit Trail**: No centralized logging of session access
4. **Cache File Exposure**: Metadata file indicates session exists

### Daemon Benefits

1. **Centralized Control**: Single process holds session, validates requests
2. **Process Validation**: Can verify process identity before sharing secrets
3. **Audit Logging**: Centralized logging of all session access
4. **Better Security**: Secrets never leave daemon process memory
5. **Access Control**: Can implement fine-grained permissions

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────┐
│  glassdome-daemon (background service)                 │
│  - Holds session in memory                              │
│  - Validates process requests                           │
│  - Logs all access attempts                            │
│  - Manages session expiration                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Unix Socket / Named Pipe
                       │ (secure IPC)
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Client Process (script, API, agent)                    │
│  - Connects to daemon                                   │
│  - Requests secrets                                     │
│  - Receives secrets (never stores master key)          │
└─────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Daemon Service
- [ ] Create `glassdome/core/daemon.py`
- [ ] Unix socket server for IPC
- [ ] Session management in daemon process
- [ ] Process validation (check PID, executable path)
- [ ] Request/response protocol

### Phase 2: Client Library
- [ ] Create `glassdome/core/daemon_client.py`
- [ ] Connect to daemon via Unix socket
- [ ] Request secrets from daemon
- [ ] Fallback to current approach if daemon unavailable

### Phase 3: Integration
- [ ] Update `GlassdomeSession` to use daemon client
- [ ] Keep current approach as fallback
- [ ] Add daemon startup script
- [ ] Add systemd service file (optional)

### Phase 4: Security Enhancements
- [ ] Process whitelist/blacklist
- [ ] Rate limiting
- [ ] Audit logging
- [ ] Session access tokens (short-lived)

## Security Features

### Process Validation
```python
def validate_process(pid: int) -> bool:
    """Validate that process is trusted"""
    # Check executable path
    # Check process owner
    # Check process tree (parent process)
    # Check whitelist
    return is_trusted
```

### Access Control
```python
# Whitelist trusted processes
TRUSTED_PROCESSES = [
    '/usr/bin/python3',
    '/home/user/glassdome/venv/bin/python',
    '/usr/bin/uvicorn',
]

# Or use process signatures
TRUSTED_SIGNATURES = [
    'glassdome.*',
    'python.*glassdome.*',
]
```

### Audit Logging
```python
logger.info(f"Session access: pid={pid}, user={user}, process={exe}, secrets={secrets_requested}")
```

## Migration Path

1. **Keep current implementation** as fallback
2. **Add daemon as optional** enhancement
3. **Gradual migration** - daemon preferred, fallback to keyring
4. **Production recommendation** - use daemon approach

## When to Implement

- **Priority**: Medium
- **Timeline**: After current implementation is stable
- **Trigger**: 
  - Production deployment
  - Security audit requirements
  - Multi-user scenarios
  - Compliance requirements

## Notes

- Current keyring + cache approach is acceptable for development
- Daemon approach recommended for production
- Can implement incrementally without breaking changes
- Keep backward compatibility with current approach

