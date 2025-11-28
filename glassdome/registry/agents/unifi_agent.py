"""
Unifi Agent module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import httpx

from glassdome.registry.agents.base import BaseAgent
from glassdome.registry.core import LabRegistry, get_registry
from glassdome.registry.models import Resource, ResourceType, ResourceState

logger = logging.getLogger(__name__)


class UnifiAgent(BaseAgent):
    """
    Agent for monitoring DHCP leases via Unifi API.
    
    Features:
    - DHCP client tracking
    - IP address discovery by MAC
    - Client online/offline status
    """
    
    def __init__(
        self,
        host: str = None,
        api_key: str = None,
        tier: int = 2,
        poll_interval: float = 5.0,
        registry: LabRegistry = None
    ):
        """
        Initialize Unifi agent.
        
        Args:
            host: Unifi gateway host (default from env)
            api_key: Unifi API key (default from env)
            tier: Update tier (2 = standard polling)
            poll_interval: Seconds between polls
            registry: Registry instance
        """
        super().__init__(name="unifi", tier=tier, poll_interval=poll_interval, registry=registry)
        
        self.host = host or os.getenv("UBIQUITI_GATEWAY_HOST", "192.168.2.1")
        self.api_key = api_key or os.getenv("UBIQUITI_API_KEY", "")
        self._clients: Dict[str, Dict[str, Any]] = {}  # MAC -> client data
    
    async def poll(self) -> List[Resource]:
        """
        Poll Unifi for DHCP clients.
        
        Returns:
            List of Resource objects for DHCP clients (informational only)
        """
        if not self.api_key:
            logger.debug("No Unifi API key configured, skipping poll")
            return []
        
        resources = []
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=10) as http:
                # Get active clients
                resp = await http.get(
                    f"https://{self.host}/proxy/network/api/s/default/stat/sta",
                    headers={"X-API-KEY": self.api_key}
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    for client in data.get("data", []):
                        mac = client.get("mac", "").lower()
                        ip = client.get("ip")
                        hostname = client.get("hostname", client.get("name", f"client-{mac[-8:]}"))
                        
                        if not mac:
                            continue
                        
                        # Store for quick lookup
                        self._clients[mac] = client
                        
                        # Don't create resources for every client - too noisy
                        # Just maintain the internal cache for IP lookups
                        
        except Exception as e:
            logger.error(f"Unifi poll error: {e}")
        
        return resources
    
    async def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get a client resource by MAC address"""
        mac = resource_id.lower().replace(":", "").replace("-", "")
        
        for stored_mac, client in self._clients.items():
            if stored_mac.replace(":", "") == mac:
                return self._client_to_resource(client)
        
        return None
    
    def _client_to_resource(self, client: Dict[str, Any]) -> Resource:
        """Convert Unifi client data to Resource"""
        mac = client.get("mac", "").lower()
        
        return Resource(
            id=Resource.make_id("unifi", "client", mac),
            resource_type=ResourceType.VM,  # Closest match
            name=client.get("hostname", client.get("name", f"client-{mac[-8:]}")),
            platform="unifi",
            platform_id=mac,
            state=ResourceState.RUNNING if client.get("ip") else ResourceState.UNKNOWN,
            config={
                "mac": mac,
                "ip": client.get("ip"),
                "hostname": client.get("hostname"),
                "oui": client.get("oui", ""),
                "rx_bytes": client.get("rx_bytes", 0),
                "tx_bytes": client.get("tx_bytes", 0),
                "last_seen": client.get("last_seen"),
            },
            tier=self.tier,
        )
    
    # =========================================================================
    # IP Lookup API
    # =========================================================================
    
    async def get_ip_by_mac(self, mac_address: str) -> Optional[str]:
        """
        Look up IP address by MAC address.
        
        Args:
            mac_address: MAC address (any format)
            
        Returns:
            IP address if found, None otherwise
        """
        mac_lower = mac_address.lower().replace("-", ":").replace(".", ":")
        
        # Check cache first
        for stored_mac, client in self._clients.items():
            if stored_mac == mac_lower or stored_mac.replace(":", "") == mac_lower.replace(":", ""):
                ip = client.get("ip")
                if ip:
                    return ip
        
        # If not in cache, do a fresh API call
        if self.api_key:
            try:
                async with httpx.AsyncClient(verify=False, timeout=10) as http:
                    resp = await http.get(
                        f"https://{self.host}/proxy/network/api/s/default/stat/sta",
                        headers={"X-API-KEY": self.api_key}
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        
                        for client in data.get("data", []):
                            stored_mac = client.get("mac", "").lower()
                            if stored_mac == mac_lower or stored_mac.replace(":", "") == mac_lower.replace(":", ""):
                                ip = client.get("ip")
                                if ip:
                                    # Update cache
                                    self._clients[stored_mac] = client
                                    return ip
            except Exception as e:
                logger.error(f"Unifi API lookup error: {e}")
        
        return None
    
    async def list_clients(self) -> List[Dict[str, Any]]:
        """
        Get all known clients.
        
        Returns:
            List of client dictionaries with mac, ip, hostname
        """
        return [
            {
                "mac": mac,
                "ip": client.get("ip"),
                "hostname": client.get("hostname", client.get("name")),
            }
            for mac, client in self._clients.items()
        ]
    
    async def wait_for_ip(self, mac_address: str, timeout: int = 60) -> Optional[str]:
        """
        Wait for a device to get an IP address.
        
        Args:
            mac_address: MAC address to monitor
            timeout: Maximum seconds to wait
            
        Returns:
            IP address if acquired, None if timeout
        """
        start = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start) < timeout:
            ip = await self.get_ip_by_mac(mac_address)
            if ip:
                return ip
            
            await asyncio.sleep(2)
        
        return None


# =============================================================================
# Singleton Access
# =============================================================================

_unifi_agent: Optional[UnifiAgent] = None


def get_unifi_agent() -> UnifiAgent:
    """Get or create the Unifi agent singleton"""
    global _unifi_agent
    if _unifi_agent is None:
        _unifi_agent = UnifiAgent()
    return _unifi_agent

