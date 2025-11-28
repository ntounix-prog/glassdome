"""
Models module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
import json


class ResourceType(str, Enum):
    """Types of resources tracked by the registry"""
    # Tier 1 - Lab Resources (1s updates)
    LAB = "lab"
    LAB_VM = "lab_vm"
    LAB_NETWORK = "lab_network"
    
    # Tier 2 - Virtualization (5-10s updates)
    VM = "vm"
    TEMPLATE = "template"
    STORAGE_POOL = "storage_pool"
    
    # Tier 3 - Infrastructure (30-60s updates)
    HOST = "host"
    SWITCH = "switch"
    SWITCH_PORT = "switch_port"
    VLAN = "vlan"
    STORAGE_SYSTEM = "storage_system"


class ResourceState(str, Enum):
    """Standard resource states"""
    UNKNOWN = "unknown"
    CREATING = "creating"
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"
    DELETING = "deleting"
    DELETED = "deleted"
    DEGRADED = "degraded"
    HEALTHY = "healthy"


class DriftType(str, Enum):
    """Types of drift detected"""
    MISSING = "missing"           # Resource should exist but doesn't
    EXTRA = "extra"               # Resource exists but shouldn't
    STATE_MISMATCH = "state"      # Wrong state (running vs stopped)
    NAME_MISMATCH = "name"        # Wrong name
    CONFIG_MISMATCH = "config"    # Configuration differs
    IP_MISMATCH = "ip"            # IP address differs
    NETWORK_MISMATCH = "network"  # Wrong network/VLAN


class EventType(str, Enum):
    """Registry event types"""
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    STATE_CHANGED = "state_changed"
    DRIFT_DETECTED = "drift_detected"
    DRIFT_RESOLVED = "drift_resolved"
    RECONCILE_START = "reconcile_start"
    RECONCILE_COMPLETE = "reconcile_complete"
    RECONCILE_FAILED = "reconcile_failed"
    AGENT_HEARTBEAT = "agent_heartbeat"


@dataclass
class Resource:
    """
    Universal resource representation.
    
    Every resource in the infrastructure - VM, network, host, switch - 
    is represented by this model in the registry.
    """
    # Identity
    id: str                           # Unique ID (platform:type:resource_id)
    resource_type: ResourceType
    name: str
    
    # Platform location
    platform: str                     # proxmox, esxi, aws, truenas, nexus
    platform_instance: Optional[str] = None  # "01", "02", region
    platform_id: Optional[str] = None  # Platform-specific ID (VMID, etc.)
    
    # State
    state: ResourceState = ResourceState.UNKNOWN
    state_detail: Optional[str] = None  # Additional state info
    
    # Lab association (Tier 1 resources)
    lab_id: Optional[str] = None
    
    # Configuration snapshot
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Desired state (for reconciliation)
    desired_state: Optional[ResourceState] = None
    desired_config: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    
    # Tier (for update frequency)
    tier: int = 2  # Default to Tier 2
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resource_type": self.resource_type.value,
            "name": self.name,
            "platform": self.platform,
            "platform_instance": self.platform_instance,
            "platform_id": self.platform_id,
            "state": self.state.value,
            "state_detail": self.state_detail,
            "lab_id": self.lab_id,
            "config": self.config,
            "desired_state": self.desired_state.value if self.desired_state else None,
            "desired_config": self.desired_config,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "tier": self.tier,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Resource":
        return cls(
            id=data["id"],
            resource_type=ResourceType(data["resource_type"]),
            name=data["name"],
            platform=data["platform"],
            platform_instance=data.get("platform_instance"),
            platform_id=data.get("platform_id"),
            state=ResourceState(data.get("state", "unknown")),
            state_detail=data.get("state_detail"),
            lab_id=data.get("lab_id"),
            config=data.get("config", {}),
            desired_state=ResourceState(data["desired_state"]) if data.get("desired_state") else None,
            desired_config=data.get("desired_config", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            last_seen=datetime.fromisoformat(data["last_seen"]) if data.get("last_seen") else datetime.utcnow(),
            tier=data.get("tier", 2),
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Resource":
        return cls.from_dict(json.loads(json_str))
    
    @staticmethod
    def make_id(platform: str, resource_type: str, platform_id: str, instance: str = None) -> str:
        """Generate a unique resource ID"""
        if instance:
            return f"{platform}:{instance}:{resource_type}:{platform_id}"
        return f"{platform}:{resource_type}:{platform_id}"


@dataclass
class StateChange:
    """
    Represents a state change event.
    Published to the event bus when resources change.
    """
    event_type: EventType
    resource_id: str
    resource_type: ResourceType
    
    # Change details
    old_state: Optional[ResourceState] = None
    new_state: Optional[ResourceState] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    
    # Context
    lab_id: Optional[str] = None
    platform: Optional[str] = None
    agent: Optional[str] = None  # Which agent detected the change
    
    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type.value,
            "old_state": self.old_state.value if self.old_state else None,
            "new_state": self.new_state.value if self.new_state else None,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "lab_id": self.lab_id,
            "platform": self.platform,
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateChange":
        return cls(
            event_type=EventType(data["event_type"]),
            resource_id=data["resource_id"],
            resource_type=ResourceType(data["resource_type"]),
            old_state=ResourceState(data["old_state"]) if data.get("old_state") else None,
            new_state=ResourceState(data["new_state"]) if data.get("new_state") else None,
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            lab_id=data.get("lab_id"),
            platform=data.get("platform"),
            agent=data.get("agent"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.utcnow(),
        )


@dataclass 
class Drift:
    """
    Represents detected drift between desired and actual state.
    """
    resource_id: str
    resource_type: ResourceType
    drift_type: DriftType
    
    # What we expected vs what we found
    expected: Any
    actual: Any
    
    # Severity and action
    severity: str = "warning"  # info, warning, critical
    auto_fix: bool = False     # Can this be auto-fixed?
    fix_action: Optional[str] = None  # Suggested fix action
    
    # Context
    lab_id: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type.value,
            "drift_type": self.drift_type.value,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "auto_fix": self.auto_fix,
            "fix_action": self.fix_action,
            "lab_id": self.lab_id,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class LabSnapshot:
    """
    Complete snapshot of a lab's state.
    Used for quick lab status checks.
    """
    lab_id: str
    name: Optional[str] = None
    
    # Resources
    vms: List[Resource] = field(default_factory=list)
    networks: List[Resource] = field(default_factory=list)
    gateway: Optional[Resource] = None
    
    # Health
    total_vms: int = 0
    running_vms: int = 0
    healthy: bool = True
    drift_count: int = 0
    
    # Timestamps
    created_at: Optional[datetime] = None
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lab_id": self.lab_id,
            "name": self.name,
            "vms": [vm.to_dict() for vm in self.vms],
            "networks": [net.to_dict() for net in self.networks],
            "gateway": self.gateway.to_dict() if self.gateway else None,
            "total_vms": self.total_vms,
            "running_vms": self.running_vms,
            "healthy": self.healthy,
            "drift_count": self.drift_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat(),
        }

