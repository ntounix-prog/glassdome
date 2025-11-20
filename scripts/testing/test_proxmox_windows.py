"""
Test Windows Server 2022 Deployment on Proxmox

Tests the complete Windows deployment flow:
1. ISO upload verification
2. Autounattend.xml generation
3. VM creation with static IP
4. Windows auto-install
"""
import asyncio
import sys
from pathlib import Path

# Add glassdome to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glassdome.core.config import settings
from glassdome.agents.windows_installer import WindowsInstallerAgent
from glassdome.platforms.proxmox_client import ProxmoxClient


async def test_proxmox_windows():
    """Test Windows Server 2022 deployment on Proxmox"""
    
    print("\n" + "="*60)
    print("  PROXMOX WINDOWS SERVER 2022 DEPLOYMENT TEST")
    print("="*60)
    print("")
    
    try:
        # Initialize Proxmox client
        print("→ Connecting to Proxmox...")
        proxmox_client = ProxmoxClient(
            host=settings.proxmox_host,
            user=settings.proxmox_user,
            token_name=settings.proxmox_token_name,
            token_value=settings.proxmox_token_value,
            verify_ssl=False,
            default_node=settings.proxmox_node
        )
        print(f"✅ Connected to Proxmox: {settings.proxmox_host}")
        print("")
        
        # Create Windows installer agent
        agent = WindowsInstallerAgent(proxmox_client)
        
        # Deploy Windows Server 2022
        print("→ Deploying Windows Server 2022...")
        print("   This will:")
        print("   1. Allocate static IP from pool (192.168.3.30-40)")
        print("   2. Generate autounattend.xml with static IP config")
        print("   3. Create VM with Windows ISO + VirtIO drivers")
        print("   4. Start VM → Windows auto-installs (~15-20 minutes)")
        print("")
        
        result = await agent.execute({
            "name": "glassdome-win-test",
            "windows_version": "server2022",
            "memory_mb": 4096,
            "cpu_cores": 2,
            "disk_size_gb": 80,
            "admin_password": "Glassdome123!",
            "network_cidr": "192.168.3.0/24"
        })
        
        print("")
        print("="*60)
        print("✅ Windows VM Created!")
        print("="*60)
        print(f"VM ID: {result['vm_id']}")
        print(f"Static IP: {result['ip_address']}")
        print(f"Status: {result['status']}")
        print("")
        print("📋 Connection Info:")
        print(f"   RDP: {result['ip_address']}:3389")
        print(f"   Username: Administrator")
        print(f"   Password: Glassdome123!")
        print("")
        print("⏱️  Windows is now installing automatically.")
        print("   This takes 15-20 minutes.")
        print("")
        print("🖥️  Monitor progress:")
        print(f"   - Open Proxmox console: https://{settings.proxmox_host}:8006")
        print(f"   - View VM: {result['vm_id']}")
        print(f"   - Click 'Console' to watch Windows installation")
        print("")
        print("✅ After installation completes, test RDP:")
        print(f"   rdesktop {result['ip_address']} -u Administrator -p Glassdome123!")
        print("")
        
        return True
        
    except Exception as e:
        print("")
        print("❌ Windows deployment FAILED")
        print(f"   Error: {e}")
        print("")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("")
    print("PREREQUISITES:")
    print("  1. ISOs must be uploaded to Proxmox")
    print("     Run: ./scripts/upload_isos_to_proxmox.sh")
    print("  2. Proxmox credentials in .env")
    print("")
    
    input("Press ENTER to continue or Ctrl+C to abort...")
    
    success = asyncio.run(test_proxmox_windows())
    
    sys.exit(0 if success else 1)

