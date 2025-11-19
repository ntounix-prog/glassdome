"""
Platform Integration Layer
"""
from backend.platforms.proxmox_client import ProxmoxClient
from backend.platforms.azure_client import AzureClient
from backend.platforms.aws_client import AWSClient

__all__ = [
    "ProxmoxClient",
    "AzureClient",
    "AWSClient",
]

