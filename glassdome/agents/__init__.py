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
from glassdome.agents.rocky_installer import RockyInstallerAgent
from glassdome.agents.kali_installer import KaliInstallerAgent
from glassdome.agents.parrot_installer import ParrotInstallerAgent
from glassdome.agents.rhel_installer import RHELInstallerAgent
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
    "RockyInstallerAgent",
    "KaliInstallerAgent",
    "ParrotInstallerAgent",
    "RHELInstallerAgent",
    "OverseerAgent",
    "MailcowAgent",
]

