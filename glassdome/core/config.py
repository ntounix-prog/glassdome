"""
Config module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, model_validator
from typing import Optional, Dict, Any
from pathlib import Path
import os
import re
from glassdome.core.paths import ENV_FILE


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=str(ENV_FILE),
        case_sensitive=False,
        extra="allow"  # Allow extra fields for multi-instance support
    )
    """Application settings"""
    
    # Application
    app_name: str = "Glassdome"
    app_version: str = "0.5.0"
    environment: str = "development"
    debug: bool = True
    
    # API - Changed default port to avoid conflicts
    api_prefix: str = "/api"
    backend_port: int = 8010
    vite_port: int = 5174
    backend_cors_origins: list = ["http://localhost:5174", "http://localhost:3000"]
    
    # Database
    database_url: str = "postgresql+asyncpg://glassdome:glassdome@localhost:5432/glassdome"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    
    # Security
    secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Proxmox (Default/Instance 01 - backward compatible)
    proxmox_host: Optional[str] = None
    proxmox_user: Optional[str] = None
    proxmox_password: Optional[str] = None
    proxmox_token_name: Optional[str] = None
    proxmox_token_value: Optional[str] = None
    proxmox_verify_ssl: bool = False
    proxmox_node: str = "pve"
    
    # Legacy/alternative Proxmox variable names (for compatibility)
    proxmox_admin: Optional[str] = None  # Alternative to proxmox_user
    proxmox_admin_passwd: Optional[str] = None  # Alternative to proxmox_password
    proxmox_root_password: Optional[str] = None  # Root password for SSH access to Proxmox host
    
    @model_validator(mode='after')
    def _load_secrets(self):
        """Override field values with secrets based on SECRETS_BACKEND config."""
        from glassdome.core.security import get_secret
        
        # Map legacy variables first
        if not self.proxmox_password and self.proxmox_admin_passwd:
            self.proxmox_password = self.proxmox_admin_passwd
        if not self.proxmox_user and self.proxmox_admin:
            self.proxmox_user = self.proxmox_admin
        
        # Override with secrets if available
        secret_mappings = {
            # Core security
            'secret_key': 'secret_key',
            
            # Proxmox
            'proxmox_password': 'proxmox_password',
            'proxmox_token_value': 'proxmox_token_value',
            'proxmox_root_password': 'proxmox_root_password',
            
            # ESXi
            'esxi_password': 'esxi_password',
            
            # Cloud providers
            'azure_client_secret': 'azure_client_secret',
            'aws_access_key_id': 'aws_access_key_id',
            'aws_secret_access_key': 'aws_secret_access_key',
            
            # AI/LLM API keys
            'openai_api_key': 'openai_api_key',
            'anthropic_api_key': 'anthropic_api_key',
            'xai_api_key': 'xai_api_key',
            'perplexity_api_key': 'perplexity_api_key',
            'rapidapi_key': 'rapidapi_key',
            'google_search_api_key': 'google_search_api_key',
            'google_engine_id': 'google_engine_id',
            
            # Mailcow
            'mail_api': 'mail_api',
            
            # Network devices - Cisco
            'nexus_3064_password': 'nexus_3064_password',
            'cisco_3850_password': 'cisco_3850_password',
            
            # Network devices - Ubiquiti
            'ubiquiti_gateway_password': 'ubiquiti_gateway_password',
            'ubiquiti_api_key': 'ubiquiti_api_key',
            
            # Default machine credentials
            'windows_default_password': 'windows_default_password',
            'linux_default_password': 'linux_default_password',
        }
        
        for field_name, secret_key in secret_mappings.items():
            secret_value = get_secret(secret_key)
            if secret_value:
                setattr(self, field_name, secret_value)
        
        # Handle legacy proxmox_admin_passwd -> proxmox_password mapping
        proxmox_admin_passwd = get_secret('proxmox_admin_passwd')
        if proxmox_admin_passwd and not self.proxmox_password:
            self.proxmox_password = proxmox_admin_passwd
        
        return self
    
    def get_proxmox_config(self, instance_id: str = "01") -> Dict[str, Any]:
        """
        Get Proxmox configuration for a specific instance.
        
        Supports multiple Proxmox instances via environment variables:
        - Instance 01 (default): PROXMOX_HOST, PROXMOX_USER, PROXMOX_TOKEN_VALUE, etc.
        - Instance 02: PROXMOX_02_HOST, PROXMOX_02_USER, PROXMOX_TOKEN_VALUE_02, etc.
        - Instance 03: PROXMOX_03_HOST, PROXMOX_03_USER, PROXMOX_TOKEN_VALUE_03, etc.
        - Future instances: PROXMOX_XX_HOST, PROXMOX_XX_USER, PROXMOX_TOKEN_VALUE_XX, etc.
        
        Args:
            instance_id: Instance identifier ("01", "02", "03", etc.)
                        Use "01" or None for default/backward compatible instance
        
        Returns:
            Dictionary with Proxmox configuration:
                - host: Proxmox host address
                - user: Username
                - password: Password (if using password auth)
                - token_name: API token name
                - token_value: API token value
                - verify_ssl: SSL verification flag
                - node: Default node name
        """
        if instance_id == "01" or instance_id is None:
            # Default instance (backward compatible)
            return {
                "host": self.proxmox_host,
                "user": self.proxmox_user,
                "password": self.proxmox_password,
                "token_name": self.proxmox_token_name,
                "token_value": self.proxmox_token_value,
                "verify_ssl": self.proxmox_verify_ssl,
                "node": self.proxmox_node
            }
        
        # Multi-instance support: Look for PROXMOX_XX_* variables
        instance_prefix = f"PROXMOX_{instance_id.upper()}_"
        
        # Read from .env file directly (pydantic-settings doesn't populate os.environ)
        env_vars = {}
        
        if ENV_FILE.exists():
            with open(ENV_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key.startswith(instance_prefix):
                            # Remove prefix and convert to lowercase
                            config_key = key[len(instance_prefix):].lower()
                            env_vars[config_key] = value
                        # Special handling for token_value (can be PROXMOX_TOKEN_VALUE_02 format)
                        elif key == f"PROXMOX_TOKEN_VALUE_{instance_id}":
                            env_vars["token_value"] = value
        
        # Also check os.environ as fallback
        for key, value in os.environ.items():
            if key.startswith(instance_prefix):
                config_key = key[len(instance_prefix):].lower()
                if config_key not in env_vars:
                    env_vars[config_key] = value
            elif key == f"PROXMOX_TOKEN_VALUE_{instance_id}":
                if "token_value" not in env_vars:
                    env_vars["token_value"] = value
        
        # Check for token_value and password via configured backend
        from glassdome.core.security import get_secret
        token_secret_key = f"proxmox_token_value_{instance_id}"
        token_from_secrets = get_secret(token_secret_key)
        
        # Get password for this instance (if multi-instance)
        password_secret_key = f"proxmox_password_{instance_id}" if instance_id != "01" else "proxmox_password"
        password_from_secrets = get_secret(password_secret_key)
        
        # Build config dict (secrets manager takes priority)
        config = {
            "host": env_vars.get("host") or os.getenv(f"PROXMOX_{instance_id}_HOST"),
            "user": env_vars.get("user") or os.getenv(f"PROXMOX_{instance_id}_USER"),
            "password": password_from_secrets or env_vars.get("password") or os.getenv(f"PROXMOX_{instance_id}_PASSWORD"),
            "token_name": env_vars.get("token_name") or os.getenv(f"PROXMOX_{instance_id}_TOKEN_NAME") or self.proxmox_token_name,
            "token_value": token_from_secrets or env_vars.get("token_value") or os.getenv(f"PROXMOX_TOKEN_VALUE_{instance_id}"),
            "verify_ssl": env_vars.get("verify_ssl", "false").lower() == "true" if env_vars.get("verify_ssl") else self.proxmox_verify_ssl,
            "node": env_vars.get("node") or os.getenv(f"PROXMOX_{instance_id}_NODE", "pve")
        }
        
        return config
    
    def list_proxmox_instances(self) -> list[str]:
        """
        List all configured Proxmox instances.
        
        Returns:
            List of instance IDs (e.g., ["01", "02"])
        """
        instances = ["01"]  # Always include default instance
        
        # Check .env file for PROXMOX_XX_HOST variables
        if ENV_FILE.exists():
            with open(ENV_FILE) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key = line.split("=", 1)[0].strip()
                        # Look for PROXMOX_XX_HOST pattern
                        match = re.match(r'^PROXMOX_(\d+)_HOST$', key)
                        if match:
                            instance_id = match.group(1)
                            if instance_id not in instances:
                                instances.append(instance_id)
                        # Also check for PROXMOX_TOKEN_VALUE_XX pattern
                        match = re.match(r'^PROXMOX_TOKEN_VALUE_(\d+)$', key)
                        if match:
                            instance_id = match.group(1)
                            if instance_id not in instances:
                                instances.append(instance_id)
        
        # Also check os.environ as fallback
        pattern = re.compile(r'^PROXMOX_(\d+)_HOST$')
        for key in os.environ.keys():
            match = pattern.match(key)
            if match:
                instance_id = match.group(1)
                if instance_id not in instances:
                    instances.append(instance_id)
        
        pattern = re.compile(r'^PROXMOX_TOKEN_VALUE_(\d+)$')
        for key in os.environ.keys():
            match = pattern.match(key)
            if match:
                instance_id = match.group(1)
                if instance_id not in instances:
                    instances.append(instance_id)
        
        return sorted(instances)
    
    # ESXi
    esxi_host: Optional[str] = None
    esxi_user: Optional[str] = None
    esxi_password: Optional[str] = None
    esxi_datastore: Optional[str] = None
    esxi_network: str = "VM Network"
    esxi_verify_ssl: bool = False
    esxi_ubuntu_template: Optional[str] = None
    esxi_testing_enabled: bool = True
    
    # VM Template IDs
    ubuntu_2204_template_id: int = 9000
    ubuntu_2004_template_id: int = 9001
    windows_server2022_template_id: Optional[int] = None  # Set after template creation
    
    # Azure
    azure_subscription_id: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_region: str = "eastus"
    azure_resource_group: str = "glassdome-rg"
    
    # AWS
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    # OpenAI (for agent intelligence)
    openai_api_key: Optional[str] = None
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    
    # XAI (Grok)
    xai_api_key: Optional[str] = None
    
    # Perplexity
    perplexity_api_key: Optional[str] = None
    
    # RapidAPI
    rapidapi_key: Optional[str] = None
    
    # Google Search API
    google_search_api_key: Optional[str] = None
    google_engine_id: Optional[str] = None
    
    # Mailcow
    mail_api: Optional[str] = None  # Mailcow API Bearer token (from .env: MAIL_API)
    mailcow_api_url: Optional[str] = None  # Mailcow API URL (e.g., https://mail.xisx.org)
    mailcow_domain: str = "xisx.org"
    mailcow_imap_host: Optional[str] = None  # Defaults to mail.{domain}
    mailcow_smtp_host: Optional[str] = None  # Defaults to mail.{domain}
    mailcow_smtp_port: int = 587
    mailcow_verify_ssl: bool = False  # Disable SSL verification for self-signed certs
    
    # ===================================================
    # Network Device Configuration
    # ===================================================
    
    # Cisco Nexus 3064 (Datacenter Switch)
    nexus_3064_host: Optional[str] = None
    nexus_3064_user: Optional[str] = None
    nexus_3064_password: Optional[str] = None
    nexus_3064_ssh_port: int = 22
    
    # Cisco 3850-48 (POE Switch)
    cisco_3850_host: Optional[str] = None
    cisco_3850_user: Optional[str] = None
    cisco_3850_password: Optional[str] = None
    cisco_3850_ssh_port: int = 22
    
    # Ubiquiti Gateway
    ubiquiti_gateway_host: Optional[str] = None
    ubiquiti_gateway_user: Optional[str] = None
    ubiquiti_gateway_password: Optional[str] = None
    ubiquiti_access_method: str = "ssh"
    ubiquiti_ssh_port: int = 22
    ubiquiti_api_name: Optional[str] = None
    ubiquiti_api_key: Optional[str] = None
    
    # ===================================================
    # Machine Credentials (WinRM/SSH for deployed VMs)
    # ===================================================
    # These are default credentials for accessing deployed VMs
    # Individual VM credentials can be stored with machine_cred_{hostname} pattern
    
    # Default Windows credentials (WinRM)
    windows_default_user: str = "Administrator"
    windows_default_password: Optional[str] = None
    winrm_port: int = 5985
    winrm_ssl_port: int = 5986
    
    # Default Linux credentials (SSH)
    linux_default_user: str = "root"
    linux_default_password: Optional[str] = None
    linux_ssh_port: int = 22
    
    def get_cisco_3850_config(self) -> Dict[str, Any]:
        """Get Cisco 3850 switch configuration."""
        return {
            "host": self.cisco_3850_host,
            "user": self.cisco_3850_user,
            "password": self.cisco_3850_password,
            "port": self.cisco_3850_ssh_port,
        }
    
    def get_nexus_3064_config(self) -> Dict[str, Any]:
        """Get Cisco Nexus 3064 switch configuration."""
        return {
            "host": self.nexus_3064_host,
            "user": self.nexus_3064_user,
            "password": self.nexus_3064_password,
            "port": self.nexus_3064_ssh_port,
        }
    
    def get_ubiquiti_config(self) -> Dict[str, Any]:
        """Get Ubiquiti gateway configuration."""
        return {
            "host": self.ubiquiti_gateway_host,
            "user": self.ubiquiti_gateway_user,
            "password": self.ubiquiti_gateway_password,
            "access_method": self.ubiquiti_access_method,
            "ssh_port": self.ubiquiti_ssh_port,
            "api_name": self.ubiquiti_api_name,
            "api_key": self.ubiquiti_api_key,
        }
    
    def get_machine_credential(self, hostname: str, os_type: str = "linux") -> Dict[str, Any]:
        """
        Get credentials for a specific machine.
        
        First checks for machine-specific credentials (machine_cred_{hostname}),
        then falls back to OS-specific defaults.
        
        Args:
            hostname: Machine hostname or identifier
            os_type: "linux" or "windows"
            
        Returns:
            Dictionary with user, password, port
        """
        from glassdome.core.security import get_secret
        
        # Try machine-specific credential first
        machine_user_key = f"machine_cred_{hostname}_user"
        machine_pass_key = f"machine_cred_{hostname}_password"
        
        machine_user = get_secret(machine_user_key)
        machine_pass = get_secret(machine_pass_key)
        
        if machine_user and machine_pass:
            port = self.winrm_port if os_type == "windows" else self.linux_ssh_port
            return {
                "user": machine_user,
                "password": machine_pass,
                "port": port,
                "source": "machine_specific"
            }
        
        # Fall back to OS defaults
        if os_type == "windows":
            return {
                "user": self.windows_default_user,
                "password": self.windows_default_password,
                "port": self.winrm_port,
                "source": "windows_default"
            }
        else:
            return {
                "user": self.linux_default_user,
                "password": self.linux_default_password,
                "port": self.linux_ssh_port,
                "source": "linux_default"
            }
    
    def set_machine_credential(self, hostname: str, user: str, password: str) -> bool:
        """
        Store credentials for a specific machine.
        
        Args:
            hostname: Machine hostname or identifier
            user: Username
            password: Password
            
        Returns:
            True if stored successfully
        """
        # For env backend, this just sets env vars for current process
        # For vault/local backends, this persists
        os.environ[f"MACHINE_CRED_{hostname.upper()}_USER"] = user
        os.environ[f"MACHINE_CRED_{hostname.upper()}_PASSWORD"] = password
        return True


settings = Settings()

