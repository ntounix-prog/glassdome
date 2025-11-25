"""
Glassdome Security Bootstrap

Provides helpers to ensure a valid security context (session + settings)
for any process that wants to run agents or access secrets.

Design goals:
- NEVER prompt for the master password here (non-interactive safe).
- Rely on session cache + OS keyring when available.
- Fail fast with a clear error if the session is not initialized.

Usage:
    from glassdome.core.security import ensure_security_context, get_secure_settings

    ensure_security_context()          # at process startup
    settings = get_secure_settings()   # anywhere after that
"""

from __future__ import annotations

from typing import Any

from .session import get_session


def ensure_security_context() -> None:
    """
    Ensure the current process has an authenticated session.

    Behavior:
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
    if not success or not session.is_initialized():
        raise RuntimeError(
            "Glassdome security context not initialized in this process.\n"
            "Initialize the session first, for example:\n"
            "  - CLI: ./glassdome_start\n"
            "  - API: POST /api/auth/login with master_password\n"
        )


def get_secure_settings() -> Any:
    """
    Get Settings instance from an authenticated session.

    This ensures:
    - Session is initialized in this process (or raises).
    - Settings are hydrated from SecretsManager.
    """
    ensure_security_context()
    session = get_session()
    return session.get_settings()


