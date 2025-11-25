sudo """
Deploy Windows Server 2022 and Windows 11 templates with Cloudbase-Init to Proxmox

This script creates Windows templates with Cloudbase-Init pre-installed for
headless cloud-init deployment on Proxmox.
"""
import asyncio
import sys
from pathlib import Path

# Add glassdome to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.integrations.cloudbase_init_builder import CloudbaseInitBuilder


async def deploy_windows_templates():
    """Deploy Windows Server 2022 and Windows 11 templates"""
    
    print("\n" + "="*70)
    print("  WINDOWS TEMPLATE DEPLOYMENT WITH CLOUDBASE-INIT")
    print("="*70)
    print()
    
    # Initialize Proxmox client
    if not settings.proxmox_host:
        print("❌ Error: PROXMOX_HOST not set in .env")
        return
    
    proxmox = ProxmoxClient(
        host=settings.proxmox_host,
        user=settings.proxmox_user or "root@pam",
        password=settings.proxmox_password,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
        default_node=settings.proxmox_node
    )
    
    # Template IDs
    windows_server2022_template_id = 9100
    windows_11_template_id = 9101
    
    print("Template IDs:")
    print(f"  Windows Server 2022: {windows_server2022_template_id}")
    print(f"  Windows 11: {windows_11_template_id}")
    print()
    
    # Check if VMs already exist and delete them
    print("Checking for existing VMs...")
    try:
        vms = proxmox.client.nodes(settings.proxmox_node).qemu.get()
        for vm in vms:
            vmid = vm.get("vmid")
            status = vm.get("status")
            
            if vmid == windows_server2022_template_id:
                print(f"⚠️  VM {windows_server2022_template_id} already exists (status: {status})")
                if status == "running":
                    print(f"   Stopping VM {windows_server2022_template_id}...")
                    try:
                        proxmox.client.nodes(settings.proxmox_node).qemu(windows_server2022_template_id).status.stop.post()
                        import time
                        time.sleep(5)
                    except Exception as e:
                        print(f"   ⚠️  Failed to stop: {e}")
                print(f"   Deleting VM {windows_server2022_template_id}...")
                try:
                    proxmox.client.nodes(settings.proxmox_node).qemu(windows_server2022_template_id).delete()
                    print(f"✅ Deleted existing VM {windows_server2022_template_id}")
                except Exception as e:
                    print(f"❌ Failed to delete VM {windows_server2022_template_id}: {e}")
            
            if vmid == windows_11_template_id:
                print(f"⚠️  VM {windows_11_template_id} already exists (status: {status})")
                if status == "running":
                    print(f"   Stopping VM {windows_11_template_id}...")
                    try:
                        proxmox.client.nodes(settings.proxmox_node).qemu(windows_11_template_id).status.stop.post()
                        import time
                        time.sleep(5)
                    except Exception as e:
                        print(f"   ⚠️  Failed to stop: {e}")
                print(f"   Deleting VM {windows_11_template_id}...")
                try:
                    proxmox.client.nodes(settings.proxmox_node).qemu(windows_11_template_id).delete()
                    print(f"✅ Deleted existing VM {windows_11_template_id}")
                except Exception as e:
                    print(f"❌ Failed to delete VM {windows_11_template_id}: {e}")
    except Exception as e:
        print(f"⚠️  Could not check for existing VMs: {e}")
    
    print()
    
    # Deploy Windows Server 2022
    print("\n" + "-"*70)
    print("  DEPLOYING WINDOWS SERVER 2022 TEMPLATE")
    print("-"*70)
    print()
    
    builder = CloudbaseInitBuilder(proxmox)
    
    result_2022 = await builder.create_windows_template_with_cloudbase_init(
        template_id=windows_server2022_template_id,
        windows_version="server2022",
        node=settings.proxmox_node,
        storage="local-lvm",
        config={
            "admin_password": "Glassdome123!",
            "vlan_tag": 2,  # VLAN 2 for 192.168.3.x network
            "desktop_experience": True  # Full GUI version (not Server Core/headless)
        }
    )
    
    if result_2022.get("success"):
        print("✅ Windows Server 2022 template creation started")
        print(f"   Template ID: {windows_server2022_template_id}")
        print(f"   Config files: {result_2022.get('config_files', {})}")
        print()
        print("⚠️  Manual steps required:")
        for i, step in enumerate(result_2022.get("next_steps", []), 1):
            print(f"   {i}. {step}")
    else:
        print(f"❌ Failed to create Windows Server 2022 template: {result_2022.get('error')}")
    
    print()
    
    # Deploy Windows 11
    print("\n" + "-"*70)
    print("  DEPLOYING WINDOWS 11 TEMPLATE")
    print("-"*70)
    print()
    
    result_11 = await builder.create_windows_template_with_cloudbase_init(
        template_id=windows_11_template_id,
        windows_version="win11",
        node=settings.proxmox_node,
        storage="local-lvm",
        config={
            "admin_password": "Glassdome123!",
            "vlan_tag": 2  # VLAN 2 for 192.168.3.x network
        }
    )
    
    if result_11.get("success"):
        print("✅ Windows 11 template creation started")
        print(f"   Template ID: {windows_11_template_id}")
        print(f"   Config files: {result_11.get('config_files', {})}")
        print()
        print("⚠️  Manual steps required:")
        for i, step in enumerate(result_11.get("next_steps", []), 1):
            print(f"   {i}. {step}")
    else:
        print(f"❌ Failed to create Windows 11 template: {result_11.get('error')}")
    
    print()
    print("="*70)
    print("  DEPLOYMENT INITIATED")
    print("="*70)
    print()
    print("Next steps:")
    print("1. Monitor Windows installation in Proxmox console")
    print("2. After installation completes, RDP into each VM")
    print("3. Install Cloudbase-Init from: https://www.cloudbase.it/cloudbase-init/")
    print("4. Copy configuration files to: C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\conf\\")
    print("5. Install QEMU guest agent")
    print("6. Run sysprep and convert to template")
    print()


if __name__ == "__main__":
    asyncio.run(deploy_windows_templates())

