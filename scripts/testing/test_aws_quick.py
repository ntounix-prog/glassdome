#!/usr/bin/env python3
"""
Quick AWS Test - t4g.nano instance

Tests AWS platform client with cheapest instance type
"""
import sys
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glassdome.core.config import settings
from glassdome.platforms.aws_client import AWSClient


async def test_aws_nano():
    """Test AWS with t4g.nano instance"""
    
    print("="*60)
    print("  AWS Platform Test - t4g.nano")
    print("="*60)
    print(f"Region: {settings.aws_region}")
    print(f"Instance Type: t4g.nano (ARM-based, ~$0.0042/hour)")
    print("="*60)
    
    # Initialize client
    client = AWSClient(
        access_key_id=settings.aws_access_key_id,
        secret_access_key=settings.aws_secret_access_key,
        region=settings.aws_region
    )
    
    # Test connection
    print("\n→ Testing AWS connection...")
    if await client.test_connection():
        print("✅ AWS connection successful!")
    else:
        print("❌ AWS connection failed!")
        return
    
    # Create VM
    print("\n→ Creating t4g.nano instance...")
    print("  (This will cost ~$0.01 for the test)")
    
    vm_config = {
        "name": "glassdome-test-nano",
        "os_type": "ubuntu",
        "os_version": "22.04",
        "instance_type": "t4g.nano",  # Explicitly use nano
        "ssh_user": "ubuntu",
        "password": "glassdome123"
    }
    
    try:
        result = await client.create_vm(vm_config)
        
        print("\n" + "="*60)
        print("✅ VM CREATED!")
        print("="*60)
        print(f"Instance ID:  {result['vm_id']}")
        print(f"Public IP:    {result['ip_address']}")
        print(f"Platform:     {result['platform']}")
        print(f"Status:       {result['status']}")
        print(f"Region:       {result['platform_specific']['region']}")
        print(f"Instance Type: {result['platform_specific']['instance_type']}")
        print("="*60)
        
        print("\n→ SSH Test (wait 30 seconds for cloud-init)...")
        print(f"  ssh ubuntu@{result['ip_address']}")
        print(f"  Password: glassdome123")
        
        # Ask user if they want to terminate
        print("\n" + "="*60)
        terminate = input("Terminate instance now? (y/n): ")
        
        if terminate.lower() == 'y':
            print(f"\n→ Terminating instance {result['vm_id']}...")
            if await client.delete_vm(result['vm_id']):
                print("✅ Instance terminated!")
            else:
                print("❌ Failed to terminate instance")
        else:
            print("\n⚠️  REMEMBER TO TERMINATE THE INSTANCE LATER!")
            print(f"   aws ec2 terminate-instances --instance-ids {result['vm_id']} --region {settings.aws_region}")
            print(f"   Or use AWS console")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_aws_nano())
    
    if result:
        print("\n✅ AWS Platform Test PASSED!")
        sys.exit(0)
    else:
        print("\n❌ AWS Platform Test FAILED!")
        sys.exit(1)

