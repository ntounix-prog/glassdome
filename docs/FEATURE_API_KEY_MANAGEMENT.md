# Feature: API Key Management System

## Overview

Glassdome needs to manage API keys for multiple external services:
- **Virtualization Platforms** (Proxmox, VMware, Hyper-V)
- **Cloud Providers** (Azure, AWS, Google Cloud)
- **AI Services** (OpenAI, Anthropic, LangChain)
- **Container Orchestration** (Kubernetes, Docker Swarm)
- **Monitoring Services** (Prometheus, Grafana)

## Current State

❌ **NOT IMPLEMENTED**

Currently:
- Only Proxmox credentials supported
- Stored in `.env` file (plaintext)
- No UI for management
- No encryption
- No multi-user support
- No credential rotation

## Proposed Feature

### User Interface

**Web UI for Managing Credentials:**

```
┌─────────────────────────────────────────────────┐
│  Credential Manager                      [ + ]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  Virtualization Platforms                       │
│  ├─ Proxmox Server 1          [Edit] [Delete]  │
│  │   Host: 192.168.1.100                       │
│  │   Status: ✅ Connected                       │
│  │                                              │
│  └─ Proxmox Server 2          [Edit] [Delete]  │
│      Host: proxmox.cloud.com                   │
│      Status: ❌ Connection Failed               │
│                                                 │
│  Cloud Providers                                │
│  ├─ Azure Production         [Edit] [Delete]   │
│  │   Subscription: prod-sub-001                │
│  │   Status: ✅ Connected                       │
│  │                                              │
│  └─ AWS Development          [Edit] [Delete]   │
│      Account: dev-account                      │
│      Status: ✅ Connected                       │
│                                                 │
│  AI Services                                    │
│  ├─ OpenAI GPT-4            [Edit] [Delete]   │
│  │   Model: gpt-4-turbo                        │
│  │   Usage: $45.32 / $100.00                   │
│  │   Status: ✅ Active                          │
│  │                                              │
│  ├─ Anthropic Claude        [Edit] [Delete]   │
│  │   Model: claude-3-opus                      │
│  │   Status: ✅ Active                          │
│  │                                              │
│  └─ LangChain               [Edit] [Delete]   │
│      Status: ✅ Active                          │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Add Credential Flow

```
┌─────────────────────────────────────────────────┐
│  Add New Credential                             │
├─────────────────────────────────────────────────┤
│                                                 │
│  Service Type:                                  │
│  ┌───────────────────────────────────────┐     │
│  │ [Proxmox] [Azure] [AWS] [OpenAI]      │     │
│  │ [Anthropic] [Kubernetes] [Other]      │     │
│  └───────────────────────────────────────┘     │
│                                                 │
│  ─────────── Proxmox Configuration ──────────  │
│                                                 │
│  Name:          [Proxmox Production     ]      │
│  Host:          [192.168.1.100          ]      │
│  User:          [root@pam               ]      │
│                                                 │
│  Authentication:                                │
│  ○ Password     ● API Token                    │
│                                                 │
│  Token Name:    [glassdome-token        ]      │
│  Token Value:   [••••••••••••••••••••••• ]     │
│                                                 │
│  [ Test Connection ]                            │
│  ✅ Connection successful!                      │
│                                                 │
│           [Cancel]  [Save Credential]           │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Backend Implementation

**Database Schema:**

```sql
CREATE TABLE credentials (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL,  -- proxmox, azure, aws, openai, etc.
    
    -- Encrypted credentials
    encrypted_data TEXT NOT NULL,  -- JSON blob, encrypted
    encryption_key_id UUID NOT NULL,
    
    -- Metadata
    config JSONB,  -- Service-specific config (host, region, etc.)
    status VARCHAR(20) DEFAULT 'active',
    last_tested_at TIMESTAMP,
    last_test_status BOOLEAN,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- For rotating credentials
    
    UNIQUE(user_id, name)
);

CREATE TABLE credential_usage (
    id UUID PRIMARY KEY,
    credential_id UUID REFERENCES credentials(id),
    used_by VARCHAR(255),  -- agent_id, deployment_id, etc.
    used_at TIMESTAMP DEFAULT NOW(),
    success BOOLEAN,
    error TEXT
);
```

**API Endpoints:**

```python
# Credential Management
POST   /api/credentials              # Add new credential
GET    /api/credentials              # List all credentials
GET    /api/credentials/{id}         # Get credential details
PUT    /api/credentials/{id}         # Update credential
DELETE /api/credentials/{id}         # Delete credential
POST   /api/credentials/{id}/test    # Test credential
POST   /api/credentials/{id}/rotate  # Rotate credential

# Credential Templates
GET    /api/credentials/templates/{service_type}  # Get credential form
```

**Credential Storage (Encrypted):**

```python
from cryptography.fernet import Fernet
import json

class CredentialManager:
    """Secure credential storage and retrieval"""
    
    def __init__(self, encryption_key: str):
        self.cipher = Fernet(encryption_key.encode())
    
    def store_credential(self, credential_data: dict) -> str:
        """Encrypt and store credential"""
        json_data = json.dumps(credential_data)
        encrypted = self.cipher.encrypt(json_data.encode())
        return encrypted.decode()
    
    def retrieve_credential(self, encrypted_data: str) -> dict:
        """Decrypt and retrieve credential"""
        decrypted = self.cipher.decrypt(encrypted_data.encode())
        return json.loads(decrypted.decode())
    
    def test_credential(self, credential_id: str, service_type: str) -> bool:
        """Test if credential works"""
        cred = self.get_credential(credential_id)
        
        if service_type == "proxmox":
            client = ProxmoxClient(**cred)
            return await client.test_connection()
        elif service_type == "azure":
            client = AzureClient(**cred)
            return await client.test_connection()
        # ... etc
```

### Configuration Templates

**Proxmox:**
```json
{
  "service_type": "proxmox",
  "required_fields": [
    {"name": "host", "type": "text", "label": "Proxmox Host"},
    {"name": "user", "type": "text", "label": "Username", "default": "root@pam"},
    {
      "name": "auth_method", 
      "type": "select", 
      "label": "Authentication",
      "options": ["password", "api_token"]
    }
  ],
  "conditional_fields": {
    "auth_method=password": [
      {"name": "password", "type": "password", "label": "Password"}
    ],
    "auth_method=api_token": [
      {"name": "token_name", "type": "text", "label": "Token Name"},
      {"name": "token_value", "type": "password", "label": "Token Secret"}
    ]
  }
}
```

**Azure:**
```json
{
  "service_type": "azure",
  "required_fields": [
    {"name": "subscription_id", "type": "text", "label": "Subscription ID"},
    {"name": "client_id", "type": "text", "label": "Client ID"},
    {"name": "client_secret", "type": "password", "label": "Client Secret"},
    {"name": "tenant_id", "type": "text", "label": "Tenant ID"}
  ]
}
```

**AWS:**
```json
{
  "service_type": "aws",
  "required_fields": [
    {"name": "access_key_id", "type": "text", "label": "Access Key ID"},
    {"name": "secret_access_key", "type": "password", "label": "Secret Access Key"},
    {"name": "region", "type": "select", "label": "Default Region", "options": ["us-east-1", "us-west-2", "eu-west-1"]}
  ]
}
```

**OpenAI:**
```json
{
  "service_type": "openai",
  "required_fields": [
    {"name": "api_key", "type": "password", "label": "API Key"},
    {
      "name": "model", 
      "type": "select", 
      "label": "Default Model",
      "options": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
    },
    {"name": "organization", "type": "text", "label": "Organization ID (optional)", "required": false}
  ]
}
```

**Anthropic:**
```json
{
  "service_type": "anthropic",
  "required_fields": [
    {"name": "api_key", "type": "password", "label": "API Key"},
    {
      "name": "model",
      "type": "select",
      "label": "Default Model",
      "options": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]
    }
  ]
}
```

### Security Features

1. **Encryption at Rest**
   - All credentials encrypted in database
   - Separate encryption key (not in repo)
   - Key rotation support

2. **Encryption in Transit**
   - HTTPS only for API calls
   - TLS for database connections

3. **Access Control**
   - User-level credential isolation
   - Role-based access control
   - Audit logging

4. **Credential Rotation**
   - Automated rotation reminders
   - API for programmatic rotation
   - Version history

5. **Testing & Validation**
   - Test credentials before saving
   - Periodic health checks
   - Alert on credential failures

### CLI Commands

```bash
# Add credential
glassdome credentials add proxmox \
  --name "Production Proxmox" \
  --host 192.168.1.100 \
  --token-name glassdome-token \
  --token-value <secret>

# List credentials
glassdome credentials list

# Test credential
glassdome credentials test <name>

# Update credential
glassdome credentials update <name> --host new-host.com

# Delete credential
glassdome credentials delete <name>

# Rotate credential
glassdome credentials rotate <name>
```

### Environment Variables (Migration Path)

**Current (.env):**
```bash
PROXMOX_HOST=...
PROXMOX_TOKEN_NAME=...
PROXMOX_TOKEN_VALUE=...
```

**Future (backward compatible):**
```bash
# New: Single encryption key for all credentials
GLASSDOME_ENCRYPTION_KEY=...

# Old env vars still work for backward compatibility
# But UI-managed credentials take precedence
```

### Migration Strategy

1. **Phase 1:** Database schema + API endpoints
2. **Phase 2:** CLI for credential management
3. **Phase 3:** Web UI for credential management
4. **Phase 4:** Migrate .env credentials to database
5. **Phase 5:** Deprecate .env credentials

## Use Cases

### Use Case 1: Multi-Cloud Deployment

User wants to deploy same lab to Proxmox AND Azure:

```python
# User configures in UI:
# - Proxmox credentials (on-prem)
# - Azure credentials (cloud)

# Then deploys lab to both:
POST /api/labs/deploy
{
  "lab_spec": {...},
  "targets": [
    {"platform": "proxmox", "credential_id": "uuid-1"},
    {"platform": "azure", "credential_id": "uuid-2"}
  ]
}
```

### Use Case 2: AI-Powered Agent

Agent needs OpenAI API to make intelligent decisions:

```python
# Agent retrieves credential
openai_cred = credential_manager.get_credential(
    user_id=user.id,
    service_type="openai"
)

# Use credential
client = OpenAI(api_key=openai_cred['api_key'])
response = client.chat.completions.create(...)
```

### Use Case 3: Team Collaboration

Multiple users, shared credentials:

```python
# Admin creates shared credential
credential_manager.create_credential(
    name="Team Proxmox",
    service_type="proxmox",
    shared=True,
    accessible_by=["team-red"]
)

# Team members can use it
creds = credential_manager.get_accessible_credentials(
    user_id=user.id
)
```

## Priority

**Medium-High Priority**

Required for:
- ✅ Multi-platform support (Azure, AWS)
- ✅ AI agent functionality (OpenAI, Anthropic)
- ✅ Multi-user deployments
- ✅ Production security

Current workaround:
- ⚠️ .env file works for single Proxmox
- ⚠️ Not suitable for production

## Implementation Estimate

- **Database schema:** 4 hours
- **Backend API:** 16 hours
- **Encryption/security:** 8 hours
- **CLI commands:** 4 hours
- **Web UI:** 24 hours
- **Testing:** 8 hours
- **Documentation:** 4 hours

**Total:** ~68 hours (~2 weeks)

## Dependencies

- `cryptography` - For credential encryption
- `sqlalchemy` - For database ORM
- Database migration system (Alembic)
- Frontend credential management UI

## Related Features

- User authentication system
- Role-based access control
- Audit logging
- Credential rotation automation
- Multi-tenant support

## References

- [Vault by HashiCorp](https://www.vaultproject.io/) - Secret management
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Azure Key Vault](https://azure.microsoft.com/en-us/products/key-vault/)

## Notes

- Consider using external secret manager (Vault) for production
- Need secure key storage for encryption key
- Should support credential templates for common services
- Consider OAuth2 for some services
- Need credential expiration/rotation policies

