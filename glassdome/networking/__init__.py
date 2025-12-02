"""
Networking module

Provides platform-agnostic network orchestration and address allocation.

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from glassdome.networking.models import (
    NetworkDefinition,
    PlatformNetworkMapping,
    VMInterface,
    DeployedVM,
    NetworkType,
    cidr_to_netmask,
    get_network_from_ip,
)

from glassdome.networking.orchestrator import (
    NetworkOrchestrator,
    PlatformNetworkHandler,
    get_network_orchestrator,
)

from glassdome.networking.address_allocator import (
    NetworkAddressAllocator,
    LabNetworkAllocation,
    SubnetAllocation,
    SubnetType,
    get_address_allocator,
)

__all__ = [
    # Models
    "NetworkDefinition",
    "PlatformNetworkMapping",
    "VMInterface",
    "DeployedVM",
    "NetworkType",
    "cidr_to_netmask",
    "get_network_from_ip",
    # Orchestrator
    "NetworkOrchestrator",
    "PlatformNetworkHandler",
    "get_network_orchestrator",
    # Address Allocator
    "NetworkAddressAllocator",
    "LabNetworkAllocation",
    "SubnetAllocation",
    "SubnetType",
    "get_address_allocator",
]

