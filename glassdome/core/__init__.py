"""
Glassdome Core Module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from glassdome.core.session import get_session, require_session, GlassdomeSession
from glassdome.core.config import settings, Settings
from glassdome.core.secrets import get_secrets_manager
from glassdome.core.secrets_backend import get_secret, set_secret, list_secrets

__all__ = [
    'get_session',
    'require_session',
    'GlassdomeSession',
    'settings',
    'Settings',
    'get_secrets_manager',
    # Vault-only secret access
    'get_secret',
    'set_secret',
    'list_secrets',
]
