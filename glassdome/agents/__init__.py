"""
Agentic Framework for Autonomous Deployment
"""
from glassdome.agents.base import (
    BaseAgent,
    DeploymentAgent,
    MonitoringAgent,
    OptimizationAgent,
    AgentStatus,
    AgentType
)
from glassdome.agents.manager import AgentManager

# Specific agent implementations
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
from glassdome.agents.windows_installer import WindowsInstallerAgent
from glassdome.agents.overseer import OverseerAgent
from glassdome.agents.mailcow_agent import MailcowAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "DeploymentAgent",
    "MonitoringAgent",
    "OptimizationAgent",
    "AgentStatus",
    "AgentType",
    # Manager
    "AgentManager",
    # Agent implementations
    "UbuntuInstallerAgent",
    "WindowsInstallerAgent",
    "OverseerAgent",
    "MailcowAgent",
]

