"""
Os Installer Factory module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from typing import Dict, Any, Optional
import logging
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
from glassdome.agents.windows_installer import WindowsInstallerAgent
from glassdome.agents.rocky_installer import RockyInstallerAgent
from glassdome.agents.kali_installer import KaliInstallerAgent
from glassdome.agents.parrot_installer import ParrotInstallerAgent
from glassdome.agents.rhel_installer import RHELInstallerAgent

logger = logging.getLogger(__name__)


class OSInstallerFactory:
    """
    Factory for creating appropriate OS installer agents
    
    This provides a single entry point while maintaining
    specialized agents for each OS type.
    
    Best of both worlds:
    - Single API endpoint
    - Specialized agent logic
    - Easy to add new OS types
    """
    
    # Registry of OS types to agent classes
    _agent_registry: Dict[str, type] = {
        "ubuntu": UbuntuInstallerAgent,
        "windows": WindowsInstallerAgent,
        "rocky": RockyInstallerAgent,
        "kali": KaliInstallerAgent,
        "parrot": ParrotInstallerAgent,
        "rhel": RHELInstallerAgent,
    }
    
    # Cached agent instances
    _agent_cache: Dict[str, Any] = {}
    
    @classmethod
    def register_os_agent(cls, os_type: str, agent_class: type) -> None:
        """
        Register a new OS agent type
        
        Args:
            os_type: OS type identifier (e.g., "ubuntu", "kali")
            agent_class: Agent class to handle this OS type
        """
        cls._agent_registry[os_type] = agent_class
        logger.info(f"Registered OS agent: {os_type} -> {agent_class.__name__}")
    
    @classmethod
    def get_agent(cls, os_type: str, platform_client: Any, agent_id: Optional[str] = None) -> Any:
        """
        Get or create agent for OS type
        
        Args:
            os_type: OS type (ubuntu, kali, windows, etc.)
            platform_client: Platform client instance
            agent_id: Optional specific agent ID
            
        Returns:
            Specialized OS installer agent
            
        Raises:
            ValueError: If OS type not supported
        """
        # Check if OS type is supported
        if os_type not in cls._agent_registry:
            supported = ", ".join(cls._agent_registry.keys())
            raise ValueError(
                f"Unsupported OS type: {os_type}. "
                f"Supported: {supported}"
            )
        
        # Check cache
        cache_key = f"{os_type}_{id(platform_client)}"
        if cache_key in cls._agent_cache:
            return cls._agent_cache[cache_key]
        
        # Create new agent
        agent_class = cls._agent_registry[os_type]
        agent_id = agent_id or f"{os_type}_installer_1"
        agent = agent_class(agent_id, platform_client)
        
        # Cache it
        cls._agent_cache[cache_key] = agent
        
        logger.info(f"Created {os_type} agent: {agent_id}")
        return agent
    
    @classmethod
    def get_supported_os_types(cls) -> list[str]:
        """Get list of supported OS types"""
        return list(cls._agent_registry.keys())
    
    @classmethod
    def create_vm(
        cls,
        os_type: str,
        platform_client: Any,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convenience method to create VM with appropriate agent
        
        Args:
            os_type: OS type
            platform_client: Platform client
            config: VM configuration
            
        Returns:
            Deployment result
        """
        agent = cls.get_agent(os_type, platform_client)
        
        task = {
            "element_type": f"{os_type}_vm",
            "config": config
        }
        
        return agent.run(task)
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear agent cache"""
        cls._agent_cache.clear()
        logger.info("Agent cache cleared")

