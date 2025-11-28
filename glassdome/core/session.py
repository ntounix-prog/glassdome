"""
Session module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from typing import Optional, Dict, Any, TYPE_CHECKING
from pathlib import Path
import getpass
import logging
import os
import json
import base64
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
import keyring

from glassdome.core.paths import (
    SESSION_CACHE_PATH,
    SESSION_KEY_PATH,
    MASTER_KEY_PATH,
    SECRETS_DIR,
)

# Settings imported lazily to avoid premature initialization
if TYPE_CHECKING:
    from glassdome.core.config import Settings

logger = logging.getLogger(__name__)


def _get_backend_type() -> str:
    """Get configured secrets backend type."""
    return os.environ.get("SECRETS_BACKEND", "env")


class GlassdomeSession:
    """
    Glassdome application session.
    
    Manages authentication, secret loading, and provides secure access
    to all configuration and secrets for agents.
    """
    
    _instance: Optional['GlassdomeSession'] = None
    _initialized: bool = False
    
    def __init__(self):
        """Initialize session (private - use get_session())"""
        self.settings: Optional[Any] = None  # Settings imported lazily
        self.secrets: Dict[str, str] = {}
        self.authenticated: bool = False
        self.authenticated_at: Optional[datetime] = None
        self.session_timeout: timedelta = timedelta(hours=8)  # 8 hour session
        self._secrets_manager = None
    
    @classmethod
    def get_session(cls) -> 'GlassdomeSession':
        """Get or create the global session instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        Check if session is initialized.
        
        For 'env' backend: Always returns True (no session needed)
        For 'local' backend: Checks if authenticated session exists
        """
        # For env/vault backends, session is not required
        if _get_backend_type() in ("env", "vault"):
            return True
        
        # For local backend, check actual session state
        if cls._instance is None:
            return False
        return cls._instance.authenticated and cls._instance._is_session_valid()
    
    @classmethod
    def _check_cache_valid(cls) -> bool:
        """Check if session cache exists and is valid"""
        if not SESSION_CACHE_PATH.exists():
            return False
        
        try:
            # Check file permissions (should be 600)
            stat = SESSION_CACHE_PATH.stat()
            if stat.st_mode & 0o077:  # Check if others/group can read
                logger.warning("Session cache has insecure permissions, ignoring")
                return False
            
            with open(SESSION_CACHE_PATH) as f:
                cache = json.load(f)
            
            # Check expiration
            expires_at = datetime.fromisoformat(cache['expires_at'])
            if datetime.now() >= expires_at:
                # Cache expired, remove it
                SESSION_CACHE_PATH.unlink()
                return False
            
            return True
        except Exception as e:
            logger.debug(f"Error checking session cache: {e}")
            return False
    
    @classmethod
    def _load_from_cache(cls) -> bool:
        """Load session from cache if valid.
        
        Tries multiple methods to get the master key:
        1. Session key file (cross-process, written during ./glassdome_start)
        2. OS keyring (if available and unlocked)
        3. Gives up (caller must prompt for password or fail)
        """
        if not cls._check_cache_valid():
            return False
        
        try:
            session = cls.get_session()
            with open(SESSION_CACHE_PATH) as f:
                cache = json.load(f)
            
            # Get secrets manager
            secrets_manager = get_secrets_manager()
            
            # Try to get master key from multiple sources
            master_key_loaded = False
            
            # Method 1: Session key file (works for headless agents)
            if SESSION_KEY_PATH.exists():
                try:
                    # Check permissions (should be 600)
                    stat = SESSION_KEY_PATH.stat()
                    if not (stat.st_mode & 0o077):  # No group/other access
                        with open(SESSION_KEY_PATH, 'rb') as f:
                            secrets_manager._master_key = f.read()
                        master_key_loaded = True
                        logger.debug("Master key loaded from session key file")
                    else:
                        logger.warning("Session key file has insecure permissions, ignoring")
                except Exception as e:
                    logger.debug(f"Failed to load session key file: {e}")
            
            # Method 2: OS keyring (if available)
            if not master_key_loaded and secrets_manager._use_keyring:
                try:
                    stored_key = keyring.get_password(secrets_manager.SERVICE_NAME, secrets_manager.MASTER_KEY_NAME)
                    if stored_key:
                        secrets_manager._master_key = base64.b64decode(stored_key)
                        master_key_loaded = True
                        logger.debug("Master key loaded from OS keyring")
                except Exception as e:
                    logger.debug(f"Failed to load from keyring: {e}")
            
            # If master key loaded, we can load secrets
            if master_key_loaded and secrets_manager._master_key:
                # Load all secrets
                all_secret_keys = secrets_manager.list_secrets()
                for secret_key in all_secret_keys:
                    try:
                        secret_value = secrets_manager.get_secret(secret_key)
                        if secret_value:
                            session.secrets[secret_key] = secret_value
                    except Exception:
                        pass
                
                # Mark as authenticated
                session.authenticated = True
                session.authenticated_at = datetime.fromisoformat(cache['authenticated_at'])
                session._secrets_manager = secrets_manager
                
                # Initialize Settings
                from glassdome.core.config import Settings
                session.settings = Settings()
                
                logger.info(f"✅ Session loaded from cache (no password required)")
                logger.info(f"   Loaded {len(session.secrets)} secrets")
                return True
            else:
                # Master key not available without password
                logger.debug("Session cache exists but master key requires password")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to load session from cache: {e}")
            if SESSION_CACHE_PATH.exists():
                SESSION_CACHE_PATH.unlink()
            return False
    
    def _save_to_cache(self):
        """Save session state to cache file for cross-process sharing.
        
        SECURITY NOTE: 
        - The cache file contains only metadata (timestamps).
        - The session key file contains the decrypted master key for cross-process access.
        - Both files are protected with 600 permissions (user-only).
        - Any process running as the same OS user can access these files.
        - This is the intended behavior: one auth per user, many agent accesses.
        
        For higher security environments, consider:
        - A secrets daemon with per-process authentication
        - HashiCorp Vault or similar external secrets management
        """
        try:
            # Ensure directory exists
            SECRETS_DIR.mkdir(parents=True, exist_ok=True)
            
            # Save metadata cache
            cache = {
                'authenticated_at': self.authenticated_at.isoformat() if self.authenticated_at else None,
                'expires_at': (self.authenticated_at + self.session_timeout).isoformat() if self.authenticated_at else None,
                'secrets_count': len(self.secrets),
            }
            
            with open(SESSION_CACHE_PATH, 'w') as f:
                json.dump(cache, f)
            os.chmod(SESSION_CACHE_PATH, 0o600)
            
            # Save session key for cross-process access (headless agents)
            if self._secrets_manager and self._secrets_manager._master_key:
                with open(SESSION_KEY_PATH, 'wb') as f:
                    f.write(self._secrets_manager._master_key)
                os.chmod(SESSION_KEY_PATH, 0o600)
                logger.debug("Session key saved for cross-process access")
            
            logger.debug("Session cache saved")
        except Exception as e:
            logger.warning(f"Failed to save session cache: {e}")
    
    def _is_session_valid(self) -> bool:
        """Check if session is still valid (not expired)"""
        if not self.authenticated_at:
            return False
        return datetime.now() - self.authenticated_at < self.session_timeout
    
    def initialize(self, master_password: Optional[str] = None, interactive: bool = True, use_cache: bool = True) -> bool:
        """
        Initialize Glassdome session with authentication.
        
        For 'env' backend: No-op, returns True immediately
        For 'local' backend: Loads secrets from encrypted store
        
        Args:
            master_password: Master password for secrets (if None, will prompt)
            interactive: Whether to prompt for password if not provided
            use_cache: Whether to try loading from cache first (default: True)
            
        Returns:
            True if initialization successful, False otherwise
        """
        backend = _get_backend_type()
        
        # For env/vault backends, no session initialization needed
        if backend in ("env", "vault"):
            logger.debug(f"Using {backend} backend - session initialization not required")
            self.authenticated = True
            self.authenticated_at = datetime.now()
            # Load settings
            from glassdome.core.config import Settings
            self.settings = Settings()
            return True
        
        # Local backend - requires encrypted secrets store
        try:
            logger.info("Initializing Glassdome session (local backend)...")
            
            # Try to load from cache first (if enabled)
            if use_cache and self._load_from_cache():
                # Successfully loaded from cache, no password needed
                return True
            
            # Get secrets manager
            from glassdome.core.secrets import get_secrets_manager
            self._secrets_manager = get_secrets_manager()
            
            # Check if secrets manager has encrypted files (without prompting for password)
            if not MASTER_KEY_PATH.exists() and not self._secrets_manager._use_keyring:
                logger.error("Local secrets not initialized. Run 'glassdome secrets setup' or set SECRETS_BACKEND=env")
                return False
            
            # If master_password was not provided, prompt for it once
            if master_password is None:
                if interactive:
                    print("\n" + "=" * 70)
                    print("GLASSDOME INITIALIZATION")
                    print("=" * 70)
                    print("Please enter your master password to unlock secrets...")
                    master_password = getpass.getpass("Master password: ")
                else:
                    logger.error("Master password required but not provided and interactive=False")
                    return False
            
            # Load all secrets into memory (decrypted)
            logger.info("Loading secrets into session...")
            
            # CRITICAL: Load master key ONCE before ANY secret access
            # This ensures password is only prompted once, not for each secret or Settings initialization
            # The master key will be cached in the secrets manager instance
            if not self._secrets_manager._master_key:
                # Master key not loaded yet - use provided password or prompt ONCE
                self._secrets_manager._get_master_key(password=master_password)
            
            # Now list and load secrets (master key already cached, no more prompts)
            all_secret_keys = self._secrets_manager.list_secrets()
            
            for secret_key in all_secret_keys:
                try:
                    # get_secret() will use cached master key, no prompt
                    secret_value = self._secrets_manager.get_secret(secret_key)
                    if secret_value:
                        self.secrets[secret_key] = secret_value
                        logger.debug(f"Loaded secret: {secret_key}")
                except Exception as e:
                    logger.warning(f"Failed to load secret {secret_key}: {e}")
            
            logger.info(f"Loaded {len(self.secrets)} secrets into session")
            
            # Initialize Settings with secrets
            # Master key is already cached, so Settings validator won't prompt again
            logger.info("Initializing Settings...")
            # Import Settings here (after master key is loaded) to avoid premature initialization
            from glassdome.core.config import Settings
            self.settings = Settings()
            
            # Verify critical secrets are loaded
            critical_secrets = ['proxmox_password', 'openai_api_key']
            missing = [s for s in critical_secrets if s not in self.secrets and not getattr(self.settings, s, None)]
            
            if missing:
                logger.warning(f"Some critical secrets not found: {missing}")
                # Don't fail - some might be optional
            
            # Mark as authenticated
            self.authenticated = True
            self.authenticated_at = datetime.now()
            GlassdomeSession._initialized = True
            
            # Save to cache for other processes
            self._save_to_cache()
            
            logger.info("✅ Glassdome session initialized successfully")
            if interactive:
                print("✅ Session initialized successfully!")
                print(f"   Loaded {len(self.secrets)} secrets")
                print(f"   Session valid for {self.session_timeout}")
            
            return True
            
        except KeyboardInterrupt:
            logger.info("Initialization cancelled by user")
            return False
        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def get_secret(self, key: str) -> Optional[str]:
        """
        Get a secret from the session.
        
        Args:
            key: Secret key name
            
        Returns:
            Secret value or None if not found/not authenticated
        """
        if not self.authenticated or not self._is_session_valid():
            raise RuntimeError("Session not authenticated or expired. Call initialize() first.")
        
        return self.secrets.get(key)
    
    def get_settings(self):
        """
        Get Settings instance.
        
        Returns:
            Settings instance
            
        Raises:
            RuntimeError: If session not authenticated
        """
        if not self.authenticated or not self._is_session_valid():
            raise RuntimeError("Session not authenticated or expired. Call initialize() first.")
        
        if self.settings is None:
            # Import Settings lazily (after master key is loaded)
            from glassdome.core.config import Settings
            self.settings = Settings()
        
        return self.settings
    
    def require_auth(self) -> None:
        """
        Require authentication - raise error if not authenticated.
        
        Raises:
            RuntimeError: If session not authenticated
        """
        if not self.authenticated or not self._is_session_valid():
            raise RuntimeError(
                "Glassdome session not authenticated or expired.\n"
                "Please initialize the session with: session.initialize()"
            )
    
    def set_secret_via_manager(self, key: str, value: str) -> bool:
        """
        Set a secret via the secrets manager.
        
        This stores the secret in the encrypted store and also
        adds it to the in-memory session secrets.
        
        Args:
            key: Secret key name
            value: Secret value
            
        Returns:
            True if stored successfully
        """
        if not self.authenticated or not self._is_session_valid():
            raise RuntimeError("Session not authenticated")
        
        if self._secrets_manager is None:
            self._secrets_manager = get_secrets_manager()
        
        try:
            success = self._secrets_manager.set_secret(key, value)
            if success:
                # Also update in-memory cache
                self.secrets[key] = value
                logger.info(f"Secret '{key}' stored successfully")
            return success
        except Exception as e:
            logger.error(f"Failed to store secret '{key}': {e}")
            return False
    
    def refresh(self) -> bool:
        """Refresh session (re-authenticate)"""
        logger.info("Refreshing session...")
        self.authenticated = False
        self.authenticated_at = None
        return self.initialize(interactive=True)
    
    def logout(self) -> None:
        """Logout and clear session"""
        logger.info("Logging out...")
        self.authenticated = False
        self.authenticated_at = None
        self.secrets.clear()
        self.settings = None
        GlassdomeSession._initialized = False
        
        # Remove cache file
        if SESSION_CACHE_PATH.exists():
            try:
                SESSION_CACHE_PATH.unlink()
                logger.debug("Session cache removed")
            except Exception as e:
                logger.warning(f"Failed to remove session cache: {e}")
        
        # Remove session key file
        if SESSION_KEY_PATH.exists():
            try:
                SESSION_KEY_PATH.unlink()
                logger.debug("Session key removed")
            except Exception as e:
                logger.warning(f"Failed to remove session key: {e}")
        
        logger.info("Session cleared")


def get_session() -> GlassdomeSession:
    """Get the global Glassdome session instance"""
    return GlassdomeSession.get_session()


def require_session() -> GlassdomeSession:
    """
    Get session and require it to be authenticated.
    
    Returns:
        Authenticated session
        
    Raises:
        RuntimeError: If session not authenticated
    """
    session = get_session()
    session.require_auth()
    return session

