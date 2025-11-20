"""
Platform Integration Layer

Supported Platforms:
- Proxmox VE (on-prem)
- VMware ESXi (on-prem, no vCenter required)
- AWS (cloud)
- Azure (cloud)
"""
from glassdome.platforms.base import PlatformClient, VMStatus
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.platforms.esxi_client import ESXiClient
from glassdome.platforms.azure_client import AzureClient
from glassdome.platforms.aws_client import AWSClient

__all__ = [
    "PlatformClient",
    "VMStatus",
    "ProxmoxClient",
    "ESXiClient",
    "AzureClient",
    "AWSClient",
]

