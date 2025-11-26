"""
Glassdome Networking Module

Platform-agnostic network management with the universal constants:
- Host interface
- VLAN
- Address space
"""

from glassdome.networking.models import (
    NetworkDefinition,
    PlatformNetworkMapping,
    VMInterface,
    NetworkType,
    cidr_to_netmask,
    get_network_from_ip,
)

__all__ = [
    "NetworkDefinition",
    "PlatformNetworkMapping",
    "VMInterface",
    "NetworkType",
    "cidr_to_netmask",
    "get_network_from_ip",
]

