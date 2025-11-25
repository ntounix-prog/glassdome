# Secrets Access Flow

## How Agents and Functions Access Secrets

This document explains how secrets stored in the `SecretsManager` are accessed by agents, functions, and other parts of the Glassdome system.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    SecretsManager                            │
│  (OS Keyring or Encrypted File)                             │
│  - Stores encrypted secrets                                 │
│  - Master key encryption                                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ get_secret(key)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Settings Class                            │
│  (Pydantic BaseSettings)                                      │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. Load from .env file                                │  │
│  │ 2. Load from environment variables                    │  │
│  │ 3. _load_secrets_from_manager() validator            │  │
│  │    → Overrides with SecretsManager values            │  │
│  └───────────────────────────────────────────────────────┘  │
│  Fields:                                                     │
│  - openai_api_key                                            │
│  - anthropic_api_key                                         │
│  - proxmox_password                                          │
│  - google_search_api_key                                     │
│  - etc.                                                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ settings.openai_api_key
                       │ settings.proxmox_password
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Agents / Functions / API Routes                 │
│  - UbuntuInstallerAgent                                      │
│  - MailcowAgent                                              │
│  - OverseerEntity                                            │
│  - API endpoints                                             │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Flow

### 1. Settings Initialization

When `Settings()` is instantiated (or the singleton `settings` is imported):

```python
from glassdome.core.config import settings
```

**What happens:**
1. Pydantic loads values from `.env` file (if exists)
2. Pydantic loads values from environment variables (`os.environ`)
3. **`_load_secrets_from_manager()` validator runs** (this is the key step!)

### 2. Secrets Manager Integration

The `_load_secrets_from_manager()` method in `Settings` class:

```python
@model_validator(mode='after')
def _load_secrets_from_manager(self):
    """Override field values with secrets from secrets manager if available."""
    secrets = get_secrets_manager()
    
    secret_mappings = {
        'openai_api_key': 'openai_api_key',
        'anthropic_api_key': 'anthropic_api_key',
        'proxmox_password': 'proxmox_password',
        'google_search_api_key': 'google_search_api_key',
        # ... etc
    }
    
    for field_name, secret_key in secret_mappings.items():
        secret_value = secrets.get_secret(secret_key)
        if secret_value:
            setattr(self, field_name, secret_value)  # Override with secret!
    
    return self
```

**Priority Order:**
1. **SecretsManager** (highest priority - most secure)
2. Environment variables
3. `.env` file (lowest priority)

### 3. Agent Access Pattern

Agents and functions access secrets through the `settings` object:

```python
# Example: UbuntuInstallerAgent
from glassdome.core.config import settings

def get_ubuntu_agent(proxmox_instance: str = "01"):
    config = settings.get_proxmox_config(proxmox_instance)
    # config['password'] comes from settings.proxmox_password
    # which was loaded from SecretsManager!
    
    proxmox_client = ProxmoxClient(
        host=config['host'],
        password=config['password']  # ← From SecretsManager
    )
```

### 4. Real-World Examples

#### Example 1: Proxmox Agent
```python
# glassdome/api/ubuntu.py
from glassdome.core.config import settings

def get_ubuntu_agent(proxmox_instance: str = "01"):
    config = settings.get_proxmox_config(proxmox_instance)
    # settings.proxmox_password was loaded from SecretsManager
    # if it exists there, otherwise falls back to .env
```

#### Example 2: Overseer Entity
```python
# glassdome/overseer/entity.py
from glassdome.core.config import Settings

class OverseerEntity:
    def __init__(self, settings: Settings = None):
        self.settings = settings or Settings()  # ← Loads secrets!
    
    @property
    def proxmox(self):
        return ProxmoxClient(
            password=self.settings.proxmox_password  # ← From SecretsManager
        )
```

#### Example 3: AI API Keys
```python
# Any agent that needs OpenAI
from glassdome.core.config import settings

# settings.openai_api_key is automatically loaded from SecretsManager
# if it exists there, otherwise from .env or environment
api_key = settings.openai_api_key
```

## Key Points

1. **Automatic Loading**: Secrets are loaded automatically when `Settings()` is instantiated
2. **Priority**: SecretsManager > Environment Variables > `.env` file
3. **No Code Changes Needed**: Existing code that uses `settings.openai_api_key` automatically gets secrets from SecretsManager
4. **Backward Compatible**: If a secret isn't in SecretsManager, it falls back to `.env` or environment variables
5. **Transparent**: Agents don't need to know where the secret came from - they just use `settings.field_name`

## Adding New Secrets

To add a new secret that agents can access:

1. **Add field to Settings class** (`glassdome/core/config.py`):
   ```python
   class Settings(BaseSettings):
       my_new_api_key: Optional[str] = None
   ```

2. **Add to secret mappings** in `_load_secrets_from_manager()`:
   ```python
   secret_mappings = {
       # ... existing mappings
       'my_new_api_key': 'my_new_api_key',
   }
   ```

3. **Store secret** via CLI or web interface:
   ```bash
   glassdome secrets set my_new_api_key "your-secret-value"
   ```

4. **Use in agents**:
   ```python
   from glassdome.core.config import settings
   api_key = settings.my_new_api_key  # Automatically loaded!
   ```

## Troubleshooting

### Secret not being loaded?

1. **Check if secret exists**:
   ```bash
   glassdome secrets list
   ```

2. **Verify mapping** in `config.py`:
   - Is the field name in `Settings` class?
   - Is it in `secret_mappings` dict?

3. **Check priority**:
   - If `.env` has the value, SecretsManager won't override it (by design)
   - Remove from `.env` to use SecretsManager value

4. **Verify Settings instantiation**:
   - Make sure you're using `settings` from `glassdome.core.config`
   - Not creating a new `Settings()` instance without the validator

## Security Notes

- Secrets are **never** logged or printed
- SecretsManager uses OS-native keyring when available
- Fallback to encrypted file with master key
- Master key is never stored in plaintext
- Secrets are decrypted on-demand, not cached in memory

