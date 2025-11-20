"""
IP Pool Manager

Manages static IP address allocation for Proxmox/ESXi networks.
Tracks allocated IPs and assigns next available IP from pool.
"""
import json
from pathlib import Path
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class IPPoolManager:
    """
    Manages static IP address pools for on-premise deployments
    
    Supports multiple networks with configurable IP ranges.
    Persists allocation state to disk.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize IP pool manager
        
        Args:
            config_file: Path to IP pool configuration file
        """
        if config_file is None:
            # Default to glassdome root
            glassdome_root = Path(__file__).parent.parent.parent
            config_file = glassdome_root / "config" / "ip_pools.json"
        
        self.config_file = config_file
        self.pools = self._load_pools()
    
    def _load_pools(self) -> Dict:
        """Load IP pool configuration from disk"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        else:
            # Default pool configuration
            default_pools = {
                "pools": {
                    "192.168.3.0/24": {
                        "name": "Proxmox Lab Network",
                        "gateway": "192.168.3.1",
                        "netmask": "255.255.255.0",
                        "dns": ["8.8.8.8", "8.8.4.4"],
                        "range_start": "192.168.3.30",
                        "range_end": "192.168.3.40",
                        "allocated": {}
                    },
                    "192.168.2.0/24": {
                        "name": "ESXi Management Network",
                        "gateway": "192.168.2.1",
                        "netmask": "255.255.255.0",
                        "dns": ["8.8.8.8", "8.8.4.4"],
                        "range_start": "192.168.2.30",
                        "range_end": "192.168.2.40",
                        "allocated": {}
                    }
                }
            }
            
            # Save default configuration
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(default_pools, f, indent=2)
            
            return default_pools
    
    def _save_pools(self):
        """Save IP pool configuration to disk"""
        with open(self.config_file, 'w') as f:
            json.dump(self.pools, f, indent=2)
    
    def _ip_to_int(self, ip: str) -> int:
        """Convert IP address string to integer"""
        parts = ip.split('.')
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])
    
    def _int_to_ip(self, num: int) -> str:
        """Convert integer to IP address string"""
        return f"{(num >> 24) & 0xFF}.{(num >> 16) & 0xFF}.{(num >> 8) & 0xFF}.{num & 0xFF}"
    
    def allocate_ip(self, network: str, vm_id: str) -> Optional[Dict[str, str]]:
        """
        Allocate next available IP from pool
        
        Args:
            network: Network CIDR (e.g., "192.168.3.0/24")
            vm_id: VM identifier (for tracking)
        
        Returns:
            Dict with ip, gateway, netmask, dns or None if pool exhausted
        """
        if network not in self.pools["pools"]:
            logger.error(f"Network {network} not found in pools")
            return None
        
        pool = self.pools["pools"][network]
        
        # Get range
        start_ip = self._ip_to_int(pool["range_start"])
        end_ip = self._ip_to_int(pool["range_end"])
        
        # Find next available IP
        allocated_ips = set(pool["allocated"].values())
        
        for ip_int in range(start_ip, end_ip + 1):
            ip_str = self._int_to_ip(ip_int)
            if ip_str not in allocated_ips:
                # Allocate this IP
                pool["allocated"][vm_id] = ip_str
                self._save_pools()
                
                logger.info(f"Allocated IP {ip_str} to VM {vm_id}")
                
                return {
                    "ip": ip_str,
                    "gateway": pool["gateway"],
                    "netmask": pool["netmask"],
                    "dns": pool["dns"]
                }
        
        logger.error(f"IP pool exhausted for network {network}")
        return None
    
    def release_ip(self, network: str, vm_id: str) -> bool:
        """
        Release an IP address back to the pool
        
        Args:
            network: Network CIDR
            vm_id: VM identifier
        
        Returns:
            True if released, False if not found
        """
        if network not in self.pools["pools"]:
            logger.error(f"Network {network} not found in pools")
            return False
        
        pool = self.pools["pools"][network]
        
        if vm_id in pool["allocated"]:
            ip = pool["allocated"][vm_id]
            del pool["allocated"][vm_id]
            self._save_pools()
            logger.info(f"Released IP {ip} from VM {vm_id}")
            return True
        
        logger.warning(f"VM {vm_id} has no allocated IP in network {network}")
        return False
    
    def get_allocated_ip(self, network: str, vm_id: str) -> Optional[str]:
        """
        Get the allocated IP for a VM
        
        Args:
            network: Network CIDR
            vm_id: VM identifier
        
        Returns:
            IP address or None if not allocated
        """
        if network not in self.pools["pools"]:
            return None
        
        pool = self.pools["pools"][network]
        return pool["allocated"].get(vm_id)
    
    def list_allocations(self, network: Optional[str] = None) -> Dict:
        """
        List all IP allocations
        
        Args:
            network: Specific network to list, or None for all
        
        Returns:
            Dict of allocations
        """
        if network:
            if network in self.pools["pools"]:
                return {network: self.pools["pools"][network]["allocated"]}
            return {}
        
        return {net: pool["allocated"] for net, pool in self.pools["pools"].items()}


# Global instance
_ip_pool_manager = None

def get_ip_pool_manager() -> IPPoolManager:
    """Get global IP pool manager instance"""
    global _ip_pool_manager
    if _ip_pool_manager is None:
        _ip_pool_manager = IPPoolManager()
    return _ip_pool_manager

