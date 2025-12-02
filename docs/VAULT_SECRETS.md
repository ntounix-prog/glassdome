# Glassdome Vault Secrets Reference

All secrets are now stored in HashiCorp Vault. This document lists all required secrets.

## Required Environment Variables (NOT secrets)

These go in `.env` - they bootstrap the Vault connection:

```bash
# Vault Connection (REQUIRED)
VAULT_ADDR=https://192.168.3.7:8200
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id
VAULT_SKIP_VERIFY=true  # For self-signed certs
VAULT_MOUNT_POINT=glassdome

# Backend Mode (REQUIRED)
SECRETS_BACKEND=vault
```

## Secrets to Store in Vault

Store these secrets in Vault at `glassdome/data/<key>`:

### Platform Credentials

#### AWS
- `aws_access_key_id` - AWS IAM access key
- `aws_secret_access_key` - AWS IAM secret key

#### Proxmox
- `proxmox_password` - Proxmox root/user password
- `proxmox_root_password` - Proxmox root password (for SSH)
- `proxmox_token_value` - Proxmox API token value
- `proxmox_token_value_02` - Proxmox instance 02 token (if applicable)

#### ESXi
- `esxi_password` - ESXi host password

#### Azure
- `azure_client_secret` - Azure service principal secret

### API Keys

#### LLM Providers
- `openai_api_key` - OpenAI API key
- `anthropic_api_key` - Anthropic API key

#### External Services
- `ubiquiti_api_key` - Unifi controller API key
- `mailcow_api_key` - Mailcow API key
- `overseer_mail_password` - SMTP password for Glassdome mail

### Application Secrets
- `secret_key` - JWT signing key (generated automatically if not set)

## Setting Secrets in Vault

### Using Vault CLI

```bash
# AWS credentials
vault kv put glassdome/data/aws_access_key_id value="AKIAXXXXXXXX"
vault kv put glassdome/data/aws_secret_access_key value="your-secret-key"

# Proxmox
vault kv put glassdome/data/proxmox_password value="your-proxmox-password"

# LLM Keys
vault kv put glassdome/data/openai_api_key value="sk-..."
vault kv put glassdome/data/anthropic_api_key value="sk-ant-..."
```

### Using Glassdome API

```bash
# Via API
curl -X POST http://localhost:8000/api/secrets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"key": "openai_api_key", "value": "sk-..."}'
```

## Architecture

```
┌─────────────────┐
│   Application   │
│    (backend)    │
└────────┬────────┘
         │
         │ get_secret('aws_access_key_id')
         ▼
┌─────────────────┐
│ secrets_backend │
│   (Vault only)  │
└────────┬────────┘
         │
         │ hvac client
         ▼
┌─────────────────┐
│  HashiCorp      │
│     Vault       │
│ (192.168.3.7)   │
└─────────────────┘
```

## Migration from .env

If you previously had secrets in `.env`, migrate them to Vault:

1. Note all secret values from your `.env`
2. Store each in Vault using the CLI or API
3. Remove secret values from `.env` (keep non-secrets like CORS_ORIGINS)
4. Set `SECRETS_BACKEND=vault` in `.env`
5. Restart the backend

## Troubleshooting

### Vault Connection Failed
- Ensure `VAULT_ADDR` is correct
- Check network connectivity to Vault
- Verify `VAULT_SKIP_VERIFY=true` if using self-signed certs

### Secret Not Found
- Check secret exists: `vault kv get glassdome/data/<key>`
- Verify mount point matches `VAULT_MOUNT_POINT`

### SSL Errors
- Set `VAULT_SKIP_VERIFY=true` for self-signed certificates
- Or add Vault CA to system trust store

