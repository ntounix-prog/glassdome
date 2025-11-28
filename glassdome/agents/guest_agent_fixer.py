"""
Guest Agent Fixer module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.core.ssh_client import SSHClient
from pathlib import Path

logger = logging.getLogger(__name__)


class GuestAgentFixer:
    """
    Automatically fixes qemu-guest-agent issues in VMs
    
    Detects:
    - Guest agent not running
    - Guest agent not installed
    - Guest agent service disabled
    
    Actions:
    - Installs qemu-guest-agent via SSH
    - Enables and starts the service
    - Verifies it's working
    """
    
    def __init__(self, proxmox_client: ProxmoxClient, ssh_key_path: str = "/tmp/glassdome_key"):
        """
        Initialize Guest Agent Fixer
        
        Args:
            proxmox_client: Proxmox client for VM management
            ssh_key_path: Path to SSH private key for VM access
        """
        self.proxmox = proxmox_client
        self.ssh_key_path = ssh_key_path
    
    async def check_guest_agent(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Check if guest agent is working for a VM
        
        Args:
            node: Proxmox node name
            vmid: VM ID
            
        Returns:
            Status dict with 'working', 'installed', 'running', 'issues'
        """
        status = {
            "working": False,
            "installed": False,
            "running": False,
            "issues": []
        }
        
        try:
            # Try to get VM info via guest agent
            info = self.proxmox.client.nodes(node).qemu(vmid).agent('info').get()
            status["working"] = True
            status["running"] = True
            logger.info(f"VM {vmid}: Guest agent is working")
            return status
        except Exception as e:
            error_msg = str(e)
            if "not running" in error_msg.lower():
                status["issues"].append("Guest agent not running")
            elif "not installed" in error_msg.lower():
                status["issues"].append("Guest agent not installed")
            else:
                status["issues"].append(f"Guest agent error: {error_msg}")
            
            logger.warning(f"VM {vmid}: Guest agent issue - {error_msg}")
            return status
    
    async def fix_guest_agent(self, node: str, vmid: int, ip_address: Optional[str] = None, 
                              ssh_user: str = "ubuntu") -> Dict[str, Any]:
        """
        Fix guest agent issues for a VM
        
        Args:
            node: Proxmox node name
            vmid: VM ID
            ip_address: VM IP address (if known, otherwise will try to get it)
            ssh_user: SSH username
            
        Returns:
            Fix result dict
        """
        result = {
            "success": False,
            "method": None,
            "error": None
        }
        
        # Get IP if not provided
        if not ip_address:
            try:
                ip_address = await self.proxmox.get_vm_ip(str(vmid), timeout=10)
            except:
                pass
        
        if not ip_address:
            result["error"] = "Cannot get IP address - guest agent required for IP detection"
            logger.error(f"VM {vmid}: Cannot fix guest agent without IP address")
            return result
        
        # Try to fix via SSH
        logger.info(f"VM {vmid}: Attempting to fix guest agent via SSH ({ip_address})")
        
        ssh = SSHClient(
            host=ip_address,
            username=ssh_user,
            key_filename=self.ssh_key_path
        )
        
        try:
            # Connect
            if not await ssh.connect():
                result["error"] = "SSH connection failed"
                return result
            
            # Check if installed
            check_result = await ssh.execute("dpkg -l | grep qemu-guest-agent")
            installed = "qemu-guest-agent" in check_result.get("stdout", "")
            
            if not installed:
                logger.info(f"VM {vmid}: Installing qemu-guest-agent...")
                # Install
                install_result = await ssh.execute("sudo apt update -qq && sudo apt install -y qemu-guest-agent")
                if not install_result.get("success"):
                    result["error"] = f"Installation failed: {install_result.get('stderr', 'Unknown')}"
                    await ssh.disconnect()
                    return result
            
            # Enable and start
            logger.info(f"VM {vmid}: Enabling and starting guest agent...")
            enable_result = await ssh.execute("sudo systemctl enable qemu-guest-agent")
            start_result = await ssh.execute("sudo systemctl start qemu-guest-agent")
            
            # Verify
            status_result = await ssh.execute("sudo systemctl is-active qemu-guest-agent")
            if "active" in status_result.get("stdout", ""):
                result["success"] = True
                result["method"] = "ssh"
                logger.info(f"VM {vmid}: Guest agent fixed and running")
            else:
                result["error"] = "Service started but not active"
            
            await ssh.disconnect()
            
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"VM {vmid}: Error fixing guest agent: {e}")
        
        return result
    
    async def check_and_fix(self, node: str, vmid: int, ip_address: Optional[str] = None,
                           ssh_user: str = "ubuntu", auto_fix: bool = True) -> Dict[str, Any]:
        """
        Check guest agent and fix if needed
        
        Args:
            node: Proxmox node name
            vmid: VM ID
            ip_address: VM IP address (optional)
            ssh_user: SSH username
            auto_fix: Whether to automatically fix issues
            
        Returns:
            Complete status and fix result
        """
        # Check status
        status = await self.check_guest_agent(node, vmid)
        
        result = {
            "status": status,
            "fixed": False,
            "fix_result": None
        }
        
        # Fix if needed
        if not status["working"] and auto_fix:
            fix_result = await self.fix_guest_agent(node, vmid, ip_address, ssh_user)
            result["fix_result"] = fix_result
            result["fixed"] = fix_result.get("success", False)
            
            # Re-check after fix
            if fix_result.get("success"):
                await asyncio.sleep(5)  # Give it a moment
                status = await self.check_guest_agent(node, vmid)
                result["status"] = status
        
        return result

