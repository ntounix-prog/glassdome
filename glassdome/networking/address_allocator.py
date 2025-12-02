"""
Network Address Allocator

Manages IP address allocation for labs across platforms.
Ensures non-overlapping addresses for concurrent lab deployments.

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import ipaddress
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class SubnetType(str, Enum):
    """Types of subnets in a lab network"""
    PUBLIC = "public"       # Guacamole gateway (internet-facing)
    ATTACK = "attack"       # Kali/Parrot attack console
    DMZ = "dmz"             # Web servers, DNS
    INTERNAL = "internal"   # Databases, file servers
    MANAGEMENT = "management"  # Domain controllers, admin


@dataclass
class SubnetAllocation:
    """Single subnet allocation within a lab"""
    subnet_type: SubnetType
    cidr: str
    gateway: str
    dhcp_start: str
    dhcp_end: str
    is_public: bool = False
    
    @property
    def network(self) -> ipaddress.IPv4Network:
        return ipaddress.ip_network(self.cidr)
    
    def get_vm_ip(self, index: int) -> str:
        """Get IP for VM at index (starting at .10)"""
        hosts = list(self.network.hosts())
        # Reserve .1-.9 for infrastructure, VMs start at .10
        return str(hosts[9 + index])


@dataclass
class LabNetworkAllocation:
    """Complete network allocation for a lab"""
    lab_id: str
    lab_number: int
    vpc_cidr: str
    subnets: Dict[SubnetType, SubnetAllocation] = field(default_factory=dict)
    
    @property
    def public_subnet(self) -> Optional[SubnetAllocation]:
        return self.subnets.get(SubnetType.PUBLIC)
    
    @property
    def attack_subnet(self) -> Optional[SubnetAllocation]:
        return self.subnets.get(SubnetType.ATTACK)
    
    @property
    def dmz_subnet(self) -> Optional[SubnetAllocation]:
        return self.subnets.get(SubnetType.DMZ)
    
    @property
    def internal_subnet(self) -> Optional[SubnetAllocation]:
        return self.subnets.get(SubnetType.INTERNAL)
    
    def get_vm_ip(self, subnet_type: SubnetType, vm_index: int) -> str:
        """Get IP address for a VM within a specific subnet"""
        subnet = self.subnets.get(subnet_type)
        if not subnet:
            raise ValueError(f"No {subnet_type.value} subnet in lab {self.lab_id}")
        return subnet.get_vm_ip(vm_index)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        return {
            "lab_id": self.lab_id,
            "lab_number": self.lab_number,
            "vpc_cidr": self.vpc_cidr,
            "subnets": {
                st.value: {
                    "cidr": sa.cidr,
                    "gateway": sa.gateway,
                    "dhcp_start": sa.dhcp_start,
                    "dhcp_end": sa.dhcp_end,
                    "is_public": sa.is_public
                }
                for st, sa in self.subnets.items()
            }
        }


class NetworkAddressAllocator:
    """
    Allocates non-overlapping network addresses for labs.
    
    Address Scheme (AWS):
    =====================
    - VPC: 10.{lab_number}.0.0/16
    - Public subnet: 10.{lab_number}.0.0/24  (Guacamole)
    - Attack subnet: 10.{lab_number}.100.0/24 (Kali)
    - DMZ subnet: 10.{lab_number}.1.0/24     (Web servers)
    - Internal subnet: 10.{lab_number}.2.0/24 (Databases)
    - Management subnet: 10.{lab_number}.3.0/24 (DC, Admin)
    
    This allows 254 concurrent labs without overlap.
    
    Address Scheme (Proxmox VLAN):
    ==============================
    - Lab network: 10.{vlan_id}.0.0/24
    - Gateway: 10.{vlan_id}.0.1 (pfSense LAN)
    - VMs: 10.{vlan_id}.0.10+ (DHCP or static)
    """
    
    # Subnet offset mapping within the /16 VPC
    SUBNET_OFFSETS = {
        SubnetType.PUBLIC: 0,       # 10.X.0.0/24
        SubnetType.DMZ: 1,          # 10.X.1.0/24
        SubnetType.INTERNAL: 2,     # 10.X.2.0/24
        SubnetType.MANAGEMENT: 3,   # 10.X.3.0/24
        SubnetType.ATTACK: 100,     # 10.X.100.0/24
    }
    
    def __init__(self):
        self._allocations: Dict[str, LabNetworkAllocation] = {}
        self._used_lab_numbers: Set[int] = set()
        self._next_lab_number = 1
    
    def allocate_lab_networks(
        self,
        lab_id: str,
        subnet_types: Optional[List[SubnetType]] = None,
        platform: str = "aws"
    ) -> LabNetworkAllocation:
        """
        Allocate network addresses for a new lab.
        
        Args:
            lab_id: Unique lab identifier
            subnet_types: Which subnets to create (default: all standard ones)
            platform: Target platform (aws, proxmox, azure)
        
        Returns:
            LabNetworkAllocation with all subnet details
        """
        # Return existing allocation if already allocated
        if lab_id in self._allocations:
            logger.info(f"Returning existing allocation for lab {lab_id}")
            return self._allocations[lab_id]
        
        # Find next available lab number
        lab_number = self._get_next_lab_number()
        
        # Default subnet types for a full lab
        if subnet_types is None:
            subnet_types = [
                SubnetType.PUBLIC,
                SubnetType.ATTACK,
                SubnetType.DMZ,
                SubnetType.INTERNAL,
            ]
        
        # Create VPC CIDR
        vpc_cidr = f"10.{lab_number}.0.0/16"
        
        # Create subnet allocations
        subnets = {}
        for subnet_type in subnet_types:
            offset = self.SUBNET_OFFSETS.get(subnet_type, 0)
            subnet_cidr = f"10.{lab_number}.{offset}.0/24"
            gateway = f"10.{lab_number}.{offset}.1"
            
            # DHCP range: .100 to .200
            dhcp_start = f"10.{lab_number}.{offset}.100"
            dhcp_end = f"10.{lab_number}.{offset}.200"
            
            subnets[subnet_type] = SubnetAllocation(
                subnet_type=subnet_type,
                cidr=subnet_cidr,
                gateway=gateway,
                dhcp_start=dhcp_start,
                dhcp_end=dhcp_end,
                is_public=(subnet_type == SubnetType.PUBLIC)
            )
        
        allocation = LabNetworkAllocation(
            lab_id=lab_id,
            lab_number=lab_number,
            vpc_cidr=vpc_cidr,
            subnets=subnets
        )
        
        self._allocations[lab_id] = allocation
        self._used_lab_numbers.add(lab_number)
        
        logger.info(f"Allocated networks for lab {lab_id}: VPC {vpc_cidr}")
        for st, sa in subnets.items():
            logger.info(f"  {st.value}: {sa.cidr} (gateway: {sa.gateway})")
        
        return allocation
    
    def allocate_proxmox_vlan_network(
        self,
        lab_id: str,
        vlan_id: int
    ) -> LabNetworkAllocation:
        """
        Allocate network for a Proxmox VLAN-based lab.
        
        Proxmox uses a simpler model: single /24 network with pfSense gateway.
        
        Args:
            lab_id: Unique lab identifier
            vlan_id: VLAN ID (100-254)
        
        Returns:
            LabNetworkAllocation with single combined subnet
        """
        if lab_id in self._allocations:
            return self._allocations[lab_id]
        
        # For Proxmox, we use the VLAN ID as the third octet
        vpc_cidr = f"10.{vlan_id}.0.0/24"
        
        # Single "lab" subnet for Proxmox (pfSense handles segmentation)
        lab_subnet = SubnetAllocation(
            subnet_type=SubnetType.INTERNAL,  # Generic lab network
            cidr=f"10.{vlan_id}.0.0/24",
            gateway=f"10.{vlan_id}.0.1",  # pfSense LAN IP
            dhcp_start=f"10.{vlan_id}.0.100",
            dhcp_end=f"10.{vlan_id}.0.200",
            is_public=False
        )
        
        allocation = LabNetworkAllocation(
            lab_id=lab_id,
            lab_number=vlan_id,
            vpc_cidr=vpc_cidr,
            subnets={SubnetType.INTERNAL: lab_subnet}
        )
        
        self._allocations[lab_id] = allocation
        self._used_lab_numbers.add(vlan_id)
        
        logger.info(f"Allocated Proxmox VLAN network for lab {lab_id}: VLAN {vlan_id}, {vpc_cidr}")
        
        return allocation
    
    def get_allocation(self, lab_id: str) -> Optional[LabNetworkAllocation]:
        """Get existing allocation for a lab"""
        return self._allocations.get(lab_id)
    
    def release_lab_networks(self, lab_id: str) -> bool:
        """
        Release network allocation when lab is terminated.
        
        Args:
            lab_id: Lab to release
        
        Returns:
            True if released, False if not found
        """
        allocation = self._allocations.pop(lab_id, None)
        if allocation:
            self._used_lab_numbers.discard(allocation.lab_number)
            logger.info(f"Released network allocation for lab {lab_id}")
            return True
        return False
    
    def _get_next_lab_number(self) -> int:
        """Find next available lab number (1-254)"""
        while self._next_lab_number in self._used_lab_numbers:
            self._next_lab_number += 1
            if self._next_lab_number > 254:
                self._next_lab_number = 1
        
        # Safety check
        if len(self._used_lab_numbers) >= 254:
            raise RuntimeError("Maximum number of concurrent labs (254) reached")
        
        return self._next_lab_number
    
    def get_statistics(self) -> Dict:
        """Get allocation statistics"""
        return {
            "total_allocations": len(self._allocations),
            "used_lab_numbers": sorted(self._used_lab_numbers),
            "available_slots": 254 - len(self._used_lab_numbers)
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_allocator: Optional[NetworkAddressAllocator] = None


def get_address_allocator() -> NetworkAddressAllocator:
    """Get or create the address allocator singleton"""
    global _allocator
    if _allocator is None:
        _allocator = NetworkAddressAllocator()
    return _allocator

