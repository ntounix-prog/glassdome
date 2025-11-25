# Secrets Management System

## Overview

Glassdome now uses a secure secrets management system that stores sensitive information (passwords, tokens, API keys) in OS-native keyring or encrypted file storage, instead of plaintext in `.env` files.

## Features

- **OS-Native Keyring**: Uses `keyring` library for secure storage (Linux: Secret Service, macOS: Keychain, Windows: Credential Manager)
- **Encrypted Fallback**: If keyring is unavailable, falls back to encrypted file storage using Fernet encryption
- **Backward Compatible**: Still reads from `.env` if secrets aren't in secure store
- **Master Key Protection**: All secrets encrypted with a master key (derived from user password)
- **CLI Management**: Easy-to-use commands for managing secrets

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Settings Class                         │
│  (pydantic-settings with model_validator)                │
└────────────────────┬──────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  SecretsManager       │
         │  - get_secret()       │
         │  - set_secret()       │
         │  - delete_secret()    │
         └───────┬───────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
   ┌─────────┐    ┌──────────────┐
   │ Keyring │    │ Encrypted    │
   │ (OS)    │    │ File (fallback)│
   └─────────┘    └──────────────┘
```

## Usage

### Migration from .env

Migrate existing secrets from `.env` to secure storage:

```bash
# Using CLI
glassdome secrets migrate

# Or using script
python scripts/migrate_secrets.py
```

This will:
1. Read all secrets from `.env`
2. Prompt for master password (first time only)
3. Store secrets securely
4. Keep `.env` intact for backward compatibility

### Setting Secrets

```bash
# Set a secret (will prompt for value)
glassdome secrets set proxmox_password

# Set with value
glassdome secrets set proxmox_token_value --value "your-token-here"
```

### Listing Secrets

```bash
# List all stored secret keys
glassdome secrets list
```

### Getting Secrets

```bash
# Get a secret value (use with caution - displays in terminal)
glassdome secrets get proxmox_password
```

### Deleting Secrets

```bash
# Delete a secret
glassdome secrets delete proxmox_password
```

## Supported Secrets

The following secrets are automatically managed:

- `proxmox_password` - Proxmox password
- `proxmox_token_value` - Proxmox API token
- `proxmox_token_value_02`, `proxmox_token_value_03`, etc. - Multi-instance tokens
- `esxi_password` - ESXi password
- `azure_client_secret` - Azure client secret
- `aws_secret_access_key` - AWS secret access key
- `openai_api_key` - OpenAI API key
- `anthropic_api_key` - Anthropic API key
- `mail_api` - Mailcow API bearer token
- `secret_key` - JWT secret key

## Code Integration

### Settings Class

The `Settings` class automatically checks secrets manager first, then falls back to `.env`:

```python
from glassdome.core.config import settings

# These automatically check secrets manager first
password = settings.proxmox_password
token = settings.proxmox_token_value
api_key = settings.openai_api_key
```

### Direct Access

For programmatic access:

```python
from glassdome.core.secrets import get_secrets_manager

secrets = get_secrets_manager()
value = secrets.get_secret("proxmox_password")
secrets.set_secret("proxmox_token_value", "new-token")
```

## Setup Wizard

The Proxmox setup wizard (`scripts/setup/setup_proxmox.py`) now automatically stores secrets in the secure store instead of `.env`.

## Security Considerations

1. **Master Password**: Choose a strong master password. You'll need it to access secrets.
2. **Keyring Backend**: On Linux, ensure Secret Service (GNOME Keyring/KWallet) is running.
3. **Fallback Storage**: Encrypted files stored in `~/.glassdome/secrets.encrypted`
4. **Backup**: Master key encrypted file: `~/.glassdome/master_key.enc`
5. **.env Files**: After migration, you can remove secrets from `.env` but keep non-secret config.

## Troubleshooting

### Keyring Not Available

If keyring fails, the system automatically falls back to encrypted file storage. This is transparent to the application.

### Master Password Forgotten

If you forget the master password:
1. Delete `~/.glassdome/master_key.enc`
2. Re-run migration or set secrets again
3. You'll be prompted for a new master password

### Testing

Run the test suite:

```bash
python scripts/test_secrets_manager.py
```

## Migration Path

1. **Phase 1 (Current)**: Secrets manager implemented, backward compatible with `.env`
2. **Phase 2 (Future)**: Option to remove secrets from `.env` after verification
3. **Phase 3 (Future)**: Support for HashiCorp Vault, AWS Secrets Manager, etc.

## Files

- `glassdome/core/secrets.py` - SecretsManager implementation
- `glassdome/core/config.py` - Settings class with secrets integration
- `glassdome/cli.py` - CLI commands for secrets management
- `scripts/migrate_secrets.py` - Migration script
- `scripts/test_secrets_manager.py` - Test suite

