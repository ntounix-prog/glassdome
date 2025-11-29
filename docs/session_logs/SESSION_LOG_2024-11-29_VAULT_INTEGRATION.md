# Session Log: 2024-11-29 - HashiCorp Vault Integration & Secrets Centralization

## Summary

Completed full HashiCorp Vault integration for centralized secrets management. Consolidated database and Vault onto single production server. Fixed WireGuard tunnel issue affecting email delivery. Configured SMTP email sending with authentication.

## Version

**Glassdome v0.5.1** - HashiCorp Vault integration

## Work Completed

### 1. HashiCorp Vault Installation & Configuration

**Server:** glassdome-prod-db (192.168.3.7)

**Installation Steps:**
- Installed HashiCorp Vault on Ubuntu 22.04
- Configured file storage backend at `/opt/vault/data`
- Generated self-signed TLS certificate for HTTPS
- Initialized Vault with 5 unseal keys (threshold: 3)
- Enabled AppRole authentication for application access
- Created `glassdome` KV v2 secrets engine

**Vault Configuration:**
```hcl
storage "file" {
  path = "/opt/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 0
  tls_cert_file = "/etc/vault.d/cert.pem"
  tls_key_file  = "/etc/vault.d/key.pem"
}
```

**AppRole Setup:**
- Created `glassdome` policy with full access to secrets engine
- Generated Role ID and Secret ID for application authentication
- Configured in `.env` for automatic connection

### 2. Database Consolidation

**Before:** Two PostgreSQL servers
- 192.168.3.26 (old database)
- 192.168.3.7 (glassdome-prod-db)

**After:** Single consolidated server
- 192.168.3.7 - PostgreSQL + HashiCorp Vault

**Changes:**
- Updated `DATABASE_URL` in `.env` to point to 192.168.3.7
- Reset `glassdome` database user password
- Created admin user `brett` with level 100 (superuser)

### 3. Secrets Migration to Vault

**Migrated 60+ secrets** from `.env` to Vault:

| Category | Secrets |
|----------|---------|
| Proxmox | 12 (hosts, users, passwords, tokens for both nodes) |
| ESXi | 3 (host, user, password) |
| Network Devices | 9 (Nexus 3064, Cisco 3850, Ubiquiti) |
| Updock/Guacamole | 9 (host, user, passwords, ports) |
| Database | 3 (host, user, password) |
| AI APIs | 4 (OpenAI, Anthropic, XAI, Perplexity) |
| Cloud | 3 (AWS keys, Azure secret) |
| Email | 8 (Mailcow API, SMTP, mailbox passwords) |
| TrueNAS | 2 (user, API key) |
| Security | 1 (JWT signing key) |
| VM Defaults | 2 (Linux/Windows passwords) |

### 4. Code Refactoring for Vault

**Files Modified:**

1. **`glassdome/core/config.py`**
   - Added 15+ new secret mappings (usernames + passwords)
   - Added Settings fields for Updock, TrueNAS, Database, Email
   - Secret mappings now include both usernames and passwords

2. **`glassdome/core/secrets_backend.py`**
   - Fixed SSL verification to respect `VAULT_SKIP_VERIFY=true`
   - Added `verify` parameter to VaultSecretsBackend

3. **`glassdome/registry/agents/unifi_agent.py`**
   - Changed from direct `os.getenv()` to `settings.xxx`

4. **`.env`**
   - Changed `SECRETS_BACKEND=env` to `SECRETS_BACKEND=vault`
   - Added Vault connection parameters

### 5. Email Configuration

**Mailcow Integration:**
- Verified Mailcow API connectivity at `https://mail.xisx.org`
- Created `overseer@xisx.org` mailbox for Overseer AI
- Reset password for `glassdome-ai@xisx.org`
- Tested SMTP sending with authentication

**Email Accounts:**
| Account | Purpose |
|---------|---------|
| glassdome-ai@xisx.org | General automation |
| overseer@xisx.org | Overseer AI notifications |

**SMTP Test:** Successfully sent email to ntounix@gmail.com

### 6. WireGuard Tunnel Fix

**Problem:** Email delivery failing - mxwest tunnel was down for 2+ days

**Diagnosis:**
- Rome (192.168.3.99) = WireGuard gateway
- mxwest (44.254.59.166 - AWS EC2) = Primary MX
- mxwest WireGuard handshake: "2 days, 20 hours ago" - tunnel DOWN

**Resolution:**
- Rebooted mxwest EC2 instance via AWS API
- WireGuard tunnel restored
- Mail queue flushed successfully

**Prevention:**
- Created `/usr/local/bin/wireguard-healthcheck.sh` on mxwest and mxeast
- Cron job every 5 minutes to check tunnel and auto-restart if down
- Logs to `/var/log/wireguard-healthcheck.log`

### 7. RBAC Verification

**Admin Account:**
- Username: `brett`
- Role: `admin`
- Level: 100 (full access)
- Superuser: ✅
- Active: ✅

**RBAC Levels:**
- Level 100 = Admin (full access)
- Level 75 = Architect (design/deploy)
- Level 50 = Engineer (operate)
- Level 25 = Observer (read-only)

## Files Changed

### New Files
- `docs/session_logs/SESSION_LOG_2024-11-29_VAULT_INTEGRATION.md` (this file)

### Modified Files
- `glassdome/core/config.py` - Secret mappings, new fields
- `glassdome/core/secrets_backend.py` - SSL verification fix
- `glassdome/registry/agents/unifi_agent.py` - Use settings
- `.env` - Vault configuration

## Infrastructure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│  glassdome-prod-db (192.168.3.7)                            │
│  ├─ PostgreSQL 14.19                                        │
│  │   └─ Database: glassdome                                 │
│  │   └─ Tables: 19                                          │
│  │   └─ Users table (RBAC)                                  │
│  └─ HashiCorp Vault                                         │
│      └─ UI: https://192.168.3.7:8200                        │
│      └─ Engine: glassdome (KV v2)                           │
│      └─ Secrets: 60+                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Email Flow                                                 │
│                                                             │
│  glassdome-ai@xisx.org ──SMTP 587──→ mooker (mail.xisx.org) │
│                                           ↓                 │
│                                      rome (WG gateway)      │
│                                           ↓                 │
│                              ┌────────────┴────────────┐    │
│                              ↓                         ↓    │
│                         mxwest (AWS)              mxeast    │
│                              ↓                              │
│                          Internet                           │
└─────────────────────────────────────────────────────────────┘
```

## Verification Results

```
Vault Connection:
  ✅ Connected to https://192.168.3.7:8200
  ✅ AppRole authentication successful
  ✅ 60+ secrets accessible

Secrets Loading:
  ✅ secret_key (JWT signing)
  ✅ proxmox_user / proxmox_password
  ✅ esxi_user / esxi_password
  ✅ openai_api_key
  ✅ anthropic_api_key
  ✅ mail_api
  ✅ glassdome_ai_password
  ✅ updock_user / updock_password
  ✅ cisco_3850_user / cisco_3850_password
  ✅ ubiquiti_gateway_user / ubiquiti_api_key

Email:
  ✅ SMTP authentication working
  ✅ Email delivered to ntounix@gmail.com

WireGuard:
  ✅ mxwest tunnel restored
  ✅ Health check installed
  ✅ Mail queue cleared

Backend:
  ✅ API healthy on port 8011
```

## Security Notes

### Vault Unseal Keys
- 5 keys generated (threshold: 3 required)
- **MUST** be stored securely offline
- Vault requires unsealing after restart

### Root Token
- Used for initial setup only
- Should be revoked after creating admin policies

### SSL Certificates
- Self-signed certificate for Vault HTTPS
- `VAULT_SKIP_VERIFY=true` in `.env` (internal network)

## Next Steps

1. ~~Test RBAC levels with different user accounts~~
2. Consider Vault auto-unseal (AWS KMS or transit)
3. Create Vault backup/restore procedure
4. Document Vault disaster recovery
5. Consider revoking Vault root token

## Quick Reference

```bash
# Check Vault status
ssh ubuntu@192.168.3.7 "vault status"

# Unseal Vault (if sealed)
ssh ubuntu@192.168.3.7 "vault operator unseal <key1>"
ssh ubuntu@192.168.3.7 "vault operator unseal <key2>"
ssh ubuntu@192.168.3.7 "vault operator unseal <key3>"

# List secrets
vault kv list glassdome/

# Get a secret
vault kv get glassdome/proxmox_password

# Test from Glassdome
cd /opt/glassdome && source venv/bin/activate
python -c "
from dotenv import load_dotenv
load_dotenv()
from glassdome.core.config import settings
print(f'Proxmox user: {settings.proxmox_user}')
print(f'Proxmox password: {settings.proxmox_password[:5]}...')
"

# Check WireGuard health
ssh -i ~/.ssh/rome_key nomad@192.168.3.99 "sudo wg show"

# Flush mail queue
ssh -i ~/.ssh/rome_key nomad@192.168.3.99 "sudo postqueue -f"
```

## Lessons Learned

1. **SSL Verification:** Self-signed certs require `verify=False` in hvac client
2. **WireGuard Monitoring:** Tunnels can silently fail - health checks essential
3. **Vault on DB Server:** Consolidating reduces infrastructure complexity
4. **Secret Mappings:** Include both usernames AND passwords in config.py
5. **Email Relay:** Authentication required for SMTP (no open relay)

