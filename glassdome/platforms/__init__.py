"""
Platform client for   Init  

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
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

