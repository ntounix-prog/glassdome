"""
Vault Integration for Central Authentication

Provides centralized secret management for auth:
- JWT signing keys
- Service-to-service tokens
- API keys for external services

Configuration:
    VAULT_ADDR: Vault server URL
    VAULT_ROLE_ID: AppRole role ID (for service auth)
    VAULT_SECRET_ID: AppRole secret ID
    VAULT_AUTH_MOUNT: Auth secrets mount point (default: glassdome/auth)
"""

import os
import logging
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# Cache for secrets to avoid repeated Vault calls
_jwt_secret_cache: Optional[str] = None


def get_vault_client():
    """Get configured Vault client."""
    try:
        import hvac
    except ImportError:
        logger.debug("hvac not installed, Vault integration disabled")
        return None
    
    vault_addr = os.environ.get("VAULT_ADDR")
    if not vault_addr:
        return None
    
    # Respect VAULT_SKIP_VERIFY for self-signed certs
    skip_verify = os.environ.get("VAULT_SKIP_VERIFY", "false").lower() in ("true", "1", "yes")
    
    # Set short timeout to avoid long waits on connection failures
    client = hvac.Client(
        url=vault_addr,
        verify=not skip_verify,
        timeout=5  # 5 second timeout
    )
    
    # Try AppRole auth first (for services)
    role_id = os.environ.get("VAULT_ROLE_ID")
    secret_id = os.environ.get("VAULT_SECRET_ID")
    
    if role_id and secret_id:
        try:
            client.auth.approle.login(role_id=role_id, secret_id=secret_id)
            logger.info("Authenticated with Vault via AppRole")
            return client
        except Exception as e:
            logger.warning(f"Vault AppRole auth failed: {e}")
    
    # Try token auth (for dev/CLI)
    token = os.environ.get("VAULT_TOKEN")
    if token:
        client.token = token
        if client.is_authenticated():
            logger.info("Authenticated with Vault via token")
            return client
    
    logger.debug("No valid Vault authentication found")
    return None


def get_jwt_secret_from_vault() -> Optional[str]:
    """
    Get JWT signing secret from Vault.
    
    Looks in: glassdome/auth/jwt_secret
    
    Returns:
        JWT secret string or None if not available
    """
    global _jwt_secret_cache
    
    if _jwt_secret_cache:
        return _jwt_secret_cache
    
    client = get_vault_client()
    if not client:
        return None
    
    mount_point = os.environ.get("VAULT_AUTH_MOUNT", "glassdome")
    
    try:
        result = client.secrets.kv.v2.read_secret_version(
            path="auth/jwt_secret",
            mount_point=mount_point
        )
        secret = result['data']['data'].get('value')
        if secret:
            _jwt_secret_cache = secret
            logger.info("Loaded JWT secret from Vault")
            return secret
    except Exception as e:
        logger.debug(f"Could not read JWT secret from Vault: {e}")
    
    return None


def store_jwt_secret_in_vault(secret: str) -> bool:
    """
    Store JWT signing secret in Vault.
    
    Used for initial setup or key rotation.
    """
    client = get_vault_client()
    if not client:
        logger.error("Cannot store JWT secret: Vault not available")
        return False
    
    mount_point = os.environ.get("VAULT_AUTH_MOUNT", "glassdome")
    
    try:
        client.secrets.kv.v2.create_or_update_secret(
            path="auth/jwt_secret",
            secret={'value': secret},
            mount_point=mount_point
        )
        logger.info("Stored JWT secret in Vault")
        
        # Clear cache so next read gets fresh value
        global _jwt_secret_cache
        _jwt_secret_cache = None
        
        return True
    except Exception as e:
        logger.error(f"Failed to store JWT secret in Vault: {e}")
        return False


def get_service_token(service_name: str) -> Optional[str]:
    """
    Get a service-to-service authentication token from Vault.
    
    Used for internal service communication (e.g., Reaper -> WhiteKnight).
    
    Args:
        service_name: Name of the service (e.g., "reaper", "whiteknight")
        
    Returns:
        Service token or None
    """
    client = get_vault_client()
    if not client:
        return None
    
    mount_point = os.environ.get("VAULT_AUTH_MOUNT", "glassdome")
    
    try:
        result = client.secrets.kv.v2.read_secret_version(
            path=f"services/{service_name}/token",
            mount_point=mount_point
        )
        return result['data']['data'].get('value')
    except Exception as e:
        logger.debug(f"Could not read service token for {service_name}: {e}")
        return None


def rotate_jwt_secret() -> Optional[str]:
    """
    Generate and store a new JWT signing secret.
    
    Returns the new secret, or None if rotation failed.
    """
    import secrets
    
    # Generate a strong random secret
    new_secret = secrets.token_urlsafe(64)
    
    if store_jwt_secret_in_vault(new_secret):
        logger.warning("JWT secret rotated - all existing tokens are now invalid!")
        return new_secret
    
    return None


@lru_cache()
def get_auth_config() -> dict:
    """
    Get authentication configuration.
    
    Priority:
    1. Vault (if configured and reachable)
    2. Environment variables
    3. Settings defaults
    
    Returns:
        Dict with jwt_secret, algorithm, expire_minutes
    """
    from glassdome.core.config import settings
    
    # Skip Vault entirely if not configured properly
    vault_addr = os.environ.get("VAULT_ADDR")
    role_id = os.environ.get("VAULT_ROLE_ID")
    secret_id = os.environ.get("VAULT_SECRET_ID")
    
    jwt_secret = None
    if vault_addr and role_id and secret_id:
        # Only try Vault if all credentials are configured
        jwt_secret = get_jwt_secret_from_vault()
    
    # Fall back to settings/env
    if not jwt_secret:
        jwt_secret = settings.secret_key
        logger.debug("Using JWT secret from settings (not Vault)")
    
    return {
        "jwt_secret": jwt_secret,
        "algorithm": settings.jwt_algorithm,
        "expire_minutes": settings.access_token_expire_minutes,
    }


def clear_auth_cache():
    """Clear cached auth configuration (for testing/rotation)."""
    global _jwt_secret_cache
    _jwt_secret_cache = None
    get_auth_config.cache_clear()

