"""
Glassdome - Agentic Cyber Range Deployment Framework

A Python package for autonomous deployment of cybersecurity lab environments
across Proxmox, Azure, and AWS platforms.
"""

__version__ = "0.1.0"
__author__ = "ntounix-prog"
__email__ = "ntounix@gmail.com"

# Core imports for easy access
from glassdome.core.config import settings
from glassdome.agents.manager import agent_manager
from glassdome.orchestration.engine import OrchestrationEngine

# Platform clients
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.platforms.azure_client import AzureClient
from glassdome.platforms.aws_client import AWSClient

# Agent types
from glassdome.agents.base import (
    BaseAgent,
    DeploymentAgent,
    MonitoringAgent,
    OptimizationAgent,
    AgentStatus,
    AgentType,
)

# Database models
from glassdome.models.lab import Lab, LabTemplate, LabElement
from glassdome.models.deployment import Deployment, DeploymentStatus
from glassdome.models.platform import Platform, PlatformType

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__email__",
    # Core
    "settings",
    "agent_manager",
    "OrchestrationEngine",
    # Platforms
    "ProxmoxClient",
    "AzureClient",
    "AWSClient",
    # Agents
    "BaseAgent",
    "DeploymentAgent",
    "MonitoringAgent",
    "OptimizationAgent",
    "AgentStatus",
    "AgentType",
    # Models
    "Lab",
    "LabTemplate",
    "LabElement",
    "Deployment",
    "DeploymentStatus",
    "Platform",
    "PlatformType",
]


# Package-level convenience functions
def get_version() -> str:
    """Get the current version of Glassdome"""
    return __version__


def initialize(config_path: str = None) -> None:
    """
    Initialize Glassdome package
    
    Args:
        config_path: Optional path to configuration file
    """
    if config_path:
        # Load custom config
        pass
    print(f"Glassdome v{__version__} initialized")
