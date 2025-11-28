"""
Lab Registry

Central source of truth for all lab and infrastructure resources.

The registry provides:
- Fast state access via Redis (<10ms)
- Event streaming via Redis pub/sub
- Tiered update strategy (1s / 5-10s / 30-60s)
- Drift detection and auto-remediation
- WebSocket API for real-time UI updates

Tiered Architecture:
- Tier 1 (Lab Resources): 1-second updates, webhooks, self-healing
- Tier 2 (Virtualization): 5-10 second polling, alerts
- Tier 3 (Infrastructure): 30-60 second polling, alerts only
"""

from glassdome.registry.core import LabRegistry, get_registry, init_registry
from glassdome.registry.models import (
    Resource, ResourceType, ResourceState,
    StateChange, EventType, Drift, DriftType, LabSnapshot
)

__all__ = [
    "LabRegistry",
    "get_registry", 
    "init_registry",
    "Resource",
    "ResourceType",
    "ResourceState", 
    "StateChange",
    "EventType",
    "Drift",
    "DriftType",
    "LabSnapshot",
]

