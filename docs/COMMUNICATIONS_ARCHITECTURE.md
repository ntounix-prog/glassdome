# Communications Architecture - Bidirectional Gateway Pattern

**Status:** Design Approved  
**Priority:** Phase 2 (Post-Demo)  
**Category:** Infrastructure, Security, Enterprise Features

---

## Overview

Bidirectional communication system enabling team-to-AI and AI-to-team interactions via Slack and Email. Implements security isolation, audit logging, and RBAC for enterprise deployments.

---

## Architecture Pattern: Communications Container

### Core Concept
Single "Coms Container" acts as bidirectional gateway between team and Glassdome agents.

```
Team (Slack/Email) ↔ Coms Container ↔ Glassdome Agents
```

### Why Gateway Pattern (Not Direct Integration)

**Security:**
- API credentials isolated to single container
- Agents can't spam external services if compromised
- Single point for credential rotation
- Network segmentation (Coms in DMZ, agents internal)

**Compliance:**
- Centralized audit trail (HIPAA, SOC2)
- Message filtering (block passwords/keys before sending)
- Retention policies (7d, 30d, 7yr for audit)
- Approval workflows for critical actions

**Operational:**
- Rate limiting (prevent alert storms)
- Retry logic with exponential backoff
- Dead letter queue for failed messages
- Priority queuing (critical alerts first)
- Graceful degradation (queue if Slack down)

**Flexibility:**
- Add channels without touching agents (Teams, SMS, PagerDuty)
- Multi-tenant routing (different Slack workspaces)
- A/B test notification strategies

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Team Interfaces                                         │
│  - Slack: @mentions, DMs, slash commands, buttons       │
│  - Email: commands@yourdomain.com                        │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  COMS CONTAINER (Bidirectional Gateway)                  │
│                                                          │
│  INBOUND (Team → AI):                                   │
│  ├─ Slack Bot (Socket Mode - no public IP needed)       │
│  ├─ Mailcow API Monitor (10s polling or webhook)        │
│  ├─ Command Parser (intent detection)                   │
│  ├─ RBAC Engine (permission checks)                     │
│  └─ State Manager (conversation context via Redis)      │
│                                                          │
│  OUTBOUND (AI → Team):                                  │
│  ├─ Slack API (rich messages, buttons, threads)         │
│  ├─ Mailcow API (send email)                            │
│  └─ Audit Logger (all messages to DB)                   │
│                                                          │
│  MIDDLEWARE:                                             │
│  ├─ Sensitive Data Filter (regex for passwords/keys)    │
│  ├─ Rate Limiter (token bucket, 10 msg/min)            │
│  └─ Message Queue (Redis for persistence)               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Command Router / AI Brain                               │
│  - Parse intent from natural language                    │
│  - Route to appropriate agent                            │
│  - Maintain conversation state                           │
│  - Ask clarifying questions                              │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┬─────────────┐
         ▼             ▼             ▼             ▼
    ┌────────┐   ┌─────────┐   ┌────────┐   ┌──────────┐
    │ Ubuntu │   │ Windows │   │ Reaper │   │Orchestr- │
    │ Agent  │   │  Agent  │   │ Agent  │   │  ator    │
    └────────┘   └─────────┘   └────────┘   └──────────┘
```

---

## Communication Channels

### 1. Slack Integration

**Implementation: Socket Mode (Recommended)**
- WebSocket connection (no public IP needed)
- Suitable for on-premise/air-gapped
- Real-time bidirectional

**Capabilities:**
- Listen for @mentions
- Respond to DMs
- Slash commands: `/glassdome deploy ubuntu`
- Interactive buttons: "Approve", "Deny", "Investigate"
- Rich formatting: code blocks, tables, charts
- Threaded conversations
- File uploads (logs, reports)

**Message Types:**
```
Deployment Status:
🚀 Deploying: Enterprise Web Application
   Progress: [▓▓▓▓▓░░░░░] 5/9 VMs (55%)
   ETA: 3 minutes

Error Alerts:
⚠️ Issue Detected: VM 3 (web-server)
   Problem: Boot failure after 3 attempts
   Action: Rebuilding from template
   [Button: View Logs] [Button: SSH Console]

Resolutions:
✅ Resolved: VM 3 (web-server)
   Fix: Disk space exhausted, extended to 40GB
   Status: Online (192.168.3.35)
   Duration: 4 minutes

Game Events:
🎯 Flag Captured: web-server-sqli
   Team: Red Team
   Time: 12 minutes into game
   Current Standings: Red (1), Blue (0), Green (0)
```

**Authentication:**
```yaml
slack_auth:
  workspace_id: T12345
  bot_token: xoxb-your-bot-token
  socket_mode_token: xapp-your-socket-token
  
  authorized_channels:
    - C67890  # #cyber-range-ops
    - C11111  # #glassdome-alerts
    
  authorized_users:
    - U12345  # John Smith (admin)
    - U67890  # Sarah Jones (operator)
```

---

### 2. Email Integration (Mailcow)

**Implementation: Mailcow REST API**
- Faster than IMAP (10s polling vs 30s)
- API key authentication
- Auto-provision mailboxes
- Webhook support (if available)

**Auto-Created Mailboxes:**
```
glassdome@yourdomain.com
├─ Main command interface
├─ Bidirectional (send & receive)
└─ Quota: 1GB

commands@yourdomain.com
├─ Inbound only (team sends commands)
├─ Strict RBAC
└─ Auto-archive after 7 days

alerts@yourdomain.com
├─ Outbound only (Glassdome sends alerts)
├─ High volume
└─ Auto-archive after 30 days

reports@yourdomain.com
├─ Outbound only (daily/weekly summaries)
├─ HTML formatted, charts
└─ Permanent retention

audit@yourdomain.com
├─ Outbound only (compliance logs)
├─ Every action logged
└─ 7-year retention
```

**Auto-Created Aliases (Smart Routing):**
```
deploy@yourdomain.com → glassdome@ (routes to deployment agent)
status@yourdomain.com → glassdome@ (routes to monitoring agent)
troubleshoot@yourdomain.com → glassdome@ (routes to AI troubleshooter)
help@yourdomain.com → glassdome@ (returns help documentation)
```

**Mailcow API Operations:**
```python
# Auto-setup on Coms Container first boot
POST /api/v1/add/mailbox
POST /api/v1/add/alias
POST /api/v1/add/filter

# Runtime operations
GET /api/v1/get/mailbox/{email}/messages  # Fetch new (10s poll)
POST /api/v1/add/mail                     # Send email
DELETE /api/v1/delete/mailbox/{id}        # Cleanup
```

**Email Command Formats:**

*Structured:*
```
To: deploy@yourdomain.com
Subject: Ubuntu VM
Body:
  PLATFORM: Proxmox
  IP: 192.168.3.60
  CPU: 4
  RAM: 8GB
  DISK: 100GB
```

*Natural Language (AI parsed):*
```
To: glassdome@yourdomain.com
Subject: Need a test server
Body:
  Can you spin up a Windows Server 2022 VM on Azure 
  for testing? Need it in East US region, cheap instance.
```

---

## Conversation Patterns

### 1. Simple Status Query
```
Team (Slack): "@glassdome status VM 114"
AI: "VM 114 (ubuntu-powerhouse) - Running
     - IP: 192.168.3.50
     - Uptime: 2 hours
     - CPU: 12%, RAM: 15%
     - Services: Minecraft server (active)"
```

### 2. Multi-Step Deployment
```
Team: "@glassdome deploy Windows Server 2022"
AI: "Where should I deploy?"
    [Button: Proxmox] [Button: ESXi] [Button: AWS] [Button: Azure]

Team: *clicks AWS*
AI: "Which region?"
    [Dropdown: us-east-1, us-west-2, eu-west-1...]

Team: *selects us-east-1*
AI: "What instance type?"
    [Dropdown: t3.medium, t3.large, m5.xlarge...]

Team: *selects t3.medium*
AI: "👍 Deploying... I'll notify you when ready."

[5 min later]
AI: "✅ Windows Server ready!
     - IP: 54.123.45.67
     - Username: Administrator
     - Password: [sent via DM]"
```

### 3. Approval Workflow (2 AM Autonomous)
```
[VM fails to boot]
AI → Slack: "⚠️ VM 115 won't boot after 3 attempts.
             Options:
             1️⃣ Rebuild from template (auto, 10 min)
             2️⃣ Investigate manually
             3️⃣ Ignore
             
             React or I'll auto-rebuild in 5 min"

Team: *reacts with 1️⃣*
AI: "👍 Rebuilding..."
[10 min later]
AI: "✅ VM 115 online at 192.168.3.55"
```

### 4. Troubleshooting Conversation
```
Team: "@glassdome why is ESXi slow?"
AI: "ESXi 192.168.3.3:
     - CPU: 85% (high)
     - RAM: 92% (critical)
     - Top consumer: VM 113 (Windows Update 40% CPU)
     
     Should I wait for update to finish?"

Team: "Yes, monitor for 30 min"
AI: "👍 Will alert if CPU >80% in 30 min"
```

---

## State Management (Redis)

**Why Needed:**
Multi-turn conversations require context preservation.

**Schema:**
```json
{
  "conversation_id": "slack-U12345-1732176000",
  "user": "john@company.com",
  "user_id": "U12345",
  "channel": "C67890",
  "platform": "slack",
  "state": "awaiting_ip_address",
  "context": {
    "action": "deploy",
    "os": "ubuntu",
    "platform": "proxmox",
    "cpu": 4,
    "ram": "8GB"
  },
  "created_at": 1732176000,
  "expires_at": 1732176900,
  "message_history": [
    {"role": "user", "content": "deploy ubuntu"},
    {"role": "assistant", "content": "To which platform?"},
    {"role": "user", "content": "proxmox"}
  ]
}
```

**Expiration:** 15 minutes (configurable)

---

## Security & RBAC

### Role-Based Access Control

**Role Definitions:**
```yaml
roles:
  admin:
    permissions:
      - deploy_vm_any
      - destroy_vm_any
      - access_all_platforms
      - inject_vulnerabilities
      - view_audit_logs
    
  operator:
    permissions:
      - deploy_vm_proxmox
      - deploy_vm_esxi
      - restart_vm
      - view_status
    
  viewer:
    permissions:
      - view_status
      - view_logs

users:
  john@company.com:
    role: admin
    slack_id: U12345
    email_verified: true
    
  sarah@company.com:
    role: operator
    slack_id: U67890
    platforms: [proxmox]  # restricted
    
  external@partner.com:
    role: viewer
    allowed_channels: [C67890]
```

**Authorization Flow:**
```
1. Message received from john@company.com
2. Lookup user → role: admin
3. Parse command → "destroy VM 114"
4. Check permission: admin.destroy_vm_any ✅
5. Check environment: VM 114 = production ⚠️
6. Require confirmation:
   "⚠️ VM 114 is PRODUCTION. Confirm with 'yes destroy' (60s)"
7. Team confirms → Execute
8. Log to audit@yourdomain.com
```

### Sensitive Data Filtering

**Patterns to Redact:**
```python
REDACT_PATTERNS = [
    r'password[=:]\s*\S+',
    r'token[=:]\s*\S+',
    r'api[_-]?key[=:]\s*\S+',
    r'secret[=:]\s*\S+',
    r'\d{16}',  # Credit cards
    r'-----BEGIN .* KEY-----',  # SSH/SSL keys
    r'xox[baprs]-[a-zA-Z0-9-]+',  # Slack tokens
]

# Before sending to Slack/Email:
message = redact_sensitive_data(message)
# "password=supersecret123" → "password=[REDACTED]"
```

### Container Hardening

**Coms Container Security:**
```dockerfile
# Run as non-root
USER coms:coms

# Read-only filesystem
--read-only --tmpfs /tmp

# No shell
CMD ["/app/coms-server"]

# Network policy
- Outbound: Slack API, Mailcow only
- Inbound: Redis, agents only

# Secrets from vault
ENV SLACK_TOKEN=${VAULT:slack/bot-token}
ENV MAILCOW_API_KEY=${VAULT:mailcow/api-key}
```

---

## Message Routing & Queuing

### Message Queue (Redis Streams)

**Queue Structure:**
```
messages:outbound:critical   (priority 1)
messages:outbound:normal     (priority 2)
messages:outbound:low        (priority 3)
messages:inbound             (commands from team)
messages:dlq                 (failed after 3 retries)
```

**Message Schema:**
```json
{
  "id": "msg-1732176000-001",
  "timestamp": 1732176000,
  "severity": "error",
  "priority": 1,
  "source": "ubuntu-installer-agent",
  "title": "VM Deployment Failed",
  "message": "VM 115 failed to boot after 3 attempts",
  "context": {
    "vm_id": 115,
    "ip": "192.168.3.55",
    "platform": "proxmox"
  },
  "channels": ["slack", "email"],
  "actions": [
    {"label": "Retry", "command": "retry_deploy 115"},
    {"label": "Investigate", "command": "get_logs 115"}
  ]
}
```

### Rate Limiting

**Token Bucket Algorithm:**
```
Slack: 10 messages/minute
Email: 50 messages/minute
SMS: 5 messages/hour (if implemented)
```

**Alert Storm Prevention:**
```
If >10 similar messages in 60s:
  - Send summary: "⚠️ 15 VMs failed in last 60s"
  - Attach CSV with details
  - Suppress individual alerts
```

---

## Audit & Compliance

### Audit Log Schema
```json
{
  "id": "audit-1732176000-001",
  "timestamp": "2025-11-21T08:00:00Z",
  "user": "john@company.com",
  "user_id": "U12345",
  "action": "deploy_vm",
  "platform": "slack",
  "command": "deploy ubuntu to proxmox 192.168.3.60",
  "result": "success",
  "vm_id": 116,
  "ip": "192.168.3.60",
  "approval_required": false,
  "approver": null,
  "duration_ms": 12450
}
```

### Retention Policies
```
Commands: 7 days
Alerts: 30 days
Reports: 1 year
Audit logs: 7 years (compliance)
Sensitive data: Immediately redacted
```

### Compliance Features
- **HIPAA:** Encryption at rest/transit, audit logs, access controls
- **SOC2:** Centralized logging, change tracking, approval workflows
- **GDPR:** Right to erasure, data minimization, consent logging

---

## Weekly/Daily Reports

### Scheduled Email Reports

**Weekly Summary (Monday 8 AM):**
```
From: reports@yourdomain.com
To: team@yourdomain.com
Subject: Weekly Glassdome Report - Nov 18-24

📊 DEPLOYMENTS
Total: 47 VMs
├─ Proxmox: 23
├─ ESXi: 12
├─ AWS: 8
└─ Azure: 4

✅ SUCCESS RATE: 94.7% (45/47)
❌ Failed: 2 (network timeouts)

👥 TOP USERS
1. john@company.com (23 deploys)
2. sarah@company.com (15 deploys)

💰 COST
Total: $127.45
├─ AWS: $89.30
├─ Azure: $38.15
└─ On-prem: $0

🎯 GAMES COMPLETED: 3
├─ Enterprise Web App: 6h 23m, 12 players
├─ AD Pentesting: 4h 10m, 8 players
└─ Cloud Misconfiguration: 2h 45m, 6 players

[Full report: report-2025-11-24.pdf]
```

---

## Implementation Notes

### Technology Stack
- **Language:** Python 3.11+
- **Slack SDK:** `slack-bolt` (Socket Mode)
- **Mailcow:** REST API client
- **Queue:** Redis Streams
- **State:** Redis with TTL
- **Auth:** JWT + RBAC engine
- **Logging:** Structured JSON to Elasticsearch

### Deployment
- **Container:** Docker (single service)
- **Orchestration:** Docker Compose or Kubernetes
- **Scaling:** Horizontal (multiple Coms containers)
- **High Availability:** Redis Sentinel, multiple replicas

### Configuration
```yaml
coms_container:
  slack:
    enabled: true
    socket_mode: true
    token: ${VAULT:slack/bot-token}
    
  mailcow:
    enabled: true
    url: https://mailcow.yourdomain.com
    api_key: ${VAULT:mailcow/api-key}
    polling_interval: 10s
    
  security:
    rbac_file: /config/rbac.yaml
    redact_patterns: /config/redact.txt
    require_approval: [destroy_vm, inject_vulnerability]
    
  rate_limits:
    slack: 10/min
    email: 50/min
    
  audit:
    enabled: true
    retention_days: 2555  # 7 years
    email: audit@yourdomain.com
```

---

## RAG Query Patterns

**When to reference this document:**

- "How do we integrate Slack?"
- "What's the email architecture?"
- "How does team communicate with AI?"
- "What's the approval workflow?"
- "How do we handle sensitive data in messages?"
- "What RBAC do we implement?"
- "How do we prevent alert storms?"
- "What compliance features exist?"
- "How do scheduled reports work?"
- "What's the Mailcow integration?"
- "How do we route commands?"
- "What's the conversation state management?"

---

## Related Documents
- `docs/OPERATIONAL_AUTOMATION.md` - Late-night autonomous operation
- `docs/AGENTS.md` - Agent architecture
- `docs/ARCHITECTURE.md` - Overall system design
- `docs/session_logs/CRITICAL_LESSONS_*.md` - Implementation learnings

---

**Last Updated:** 2025-11-21  
**Approved By:** User (Strategic Planning)  
**Implementation Status:** Design Complete, Phase 2 Queue

