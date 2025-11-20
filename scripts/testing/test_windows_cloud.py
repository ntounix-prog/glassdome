"""
Test Windows deployment on AWS and Azure

Tests Windows Server 2022 deployment on cloud platforms to prove concept.
"""
import asyncio
import sys
from pathlib import Path

# Add glassdome to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glassdome.core.config import settings
from glassdome.agents.windows_installer import WindowsInstallerAgent
from glassdome.platforms.aws_client import AWSClient
from glassdome.platforms.azure_client import AzureClient


async def test_aws_windows():
    """Test Windows Server 2022 on AWS"""
    print("\n" + "="*60)
    print("  TEST 1: AWS Windows Server 2022")
    print("="*60)
    
    try:
        # Initialize AWS client
        aws_client = AWSClient(
            access_key_id=settings.aws_access_key_id,
            secret_access_key=settings.aws_secret_access_key,
            region=settings.aws_region
        )
        
        # Create Windows installer agent
        agent = WindowsInstallerAgent(aws_client)
        
        # Deploy Windows Server 2022
        print("\n→ Deploying Windows Server 2022 on AWS...")
        result = await agent.execute({
            "name": "glassdome-win-aws",
            "windows_version": "server2022",
            "memory_mb": 4096,
            "cpu_cores": 2
        })
        
        print("\n✅ AWS Windows Deployment SUCCESS!")
        print(f"   VM ID: {result['vm_id']}")
        print(f"   IP: {result['ip_address']}")
        print(f"   RDP: {result['windows_connection']['rdp_host']}:3389")
        print(f"   Username: {result['windows_connection']['username']}")
        print(f"   Password: {result['windows_connection']['password']}")
        
        # Ask if user wants to keep it or delete
        print("\n⚠️  VM is running (costs $$). Delete? (y/n): ", end="")
        sys.stdout.flush()
        # Auto-delete for testing
        print("y (auto-deleting)")
        
        print("\n→ Deleting Windows VM...")
        await agent.cleanup(result['vm_id'])
        print("✅ VM deleted")
        
        return True
        
    except Exception as e:
        print(f"\n❌ AWS Windows test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_azure_windows():
    """Test Windows Server 2022 on Azure"""
    print("\n" + "="*60)
    print("  TEST 2: Azure Windows Server 2022")
    print("="*60)
    
    try:
        # Initialize Azure client
        azure_client = AzureClient(
            subscription_id=settings.azure_subscription_id,
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
            region='eastus'
        )
        
        # Create Windows installer agent
        agent = WindowsInstallerAgent(azure_client)
        
        # Deploy Windows Server 2022
        print("\n→ Deploying Windows Server 2022 on Azure...")
        result = await agent.execute({
            "name": "glassdome-win-azure",
            "windows_version": "server2022",
            "memory_mb": 8192,
            "cpu_cores": 2
        })
        
        print("\n✅ Azure Windows Deployment SUCCESS!")
        print(f"   VM ID: {result['vm_id']}")
        print(f"   IP: {result['ip_address']}")
        print(f"   RDP: {result['windows_connection']['rdp_host']}:3389")
        print(f"   Username: {result['windows_connection']['username']}")
        print(f"   Password: {result['windows_connection']['password']}")
        
        # Ask if user wants to keep it or delete
        print("\n⚠️  VM is running (costs $$). Delete? (y/n): ", end="")
        sys.stdout.flush()
        # Auto-delete for testing
        print("y (auto-deleting)")
        
        print("\n→ Deleting Windows VM...")
        await agent.cleanup(result['vm_id'])
        print("✅ VM deleted")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Azure Windows test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all Windows cloud tests"""
    print("\n" + "="*60)
    print("  GLASSDOME WINDOWS DEPLOYMENT TEST")
    print("  Testing: AWS + Azure")
    print("="*60)
    
    # Test AWS
    aws_success = await test_aws_windows()
    
    # Test Azure
    azure_success = await test_azure_windows()
    
    # Summary
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    print(f"AWS:   {'✅ PASS' if aws_success else '❌ FAIL'}")
    print(f"Azure: {'✅ PASS' if azure_success else '❌ FAIL'}")
    print("="*60)
    
    if aws_success and azure_success:
        print("\n✅ ALL WINDOWS CLOUD TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

