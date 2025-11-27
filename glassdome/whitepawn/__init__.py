"""
WhitePawn - Continuous Network Monitoring Agent

WhitePawn is deployed into every lab network as an invisible sentinel.
It continuously monitors:
- Network connectivity between all VMs
- Gateway and DNS availability
- VLAN isolation
- VM health and responsiveness

Future capabilities:
- Player activity monitoring
- Traffic analysis for coaching
- Real-time performance metrics
"""

from glassdome.whitepawn.models import (
    WhitePawnDeployment,
    NetworkAlert,
    MonitoringEvent,
    AlertSeverity,
    AlertType
)
from glassdome.whitepawn.monitor import WhitePawnMonitor
from glassdome.whitepawn.orchestrator import WhitePawnOrchestrator

__all__ = [
    "WhitePawnDeployment",
    "NetworkAlert", 
    "MonitoringEvent",
    "AlertSeverity",
    "AlertType",
    "WhitePawnMonitor",
    "WhitePawnOrchestrator"
]

