"""
Proxmox Agent module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set

from glassdome.registry.agents.base import BaseAgent
from glassdome.registry.core import LabRegistry, get_registry
from glassdome.registry.models import (
    Resource, ResourceType, ResourceState, StateChange, EventType
)
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.core.config import settings

logger = logging.getLogger(__name__)


class ProxmoxAgent(BaseAgent):
    """
    Agent for monitoring Proxmox VMs.
    
    Features:
    - Fast polling for lab VMs (Tier 1)
    - Standard polling for all VMs (Tier 2)
    - VM state tracking (running/stopped/paused)
    - Name drift detection
    - IP address tracking via QEMU guest agent
    """
    
    def __init__(
        self,
        instance_id: str = "01",
        tier: int = 1,
        poll_interval: float = 1.0,
        registry: LabRegistry = None,
        track_lab_vms_only: bool = False
    ):
        """
        Initialize Proxmox agent.
        
        Args:
            instance_id: Proxmox instance ID (01, 02, etc.)
            tier: Update tier (1 = lab VMs, 2 = all VMs)
            poll_interval: Seconds between polls
            registry: Registry instance
            track_lab_vms_only: If True, only track VMs with lab_id
        """
        name = f"proxmox-{instance_id}"
        super().__init__(name=name, tier=tier, poll_interval=poll_interval, registry=registry)
        
        self.instance_id = instance_id
        self.track_lab_vms_only = track_lab_vms_only
        self._client: Optional[ProxmoxClient] = None
        self._nodes: List[str] = []
        self._known_vms: Set[str] = set()  # Track known VM IDs for deletion detection
        
    async def _get_client(self) -> ProxmoxClient:
        """Get or create Proxmox client"""
        if self._client is None:
            config = settings.get_proxmox_config(self.instance_id)
            
            if not config.get("host"):
                raise ValueError(f"No Proxmox host configured for instance {self.instance_id}")
            
            self._client = ProxmoxClient(
                host=config["host"],
                user=config["user"],
                password=config.get("password"),
                token_name=config.get("token_name"),
                token_value=config.get("token_value"),
                verify_ssl=config.get("verify_ssl", False),
                default_node=config.get("node", "pve"),
            )
            
            # Get list of nodes
            self._nodes = [n["node"] for n in await self._client.list_nodes()]
            logger.info(f"Proxmox agent {self.name} connected to nodes: {self._nodes}")
        
        return self._client
    
    async def poll(self) -> List[Resource]:
        """
        Poll all Proxmox nodes for VM state.
        
        Returns:
            List of Resource objects for all VMs
        """
        try:
            # 15s timeout - generous to handle load spikes
            # If it times out, next poll will try again
            return await asyncio.wait_for(self._poll_proxmox(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning(f"Poll timeout for {self.name} - will retry next cycle")
            return []
        except Exception as e:
            logger.error(f"Poll error for {self.name}: {e}")
            return []
    
    async def _poll_proxmox(self) -> List[Resource]:
        """Internal poll implementation - fetches VMs from Proxmox"""
        try:
            client = await self._get_client()
        except Exception as e:
            logger.error(f"Failed to get client for {self.name}: {e}")
            self._client = None  # Reset client on error
            return []
            
        resources = []
        current_vms = set()
        
        for node in self._nodes:
            try:
                # 5s per node - enough for normal response, skip if slow
                vms = await asyncio.wait_for(
                    asyncio.to_thread(lambda n=node: client.client.nodes(n).qemu.get()),
                    timeout=5.0
                )
                
                for vm in vms:
                    try:
                        resource = await self._vm_to_resource(node, vm)
                        if resource:
                            # Filter by tier if needed
                            if self.tier == 1 and self.track_lab_vms_only:
                                if not resource.lab_id:
                                    continue
                            
                            resources.append(resource)
                            current_vms.add(resource.id)
                    except Exception as e:
                        logger.warning(f"Error processing VM {vm.get('vmid')}: {e}")
                        
            except asyncio.TimeoutError:
                logger.debug(f"Timeout polling node {node} - will retry")
            except Exception as e:
                logger.error(f"Error polling node {node}: {e}")
        
        # Detect deleted VMs
        deleted_vms = self._known_vms - current_vms
        for vm_id in deleted_vms:
            await self._handle_deleted_vm(vm_id)
        
        self._known_vms = current_vms
        
        return resources
    
    async def _vm_to_resource(self, node: str, vm: Dict[str, Any]) -> Optional[Resource]:
        """
        Convert Proxmox VM data to Resource model.
        
        Args:
            node: Node name
            vm: VM data from Proxmox API
            
        Returns:
            Resource object
        """
        vmid = vm.get("vmid")
        name = vm.get("name", f"vm-{vmid}")
        status = vm.get("status", "unknown")
        
        # Skip templates for Tier 1 (lab VMs only)
        is_template = vm.get("template", False)
        if is_template and self.tier == 1:
            return None
        
        # Determine resource type
        if is_template:
            resource_type = ResourceType.TEMPLATE
        else:
            # Check if this is a lab VM (has lab_id in name or tags)
            # Lab VMs typically named like: lab-{lab_id}-{element_name}
            if name.startswith("lab-"):
                resource_type = ResourceType.LAB_VM
            else:
                resource_type = ResourceType.VM
        
        # Map Proxmox status to ResourceState
        state_map = {
            "running": ResourceState.RUNNING,
            "stopped": ResourceState.STOPPED,
            "paused": ResourceState.PAUSED,
        }
        state = state_map.get(status, ResourceState.UNKNOWN)
        
        # Extract lab_id from VM name if present
        lab_id = None
        if name.startswith("lab-"):
            parts = name.split("-")
            if len(parts) >= 2:
                lab_id = parts[1]
        
        # Build resource ID
        resource_id = Resource.make_id(
            platform="proxmox",
            resource_type=resource_type.value,
            platform_id=str(vmid),
            instance=self.instance_id
        )
        
        # Get additional config
        config = {
            "node": node,
            "vmid": vmid,
            "name": name,
            "cpus": vm.get("cpus", 0),
            "maxmem": vm.get("maxmem", 0),
            "maxdisk": vm.get("maxdisk", 0),
            "uptime": vm.get("uptime", 0),
            "template": is_template,
        }
        
        # Try to get IP address for running VMs
        if state == ResourceState.RUNNING and not is_template:
            try:
                ip = await self._get_vm_ip(node, vmid)
                if ip:
                    config["ip_address"] = ip
            except Exception:
                pass  # IP not available (no guest agent)
        
        return Resource(
            id=resource_id,
            resource_type=resource_type,
            name=name,
            platform="proxmox",
            platform_instance=self.instance_id,
            platform_id=str(vmid),
            state=state,
            lab_id=lab_id,
            config=config,
            tier=self.tier,
        )
    
    async def _get_vm_ip(self, node: str, vmid: int) -> Optional[str]:
        """Get VM IP address from guest agent (non-blocking, short timeout)"""
        client = await self._get_client()
        
        try:
            # Quick check - don't wait long
            interfaces = client.client.nodes(node).qemu(vmid).agent.get('network-get-interfaces')
            
            for iface in interfaces.get('result', []):
                if iface.get('name') not in ['lo', 'Loopback Pseudo-Interface 1']:
                    for addr in iface.get('ip-addresses', []):
                        if addr.get('ip-address-type') == 'ipv4':
                            ip = addr.get('ip-address')
                            if ip and not ip.startswith('127.'):
                                return ip
        except Exception:
            pass
        
        return None
    
    async def _handle_deleted_vm(self, resource_id: str):
        """Handle a VM that was deleted from Proxmox"""
        # Get existing resource
        resource = await self.registry.get(resource_id)
        if not resource:
            return
        
        # Only alert for lab VMs (Tier 1)
        if resource.resource_type == ResourceType.LAB_VM:
            logger.warning(f"Lab VM deleted: {resource.name} (id={resource_id})")
            
            # Publish deletion event
            await self.registry.publish_event(StateChange(
                event_type=EventType.DELETED,
                resource_id=resource_id,
                resource_type=resource.resource_type,
                old_state=resource.state,
                lab_id=resource.lab_id,
                platform="proxmox",
                agent=self.name,
            ))
        
        # Remove from registry
        await self.registry.delete(resource_id)
    
    async def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Get a specific VM resource"""
        # Parse resource ID to get vmid
        parts = resource_id.split(":")
        if len(parts) < 4:
            return None
        
        vmid = parts[-1]
        client = await self._get_client()
        
        for node in self._nodes:
            try:
                vm = client.client.nodes(node).qemu(int(vmid)).status.current.get()
                if vm:
                    return await self._vm_to_resource(node, {
                        "vmid": int(vmid),
                        "name": vm.get("name", f"vm-{vmid}"),
                        "status": vm.get("status"),
                        **vm
                    })
            except Exception:
                continue
        
        return None
    
    # =========================================================================
    # Actions (for reconciliation)
    # =========================================================================
    
    async def start_vm(self, vmid: int, node: str = None) -> bool:
        """Start a VM"""
        client = await self._get_client()
        node = node or self._nodes[0]
        
        try:
            client.client.nodes(node).qemu(vmid).status.start.post()
            logger.info(f"Started VM {vmid} on {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to start VM {vmid}: {e}")
            return False
    
    async def stop_vm(self, vmid: int, node: str = None) -> bool:
        """Stop a VM"""
        client = await self._get_client()
        node = node or self._nodes[0]
        
        try:
            client.client.nodes(node).qemu(vmid).status.stop.post()
            logger.info(f"Stopped VM {vmid} on {node}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop VM {vmid}: {e}")
            return False
    
    async def rename_vm(self, vmid: int, new_name: str, node: str = None) -> bool:
        """Rename a VM"""
        client = await self._get_client()
        node = node or self._nodes[0]
        
        try:
            client.client.nodes(node).qemu(vmid).config.put(name=new_name)
            logger.info(f"Renamed VM {vmid} to {new_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to rename VM {vmid}: {e}")
            return False


# =============================================================================
# Factory Functions
# =============================================================================

def create_proxmox_agents() -> List[ProxmoxAgent]:
    """
    Create agents for all configured Proxmox instances.
    
    Note: We only create Tier 2 agents (10s polling) to avoid overwhelming
    the Proxmox API. Lab VMs are tracked at the same frequency - 
    fast updates can come via webhooks when implemented.
    
    Returns:
        List of ProxmoxAgent instances
    """
    agents = []
    
    for instance_id in settings.list_proxmox_instances():
        config = settings.get_proxmox_config(instance_id)
        
        if config.get("host"):
            # Create single agent per instance - 10s polling for all VMs
            # This prevents API overload while still providing good visibility
            agent = ProxmoxAgent(
                instance_id=instance_id,
                tier=2,
                poll_interval=10.0,  # 10 seconds for all VMs
                track_lab_vms_only=False,
            )
            agents.append(agent)
            logger.info(f"Created Proxmox agent for instance {instance_id}")
    
    return agents

