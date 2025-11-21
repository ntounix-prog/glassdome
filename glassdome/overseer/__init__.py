"""
Glassdome Overseer - Autonomous System Administrator

The Overseer is an autonomous entity that:
- Continuously monitors all infrastructure
- Gates all requests for safety
- Makes intelligent decisions using RAG
- Executes approved operations
- Protects production systems
- Learns from past failures

Not just an API - a 24/7 senior ops engineer.
"""

from glassdome.overseer.entity import OverseerEntity
from glassdome.overseer.state import SystemState

__all__ = ["OverseerEntity", "SystemState"]

