"""
Proxmox Handler module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import logging
from typing import Dict, Any, List, Optional

from glassdome.networking.orchestrator import PlatformNetworkHandler
from glassdome.networking.models import NetworkDefinition
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.core.config import Settings

logger = logging.getLogger(__name__)


class ProxmoxNetworkHandler(PlatformNetworkHandler):
    """
    Proxmox-specific network operations.
    
    Proxmox networking uses:
    - Linux bridges (vmbr0, vmbr1, etc.)
    - VLAN tagging (tag=100 on the NIC)
    - Physical interfaces bound to bridges
    
    For Glassdome:
    - Use existing bridges (don't create new ones - requires node config)
    - Apply VLAN tags to VM NICs
    - Configure IPs via cloud-init or QEMU guest agent
    """
    
    def __init__(self):
        self._clients: Dict[str, ProxmoxClient] = {}
    
    def _get_client(self, platform_instance: str = "01") -> ProxmoxClient:
        """Get or create a Proxmox client for the instance"""
        if platform_instance not in self._clients:
            settings = Settings()
            config = settings.get_proxmox_config(platform_instance)
            
            self._clients[platform_instance] = ProxmoxClient(
                host=config["host"],
                user=config["user"],
                password=config.get("password"),
                token_name=config.get("token_name"),
                token_value=config.get("token_value"),
                verify_ssl=config.get("verify_ssl", False),
                default_node=config.get("node", f"pve{platform_instance}")
            )
        
        return self._clients[platform_instance]
    
    async def generate_network_config(
        self,
        network: NetworkDefinition,
        platform_instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate Proxmox-specific config from abstract network definition.
        
        Maps abstract network to:
        - bridge: Which Linux bridge to use (vmbr0, vmbr1, etc.)
        - vlan_tag: VLAN ID to tag on the NIC
        - model: NIC model (virtio recommended)
        """
        # Default bridge mapping based on network type
        # These should be customizable per environment
        bridge_mapping = {
            "isolated": "vmbr2",   # Isolated/lab networks
            "nat": "vmbr1",        # NAT networks
            "bridged": "vmbr0",    # Direct bridge to physical
            "routed": "vmbr1",     # Routed networks
        }
        
        bridge = bridge_mapping.get(network.network_type, "vmbr2")
        
        config = {
            "bridge": bridge,
            "model": "virtio",
            "firewall": 0,
        }
        
        # Add VLAN tag if specified
        if network.vlan_id:
            config["vlan_tag"] = network.vlan_id
        
        return config
    
    async def create_network(
        self,
        network: NetworkDefinition,
        config: Dict[str, Any],
        platform_instance: Optional[str] = None
    ) -> bool:
        """
        Create/verify network on Proxmox.
        
        Note: Creating bridges requires node-level access and is typically
        done manually. This method verifies the bridge exists and is usable.
        
        For VLANs, we don't need to create anything - just use the tag
        when attaching VMs.
        """
        instance = platform_instance or "02"
        client = self._get_client(instance)
        
        bridge = config.get("bridge", "vmbr2")
        
        # Verify the bridge exists on the node
        try:
            node = client.default_node
            node_network = client.client.nodes(node).network.get()
            
            bridge_exists = any(
                iface.get("iface") == bridge 
                for iface in node_network
            )
            
            if not bridge_exists:
                logger.warning(f"Bridge {bridge} not found on {node}. Available: {[i.get('iface') for i in node_network]}")
                # Don't fail - the bridge might still work
            else:
                logger.info(f"Verified bridge {bridge} exists on {node}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to verify network on Proxmox: {e}")
            raise
    
    async def delete_network(
        self,
        config: Dict[str, Any],
        platform_instance: Optional[str] = None
    ) -> bool:
        """
        Delete network from Proxmox.
        
        For Proxmox, we don't actually delete bridges (they're node-level).
        This is a no-op but could clean up any associated resources.
        """
        # Nothing to delete - bridges are managed at node level
        return True
    
    async def attach_interface(
        self,
        vm_id: str,
        network: NetworkDefinition,
        config: Dict[str, Any],
        interface_index: int = 0,
        platform_instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Attach a network interface to a VM.
        
        Creates a NIC on the VM connected to the specified bridge
        with optional VLAN tag.
        """
        instance = platform_instance or "02"
        client = self._get_client(instance)
        node = client.default_node
        vmid = int(vm_id)
        
        bridge = config.get("bridge", "vmbr2")
        model = config.get("model", "virtio")
        vlan_tag = config.get("vlan_tag")
        
        # Build the NIC config string
        # Format: virtio=XX:XX:XX:XX:XX:XX,bridge=vmbr2,tag=100
        nic_config = f"{model}=auto,bridge={bridge}"
        if vlan_tag:
            nic_config += f",tag={vlan_tag}"
        
        # Add the NIC to the VM
        net_device = f"net{interface_index}"
        
        try:
            client.client.nodes(node).qemu(vmid).config.put(**{net_device: nic_config})
            logger.info(f"Attached {net_device} to VM {vmid}: {nic_config}")
            
            # Get the MAC address that was assigned
            vm_config = client.client.nodes(node).qemu(vmid).config.get()
            nic_value = vm_config.get(net_device, "")
            
            # Parse MAC from "virtio=BC:24:11:xx:xx:xx,bridge=vmbr2"
            mac_address = None
            if "=" in nic_value:
                parts = nic_value.split(",")
                for part in parts:
                    if "=" in part and part.count(":") >= 5:
                        mac_address = part.split("=")[1]
                        break
            
            return {
                "index": interface_index,
                "device": net_device,
                "bridge": bridge,
                "vlan_tag": vlan_tag,
                "mac_address": mac_address,
                "model": model,
            }
            
        except Exception as e:
            logger.error(f"Failed to attach interface to VM {vmid}: {e}")
            raise
    
    async def detach_interface(
        self,
        vm_id: str,
        interface_index: int = 0,
        platform_instance: Optional[str] = None
    ) -> bool:
        """Remove a network interface from a VM"""
        instance = platform_instance or "02"
        client = self._get_client(instance)
        node = client.default_node
        vmid = int(vm_id)
        
        net_device = f"net{interface_index}"
        
        try:
            # Delete the NIC by setting to empty
            client.client.nodes(node).qemu(vmid).config.put(delete=net_device)
            logger.info(f"Detached {net_device} from VM {vmid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to detach interface from VM {vmid}: {e}")
            return False
    
    async def get_vm_interfaces(
        self,
        vm_id: str,
        platform_instance: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all network interfaces for a VM.
        
        Queries the VM config and QEMU guest agent for interface details.
        """
        instance = platform_instance or "02"
        client = self._get_client(instance)
        node = client.default_node
        vmid = int(vm_id)
        
        interfaces = []
        
        try:
            # Get VM config
            vm_config = client.client.nodes(node).qemu(vmid).config.get()
            
            # Parse net0, net1, etc.
            for i in range(10):  # Check up to 10 NICs
                net_device = f"net{i}"
                nic_value = vm_config.get(net_device)
                
                if not nic_value:
                    continue
                
                # Parse: "virtio=BC:24:11:xx:xx:xx,bridge=vmbr2,tag=100"
                iface = {
                    "index": i,
                    "device": net_device,
                    "platform_config": {},
                }
                
                parts = nic_value.split(",")
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        if key in ["virtio", "e1000", "vmxnet3"]:
                            iface["mac_address"] = value
                            iface["platform_config"]["model"] = key
                        elif key == "bridge":
                            iface["platform_config"]["bridge"] = value
                        elif key == "tag":
                            iface["platform_config"]["vlan_tag"] = int(value)
                
                interfaces.append(iface)
            
            # Try to get IP addresses from QEMU guest agent
            try:
                agent_info = client.client.nodes(node).qemu(vmid).agent("network-get-interfaces").get()
                
                for agent_iface in agent_info.get("result", []):
                    name = agent_iface.get("name", "")
                    
                    # Skip loopback
                    if name == "lo":
                        continue
                    
                    # Find matching interface by MAC or index
                    mac = agent_iface.get("hardware-address", "").upper()
                    
                    for iface in interfaces:
                        if iface.get("mac_address", "").upper() == mac:
                            iface["interface_name"] = name
                            
                            # Get IPv4 address
                            for addr in agent_iface.get("ip-addresses", []):
                                if addr.get("ip-address-type") == "ipv4":
                                    iface["ip_address"] = addr.get("ip-address")
                                    iface["subnet_mask"] = f"/{addr.get('prefix', 24)}"
                                    break
                            break
                            
            except Exception as e:
                logger.debug(f"Could not get guest agent info for VM {vmid}: {e}")
            
            return interfaces
            
        except Exception as e:
            logger.error(f"Failed to get interfaces for VM {vmid}: {e}")
            return []
    
    async def configure_vm_ip(
        self,
        vm_id: str,
        interface_index: int,
        ip_address: str,
        gateway: Optional[str] = None,
        dns_servers: Optional[List[str]] = None,
        platform_instance: Optional[str] = None
    ) -> bool:
        """
        Configure IP address on a VM interface via cloud-init.
        
        Note: This updates the cloud-init config. For running VMs,
        you may need to use QEMU guest agent or SSH.
        """
        instance = platform_instance or "02"
        client = self._get_client(instance)
        node = client.default_node
        vmid = int(vm_id)
        
        # Build ipconfig string
        # Format: ip=192.168.1.10/24,gw=192.168.1.1
        prefix = ip_address.split("/")[1] if "/" in ip_address else "24"
        ip_only = ip_address.split("/")[0]
        
        ipconfig = f"ip={ip_only}/{prefix}"
        if gateway:
            ipconfig += f",gw={gateway}"
        
        ipconfig_key = f"ipconfig{interface_index}"
        
        try:
            client.client.nodes(node).qemu(vmid).config.put(**{ipconfig_key: ipconfig})
            
            # Also set nameserver if DNS provided
            if dns_servers:
                nameserver = " ".join(dns_servers)
                client.client.nodes(node).qemu(vmid).config.put(nameserver=nameserver)
            
            logger.info(f"Configured IP for VM {vmid} interface {interface_index}: {ipconfig}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure IP for VM {vmid}: {e}")
            return False


# ============================================================================
# Factory Function
# ============================================================================

_handler: Optional[ProxmoxNetworkHandler] = None


def get_proxmox_network_handler() -> ProxmoxNetworkHandler:
    """Get or create the Proxmox network handler singleton"""
    global _handler
    if _handler is None:
        _handler = ProxmoxNetworkHandler()
    return _handler

