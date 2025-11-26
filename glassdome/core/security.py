"""
Glassdome Security Bootstrap

Provides helpers to ensure a valid security context (session + settings)
for any process that wants to run agents or access secrets.

Design goals:
- NEVER prompt for the master password here (non-interactive safe).
- Rely on session cache + OS keyring when available.
- Support production mode with environment variables only.
- Fail fast with a clear error if the session is not initialized.

Usage:
    from glassdome.core.security import ensure_security_context, get_secure_settings

    ensure_security_context()          # at process startup
    settings = get_secure_settings()   # anywhere after that
"""

from __future__ import annotations

import os
from typing import Any

from .session import get_session


def _has_env_secrets() -> bool:
    """Check if essential secrets are available in environment variables."""
    # Check for at least one critical secret in env
    env_secrets = [
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'PROXMOX_PASSWORD',
        'AWS_SECRET_ACCESS_KEY', 'DATABASE_URL'
    ]
    return any(os.environ.get(key) for key in env_secrets)


def ensure_security_context() -> None:
    """
    Ensure the current process has an authenticated session.

    Behavior:
    - If environment variables provide secrets, session is optional (production mode).
    - Uses cache + keyring only (no interactive prompts).
    - If the session is already initialized in this process, it's a no-op.
    - If cache/keyring are not available or invalid, raises RuntimeError
      with guidance to initialize via CLI or API first.
    """
    session = get_session()

    # If this process already has an authenticated session, nothing to do
    if session.is_initialized():
        return

    # Try to hydrate from cache/keyring without prompting
    success = session.initialize(interactive=False, use_cache=True)
    if success and session.is_initialized():
        return
    
    # Production mode: if secrets are in env vars, allow startup without full session
    if _has_env_secrets():
        # Log warning but allow startup
        import logging
        logging.getLogger(__name__).info(
            "Running in production mode with environment variable secrets. "
            "Session not initialized, but secrets available from environment."
        )
        return
    
    # Neither session nor env vars available
    raise RuntimeError(
        "Glassdome security context not initialized in this process.\n"
        "Initialize the session first, for example:\n"
        "  - CLI: ./glassdome_start\n"
        "  - API: POST /api/auth/login with master_password\n"
        "  - Or set secrets as environment variables (OPENAI_API_KEY, etc.)\n"
    )


def get_secure_settings() -> Any:
    """
    Get Settings instance from an authenticated session or environment.

    This ensures:
    - Session is initialized in this process (or env vars available).
    - Settings are hydrated from SecretsManager (which now checks env vars first).
    """
    ensure_security_context()
    session = get_session()
    
    # If session is fully initialized, use its settings
    if session.is_initialized():
        return session.get_settings()
    
    # Production mode: create settings directly (env vars will be used)
    from glassdome.core.config import Settings
    return Settings()


