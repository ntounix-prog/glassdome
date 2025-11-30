#!/usr/bin/env python3
"""
Test Windows Server 2022 deployment on ESXi
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from glassdome.agents.windows_installer import WindowsInstallerAgent
from glassdome.platforms.esxi_client import ESXiClient
from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
import logging

# Use centralized logging
try:
    from glassdome.core.logging import setup_logging_from_settings
    setup_logging_from_settings()
except ImportError:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_esxi_windows():
    """Test Windows Server 2022 on ESXi"""
    
    # Initialize ESXi platform client
    platform_client = ESXiClient(
        host=settings.esxi_host,
        user=settings.esxi_user,
        password=settings.esxi_password,
        verify_ssl=False
    )
    agent = WindowsInstallerAgent(platform_client)
    
    # ESXi Windows deployment configuration
    task = {
        "platform": "esxi",
        "name": "glassdome-win-esxi-test",
        "os_version": "2022",  # Windows Server 2022
        "cores": 2,
        "memory": 4096,
        "disk_size_gb": 80,
        "password": "Glassdome123!",
        
        # Static IP configuration (required for ESXi)
        "ip_address": "192.168.3.35",
        "gateway": "192.168.3.1",
        "subnet_mask": "255.255.255.0",
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        
        # ISO paths on ESXi NFSSTORE
        "iso_path": "[NFSSTORE] iso/windows-server-2022-eval.iso",
        "virtio_iso_path": "[NFSSTORE] iso/virtio-win.iso",
    }
    
    logger.info("=" * 60)
    logger.info("🪟 Testing Windows Server 2022 deployment on ESXi")
    logger.info("=" * 60)
    logger.info(f"VM Name: {task['name']}")
    logger.info(f"OS: Windows Server {task['os_version']}")
    logger.info(f"IP: {task['ip_address']}")
    logger.info(f"Resources: {task['cores']} cores, {task['memory']} MB RAM, {task['disk_size_gb']} GB disk")
    logger.info(f"ISOs: {task['iso_path']}, {task['virtio_iso_path']}")
    logger.info("=" * 60)
    
    try:
        result = await agent.execute(task)
        
        if result.get('status') == 'completed':
            logger.info("")
            logger.info("✅ Windows VM deployed successfully on ESXi!")
            logger.info(f"VM ID: {result.get('vm_id')}")
            logger.info(f"IP Address: {task['ip_address']}")
            logger.info(f"Username: Administrator")
            logger.info(f"Password: {task['password']}")
            logger.info("")
            logger.info("⏳ Windows installation is now running automatically...")
            logger.info("   - This will take 15-20 minutes")
            logger.info("   - VM will reboot several times")
            logger.info("   - RDP will be enabled automatically")
            logger.info("")
            logger.info(f"🔌 Connect via RDP: {task['ip_address']}:3389")
            logger.info(f"   Username: Administrator")
            logger.info(f"   Password: {task['password']}")
            
            return result
        else:
            logger.error(f"❌ Deployment failed: {result.get('error')}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    asyncio.run(test_esxi_windows())

