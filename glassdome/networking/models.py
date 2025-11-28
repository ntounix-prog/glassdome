"""
Models module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

from glassdome.core.database import Base


class NetworkType(str, Enum):
    """Types of networks"""
    ISOLATED = "isolated"      # No external access
    NAT = "nat"                # NAT to external
    BRIDGED = "bridged"        # Direct bridge to physical
    ROUTED = "routed"          # Routed through gateway


class NetworkDefinition(Base):
    """
    Abstract network definition - platform-agnostic
    
    The universal constants:
    - name: Human-readable identifier
    - cidr: Address space (e.g., "192.168.100.0/24")
    - vlan_id: VLAN tag (every platform has VLANs)
    - gateway: Network gateway address
    """
    __tablename__ = "network_definitions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identity
    name = Column(String(100), nullable=False, unique=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    # Universal Constants
    cidr = Column(String(50), nullable=False)           # "192.168.100.0/24"
    vlan_id = Column(Integer, nullable=True)            # VLAN tag (optional)
    gateway = Column(String(50), nullable=True)         # "192.168.100.1"
    
    # Network Type
    network_type = Column(String(20), default=NetworkType.ISOLATED.value)
    
    # DHCP Configuration (optional)
    dhcp_enabled = Column(Boolean, default=False)
    dhcp_range_start = Column(String(50), nullable=True)  # "192.168.100.100"
    dhcp_range_end = Column(String(50), nullable=True)    # "192.168.100.200"
    dns_servers = Column(JSON, nullable=True)             # ["8.8.8.8", "8.8.4.4"]
    
    # Lab Association
    lab_id = Column(String(100), nullable=True, index=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    platform_mappings = relationship("PlatformNetworkMapping", back_populates="network", cascade="all, delete-orphan")
    interfaces = relationship("VMInterface", back_populates="network", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "cidr": self.cidr,
            "vlan_id": self.vlan_id,
            "gateway": self.gateway,
            "network_type": self.network_type,
            "dhcp_enabled": self.dhcp_enabled,
            "dhcp_range_start": self.dhcp_range_start,
            "dhcp_range_end": self.dhcp_range_end,
            "dns_servers": self.dns_servers,
            "lab_id": self.lab_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @property
    def network_address(self) -> str:
        """Get network address from CIDR"""
        return self.cidr.split("/")[0] if self.cidr else None
    
    @property
    def prefix_length(self) -> int:
        """Get prefix length from CIDR"""
        return int(self.cidr.split("/")[1]) if self.cidr and "/" in self.cidr else 24


class PlatformNetworkMapping(Base):
    """
    Maps abstract networks to platform-specific implementations
    
    Each platform has its own way of representing networks:
    - Proxmox: bridge name (vmbr1), VLAN tag
    - ESXi: vSwitch, port group name
    - AWS: VPC ID, subnet ID
    - Azure: VNet name, subnet name
    """
    __tablename__ = "platform_network_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Link to abstract network
    network_id = Column(Integer, ForeignKey("network_definitions.id"), nullable=False)
    
    # Platform identification
    platform = Column(String(50), nullable=False)  # proxmox, esxi, aws, azure
    platform_instance = Column(String(50), nullable=True)  # "01", "02", region, etc.
    
    # Platform-specific identifiers (JSON for flexibility)
    # Proxmox: {"bridge": "vmbr1", "vlan_tag": 100}
    # ESXi: {"vswitch": "vSwitch0", "portgroup": "attack-net"}
    # AWS: {"vpc_id": "vpc-xxx", "subnet_id": "subnet-xxx", "security_group": "sg-xxx"}
    # Azure: {"vnet": "glassdome-vnet", "subnet": "attack-subnet", "nsg": "attack-nsg"}
    platform_config = Column(JSON, nullable=False)
    
    # Status
    provisioned = Column(Boolean, default=False)
    provision_error = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    
    # Relationship
    network = relationship("NetworkDefinition", back_populates="platform_mappings")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "network_id": self.network_id,
            "platform": self.platform,
            "platform_instance": self.platform_instance,
            "platform_config": self.platform_config,
            "provisioned": self.provisioned,
            "provision_error": self.provision_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VMInterface(Base):
    """
    Tracks VM network interfaces
    
    Universal constants for every VM NIC:
    - Which network it's connected to
    - MAC address
    - IP address (static or DHCP)
    - Interface name in the guest OS
    """
    __tablename__ = "vm_interfaces"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Lab Association (for orchestration - pick up all resources for a lab)
    lab_id = Column(String(100), nullable=True, index=True)
    
    # VM Identification
    vm_id = Column(String(100), nullable=False, index=True)  # Platform VM ID
    platform = Column(String(50), nullable=False)            # proxmox, esxi, aws, azure
    platform_instance = Column(String(50), nullable=True)    # "01", "02", region, etc.
    
    # Network Link
    network_id = Column(Integer, ForeignKey("network_definitions.id"), nullable=True)
    
    # Interface Details
    interface_index = Column(Integer, default=0)             # 0 = first NIC, 1 = second, etc.
    interface_name = Column(String(50), nullable=True)       # "eth0", "ens18", "Ethernet 2"
    mac_address = Column(String(20), nullable=True)          # "BC:24:11:xx:xx:xx"
    
    # IP Configuration
    ip_address = Column(String(50), nullable=True)           # "192.168.100.10"
    ip_method = Column(String(20), default="dhcp")           # "dhcp" or "static"
    subnet_mask = Column(String(50), nullable=True)          # "255.255.255.0" or "/24"
    gateway = Column(String(50), nullable=True)              # Interface-specific gateway
    
    # Platform-specific details
    # Proxmox: {"device": "net0", "bridge": "vmbr1", "model": "virtio"}
    # ESXi: {"adapter_type": "vmxnet3", "portgroup": "attack-net"}
    # AWS: {"eni_id": "eni-xxx", "subnet_id": "subnet-xxx"}
    platform_config = Column(JSON, nullable=True)
    
    # State
    connected = Column(Boolean, default=True)
    last_seen = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship
    network = relationship("NetworkDefinition", back_populates="interfaces")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "lab_id": self.lab_id,
            "vm_id": self.vm_id,
            "platform": self.platform,
            "platform_instance": self.platform_instance,
            "network_id": self.network_id,
            "interface_index": self.interface_index,
            "interface_name": self.interface_name,
            "mac_address": self.mac_address,
            "ip_address": self.ip_address,
            "ip_method": self.ip_method,
            "subnet_mask": self.subnet_mask,
            "gateway": self.gateway,
            "platform_config": self.platform_config,
            "connected": self.connected,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DeployedVM(Base):
    """
    Tracks deployed VMs per lab
    
    This is the key for orchestration - when moving a lab,
    the orchestrator queries all DeployedVMs with the same lab_id.
    """
    __tablename__ = "deployed_vms"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Lab Association - THE KEY for migration
    lab_id = Column(String(100), nullable=False, index=True)
    
    # VM Identity
    name = Column(String(255), nullable=False)              # Human-readable name
    vm_id = Column(String(100), nullable=False, index=True) # Platform VM ID (e.g., "101", "i-0abc123")
    
    # Platform Location
    platform = Column(String(50), nullable=False)           # proxmox, esxi, aws, azure
    platform_instance = Column(String(50), nullable=True)   # "01", "02", "us-east-1"
    
    # VM Configuration (for migration/recreation)
    os_type = Column(String(50), nullable=True)             # linux, windows
    template_id = Column(String(100), nullable=True)        # Source template used
    cpu_cores = Column(Integer, nullable=True)
    memory_mb = Column(Integer, nullable=True)
    disk_gb = Column(Integer, nullable=True)
    
    # State
    status = Column(String(50), default="deployed")         # deployed, migrating, stopped, deleted
    ip_address = Column(String(50), nullable=True)          # Primary IP
    
    # Migration tracking
    source_platform = Column(String(50), nullable=True)     # Original platform if migrated
    source_vm_id = Column(String(100), nullable=True)       # Original VM ID if migrated
    migrated_at = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    interfaces = relationship("VMInterface", 
                            primaryjoin="DeployedVM.vm_id == foreign(VMInterface.vm_id)",
                            viewonly=True)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "lab_id": self.lab_id,
            "name": self.name,
            "vm_id": self.vm_id,
            "platform": self.platform,
            "platform_instance": self.platform_instance,
            "os_type": self.os_type,
            "template_id": self.template_id,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "disk_gb": self.disk_gb,
            "status": self.status,
            "ip_address": self.ip_address,
            "source_platform": self.source_platform,
            "source_vm_id": self.source_vm_id,
            "migrated_at": self.migrated_at.isoformat() if self.migrated_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Helper Functions
# ============================================================================

def cidr_to_netmask(cidr: str) -> str:
    """Convert CIDR prefix to subnet mask"""
    prefix_to_mask = {
        8: "255.0.0.0",
        16: "255.255.0.0",
        24: "255.255.255.0",
        25: "255.255.255.128",
        26: "255.255.255.192",
        27: "255.255.255.224",
        28: "255.255.255.240",
        29: "255.255.255.248",
        30: "255.255.255.252",
    }
    prefix = int(cidr.split("/")[1]) if "/" in cidr else 24
    return prefix_to_mask.get(prefix, "255.255.255.0")


def get_network_from_ip(ip: str, prefix: int = 24) -> str:
    """Calculate network address from IP and prefix"""
    parts = [int(p) for p in ip.split(".")]
    if prefix >= 24:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/{prefix}"
    elif prefix >= 16:
        return f"{parts[0]}.{parts[1]}.0.0/{prefix}"
    else:
        return f"{parts[0]}.0.0.0/{prefix}"

