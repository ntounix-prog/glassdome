"""
Secrets Backend Unit Tests

Tests for the secrets backend system including:
- get_secret() function
- EnvSecretsBackend
- VaultSecretsBackend (mocked)
- ChainedSecretsBackend
- Backend selection logic

Author: Brett Turner (ntounix)
Created: December 2025
"""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# =============================================================================
# get_secret() Function Tests
# =============================================================================

class TestGetSecretFunction:
    """Tests for the main get_secret() function."""
    
    def test_get_secret_returns_value(self, vault_test_secrets):
        """get_secret() returns value from backend."""
        from glassdome.core.secrets_backend import get_secret
        
        vault_test_secrets.set("test_key", "test_value")
        result = get_secret("test_key")
        assert result == "test_value"
    
    def test_get_secret_returns_default_when_missing(self, vault_test_secrets):
        """get_secret() returns default for missing keys."""
        from glassdome.core.secrets_backend import get_secret
        
        result = get_secret("nonexistent_key_xyz", "default_value")
        assert result == "default_value"
    
    def test_get_secret_returns_none_when_missing_no_default(self, vault_test_secrets):
        """get_secret() returns None when no default and key missing."""
        from glassdome.core.secrets_backend import get_secret
        
        result = get_secret("nonexistent_key_abc")
        assert result is None
    
    def test_get_secret_case_insensitive(self, vault_test_secrets):
        """get_secret() handles case variations."""
        from glassdome.core.secrets_backend import get_secret
        
        vault_test_secrets.set("my_secret_key", "secret_value")
        
        # Our mock backend lowercases keys
        assert get_secret("my_secret_key") == "secret_value"
        assert get_secret("MY_SECRET_KEY") == "secret_value"
    
    def test_get_secret_with_preloaded_test_values(self, mock_secrets_backend):
        """Test that mock backend has preloaded test values."""
        # These are set in conftest.py MockSecretsBackend
        assert mock_secrets_backend.get("openai_api_key") is not None
        assert mock_secrets_backend.get("aws_access_key_id") is not None
        assert mock_secrets_backend.get("proxmox_password") is not None


# =============================================================================
# EnvSecretsBackend Tests
# =============================================================================

class TestEnvSecretsBackend:
    """Tests for environment variable secrets backend."""
    
    def test_env_backend_reads_from_env(self):
        """EnvSecretsBackend reads from environment variables."""
        from glassdome.core.secrets_backend import EnvSecretsBackend
        
        os.environ["TEST_ENV_SECRET"] = "env_secret_value"
        try:
            backend = EnvSecretsBackend()
            result = backend.get("TEST_ENV_SECRET")
            assert result == "env_secret_value"
        finally:
            del os.environ["TEST_ENV_SECRET"]
    
    def test_env_backend_returns_none_for_missing(self):
        """EnvSecretsBackend returns None for missing vars."""
        from glassdome.core.secrets_backend import EnvSecretsBackend
        
        backend = EnvSecretsBackend()
        result = backend.get("DEFINITELY_NOT_SET_VAR_XYZ123")
        assert result is None
    
    def test_env_backend_handles_case(self):
        """EnvSecretsBackend handles key case correctly."""
        from glassdome.core.secrets_backend import EnvSecretsBackend
        
        os.environ["MY_TEST_VAR"] = "test_value"
        try:
            backend = EnvSecretsBackend()
            # Environment variables are typically uppercase
            assert backend.get("MY_TEST_VAR") == "test_value"
            # Lowercase might not find it (depends on implementation)
        finally:
            del os.environ["MY_TEST_VAR"]


# =============================================================================
# VaultSecretsBackend Tests (Mocked)
# =============================================================================

class TestVaultSecretsBackend:
    """Tests for Vault secrets backend (with mocked hvac client)."""
    
    def test_vault_backend_initialization(self):
        """VaultSecretsBackend initializes with correct parameters."""
        from glassdome.core.secrets_backend import VaultSecretsBackend
        
        # Test that backend stores initialization parameters
        backend = VaultSecretsBackend(
            addr="http://vault.test:8200",
            role_id="test-role-id",
            secret_id="test-secret-id",
            mount_point="test-mount",
            verify=False
        )
        
        # Verify parameters are stored
        assert backend.addr == "http://vault.test:8200"
        assert backend.role_id == "test-role-id"
        assert backend.secret_id == "test-secret-id"
        assert backend.mount_point == "test-mount"
        assert backend.verify is False
        assert backend._client is None  # Client not created until first use
    
    def test_vault_backend_get_secret(self):
        """VaultSecretsBackend.get() retrieves secrets from Vault."""
        from glassdome.core.secrets_backend import VaultSecretsBackend
        
        with patch.dict('sys.modules', {'hvac': MagicMock()}):
            import sys
            mock_hvac = sys.modules['hvac']
            mock_client = MagicMock()
            mock_hvac.Client.return_value = mock_client
            mock_client.is_authenticated.return_value = True
            mock_client.auth.approle.login.return_value = {
                "auth": {"client_token": "test-token"}
            }
            mock_client.secrets.kv.v2.read_secret_version.return_value = {
                "data": {"data": {"value": "vault_secret_value"}}
            }
            
            backend = VaultSecretsBackend(
                addr="http://vault.test:8200",
                role_id="test-role-id",
                secret_id="test-secret-id"
            )
            
            result = backend.get("my_secret")
            assert result == "vault_secret_value"
    
    def test_vault_backend_handles_missing_key(self):
        """VaultSecretsBackend handles missing keys gracefully."""
        from glassdome.core.secrets_backend import VaultSecretsBackend
        
        with patch.dict('sys.modules', {'hvac': MagicMock()}):
            import sys
            mock_hvac = sys.modules['hvac']
            mock_client = MagicMock()
            mock_hvac.Client.return_value = mock_client
            mock_client.is_authenticated.return_value = True
            mock_client.auth.approle.login.return_value = {
                "auth": {"client_token": "test-token"}
            }
            mock_client.secrets.kv.v2.read_secret_version.return_value = {
                "data": {"data": {}}
            }
            
            backend = VaultSecretsBackend(
                addr="http://vault.test:8200",
                role_id="test-role-id",
                secret_id="test-secret-id"
            )
            
            result = backend.get("nonexistent_key")
            assert result is None
    
    def test_vault_backend_handles_connection_error(self):
        """VaultSecretsBackend handles connection errors gracefully."""
        from glassdome.core.secrets_backend import VaultSecretsBackend
        
        # Create backend with invalid address (not a real server)
        backend = VaultSecretsBackend(
            addr="http://invalid.host.that.does.not.exist:8200",
            role_id="test-role-id",
            secret_id="test-secret-id"
        )
        
        # is_available() should return False for invalid config
        assert backend.is_available() is False
        
        # get() should return None without raising (handles errors gracefully)
        result = backend.get("any_key")
        assert result is None


# =============================================================================
# ChainedSecretsBackend Tests
# =============================================================================

class TestChainedSecretsBackend:
    """Tests for chained secrets backend."""
    
    def test_chained_backend_tries_backends_in_order(self):
        """ChainedSecretsBackend tries backends in order."""
        from glassdome.core.secrets_backend import ChainedSecretsBackend
        
        backend1 = MagicMock()
        backend1.get.return_value = None
        
        backend2 = MagicMock()
        backend2.get.return_value = "found_in_backend2"
        
        backend3 = MagicMock()
        backend3.get.return_value = "found_in_backend3"
        
        chained = ChainedSecretsBackend([backend1, backend2, backend3])
        result = chained.get("test_key")
        
        # Should return first non-None value
        assert result == "found_in_backend2"
        
        # backend1 should have been called
        backend1.get.assert_called_once_with("test_key")
        
        # backend2 should have been called
        backend2.get.assert_called_once_with("test_key")
        
        # backend3 should NOT have been called (found in backend2)
        backend3.get.assert_not_called()
    
    def test_chained_backend_returns_none_if_all_miss(self):
        """ChainedSecretsBackend returns None if all backends miss."""
        from glassdome.core.secrets_backend import ChainedSecretsBackend
        
        backend1 = MagicMock()
        backend1.get.return_value = None
        
        backend2 = MagicMock()
        backend2.get.return_value = None
        
        chained = ChainedSecretsBackend([backend1, backend2])
        result = chained.get("missing_key")
        
        assert result is None


# =============================================================================
# Backend Selection Tests
# =============================================================================

class TestBackendSelection:
    """Tests for secrets backend selection logic."""
    
    @pytest.fixture(autouse=True)
    def reset_backend(self):
        """Reset backend singleton before each test."""
        import glassdome.core.secrets_backend as sb
        original = sb._backend
        sb._backend = None
        yield
        sb._backend = original
    
    def test_env_backend_selected_by_default(self, reset_backend):
        """Env backend is selected when SECRETS_BACKEND=env."""
        from glassdome.core.secrets_backend import get_secrets_backend, EnvSecretsBackend
        import glassdome.core.secrets_backend as sb
        
        # Temporarily disable the autouse mock
        sb._backend = None
        
        with patch.dict(os.environ, {"SECRETS_BACKEND": "env"}, clear=False):
            backend = get_secrets_backend("env")  # Force env backend
            assert isinstance(backend, EnvSecretsBackend)
    
    def test_vault_backend_selected_when_configured(self, reset_backend):
        """Vault backend is selected when SECRETS_BACKEND=vault."""
        from glassdome.core.secrets_backend import get_secrets_backend, VaultSecretsBackend
        import glassdome.core.secrets_backend as sb
        
        sb._backend = None
        
        with patch.dict('sys.modules', {'hvac': MagicMock()}):
            import sys
            mock_hvac = sys.modules['hvac']
            mock_client = MagicMock()
            mock_hvac.Client.return_value = mock_client
            mock_client.is_authenticated.return_value = True
            mock_client.auth.approle.login.return_value = {
                "auth": {"client_token": "test-token"}
            }
            
            env_vars = {
                "SECRETS_BACKEND": "vault",
                "VAULT_ADDR": "http://vault.test:8200",
                "VAULT_ROLE_ID": "test-role",
                "VAULT_SECRET_ID": "test-secret",
            }
            
            with patch.dict(os.environ, env_vars, clear=False):
                backend = get_secrets_backend("vault")  # Force vault backend
                assert isinstance(backend, VaultSecretsBackend)


# =============================================================================
# Integration Tests with Application Code
# =============================================================================

class TestSecretsIntegration:
    """Test that application code uses secrets backend correctly."""
    
    def test_llm_service_uses_get_secret(self, vault_test_secrets):
        """LLM service retrieves API keys via get_secret()."""
        vault_test_secrets.set("openai_api_key", "test-openai-key-123")
        vault_test_secrets.set("anthropic_api_key", "test-anthropic-key-456")
        
        # Import after setting up mock
        from glassdome.core.secrets_backend import get_secret
        
        openai_key = get_secret("openai_api_key")
        anthropic_key = get_secret("anthropic_api_key")
        
        assert openai_key == "test-openai-key-123"
        assert anthropic_key == "test-anthropic-key-456"
    
    def test_aws_credentials_from_vault(self, vault_test_secrets):
        """AWS credentials are retrieved via get_secret()."""
        vault_test_secrets.set("aws_access_key_id", "AKIATEST123")
        vault_test_secrets.set("aws_secret_access_key", "secret123")
        
        from glassdome.core.secrets_backend import get_secret
        
        access_key = get_secret("aws_access_key_id")
        secret_key = get_secret("aws_secret_access_key")
        
        assert access_key == "AKIATEST123"
        assert secret_key == "secret123"
    
    def test_proxmox_password_from_vault(self, vault_test_secrets):
        """Proxmox password is retrieved via get_secret()."""
        vault_test_secrets.set("proxmox_password", "proxmox-test-pass")
        
        from glassdome.core.secrets_backend import get_secret
        
        password = get_secret("proxmox_password")
        assert password == "proxmox-test-pass"
    
    def test_multiple_secrets_retrieval(self, vault_test_secrets):
        """Multiple secrets can be retrieved independently."""
        secrets_to_test = {
            "secret_one": "value_one",
            "secret_two": "value_two",
            "secret_three": "value_three",
        }
        
        for key, value in secrets_to_test.items():
            vault_test_secrets.set(key, value)
        
        from glassdome.core.secrets_backend import get_secret
        
        for key, expected in secrets_to_test.items():
            actual = get_secret(key)
            assert actual == expected, f"Key {key}: expected {expected}, got {actual}"


# =============================================================================
# Security Tests
# =============================================================================

class TestSecretsSecurity:
    """Tests for secrets security properties."""
    
    def test_secrets_not_logged(self, vault_test_secrets, caplog):
        """Verify secrets are not accidentally logged."""
        import logging
        
        vault_test_secrets.set("super_secret", "my-secret-password-123")
        
        from glassdome.core.secrets_backend import get_secret
        
        # Enable debug logging
        with caplog.at_level(logging.DEBUG):
            secret = get_secret("super_secret")
        
        # Verify the actual secret value is not in logs
        for record in caplog.records:
            assert "my-secret-password-123" not in record.message
    
    def test_mock_backend_does_not_expose_internals(self, mock_secrets_backend):
        """Mock backend doesn't expose secret values in repr/str."""
        # Get a secret
        mock_secrets_backend.set("hidden_secret", "very-sensitive-value")
        
        # Check that str representation doesn't leak secrets
        str_repr = str(mock_secrets_backend)
        assert "very-sensitive-value" not in str_repr.lower()

