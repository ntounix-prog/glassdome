"""
Core Configuration Management
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
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
    
    # Proxmox
    proxmox_host: Optional[str] = None
    proxmox_user: Optional[str] = None
    proxmox_password: Optional[str] = None
    proxmox_token_name: Optional[str] = None
    proxmox_token_value: Optional[str] = None
    proxmox_verify_ssl: bool = False
    proxmox_node: str = "pve"
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

