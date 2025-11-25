#!/usr/bin/env python3
"""
Quick Azure Test - B1s instance

Tests Azure platform client with cheap instance type
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()
from glassdome.platforms.azure_client import AzureClient


async def test_azure_b1s():
    """Test Azure with B1s instance"""
    
    print("="*60)
    print("  Azure Platform Test - B1s")
    print("="*60)
    print(f"Region: {settings.azure_region}")
    print(f"Resource Group: {settings.azure_resource_group}")
    print(f"Instance Type: B1s (~$0.0104/hour)")
    print("="*60)
    
    # Initialize client
    client = AzureClient(
        subscription_id=settings.azure_subscription_id,
        tenant_id=settings.azure_tenant_id,
        client_id=settings.azure_client_id,
        client_secret=settings.azure_client_secret,
        region=settings.azure_region,
        resource_group=settings.azure_resource_group
    )
    
    # Test connection
    print("\n→ Testing Azure connection...")
    if await client.test_connection():
        print("✅ Azure connection successful!")
    else:
        print("❌ Azure connection failed!")
        return
    
    # Create VM
    print("\n→ Creating B1s instance...")
    print("  (This will cost ~$0.02 for the test)")
    
    vm_config = {
        "name": "glassdome-test-b1s",
        "os_type": "ubuntu",
        "os_version": "22.04",
        "vm_size": "Standard_B1s",
        "ssh_user": "ubuntu",
        "password": "Glassdome123!"
    }
    
    try:
        result = await client.create_vm(vm_config)
        
        print("\n" + "="*60)
        print("✅ VM CREATED!")
        print("="*60)
        print(f"VM ID:        {result['vm_id']}")
        print(f"Public IP:    {result['ip_address']}")
        print(f"Platform:     {result['platform']}")
        print(f"Status:       {result['status']}")
        print(f"Region:       {result['platform_specific']['region']}")
        print(f"VM Size:      {result['platform_specific']['vm_size']}")
        print(f"Resource Group: {result['platform_specific']['resource_group']}")
        print("="*60)
        
        print("\n→ SSH Test (wait 60 seconds for cloud-init)...")
        print(f"  ssh ubuntu@{result['ip_address']}")
        print(f"  Password: Glassdome123!")
        
        # Ask user if they want to terminate
        print("\n" + "="*60)
        terminate = input("Terminate instance now? (y/n): ")
        
        if terminate.lower() == 'y':
            print(f"\n→ Deleting VM {result['vm_id']}...")
            if await client.delete_vm(result['vm_id']):
                print("✅ VM deleted!")
            else:
                print("❌ Failed to delete VM")
        else:
            print("\n⚠️  REMEMBER TO DELETE THE VM LATER!")
            print(f"   Azure Portal → Resource Groups → {settings.azure_resource_group}")
            print(f"   Or use Azure CLI:")
            print(f"   az vm delete --resource-group {settings.azure_resource_group} --name {result['vm_id']} --yes")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_azure_b1s())
    
    if result:
        print("\n✅ Azure Platform Test PASSED!")
        sys.exit(0)
    else:
        print("\n❌ Azure Platform Test FAILED!")
        sys.exit(1)

