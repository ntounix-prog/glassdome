"""
Secrets Backend module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, List
import os
import logging

logger = logging.getLogger(__name__)


class SecretsBackend(ABC):
    """Abstract base class for secrets backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a secret value by key."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: str) -> bool:
        """Set a secret value."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    def list_keys(self) -> List[str]:
        """List all secret keys."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available and configured."""
        pass


class EnvSecretsBackend(SecretsBackend):
    """
    Environment variable secrets backend.
    
    Simple backend that reads secrets from environment variables.
    Good for containers, CI/CD, and simple deployments.
    
    Key mapping: openai_api_key -> OPENAI_API_KEY
    """
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
    
    def _env_key(self, key: str) -> str:
        """Convert secret key to environment variable name."""
        env_key = key.upper()
        if self.prefix:
            env_key = f"{self.prefix}_{env_key}"
        return env_key
    
    def get(self, key: str) -> Optional[str]:
        return os.environ.get(self._env_key(key))
    
    def set(self, key: str, value: str) -> bool:
        # Can't persist env vars, but can set for current process
        os.environ[self._env_key(key)] = value
        return True
    
    def delete(self, key: str) -> bool:
        env_key = self._env_key(key)
        if env_key in os.environ:
            del os.environ[env_key]
            return True
        return False
    
    def list_keys(self) -> List[str]:
        # Return known secret keys that exist in env
        known_keys = [
            'openai_api_key', 'anthropic_api_key', 'proxmox_password',
            'aws_secret_access_key', 'azure_client_secret', 'esxi_password'
        ]
        return [k for k in known_keys if self.get(k)]
    
    def is_available(self) -> bool:
        return True  # Always available


class LocalSecretsBackend(SecretsBackend):
    """
    Local secrets backend using keyring + encrypted file.
    
    Wraps the existing SecretsManager for backward compatibility.
    Best for development and single-server deployments.
    """
    
    def __init__(self):
        self._manager = None
    
    def _get_manager(self):
        if self._manager is None:
            from glassdome.core.secrets import SecretsManager
            self._manager = SecretsManager()
        return self._manager
    
    def get(self, key: str) -> Optional[str]:
        return self._get_manager().get_secret(key)
    
    def set(self, key: str, value: str) -> bool:
        return self._get_manager().set_secret(key, value)
    
    def delete(self, key: str) -> bool:
        return self._get_manager().delete_secret(key)
    
    def list_keys(self) -> List[str]:
        return self._get_manager().list_secrets()
    
    def is_available(self) -> bool:
        try:
            self._get_manager()
            return True
        except Exception:
            return False


class VaultSecretsBackend(SecretsBackend):
    """
    HashiCorp Vault secrets backend.
    
    For multi-server production deployments.
    Supports AppRole authentication for automated systems.
    
    Environment variables:
        VAULT_ADDR: Vault server URL (e.g., https://vault.internal:8200)
        VAULT_ROLE_ID: AppRole role ID
        VAULT_SECRET_ID: AppRole secret ID
        VAULT_MOUNT_POINT: KV secrets engine mount (default: glassdome)
    """
    
    def __init__(self, 
                 addr: str = None,
                 role_id: str = None,
                 secret_id: str = None,
                 mount_point: str = "glassdome",
                 verify: bool = None):
        self.addr = addr or os.environ.get("VAULT_ADDR")
        self.role_id = role_id or os.environ.get("VAULT_ROLE_ID")
        self.secret_id = secret_id or os.environ.get("VAULT_SECRET_ID")
        self.mount_point = mount_point or os.environ.get("VAULT_MOUNT_POINT", "glassdome")
        # Check VAULT_SKIP_VERIFY env var (default to verifying)
        if verify is None:
            skip_verify = os.environ.get("VAULT_SKIP_VERIFY", "false").lower() in ("true", "1", "yes")
            self.verify = not skip_verify
        else:
            self.verify = verify
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            try:
                import hvac
            except ImportError:
                raise ImportError("hvac package required for Vault backend: pip install hvac")
            
            self._client = hvac.Client(url=self.addr, verify=self.verify, timeout=5)
            
            # Authenticate with AppRole
            if self.role_id and self.secret_id:
                self._client.auth.approle.login(
                    role_id=self.role_id,
                    secret_id=self.secret_id
                )
            
            if not self._client.is_authenticated():
                raise RuntimeError("Failed to authenticate with Vault")
        
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        try:
            client = self._get_client()
            result = client.secrets.kv.v2.read_secret_version(
                path=key,
                mount_point=self.mount_point
            )
            return result['data']['data'].get('value')
        except Exception as e:
            logger.debug(f"Vault get({key}) failed: {e}")
            return None
    
    def set(self, key: str, value: str) -> bool:
        try:
            client = self._get_client()
            client.secrets.kv.v2.create_or_update_secret(
                path=key,
                secret={'value': value},
                mount_point=self.mount_point
            )
            return True
        except Exception as e:
            logger.error(f"Vault set({key}) failed: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            client = self._get_client()
            client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=key,
                mount_point=self.mount_point
            )
            return True
        except Exception as e:
            logger.error(f"Vault delete({key}) failed: {e}")
            return False
    
    def list_keys(self) -> List[str]:
        try:
            client = self._get_client()
            result = client.secrets.kv.v2.list_secrets(
                path="",
                mount_point=self.mount_point
            )
            return result['data']['keys']
        except Exception as e:
            logger.debug(f"Vault list_keys() failed: {e}")
            return []
    
    def is_available(self) -> bool:
        if not self.addr:
            return False
        try:
            self._get_client()
            return True
        except Exception:
            return False


class ChainedSecretsBackend(SecretsBackend):
    """
    Chains multiple backends together.
    
    Reads from backends in order until a value is found.
    Writes to the first writable backend.
    
    Default chain: env -> vault -> local
    """
    
    def __init__(self, backends: List[SecretsBackend] = None):
        if backends is None:
            # Default chain based on what's available
            self.backends = []
            
            # Environment always first (overrides everything)
            self.backends.append(EnvSecretsBackend())
            
            # Vault if configured
            vault = VaultSecretsBackend()
            if vault.is_available():
                self.backends.append(vault)
            
            # Local as fallback
            self.backends.append(LocalSecretsBackend())
        else:
            self.backends = backends
    
    def get(self, key: str) -> Optional[str]:
        for backend in self.backends:
            try:
                value = backend.get(key)
                if value is not None:
                    return value
            except Exception as e:
                logger.debug(f"Backend {backend.__class__.__name__} failed for {key}: {e}")
                continue
        return None
    
    def set(self, key: str, value: str) -> bool:
        # Write to first backend that supports writes
        for backend in self.backends:
            if isinstance(backend, EnvSecretsBackend):
                continue  # Skip env for writes
            try:
                if backend.set(key, value):
                    return True
            except Exception:
                continue
        return False
    
    def delete(self, key: str) -> bool:
        # Delete from all backends
        success = False
        for backend in self.backends:
            try:
                if backend.delete(key):
                    success = True
            except Exception:
                continue
        return success
    
    def list_keys(self) -> List[str]:
        # Merge keys from all backends
        all_keys = set()
        for backend in self.backends:
            try:
                all_keys.update(backend.list_keys())
            except Exception:
                continue
        return sorted(all_keys)
    
    def is_available(self) -> bool:
        return any(b.is_available() for b in self.backends)


# Global backend instance
_backend: Optional[SecretsBackend] = None


def get_secrets_backend(backend_type: str = None) -> SecretsBackend:
    """
    Get the configured secrets backend.
    
    Args:
        backend_type: Force a specific backend type:
            - "env": Environment variables only
            - "local": Keyring/encrypted file
            - "vault": HashiCorp Vault
            - "chain": Chained (default, tries all)
            - None: Auto-detect from SECRETS_BACKEND env var
    
    Returns:
        SecretsBackend instance
    """
    global _backend
    
    if _backend is not None and backend_type is None:
        return _backend
    
    backend_type = backend_type or os.environ.get("SECRETS_BACKEND", "chain")
    
    if backend_type == "env":
        _backend = EnvSecretsBackend()
    elif backend_type == "local":
        _backend = LocalSecretsBackend()
    elif backend_type == "vault":
        _backend = VaultSecretsBackend()
    elif backend_type == "chain":
        _backend = ChainedSecretsBackend()
    else:
        raise ValueError(f"Unknown secrets backend: {backend_type}")
    
    logger.info(f"Using secrets backend: {_backend.__class__.__name__}")
    return _backend


def reset_backend():
    """Reset the global backend (for testing)."""
    global _backend
    _backend = None


# =============================================================================
# Simple get_secret() - VAULT ONLY
# =============================================================================

_vault_client: Optional[VaultSecretsBackend] = None


def get_secret(key: str, default: str = None) -> Optional[str]:
    """
    Get a secret from Vault. VAULT ONLY - no env fallback.
    
    This is the primary function all code should use to access secrets.
    
    Args:
        key: Secret key (e.g., 'openai_api_key', 'aws_secret_access_key')
        default: Default value if secret not found (use sparingly)
    
    Returns:
        Secret value or default
    
    Raises:
        RuntimeError: If Vault is not configured or unavailable
    """
    global _vault_client
    
    if _vault_client is None:
        _vault_client = VaultSecretsBackend()
        if not _vault_client.is_available():
            raise RuntimeError(
                "Vault is not available. Ensure VAULT_ADDR, VAULT_ROLE_ID, "
                "and VAULT_SECRET_ID are set in .env"
            )
    
    value = _vault_client.get(key)
    if value is None and default is not None:
        logger.debug(f"Secret '{key}' not found, using default")
        return default
    
    return value


def set_secret(key: str, value: str) -> bool:
    """
    Store a secret in Vault.
    
    Args:
        key: Secret key
        value: Secret value
    
    Returns:
        True if successful
    """
    global _vault_client
    
    if _vault_client is None:
        _vault_client = VaultSecretsBackend()
    
    return _vault_client.set(key, value)


def list_secrets() -> List[str]:
    """
    List all secrets in Vault.
    
    Returns:
        List of secret keys
    """
    global _vault_client
    
    if _vault_client is None:
        _vault_client = VaultSecretsBackend()
    
    return _vault_client.list_keys()

