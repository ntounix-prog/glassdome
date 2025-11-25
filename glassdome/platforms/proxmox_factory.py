"""
Proxmox Client Factory

Creates ProxmoxClient instances for specific Proxmox instances.
Supports multiple Proxmox platforms with instance selection.
"""
from typing import Optional
from glassdome.core.config import settings
from glassdome.platforms.proxmox_client import ProxmoxClient
import logging

logger = logging.getLogger(__name__)


def get_proxmox_client(instance_id: str = "01", default_node: Optional[str] = None, default_storage: str = "local-lvm") -> ProxmoxClient:
    """
    Get ProxmoxClient for a specific Proxmox instance.
    
    Args:
        instance_id: Proxmox instance ID ("01", "02", "03", etc.)
                    Use "01" for default/backward compatible instance
        default_node: Override default node name (optional)
        default_storage: Override default storage (optional)
    
    Returns:
        ProxmoxClient instance configured for the specified Proxmox platform
    
    Raises:
        ValueError: If instance is not configured or missing required credentials
    """
    # Get configuration for this instance
    config = settings.get_proxmox_config(instance_id)
    
    # Validate required fields
    if not config.get("host"):
        raise ValueError(f"Proxmox instance {instance_id} not configured: PROXMOX_{instance_id}_HOST not set")
    
    if not config.get("user"):
        raise ValueError(f"Proxmox instance {instance_id} not configured: PROXMOX_{instance_id}_USER not set")
    
    # Check for authentication method
    has_token = config.get("token_name") and config.get("token_value")
    has_password = config.get("password")
    
    if not has_token and not has_password:
        raise ValueError(
            f"Proxmox instance {instance_id} missing credentials. "
            f"Set PROXMOX_{instance_id}_TOKEN_NAME and PROXMOX_TOKEN_VALUE_{instance_id} "
            f"or PROXMOX_{instance_id}_PASSWORD"
        )
    
    # Create client
    client = ProxmoxClient(
        host=config["host"],
        user=config["user"],
        password=config.get("password"),
        token_name=config.get("token_name"),
        token_value=config.get("token_value"),
        verify_ssl=config.get("verify_ssl", False),
        default_node=default_node or config.get("node", "pve"),
        default_storage=default_storage
    )
    
    logger.info(f"Created ProxmoxClient for instance {instance_id} ({config['host']})")
    return client


def list_available_proxmox_instances() -> list[str]:
    """
    List all configured Proxmox instances.
    
    Returns:
        List of instance IDs (e.g., ["01", "02"])
    """
    return settings.list_proxmox_instances()

