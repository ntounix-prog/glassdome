"""
Security module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Cache the backend type
_backend_type: Optional[str] = None
_env_loaded: bool = False


def _load_env_file() -> None:
    """Load .env file into os.environ (once)."""
    global _env_loaded
    if _env_loaded:
        return
    _env_loaded = True
    
    from glassdome.core.paths import ENV_FILE
    if ENV_FILE.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(ENV_FILE, override=False)  # Don't override existing env vars
            logger.debug(f"Loaded .env from {ENV_FILE}")
        except ImportError:
            # Fallback: manual parse
            with open(ENV_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key not in os.environ:  # Don't override
                            os.environ[key] = value


def get_backend_type() -> str:
    """Get the configured secrets backend type."""
    global _backend_type
    if _backend_type is None:
        _backend_type = os.environ.get("SECRETS_BACKEND", "env")
        logger.debug(f"Secrets backend: {_backend_type}")
    return _backend_type


def get_secret(key: str) -> Optional[str]:
    """
    Get a secret value.
    
    Args:
        key: Secret key name (e.g., 'openai_api_key')
        
    Returns:
        Secret value or None if not found
    """
    backend_type = get_backend_type()
    
    if backend_type == "env":
        # Load .env file first (if not already loaded)
        _load_env_file()
        # Then read from environment
        return os.environ.get(key.upper())
    
    elif backend_type == "vault":
        # Future: HashiCorp Vault
        from glassdome.core.secrets_backend import VaultSecretsBackend
        vault = VaultSecretsBackend()
        return vault.get(key)
    
    elif backend_type == "local":
        # Legacy: encrypted local store
        from glassdome.core.secrets import get_secrets_manager
        return get_secrets_manager().get_secret(key)
    
    else:
        raise ValueError(f"Unknown SECRETS_BACKEND: {backend_type}")


def ensure_security_context() -> None:
    """
    Ensure secrets are accessible. Called at process startup.
    
    For env backend: No-op (env vars are always available)
    For local backend: Tries to initialize session from cache
    For vault backend: Verifies vault connectivity
    """
    backend_type = get_backend_type()
    
    if backend_type == "env":
        # Environment variables are always available
        # Just verify we have at least some secrets
        test_keys = ['OPENAI_API_KEY', 'DATABASE_URL', 'PROXMOX_PASSWORD']
        if not any(os.environ.get(k) for k in test_keys):
            logger.warning("No secrets found in environment. Check your .env file.")
        return
    
    elif backend_type == "vault":
        # Verify Vault is accessible
        from glassdome.core.secrets_backend import VaultSecretsBackend
        vault = VaultSecretsBackend()
        if not vault.is_available():
            raise RuntimeError(
                "Vault backend configured but not available.\n"
                "Set VAULT_ADDR and VAULT_TOKEN environment variables."
            )
        return
    
    elif backend_type == "local":
        # Try to initialize session from cache (legacy behavior)
        from .session import get_session
        session = get_session()
        if not session.is_initialized():
            success = session.initialize(interactive=False, use_cache=True)
            if not success:
                raise RuntimeError(
                    "Local secrets backend requires initialized session.\n"
                    "Run: ./glassdome_start"
                )
        return


def get_secure_settings() -> Any:
    """
    Get Settings instance with secrets populated.
    
    Returns:
        Settings instance
    """
    ensure_security_context()
    
    # Settings will use get_secret() internally which respects SECRETS_BACKEND
    from glassdome.core.config import Settings
    return Settings()
