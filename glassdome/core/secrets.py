"""
Secure Secrets Management

Uses OS-native keyring for secure storage with encryption fallback.
"""
import keyring
import keyring.backends
from typing import Optional, Dict, List
from pathlib import Path
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import getpass
import os


class SecretsManager:
    """
    Manages secrets securely using OS-native keyring.
    Falls back to encrypted file storage if keyring is unavailable.
    """
    
    SERVICE_NAME = "glassdome"
    MASTER_KEY_NAME = "master_key"
    FALLBACK_STORE_PATH = Path.home() / ".glassdome" / "secrets.encrypted"
    
    def __init__(self):
        self._master_key: Optional[bytes] = None
        self._use_keyring = self._check_keyring_available()
        
    def _check_keyring_available(self) -> bool:
        """Check if keyring backend is available and functional."""
        try:
            # Test keyring
            test_key = "test_key"
            test_value = "test_value"
            keyring.set_password(self.SERVICE_NAME, test_key, test_value)
            retrieved = keyring.get_password(self.SERVICE_NAME, test_key)
            keyring.delete_password(self.SERVICE_NAME, test_key)
            return retrieved == test_value
        except Exception:
            return False
    
    def _get_master_key(self) -> bytes:
        """Get or prompt for master key."""
        if self._master_key:
            return self._master_key
        
        # Try to get from keyring first
        if self._use_keyring:
            stored_key = keyring.get_password(self.SERVICE_NAME, self.MASTER_KEY_NAME)
            if stored_key:
                # Decode from base64
                try:
                    self._master_key = base64.b64decode(stored_key)
                    return self._master_key
                except Exception:
                    pass
        
        # Check fallback file
        if self.FALLBACK_STORE_PATH.exists():
            # Master key is stored encrypted with a derived key from user input
            master_key_encrypted_path = self.FALLBACK_STORE_PATH.parent / "master_key.enc"
            if master_key_encrypted_path.exists():
                # Prompt for password to decrypt master key
                password = getpass.getpass("Enter master password for secrets: ")
                try:
                    with open(master_key_encrypted_path, 'rb') as f:
                        salt = f.read(16)
                        encrypted_key = f.read()
                    
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=100000,
                    )
                    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
                    fernet = Fernet(key)
                    self._master_key = fernet.decrypt(encrypted_key)
                    return self._master_key
                except Exception:
                    raise ValueError("Invalid master password")
        
        # No master key exists - prompt to create one
        print("\n🔐 First time setup: Creating master key for secrets storage")
        password = getpass.getpass("Enter a master password (you'll need this to access secrets): ")
        confirm = getpass.getpass("Confirm master password: ")
        
        if password != confirm:
            raise ValueError("Passwords do not match")
        
        # Generate master key
        self._master_key = Fernet.generate_key()
        
        # Store master key encrypted with user password
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        fernet = Fernet(key)
        encrypted_master = fernet.encrypt(self._master_key)
        
        # Save encrypted master key
        self.FALLBACK_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.FALLBACK_STORE_PATH.parent / "master_key.enc", 'wb') as f:
            f.write(salt + encrypted_master)
        
        # Also store in keyring if available
        if self._use_keyring:
            try:
                keyring.set_password(
                    self.SERVICE_NAME,
                    self.MASTER_KEY_NAME,
                    base64.b64encode(self._master_key).decode()
                )
            except Exception:
                pass
        
        print("✅ Master key created and stored securely")
        return self._master_key
    
    def set_secret(self, key: str, value: str) -> bool:
        """
        Store a secret securely.
        
        Args:
            key: Secret key name (e.g., 'proxmox_password')
            value: Secret value to store
            
        Returns:
            True if successful
        """
        if not value:
            return False
        
        if self._use_keyring:
            try:
                keyring.set_password(self.SERVICE_NAME, key, value)
                return True
            except Exception as e:
                print(f"⚠️  Keyring storage failed: {e}, using fallback")
                self._use_keyring = False
        
        # Fallback: Encrypted file storage
        self._get_master_key()
        fernet = Fernet(self._master_key)
        encrypted_value = fernet.encrypt(value.encode())
        
        # Load existing secrets
        secrets = self._load_fallback_secrets()
        secrets[key] = base64.b64encode(encrypted_value).decode()
        self._save_fallback_secrets(secrets)
        
        return True
    
    def get_secret(self, key: str) -> Optional[str]:
        """
        Retrieve a secret.
        
        Args:
            key: Secret key name
            
        Returns:
            Secret value or None if not found
        """
        if self._use_keyring:
            try:
                value = keyring.get_password(self.SERVICE_NAME, key)
                if value:
                    return value
            except Exception:
                pass
        
        # Fallback: Encrypted file storage
        if not self.FALLBACK_STORE_PATH.exists():
            return None
        
        try:
            self._get_master_key()
            secrets = self._load_fallback_secrets()
            if key not in secrets:
                return None
            
            encrypted_value = base64.b64decode(secrets[key])
            fernet = Fernet(self._master_key)
            return fernet.decrypt(encrypted_value).decode()
        except Exception:
            return None
    
    def delete_secret(self, key: str) -> bool:
        """Delete a secret."""
        if self._use_keyring:
            try:
                keyring.delete_password(self.SERVICE_NAME, key)
                return True
            except Exception:
                pass
        
        # Fallback: Remove from file
        if not self.FALLBACK_STORE_PATH.exists():
            return False
        
        try:
            secrets = self._load_fallback_secrets()
            if key in secrets:
                del secrets[key]
                self._save_fallback_secrets(secrets)
                return True
        except Exception:
            pass
        
        return False
    
    def list_secrets(self) -> List[str]:
        """List all stored secret keys (names only, not values)."""
        keys = []
        
        if self._use_keyring:
            # Keyring doesn't have a list method, so we check common keys
            # This is a limitation - we'll maintain a registry
            registry_path = Path.home() / ".glassdome" / "secrets_registry.json"
            if registry_path.exists():
                try:
                    with open(registry_path) as f:
                        keys = json.load(f)
                except Exception:
                    pass
        
        # Also check fallback store
        if self.FALLBACK_STORE_PATH.exists():
            try:
                secrets = self._load_fallback_secrets()
                for key in secrets.keys():
                    if key not in keys:
                        keys.append(key)
            except Exception:
                pass
        
        return sorted(keys)
    
    def _load_fallback_secrets(self) -> Dict[str, str]:
        """Load secrets from encrypted fallback file."""
        if not self.FALLBACK_STORE_PATH.exists():
            return {}
        
        try:
            with open(self.FALLBACK_STORE_PATH) as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _save_fallback_secrets(self, secrets: Dict[str, str]) -> None:
        """Save secrets to encrypted fallback file."""
        self.FALLBACK_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(self.FALLBACK_STORE_PATH, 'w') as f:
            json.dump(secrets, f, indent=2)
        
        # Update registry
        registry_path = Path.home() / ".glassdome" / "secrets_registry.json"
        with open(registry_path, 'w') as f:
            json.dump(list(secrets.keys()), f, indent=2)
    
    def migrate_from_env(self, env_file: Path) -> Dict[str, bool]:
        """
        Migrate secrets from .env file to secure store.
        
        Args:
            env_file: Path to .env file
            
        Returns:
            Dictionary mapping secret keys to migration success status
        """
        if not env_file.exists():
            return {}
        
        # Define which .env keys are secrets
        secret_keys = {
            'PROXMOX_PASSWORD': 'proxmox_password',
            'PROXMOX_TOKEN_VALUE': 'proxmox_token_value',
            'PROXMOX_ADMIN_PASSWD': 'proxmox_admin_passwd',
            'PROXMOX_TOKEN_VALUE_02': 'proxmox_token_value_02',
            'PROXMOX_TOKEN_VALUE_03': 'proxmox_token_value_03',
            'ESXI_PASSWORD': 'esxi_password',
            'AZURE_CLIENT_SECRET': 'azure_client_secret',
            'AWS_SECRET_ACCESS_KEY': 'aws_secret_access_key',
            'OPENAI_API_KEY': 'openai_api_key',
            'ANTHROPIC_API_KEY': 'anthropic_api_key',
            'MAIL_API': 'mail_api',
            'SECRET_KEY': 'secret_key',
        }
        
        # Also match any PROXMOX_TOKEN_VALUE_XX pattern
        import re
        token_pattern = re.compile(r'^PROXMOX_TOKEN_VALUE_(\d+)$')
        
        results = {}
        env_secrets = {}
        
        # Parse .env file
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    
                    # Check if it's a known secret
                    if key in secret_keys:
                        env_secrets[secret_keys[key]] = value
                    # Check for PROXMOX_TOKEN_VALUE_XX pattern
                    elif token_pattern.match(key):
                        match = token_pattern.match(key)
                        instance_id = match.group(1)
                        env_secrets[f'proxmox_token_value_{instance_id}'] = value
                    # Check for database password in DATABASE_URL
                    elif key == 'DATABASE_URL' and ':' in value and '@' in value:
                        # Extract password from postgresql://user:password@host/db
                        try:
                            parts = value.split('@')[0].split('://')[1]
                            if ':' in parts:
                                password = parts.split(':')[1]
                                if password:
                                    env_secrets['database_password'] = password
                        except Exception:
                            pass
        
        # Migrate each secret
        for secret_key, secret_value in env_secrets.items():
            if secret_value:
                try:
                    success = self.set_secret(secret_key, secret_value)
                    results[secret_key] = success
                except Exception as e:
                    print(f"⚠️  Failed to migrate {secret_key}: {e}")
                    results[secret_key] = False
        
        return results


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get or create the global SecretsManager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

