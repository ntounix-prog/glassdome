# Glassdome Security Daemon (securityd)

## Overview

The Glassdome Security Daemon (`glassdome-securityd`) is a proposed centralized secrets management service that provides secure, auditable access to credentials for agents, containers, and distributed workloads across multiple hosts.

## Current State vs. Daemon Approach

### Current Implementation (File-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│  Host: agentX                                                   │
│  User: nomad                                                    │
│                                                                 │
│  ~/.glassdome/                                                  │
│  ├── session_cache.json    (metadata, 600 perms)               │
│  ├── session_key.bin       (master key, 600 perms)             │
│  ├── master_key.enc        (encrypted master key)              │
│  └── secrets.encrypted     (encrypted secrets)                 │
│                                                                 │
│  Process A ──┐                                                  │
│  Process B ──┼── All read same files ── No audit trail         │
│  Process C ──┘                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Pros:**
- Simple, no moving parts
- Works today
- No network attack surface

**Cons:**
- Per-host initialization required
- No audit trail
- No process-level access control
- Doesn't scale to containers

### Daemon Approach (Proposed)

```
┌─────────────────────────────────────────────────────────────────┐
│  glassdome-securityd (single daemon per cluster/lab)           │
│  ├── Holds master key in memory                                 │
│  ├── Validates client identity                                  │
│  ├── Logs all access                                            │
│  └── Serves secrets via API                                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Host A  │   │ Host B  │   │Container│
   │ Agent   │   │ Agent   │   │ Agent   │
   └─────────┘   └─────────┘   └─────────┘
   
   All clients call daemon API - centralized audit
```

**Pros:**
- Centralized secret management
- Full audit trail
- Process-level access control
- Scales to containers and multi-host
- Single point of secret rotation

**Cons:**
- Additional complexity
- Network attack surface (mitigated by mTLS)
- Single point of failure (mitigated by HA)

## When to Implement

Implement the daemon approach when any of these conditions are met:

| Trigger | Threshold | Rationale |
|---------|-----------|-----------|
| Host count | > 3 hosts running agents | Manual `./glassdome_start` on each host becomes tedious |
| Container usage | Any containerized agents | Containers don't share host keyring/filesystem |
| Audit requirements | Compliance/security review | Need to prove who accessed what, when |
| Multi-user | > 1 user running agents | Current approach is per-user |
| Secret rotation | Frequent key changes | Daemon makes rotation atomic |

## Quick Start (Future)

Once implemented, the daemon will be started with:

```bash
# Start daemon (prompts for master password once)
glassdome secrets daemon start

# Check status
glassdome secrets daemon status

# Agents automatically use daemon if available
python scripts/test_platform_connections.py  # No password prompt
```

## Documentation Index

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and component breakdown |
| [PROTOCOL.md](PROTOCOL.md) | API specification and communication protocol |
| [SECURITY_MODEL.md](SECURITY_MODEL.md) | Threat model and authentication methods |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Installation and operations guide |
| [MIGRATION.md](MIGRATION.md) | Transition from file-based approach |
| [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) | Phased implementation tasks |

## Related Files

Current implementation (to be enhanced, not replaced):

- `glassdome/core/session.py` - Session management
- `glassdome/core/secrets.py` - Secrets encryption/decryption
- `glassdome/core/security.py` - Security context helpers

## Status

**Current:** Design phase (this documentation)
**Next:** Implementation when triggers are met
**Priority:** Medium - current file-based approach works for lab environment

