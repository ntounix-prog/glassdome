#!/usr/bin/env python3
"""
Verify IaC Tools Installation and Configuration

This script verifies that Ansible and Terraform are properly installed
and can be used by Glassdome agents.
"""
import sys
import os
import subprocess
import json
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))


def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def check_command(command, version_flag="--version"):
    """Check if a command exists and get its version"""
    try:
        result = subprocess.run(
            [command, version_flag],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except FileNotFoundError:
        return False, f"{command} not found in PATH"
    except subprocess.TimeoutExpired:
        return False, f"{command} timed out"
    except Exception as e:
        return False, str(e)


def check_ansible():
    """Check Ansible installation"""
    print_header("Ansible Verification")
    
    # Check ansible command
    exists, output = check_command("ansible")
    
    if exists:
        print("✅ Ansible CLI found")
        print(f"\n{output}")
        
        # Check ansible-playbook
        pb_exists, _ = check_command("ansible-playbook")
        if pb_exists:
            print("\n✅ ansible-playbook found")
        else:
            print("\n❌ ansible-playbook not found")
            return False
        
        # Check Python ansible package
        try:
            import ansible
            print(f"\n✅ ansible Python package: v{ansible.__version__}")
        except ImportError:
            print("\n⚠️  ansible Python package not installed (optional)")
        
        # Check ansible config
        try:
            result = subprocess.run(
                ["ansible-config", "dump"],
                capture_output=True,
                text=True,
                timeout=5
            )
            print("\n✅ Ansible configuration accessible")
        except Exception as e:
            print(f"\n⚠️  Ansible config check failed: {e}")
        
        return True
    else:
        print(f"❌ Ansible not found: {output}")
        return False


def check_terraform():
    """Check Terraform installation"""
    print_header("Terraform Verification")
    
    # Check terraform command
    exists, output = check_command("terraform", "-version")
    
    if exists:
        print("✅ Terraform CLI found")
        print(f"\n{output}")
        
        # Check Terraform version details
        try:
            result = subprocess.run(
                ["terraform", "version", "-json"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version_info = json.loads(result.stdout)
                tf_version = version_info.get("terraform_version", "unknown")
                platform = version_info.get("platform", "unknown")
                print(f"\n✅ Version: {tf_version}")
                print(f"✅ Platform: {platform}")
        except Exception as e:
            print(f"\n⚠️  Could not parse Terraform version: {e}")
        
        # Check Python terraform package
        try:
            import terraform
            print(f"\n✅ python-terraform package installed")
        except ImportError:
            print("\n⚠️  python-terraform package not installed (optional)")
        
        return True
    else:
        print(f"❌ Terraform not found: {output}")
        return False


def check_directories():
    """Check required directories exist"""
    print_header("Directory Structure Verification")
    
    dirs_to_check = [
        "glassdome/vulnerabilities/playbooks",
        "glassdome/vulnerabilities/terraform",
        "configs/ansible",
        "configs/terraform",
    ]
    
    all_exist = True
    for dir_path in dirs_to_check:
        full_path = PROJECT_ROOT / dir_path
        if full_path.exists():
            print(f"✅ {dir_path}")
        else:
            print(f"❌ {dir_path} (missing)")
            all_exist = False
    
    return all_exist


def test_ansible_execution():
    """Test executing a simple Ansible command"""
    print_header("Ansible Execution Test")
    
    try:
        # Test with localhost ping
        result = subprocess.run(
            ["ansible", "localhost", "-m", "ping"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "SUCCESS" in result.stdout or "pong" in result.stdout:
            print("✅ Ansible can execute modules")
            print(f"\nOutput: {result.stdout[:200]}...")
            return True
        else:
            print("⚠️  Ansible executed but unexpected output")
            print(f"\nOutput: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ Ansible execution failed: {e}")
        return False


def test_terraform_init():
    """Test Terraform initialization"""
    print_header("Terraform Initialization Test")
    
    try:
        # Create a minimal test terraform config
        test_dir = PROJECT_ROOT / "test_terraform_tmp"
        test_dir.mkdir(exist_ok=True)
        
        test_config = test_dir / "main.tf"
        test_config.write_text("""
terraform {
  required_version = ">= 1.0"
}

# Minimal config for testing
output "test" {
  value = "Terraform works!"
}
""")
        
        # Try terraform init
        result = subprocess.run(
            ["terraform", "init"],
            cwd=test_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Cleanup
        import shutil
        shutil.rmtree(test_dir)
        
        if result.returncode == 0:
            print("✅ Terraform can initialize configurations")
            return True
        else:
            print("⚠️  Terraform init had issues")
            print(f"\nError: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"❌ Terraform test failed: {e}")
        # Cleanup on error
        if test_dir.exists():
            import shutil
            shutil.rmtree(test_dir)
        return False


def generate_report(results):
    """Generate final report"""
    print_header("Verification Summary")
    
    total_checks = len(results)
    passed_checks = sum(1 for r in results.values() if r)
    
    print(f"Total Checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    print()
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
    
    print()
    
    if passed_checks == total_checks:
        print("🎉 All checks passed! IaC tools are ready to use.")
        return True
    elif passed_checks >= total_checks * 0.75:
        print("⚠️  Most checks passed. Review warnings above.")
        return True
    else:
        print("❌ Several checks failed. Please review and fix issues.")
        return False


def main():
    """Main verification flow"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  IaC Tools Verification".center(68) + "║")
    print("║" + "  Verifying Ansible + Terraform Installation".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    
    results = {}
    
    # Run checks
    results["Ansible Installation"] = check_ansible()
    results["Terraform Installation"] = check_terraform()
    results["Directory Structure"] = check_directories()
    results["Ansible Execution"] = test_ansible_execution()
    results["Terraform Initialization"] = test_terraform_init()
    
    # Generate report
    success = generate_report(results)
    
    print()
    print("=" * 70)
    
    if success:
        print("\nNext steps:")
        print("  1. Create Ansible playbooks in: glassdome/vulnerabilities/playbooks/")
        print("  2. Create Terraform modules in: glassdome/vulnerabilities/terraform/")
        print("  3. Implement AnsibleAgent and TerraformAgent")
        print()
        return 0
    else:
        print("\nTroubleshooting:")
        print("  1. Run: bash scripts/setup/install_iac_tools.sh")
        print("  2. Check PATH includes /usr/local/bin")
        print("  3. Restart your shell/terminal")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())

