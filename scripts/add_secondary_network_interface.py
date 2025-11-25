#!/usr/bin/env python3
"""
Add Secondary Network Interface to VMs for Direct Proxmox Access

Adds a secondary network interface to agentX and server VM on 192.168.215.0/24
network to enable direct access to original Proxmox (192.168.215.78).
"""
import sys
import os
import asyncio
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import with error handling to avoid config validation issues
try:
    from glassdome.core.security import ensure_security_context, get_secure_settings
    ensure_security_context()
    from glassdome.platforms.proxmox_factory import get_proxmox_client
except Exception as e:
    # Fallback: direct Proxmox API import
    import os
    from pathlib import Path
    from proxmoxer import ProxmoxAPI
    
    def get_proxmox_client(instance_id="02"):
        env_file = Path(__file__).parent.parent / ".env"
        config = {}
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        
        host_key = f"PROXMOX_{instance_id}_HOST" if instance_id != "01" else "PROXMOX_HOST"
        user_key = f"PROXMOX_{instance_id}_USER" if instance_id != "01" else "PROXMOX_USER"
        token_name_key = f"PROXMOX_{instance_id}_TOKEN_NAME" if instance_id != "01" else "PROXMOX_TOKEN_NAME"
        token_value_key = f"PROXMOX_TOKEN_VALUE_{instance_id}" if instance_id != "01" else "PROXMOX_TOKEN_VALUE"
        
        host = config.get(host_key) or config.get("PROXMOX_HOST")
        user = config.get(user_key) or config.get("PROXMOX_USER", "apex@pve")
        token_name = config.get(token_name_key) or config.get("PROXMOX_TOKEN_NAME", "PVEAPIToken")
        token_value = config.get(token_value_key) or config.get("PROXMOX_TOKEN_VALUE")
        
        if not host or not token_value:
            raise ValueError(f"Missing Proxmox credentials for instance {instance_id}")
        
        class SimpleProxmoxClient:
            def __init__(self, client, host, default_node="pve"):
                self.client = client
                self.host = host
                self.default_node = default_node
        
        client = ProxmoxAPI(host, user=user, token_name=token_name, token_value=token_value, verify_ssl=False)
        return SimpleProxmoxClient(client, host)
    
    class Settings:
        pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Network configuration
TARGET_NETWORK = "192.168.215.0/24"
TARGET_NETWORK_BASE = "192.168.215"
ORIGINAL_PROXMOX_IP = "192.168.215.78"


async def find_network_bridge(proxmox_client, target_network: str) -> Optional[str]:
    """Find the bridge that serves the target network"""
    try:
        # Get node name
        nodes = proxmox_client.client.nodes.get()
        if not nodes:
            logger.error("No nodes found")
            return None
        
        node = nodes[0].get("node", "pve")
        
        # Get network configuration
        networks = proxmox_client.client.nodes(node).network.get()
        
        for net in networks:
            if net.get("type") == "bridge":
                bridge_name = net.get("iface")
                # Check if bridge has IP in target network
                addresses = net.get("address", "")
                if TARGET_NETWORK_BASE in addresses:
                    logger.info(f"Found bridge {bridge_name} for {target_network}")
                    return bridge_name
        
        # If not found, try common bridge names
        logger.warning("Bridge not found via API, trying common names...")
        for bridge_name in ["vmbr0", "vmbr1", "vmbr2"]:
            try:
                # Try to get bridge info
                bridge_info = proxmox_client.client.nodes(node).network(bridge_name).get()
                if bridge_info:
                    logger.info(f"Found bridge {bridge_name}")
                    return bridge_name
            except:
                continue
        
        logger.error(f"Could not find bridge for {target_network}")
        return None
        
    except Exception as e:
        logger.error(f"Error finding network bridge: {e}")
        return None


async def get_vm_network_interfaces(proxmox_client, node: str, vm_id: int) -> List[str]:
    """Get list of network interfaces on VM"""
    try:
        config = proxmox_client.client.nodes(node).qemu(vm_id).config.get()
        
        interfaces = []
        for key in config.keys():
            if key.startswith("net") and key[3:].isdigit():
                interfaces.append(key)
        
        return sorted(interfaces, key=lambda x: int(x[3:]))
    except Exception as e:
        logger.error(f"Error getting VM network interfaces: {e}")
        return []


async def add_network_interface(proxmox_client, node: str, vm_id: int, 
                                bridge: str, interface_num: int = 1) -> bool:
    """Add secondary network interface to VM"""
    try:
        # Check existing interfaces
        existing = await get_vm_network_interfaces(proxmox_client, node, vm_id)
        
        # Find next available interface number
        if existing:
            max_num = max([int(iface[3:]) for iface in existing])
            interface_num = max_num + 1
        
        interface_name = f"net{interface_num}"
        
        # Check if interface already exists
        config = proxmox_client.client.nodes(node).qemu(vm_id).config.get()
        if interface_name in config:
            logger.warning(f"Interface {interface_name} already exists on VM {vm_id}")
            return True
        
        # Add interface (no firewall, no gateway)
        interface_config = f"virtio,bridge={bridge},firewall=0"
        
        logger.info(f"Adding {interface_name} to VM {vm_id} on bridge {bridge}...")
        proxmox_client.client.nodes(node).qemu(vm_id).config.post(
            **{interface_name: interface_config}
        )
        
        logger.info(f"✅ Successfully added {interface_name} to VM {vm_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error adding network interface: {e}")
        return False


async def configure_static_ip_via_ssh(vm_host: str, interface_name: str, 
                                     ip_address: str, netmask: str = "255.255.255.0") -> bool:
    """Configure static IP on VM via SSH (no gateway)"""
    try:
        # Determine interface name (may need to be discovered)
        # Common names: ens7, ens8, eth1, enp7s0
        
        # First, discover interface name
        discover_cmd = "ip link show | grep -E '^[0-9]+:' | tail -1 | cut -d: -f2 | tr -d ' '"
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{vm_host} '{discover_cmd}'"
        
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            discovered_iface = result.stdout.strip()
            if discovered_iface:
                interface_name = discovered_iface
                logger.info(f"Discovered interface: {interface_name}")
        
        # Configure IP (no gateway)
        cidr = 24 if netmask == "255.255.255.0" else 16
        ip_config_cmd = f"sudo ip addr add {ip_address}/{cidr} dev {interface_name} 2>/dev/null || true"
        up_cmd = f"sudo ip link set {interface_name} up"
        
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{vm_host} '{ip_config_cmd} && {up_cmd}'"
        
        logger.info(f"Configuring {ip_address} on {interface_name}...")
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully configured IP {ip_address} on {interface_name}")
            return True
        else:
            logger.warning(f"⚠️  IP configuration may have failed: {result.stderr}")
            # Try netplan configuration for Ubuntu
            return await configure_static_ip_netplan(vm_host, interface_name, ip_address, cidr)
            
    except Exception as e:
        logger.error(f"❌ Error configuring static IP: {e}")
        return False


async def configure_static_ip_netplan(vm_host: str, interface_name: str, 
                                     ip_address: str, cidr: int) -> bool:
    """Configure static IP using netplan (Ubuntu)"""
    try:
        netplan_config = f"""
network:
  version: 2
  ethernets:
    {interface_name}:
      addresses:
        - {ip_address}/{cidr}
      # No gateway specified
"""
        
        # Write netplan config
        config_file = f"/tmp/{interface_name}-config.yaml"
        write_cmd = f"cat > {config_file} << 'EOF'\n{netplan_config}\nEOF"
        apply_cmd = f"sudo netplan apply"
        
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{vm_host} '{write_cmd} && sudo cp {config_file} /etc/netplan/50-{interface_name}.yaml && {apply_cmd}'"
        
        logger.info(f"Configuring via netplan...")
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully configured via netplan")
            return True
        else:
            logger.error(f"❌ Netplan configuration failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error configuring via netplan: {e}")
        return False


async def verify_connectivity(source_ip: str, target_ip: str) -> bool:
    """Test network connectivity"""
    try:
        ping_cmd = f"ping -c 2 -W 2 {target_ip}"
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no root@{source_ip} '{ping_cmd}'"
        
        result = subprocess.run(
            ssh_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Successfully pinged {target_ip} from {source_ip}")
            return True
        else:
            logger.warning(f"⚠️  Cannot ping {target_ip} from {source_ip}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing connectivity: {e}")
        return False


async def main():
    """Main configuration process"""
    # Use session-aware settings
    from glassdome.core.security import get_secure_settings
    settings = get_secure_settings()
    
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        logger.info("=" * 70)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 70)
        logger.info("Add --execute flag to perform actual configuration")
        logger.info("")
    
    logger.info("=" * 70)
    logger.info("Add Secondary Network Interface for Direct Proxmox Access")
    logger.info("=" * 70)
    logger.info(f"Target Network: {TARGET_NETWORK}")
    logger.info(f"Original Proxmox: {ORIGINAL_PROXMOX_IP}")
    logger.info("")
    
    # Get Proxmox client (current Proxmox)
    # Use session-aware settings (automatically uses secrets manager)
    proxmox_config = settings.get_proxmox_config("01")
    
    # Get Proxmox credentials - use instance 01 (current Proxmox at 10.0.0.1)
    proxmox_host = proxmox_config.get("host", "10.0.0.1")
    proxmox_user = proxmox_config.get("user", "apex@pve")
    proxmox_token_name = proxmox_config.get("token_name", "glassdome-token")
    proxmox_token_value = proxmox_config.get("token_value")
    
    # If token not found, try password
    proxmox_password = proxmox_config.get("password")
    
    if not proxmox_host:
        logger.error("❌ Missing PROXMOX_HOST in .env")
        return 1
    
    try:
        from proxmoxer import ProxmoxAPI
        
        class SimpleProxmoxClient:
            def __init__(self, client, host, default_node="pve"):
                self.client = client
                self.host = host
                self.default_node = default_node
        
        # Try token first, then password
        if proxmox_token_value:
            client = ProxmoxAPI(
                proxmox_host,
                user=proxmox_user,
                token_name=proxmox_token_name,
                token_value=proxmox_token_value,
                verify_ssl=False
            )
        elif proxmox_password:
            client = ProxmoxAPI(
                proxmox_host,
                user=proxmox_user,
                password=proxmox_password,
                verify_ssl=False
            )
        else:
            logger.error("❌ Missing Proxmox credentials (need PROXMOX_TOKEN_VALUE or PROXMOX_PASSWORD)")
            return 1
        
        proxmox = SimpleProxmoxClient(client, proxmox_host)
        logger.info(f"✅ Connected to current Proxmox at {proxmox_host}")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Proxmox: {e}")
        logger.error(f"   Host: {proxmox_host}, User: {proxmox_user}")
        return 1
    
    # Get node
    nodes = proxmox.client.nodes.get()
    if not nodes:
        logger.error("No nodes found")
        return 1
    
    node = nodes[0].get("node", "pve")
    logger.info(f"Using node: {node}")
    
    # Step 1: Find network bridge
    logger.info("")
    logger.info("Phase 1: Network Bridge Discovery")
    logger.info("-" * 70)
    bridge = await find_network_bridge(proxmox, TARGET_NETWORK)
    
    if not bridge:
        logger.error("❌ Could not find network bridge. Please specify bridge name manually.")
        logger.info("Common bridges: vmbr0, vmbr1, vmbr2")
        return 1
    
    logger.info(f"✅ Using bridge: {bridge}")
    
    # Step 2: Identify VMs
    logger.info("")
    logger.info("Phase 2: VM Identification")
    logger.info("-" * 70)
    
    # Find agentX VM (usually VM 100, check management network)
    agentx_vmid = None
    server_vmid = None
    
    vms = proxmox.client.nodes(node).qemu.get()
    for vm in vms:
        vmid = vm.get("vmid")
        name = vm.get("name", "").lower()
        
        if "agentx" in name or "agent" in name or vmid == 100:
            agentx_vmid = vmid
            logger.info(f"Found agentX: VM {vmid} ({vm.get('name')})")
        
        if "server" in name and not agentx_vmid:
            server_vmid = vmid
            logger.info(f"Found server VM: VM {vmid} ({vm.get('name')})")
    
    if not agentx_vmid:
        logger.error("❌ Could not find agentX VM")
        logger.info("Please specify VM ID manually")
        return 1
    
    # Step 3: Add network interfaces
    if not dry_run:
        logger.info("")
        logger.info("Phase 3: Adding Network Interfaces")
        logger.info("-" * 70)
        
        # Add to agentX
        logger.info(f"Adding interface to agentX (VM {agentx_vmid})...")
        if await add_network_interface(proxmox, node, agentx_vmid, bridge, interface_num=1):
            logger.info("✅ Interface added to agentX")
        else:
            logger.error("❌ Failed to add interface to agentX")
            return 1
        
        # Add to server VM if found
        if server_vmid:
            logger.info(f"Adding interface to server VM (VM {server_vmid})...")
            if await add_network_interface(proxmox, node, server_vmid, bridge, interface_num=1):
                logger.info("✅ Interface added to server VM")
            else:
                logger.warning("⚠️  Failed to add interface to server VM")
        
        # Step 4: Configure IPs
        logger.info("")
        logger.info("Phase 4: Configuring Static IPs")
        logger.info("-" * 70)
        
        # Configure agentX IP (e.g., 192.168.215.10)
        agentx_ip = "192.168.215.10"
        agentx_host = "10.0.0.2"  # Current management IP
        
        logger.info(f"Configuring {agentx_ip} on agentX...")
        if await configure_static_ip_via_ssh(agentx_host, "ens7", agentx_ip):
            logger.info("✅ IP configured on agentX")
        else:
            logger.warning("⚠️  IP configuration may need manual intervention")
        
        # Configure server VM IP if found
        if server_vmid:
            server_ip = "192.168.215.11"
            # Get server VM current IP (would need to query)
            logger.info(f"Configuring {server_ip} on server VM...")
            logger.warning("⚠️  Server VM IP configuration requires manual setup")
        
        # Step 5: Verify connectivity
        logger.info("")
        logger.info("Phase 5: Verification")
        logger.info("-" * 70)
        
        if await verify_connectivity(agentx_ip, ORIGINAL_PROXMOX_IP):
            logger.info("✅ Connectivity verified!")
        else:
            logger.warning("⚠️  Connectivity test failed - may need time to establish")
    else:
        logger.info("")
        logger.info("Dry run complete. Review above and run with --execute to configure.")
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("Configuration Complete")
    logger.info("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

