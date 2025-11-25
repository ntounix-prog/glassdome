"""
Reaper - Vulnerability Injection System

Event-driven system for injecting vulnerabilities into deployed VMs.
Works in parallel with LabOrchestrator to create cyber range training scenarios.

Key Components:
- MissionEngine: Orchestrates vulnerability injection missions
- Agents: Execute tasks on Windows/Linux/Mac VMs
- Planner: Decides which vulnerabilities to inject based on VM state
- Infrastructure: Task queues, event bus, state storage
"""

from glassdome.reaper.models import Task, ResultEvent, HostState, MissionState
from glassdome.reaper.engine import MissionEngine
from glassdome.reaper.planner import VulnerabilityPlanner

__all__ = [
    'Task',
    'ResultEvent',
    'HostState',
    'MissionState',
    'MissionEngine',
    'VulnerabilityPlanner',
]

