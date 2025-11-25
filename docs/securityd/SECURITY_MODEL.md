# Securityd Security Model

## Threat Model

### Assets to Protect

| Asset | Sensitivity | Impact if Compromised |
|-------|-------------|----------------------|
| Master encryption key | Critical | All secrets exposed |
| Decrypted secrets in memory | Critical | Direct credential theft |
| Session tokens | High | Unauthorized secret access |
| Audit logs | Medium | Evidence tampering |
| Configuration files | Medium | Service disruption |

### Threat Actors

| Actor | Capability | Motivation |
|-------|------------|------------|
| External attacker | Network access, exploit knowledge | Credential theft, lateral movement |
| Malicious insider | Local access, some credentials | Data exfiltration |
| Compromised process | Code execution on host | Privilege escalation |
| Container escape | Container runtime access | Host compromise |

### Attack Vectors

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ATTACK SURFACE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Network Attack  │                                                        │
│  │                 │                                                        │
│  │ - MITM on HTTPS │──▶ Mitigated by: mTLS, certificate pinning            │
│  │ - Port scanning │──▶ Mitigated by: firewall, bind to localhost          │
│  │ - DoS           │──▶ Mitigated by: rate limiting, connection limits     │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Local Attack    │                                                        │
│  │                 │                                                        │
│  │ - Socket hijack │──▶ Mitigated by: socket permissions (0660)            │
│  │ - Memory dump   │──▶ Mitigated by: mlock(), no core dumps               │
│  │ - Process spoof │──▶ Mitigated by: PID + exe validation                 │
│  │ - File theft    │──▶ Mitigated by: encrypted at rest, 600 perms         │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Insider Attack  │                                                        │
│  │                 │                                                        │
│  │ - Token theft   │──▶ Mitigated by: short TTL, per-process tokens        │
│  │ - Log tampering │──▶ Mitigated by: append-only logs, remote syslog      │
│  │ - Config change │──▶ Mitigated by: file permissions, config validation  │
│  └─────────────────┘                                                        │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │ Container Attack│                                                        │
│  │                 │                                                        │
│  │ - Escape to host│──▶ Mitigated by: sidecar pattern, minimal privileges  │
│  │ - Env var leak  │──▶ Mitigated by: secrets never in env vars            │
│  │ - Image theft   │──▶ Mitigated by: secrets not baked into images        │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Authentication Methods

### 1. Process Validation (Local Unix Socket)

For local processes connecting via Unix socket, the daemon validates:

```python
def validate_local_process(pid: int, claimed_exe: str) -> bool:
    """
    Validate that a local process is trusted.
    
    Checks:
    1. PID exists and is running
    2. Executable path matches claimed path
    3. Executable is in allowed list
    4. Process owner matches expected user
    5. Parent process chain is valid (optional)
    """
    
    # 1. Check PID exists
    proc_path = Path(f'/proc/{pid}')
    if not proc_path.exists():
        return False
    
    # 2. Get actual executable
    actual_exe = (proc_path / 'exe').resolve()
    if str(actual_exe) != claimed_exe:
        return False
    
    # 3. Check against allowlist
    if actual_exe not in ALLOWED_EXECUTABLES:
        return False
    
    # 4. Check process owner
    stat = proc_path.stat()
    if stat.st_uid != EXPECTED_UID:
        return False
    
    # 5. Optional: Validate parent chain
    # Prevents process injection attacks
    if VALIDATE_PARENT_CHAIN:
        parent_pid = get_parent_pid(pid)
        if not is_trusted_parent(parent_pid):
            return False
    
    return True
```

**Configuration:**

```yaml
auth:
  process_validation:
    enabled: true
    
    # Allowed executable paths
    allowed_executables:
      - /usr/bin/python3
      - /usr/bin/python3.12
      - /home/nomad/glassdome/venv/bin/python
      - /home/nomad/glassdome/venv/bin/python3
      - /usr/bin/uvicorn
    
    # Allowed working directories
    allowed_paths:
      - /home/nomad/glassdome/
      - /opt/glassdome/
    
    # Expected user
    allowed_users:
      - nomad
      - glassdome
    
    # Validate parent process chain
    validate_parent_chain: false  # Enable for high-security
```

### 2. mTLS Certificates (Remote/Container Access)

For remote clients or containers, authentication uses mutual TLS:

```
┌─────────────────────────────────────────────────────────────────┐
│                     mTLS HANDSHAKE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client                              Server (securityd)         │
│    │                                        │                   │
│    │  ClientHello                           │                   │
│    │───────────────────────────────────────▶│                   │
│    │                                        │                   │
│    │  ServerHello + ServerCert + CertReq    │                   │
│    │◀───────────────────────────────────────│                   │
│    │                                        │                   │
│    │  ClientCert + ClientKeyExchange        │                   │
│    │───────────────────────────────────────▶│                   │
│    │                                        │ Validate client   │
│    │                                        │ cert against CA   │
│    │                                        │ Check CN in       │
│    │                                        │ allowed list      │
│    │  Finished                              │                   │
│    │◀──────────────────────────────────────▶│                   │
│    │                                        │                   │
│    │  Encrypted Application Data            │                   │
│    │◀──────────────────────────────────────▶│                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Certificate Structure:**

```
# CA Certificate (self-signed, kept secure)
CN: glassdome-ca
Valid: 10 years

# Server Certificate (daemon)
CN: securityd.glassdome.local
SAN: DNS:securityd.local, IP:192.168.215.78
Valid: 1 year
Signed by: glassdome-ca

# Client Certificates (per agent/service)
CN: agent-proxmox-01
Valid: 90 days
Signed by: glassdome-ca
```

**Configuration:**

```yaml
auth:
  certificate_validation:
    enabled: true
    
    # CA certificate for validating clients
    ca_cert: /etc/glassdome/certs/ca.crt
    
    # Allowed certificate Common Names (supports wildcards)
    allowed_cns:
      - agent-*
      - overseer-*
      - api-server
    
    # Certificate fingerprint pinning (optional, high-security)
    pinned_fingerprints:
      - "sha256:abc123..."
      - "sha256:def456..."
    
    # Revocation checking
    check_crl: true
    crl_url: http://ca.glassdome.local/crl.pem
```

### 3. Short-Lived Tokens (Ephemeral Workloads)

For CI/CD pipelines, serverless functions, or short-lived containers:

```
┌─────────────────────────────────────────────────────────────────┐
│                   TOKEN-BASED AUTH FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Admin                    Daemon                  Ephemeral Job │
│    │                        │                          │        │
│    │  Create bootstrap      │                          │        │
│    │  token for job-123     │                          │        │
│    │───────────────────────▶│                          │        │
│    │                        │                          │        │
│    │  Bootstrap token:      │                          │        │
│    │  bt_abc123...          │                          │        │
│    │◀───────────────────────│                          │        │
│    │                        │                          │        │
│    │  Pass token to job     │                          │        │
│    │  (env var, secret vol) │                          │        │
│    │────────────────────────┼─────────────────────────▶│        │
│    │                        │                          │        │
│    │                        │  Exchange bootstrap      │        │
│    │                        │  for session token       │        │
│    │                        │◀─────────────────────────│        │
│    │                        │                          │        │
│    │                        │  Session token:          │        │
│    │                        │  st_xyz789...            │        │
│    │                        │  (valid 1 hour)          │        │
│    │                        │─────────────────────────▶│        │
│    │                        │                          │        │
│    │                        │  GET /secrets/...        │        │
│    │                        │◀─────────────────────────│        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Token Types:**

| Type | TTL | Use Case | Renewable |
|------|-----|----------|-----------|
| Bootstrap | 5 minutes | Initial auth | No |
| Session | 8 hours | Normal operations | Yes |
| Admin | 1 hour | Administrative tasks | Yes |

## Authorization

### Secret-Level Access Control

Fine-grained control over which clients can access which secrets:

```yaml
authorization:
  # Default policy (if no specific rule matches)
  default_policy: deny
  
  # Access rules
  rules:
    # All agents can access platform credentials
    - name: platform-access
      clients:
        - "agent-*"
      secrets:
        - "proxmox_*"
        - "esxi_*"
        - "aws_*"
        - "azure_*"
      actions: [read]
    
    # Only specific agents can access AI keys
    - name: ai-access
      clients:
        - "agent-research"
        - "agent-rag"
      secrets:
        - "openai_api_key"
        - "anthropic_api_key"
      actions: [read]
    
    # Admin can do everything
    - name: admin-full
      clients:
        - "admin-*"
      secrets:
        - "*"
      actions: [read, write, delete, rotate]
```

### Role-Based Access Control (RBAC)

```yaml
roles:
  agent:
    description: "Standard agent role"
    permissions:
      - secrets:read:platform_*
      - secrets:read:mail_*
  
  ai-agent:
    description: "AI-enabled agent role"
    inherits: agent
    permissions:
      - secrets:read:openai_*
      - secrets:read:anthropic_*
  
  admin:
    description: "Full administrative access"
    permissions:
      - secrets:*
      - admin:*

client_roles:
  agent-proxmox-01: agent
  agent-research: ai-agent
  admin-cli: admin
```

## Audit Logging

### Log Format

```json
{
  "timestamp": "2024-11-25T10:55:26.123456Z",
  "event_id": "evt_abc123",
  "event_type": "secret_access",
  "client": {
    "id": "agent-proxmox-01",
    "pid": 12345,
    "exe": "/usr/bin/python3",
    "ip": "192.168.215.100"
  },
  "action": "get_secret",
  "resource": "proxmox_password",
  "result": "success",
  "metadata": {
    "session_id": "sess_xyz789",
    "request_id": "req_def456"
  }
}
```

### Logged Events

| Event Type | Description | Logged Fields |
|------------|-------------|---------------|
| `auth_attempt` | Authentication attempt | client, method, result |
| `auth_success` | Successful auth | client, session_id |
| `auth_failure` | Failed auth | client, reason |
| `secret_access` | Secret retrieved | client, secret_key, result |
| `secret_denied` | Access denied | client, secret_key, reason |
| `admin_action` | Admin operation | client, action, details |
| `session_expired` | Session timeout | session_id |
| `rate_limited` | Rate limit hit | client, endpoint |

### Log Security

```yaml
audit:
  # Local log file
  file:
    path: /var/log/glassdome/securityd-audit.log
    rotation: daily
    retention: 90 days
    permissions: 0600
  
  # Remote syslog (tamper-resistant)
  syslog:
    enabled: true
    server: syslog.glassdome.local
    port: 514
    protocol: tcp  # Use TCP for reliability
    facility: auth
    
  # SIEM integration (optional)
  siem:
    enabled: false
    endpoint: https://siem.example.com/api/events
    api_key_secret: siem_api_key
```

## Comparison to Alternatives

| Feature | Securityd | HashiCorp Vault | K8s Secrets | AWS Secrets Manager |
|---------|-----------|-----------------|-------------|---------------------|
| **Deployment** | Single binary | Complex (HA requires Consul) | K8s only | AWS only |
| **Cost** | Free | Free (OSS) / Paid (Enterprise) | Free | $0.40/secret/month |
| **Local access** | Unix socket | HTTP API | Volume mount | AWS API |
| **Process validation** | Yes | No | No | IAM roles |
| **mTLS** | Yes | Yes | No | No |
| **Audit logging** | Yes | Yes (Enterprise) | Limited | Yes |
| **Secret rotation** | Manual | Auto (Enterprise) | Manual | Auto |
| **Air-gapped** | Yes | Yes | Yes | No |
| **Complexity** | Low | High | Medium | Low |

### When to Use Securityd vs. Alternatives

**Use Securityd when:**
- Lab/development environment
- Air-gapped networks
- Simple deployment requirements
- Custom process validation needed
- Cost-sensitive

**Use HashiCorp Vault when:**
- Enterprise environment
- Complex secret hierarchies
- Dynamic secrets (database credentials)
- Multiple teams/tenants
- Compliance requirements (SOC2, PCI)

**Use Kubernetes Secrets when:**
- Pure Kubernetes environment
- Simple secret needs
- Already using K8s RBAC

**Use AWS Secrets Manager when:**
- AWS-native infrastructure
- Automatic rotation needed
- Integration with AWS services

## Security Hardening Checklist

### Daemon Host

- [ ] Run daemon as dedicated user (not root)
- [ ] Use systemd with `ProtectSystem=strict`
- [ ] Disable core dumps (`ulimit -c 0`)
- [ ] Lock memory to prevent swapping (`mlock()`)
- [ ] Firewall: only allow necessary ports
- [ ] SELinux/AppArmor profile (optional)

### Network

- [ ] Bind HTTPS to specific interface (not 0.0.0.0)
- [ ] Use TLS 1.3 only (or minimum TLS 1.2)
- [ ] Require client certificates
- [ ] Certificate pinning for known clients
- [ ] Rate limiting enabled

### Secrets

- [ ] Master key never written to disk while daemon running
- [ ] Secrets encrypted at rest (AES-256-GCM)
- [ ] Key derivation uses PBKDF2 (100k+ iterations)
- [ ] Secrets cleared from memory on shutdown

### Logging

- [ ] Audit logging enabled
- [ ] Logs sent to remote syslog (tamper-resistant)
- [ ] Log rotation configured
- [ ] Secret values never logged

### Operations

- [ ] Regular certificate rotation (90 days)
- [ ] Master key rotation procedure documented
- [ ] Incident response plan for key compromise
- [ ] Backup and recovery tested

