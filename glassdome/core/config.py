"""
Core Configuration Management
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, Dict, Any
from pathlib import Path
import os
import re


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow"  # Allow extra fields for multi-instance support
    )
    """Application settings"""
    
    # Application
    app_name: str = "Glassdome"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    
    # API - Changed default port to avoid conflicts
    api_prefix: str = "/api"
    backend_port: int = 8001
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
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map legacy variables to standard ones if not already set
        if not self.proxmox_password and self.proxmox_admin_passwd:
            self.proxmox_password = self.proxmox_admin_passwd
        if not self.proxmox_user and self.proxmox_admin:
            self.proxmox_user = self.proxmox_admin
    
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
        env_file_path = Path(".env")
        env_vars = {}
        
        if env_file_path.exists():
            with open(env_file_path) as f:
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
        
        # Build config dict
        config = {
            "host": env_vars.get("host") or os.getenv(f"PROXMOX_{instance_id}_HOST"),
            "user": env_vars.get("user") or os.getenv(f"PROXMOX_{instance_id}_USER"),
            "password": env_vars.get("password") or os.getenv(f"PROXMOX_{instance_id}_PASSWORD"),
            "token_name": env_vars.get("token_name") or os.getenv(f"PROXMOX_{instance_id}_TOKEN_NAME") or self.proxmox_token_name,
            "token_value": env_vars.get("token_value") or os.getenv(f"PROXMOX_TOKEN_VALUE_{instance_id}"),
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
        
        # Find all PROXMOX_XX_HOST variables
        pattern = re.compile(r'^PROXMOX_(\d+)_HOST$')
        for key in os.environ.keys():
            match = pattern.match(key)
            if match:
                instance_id = match.group(1)
                if instance_id not in instances:
                    instances.append(instance_id)
        
        # Also check for PROXMOX_TOKEN_VALUE_XX format
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
    
    # Mailcow
    mail_api: Optional[str] = None  # Mailcow API Bearer token (from .env: MAIL_API)
    mailcow_api_url: Optional[str] = None  # Mailcow API URL (e.g., https://mail.xisx.org)
    mailcow_domain: str = "xisx.org"
    mailcow_imap_host: Optional[str] = None  # Defaults to mail.{domain}
    mailcow_smtp_host: Optional[str] = None  # Defaults to mail.{domain}
    mailcow_smtp_port: int = 587
    mailcow_verify_ssl: bool = False  # Disable SSL verification for self-signed certs


settings = Settings()

