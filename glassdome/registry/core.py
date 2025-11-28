"""
Core module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, AsyncIterator, Set
import redis.asyncio as redis

from glassdome.registry.models import (
    Resource, ResourceType, ResourceState,
    StateChange, EventType, Drift, DriftType, LabSnapshot
)
from glassdome.core.config import settings

logger = logging.getLogger(__name__)


class LabRegistry:
    """
    Central registry for all lab and infrastructure resources.
    
    Features:
    - Fast state access via Redis (<10ms)
    - Event streaming via Redis pub/sub
    - Automatic drift detection
    - Tiered update support (1s / 5-10s / 30-60s)
    """
    
    # Redis key prefixes
    RESOURCE_PREFIX = "registry:resource:"
    LAB_PREFIX = "registry:lab:"
    EVENT_CHANNEL = "registry:events"
    AGENT_PREFIX = "registry:agent:"
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._running = False
        self._event_handlers: List[callable] = []
        
    async def connect(self):
        """Connect to Redis"""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            logger.info(f"Registry connected to Redis")
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self._pubsub:
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        self._redis = None
        self._pubsub = None
    
    # =========================================================================
    # Resource CRUD
    # =========================================================================
    
    async def register(self, resource: Resource) -> bool:
        """
        Register or update a resource in the registry.
        Publishes a state change event.
        """
        await self.connect()
        
        key = f"{self.RESOURCE_PREFIX}{resource.id}"
        
        # Check if exists (for event type)
        existing_json = await self._redis.get(key)
        existing = Resource.from_json(existing_json) if existing_json else None
        
        # Update timestamps
        resource.updated_at = datetime.utcnow()
        resource.last_seen = datetime.utcnow()
        if not existing:
            resource.created_at = datetime.utcnow()
        
        # Store in Redis
        await self._redis.set(key, resource.to_json())
        
        # Add to type index
        type_key = f"registry:index:type:{resource.resource_type.value}"
        await self._redis.sadd(type_key, resource.id)
        
        # Add to lab index if lab resource
        if resource.lab_id:
            lab_key = f"{self.LAB_PREFIX}{resource.lab_id}:resources"
            await self._redis.sadd(lab_key, resource.id)
        
        # Publish event
        event_type = EventType.UPDATED if existing else EventType.CREATED
        if existing and existing.state != resource.state:
            event_type = EventType.STATE_CHANGED
        
        await self.publish_event(StateChange(
            event_type=event_type,
            resource_id=resource.id,
            resource_type=resource.resource_type,
            old_state=existing.state if existing else None,
            new_state=resource.state,
            lab_id=resource.lab_id,
            platform=resource.platform,
        ))
        
        logger.debug(f"Registered resource: {resource.id} ({resource.name})")
        return True
    
    async def get(self, resource_id: str) -> Optional[Resource]:
        """Get a resource by ID"""
        await self.connect()
        
        key = f"{self.RESOURCE_PREFIX}{resource_id}"
        data = await self._redis.get(key)
        
        if data:
            return Resource.from_json(data)
        return None
    
    async def delete(self, resource_id: str) -> bool:
        """Delete a resource from the registry"""
        await self.connect()
        
        resource = await self.get(resource_id)
        if not resource:
            return False
        
        key = f"{self.RESOURCE_PREFIX}{resource_id}"
        await self._redis.delete(key)
        
        # Remove from indexes
        type_key = f"registry:index:type:{resource.resource_type.value}"
        await self._redis.srem(type_key, resource_id)
        
        if resource.lab_id:
            lab_key = f"{self.LAB_PREFIX}{resource.lab_id}:resources"
            await self._redis.srem(lab_key, resource_id)
        
        # Publish event
        await self.publish_event(StateChange(
            event_type=EventType.DELETED,
            resource_id=resource_id,
            resource_type=resource.resource_type,
            old_state=resource.state,
            lab_id=resource.lab_id,
            platform=resource.platform,
        ))
        
        return True
    
    async def list_by_type(self, resource_type: ResourceType) -> List[Resource]:
        """List all resources of a given type"""
        await self.connect()
        
        type_key = f"registry:index:type:{resource_type.value}"
        resource_ids = await self._redis.smembers(type_key)
        
        resources = []
        for rid in resource_ids:
            resource = await self.get(rid)
            if resource:
                resources.append(resource)
        
        return resources
    
    async def list_by_lab(self, lab_id: str) -> List[Resource]:
        """List all resources for a lab"""
        await self.connect()
        
        lab_key = f"{self.LAB_PREFIX}{lab_id}:resources"
        resource_ids = await self._redis.smembers(lab_key)
        
        resources = []
        for rid in resource_ids:
            resource = await self.get(rid)
            if resource:
                resources.append(resource)
        
        return resources
    
    async def list_by_platform(self, platform: str, instance: str = None) -> List[Resource]:
        """List all resources on a platform"""
        await self.connect()
        
        # Scan for matching resources
        pattern = f"{self.RESOURCE_PREFIX}{platform}:*"
        if instance:
            pattern = f"{self.RESOURCE_PREFIX}{platform}:{instance}:*"
        
        resources = []
        async for key in self._redis.scan_iter(match=pattern):
            data = await self._redis.get(key)
            if data:
                resources.append(Resource.from_json(data))
        
        return resources
    
    # =========================================================================
    # Lab Operations
    # =========================================================================
    
    async def get_lab_snapshot(self, lab_id: str) -> Optional[LabSnapshot]:
        """Get a complete snapshot of a lab's state"""
        resources = await self.list_by_lab(lab_id)
        
        if not resources:
            return None
        
        snapshot = LabSnapshot(lab_id=lab_id)
        
        for resource in resources:
            if resource.resource_type == ResourceType.LAB_VM:
                snapshot.vms.append(resource)
                snapshot.total_vms += 1
                if resource.state == ResourceState.RUNNING:
                    snapshot.running_vms += 1
                # Check if this is the gateway
                if resource.config.get("role") == "gateway":
                    snapshot.gateway = resource
            elif resource.resource_type == ResourceType.LAB_NETWORK:
                snapshot.networks.append(resource)
            elif resource.resource_type == ResourceType.LAB:
                snapshot.name = resource.name
                snapshot.created_at = resource.created_at
        
        # Check health
        drifts = await self.get_drifts(lab_id=lab_id)
        snapshot.drift_count = len(drifts)
        snapshot.healthy = len(drifts) == 0 and snapshot.running_vms == snapshot.total_vms
        
        return snapshot
    
    async def list_labs(self) -> List[str]:
        """List all lab IDs in the registry"""
        await self.connect()
        
        labs = set()
        async for key in self._redis.scan_iter(match=f"{self.LAB_PREFIX}*:resources"):
            # Extract lab_id from key
            parts = key.split(":")
            if len(parts) >= 3:
                labs.add(parts[2])
        
        return list(labs)
    
    # =========================================================================
    # Event System
    # =========================================================================
    
    async def publish_event(self, event: StateChange):
        """Publish a state change event"""
        await self.connect()
        
        # Publish to general channel
        await self._redis.publish(self.EVENT_CHANNEL, event.to_json())
        
        # Also publish to lab-specific channel if applicable
        if event.lab_id:
            lab_channel = f"registry:events:lab:{event.lab_id}"
            await self._redis.publish(lab_channel, event.to_json())
        
        # Store recent events (last 1000)
        event_list_key = "registry:events:recent"
        await self._redis.lpush(event_list_key, event.to_json())
        await self._redis.ltrim(event_list_key, 0, 999)
        
        logger.debug(f"Published event: {event.event_type.value} for {event.resource_id}")
    
    async def subscribe_events(self, lab_id: str = None) -> AsyncIterator[StateChange]:
        """
        Subscribe to state change events.
        
        Args:
            lab_id: If provided, only receive events for this lab
        """
        await self.connect()
        
        pubsub = self._redis.pubsub()
        
        if lab_id:
            channel = f"registry:events:lab:{lab_id}"
        else:
            channel = self.EVENT_CHANNEL
        
        await pubsub.subscribe(channel)
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = StateChange.from_dict(json.loads(message["data"]))
                        yield event
                    except Exception as e:
                        logger.error(f"Failed to parse event: {e}")
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
    
    async def get_recent_events(self, limit: int = 100, lab_id: str = None) -> List[StateChange]:
        """Get recent events"""
        await self.connect()
        
        event_list_key = "registry:events:recent"
        events_json = await self._redis.lrange(event_list_key, 0, limit - 1)
        
        events = []
        for ej in events_json:
            try:
                event = StateChange.from_dict(json.loads(ej))
                if lab_id is None or event.lab_id == lab_id:
                    events.append(event)
            except Exception:
                continue
        
        return events
    
    # =========================================================================
    # Drift Detection
    # =========================================================================
    
    async def detect_drift(self, resource: Resource) -> Optional[Drift]:
        """
        Detect drift between desired and actual state.
        Returns Drift object if drift detected, None otherwise.
        """
        # No desired state = no drift
        if resource.desired_state is None and not resource.desired_config:
            return None
        
        # Check state drift
        if resource.desired_state and resource.state != resource.desired_state:
            return Drift(
                resource_id=resource.id,
                resource_type=resource.resource_type,
                drift_type=DriftType.STATE_MISMATCH,
                expected=resource.desired_state.value,
                actual=resource.state.value,
                severity="warning" if resource.tier == 1 else "info",
                auto_fix=resource.tier == 1,  # Auto-fix Tier 1 only
                fix_action=f"set_state:{resource.desired_state.value}",
                lab_id=resource.lab_id,
            )
        
        # Check name drift
        expected_name = resource.desired_config.get("name")
        if expected_name and resource.name != expected_name:
            return Drift(
                resource_id=resource.id,
                resource_type=resource.resource_type,
                drift_type=DriftType.NAME_MISMATCH,
                expected=expected_name,
                actual=resource.name,
                severity="warning",
                auto_fix=True,
                fix_action=f"rename:{expected_name}",
                lab_id=resource.lab_id,
            )
        
        # Check network/VLAN drift
        expected_network = resource.desired_config.get("network")
        actual_network = resource.config.get("network")
        if expected_network and actual_network != expected_network:
            return Drift(
                resource_id=resource.id,
                resource_type=resource.resource_type,
                drift_type=DriftType.NETWORK_MISMATCH,
                expected=expected_network,
                actual=actual_network,
                severity="critical",
                auto_fix=False,  # Network changes need manual review
                fix_action=f"reconfigure_network:{expected_network}",
                lab_id=resource.lab_id,
            )
        
        return None
    
    async def record_drift(self, drift: Drift):
        """Record a detected drift"""
        await self.connect()
        
        drift_key = f"registry:drift:{drift.resource_id}"
        await self._redis.set(drift_key, json.dumps(drift.to_dict()))
        
        # Add to drift index
        await self._redis.sadd("registry:drift:active", drift.resource_id)
        
        if drift.lab_id:
            await self._redis.sadd(f"registry:drift:lab:{drift.lab_id}", drift.resource_id)
        
        # Publish drift event
        await self.publish_event(StateChange(
            event_type=EventType.DRIFT_DETECTED,
            resource_id=drift.resource_id,
            resource_type=drift.resource_type,
            old_value=drift.expected,
            new_value=drift.actual,
            lab_id=drift.lab_id,
        ))
    
    async def resolve_drift(self, resource_id: str):
        """Mark a drift as resolved"""
        await self.connect()
        
        drift_key = f"registry:drift:{resource_id}"
        drift_data = await self._redis.get(drift_key)
        
        if drift_data:
            drift = Drift(**json.loads(drift_data))
            drift.resolved_at = datetime.utcnow()
            
            # Move to resolved
            await self._redis.srem("registry:drift:active", resource_id)
            if drift.lab_id:
                await self._redis.srem(f"registry:drift:lab:{drift.lab_id}", resource_id)
            
            await self._redis.delete(drift_key)
            
            # Publish resolved event
            await self.publish_event(StateChange(
                event_type=EventType.DRIFT_RESOLVED,
                resource_id=resource_id,
                resource_type=drift.resource_type,
                lab_id=drift.lab_id,
            ))
    
    async def get_drifts(self, lab_id: str = None) -> List[Drift]:
        """Get all active drifts"""
        await self.connect()
        
        if lab_id:
            drift_ids = await self._redis.smembers(f"registry:drift:lab:{lab_id}")
        else:
            drift_ids = await self._redis.smembers("registry:drift:active")
        
        drifts = []
        for rid in drift_ids:
            drift_key = f"registry:drift:{rid}"
            data = await self._redis.get(drift_key)
            if data:
                drifts.append(Drift(**json.loads(data)))
        
        return drifts
    
    # =========================================================================
    # Agent Management
    # =========================================================================
    
    async def agent_heartbeat(self, agent_name: str, status: Dict[str, Any] = None):
        """Record agent heartbeat"""
        await self.connect()
        
        key = f"{self.AGENT_PREFIX}{agent_name}"
        data = {
            "name": agent_name,
            "last_heartbeat": datetime.utcnow().isoformat(),
            "status": status or {},
        }
        await self._redis.set(key, json.dumps(data))
        await self._redis.expire(key, 120)  # Expire after 2 minutes
        
        # Publish heartbeat event
        await self.publish_event(StateChange(
            event_type=EventType.AGENT_HEARTBEAT,
            resource_id=agent_name,
            resource_type=ResourceType.HOST,  # Agents are associated with hosts
            agent=agent_name,
        ))
    
    async def get_agent_status(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent status"""
        await self.connect()
        
        key = f"{self.AGENT_PREFIX}{agent_name}"
        data = await self._redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def list_agents(self) -> List[Dict[str, Any]]:
        """List all agents"""
        await self.connect()
        
        agents = []
        async for key in self._redis.scan_iter(match=f"{self.AGENT_PREFIX}*"):
            data = await self._redis.get(key)
            if data:
                agents.append(json.loads(data))
        
        return agents
    
    # =========================================================================
    # Status
    # =========================================================================
    
    async def get_status(self) -> Dict[str, Any]:
        """Get registry status"""
        await self.connect()
        
        # Count resources by type
        type_counts = {}
        for rt in ResourceType:
            type_key = f"registry:index:type:{rt.value}"
            count = await self._redis.scard(type_key)
            if count > 0:
                type_counts[rt.value] = count
        
        # Count labs
        labs = await self.list_labs()
        
        # Count active drifts
        drift_count = await self._redis.scard("registry:drift:active")
        
        # Count agents
        agents = await self.list_agents()
        
        return {
            "connected": self._redis is not None,
            "resource_counts": type_counts,
            "total_resources": sum(type_counts.values()),
            "lab_count": len(labs),
            "active_drifts": drift_count,
            "agents": len(agents),
            "agent_names": [a["name"] for a in agents],
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_registry: Optional[LabRegistry] = None


def get_registry() -> LabRegistry:
    """Get or create the registry singleton"""
    global _registry
    if _registry is None:
        _registry = LabRegistry()
    return _registry


async def init_registry() -> LabRegistry:
    """Initialize and connect the registry"""
    registry = get_registry()
    await registry.connect()
    return registry

