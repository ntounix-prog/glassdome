"""
Cloudbase-Init Configuration Generator

Generates Cloudbase-Init configuration files for Windows VMs on Proxmox.
Cloudbase-Init is the Windows equivalent of cloud-init.
"""
from typing import Dict, Any, Optional
import json
from pathlib import Path


def generate_cloudbase_init_conf(
    username: str = "Administrator",
    groups: str = "Administrators",
    inject_user_password: bool = True,
    metadata_services: Optional[list] = None,
    plugins: Optional[list] = None
) -> str:
    """
    Generate cloudbase-init.conf configuration file
    
    Args:
        username: Default username to create
        groups: Groups for the user
        inject_user_password: Whether to inject user password
        metadata_services: List of metadata service plugins
        plugins: List of Cloudbase-Init plugins to enable
    
    Returns:
        cloudbase-init.conf content as string
    """
    if metadata_services is None:
        metadata_services = [
            "cloudbaseinit.metadata.services.configdrive.ConfigDriveService"
        ]
    
    if plugins is None:
        plugins = [
            "cloudbaseinit.plugins.windows.createuser.CreateUserPlugin",
            "cloudbaseinit.plugins.windows.setuserpassword.SetUserPasswordPlugin",
            "cloudbaseinit.plugins.windows.networkingconfig.NetworkingConfigPlugin",
            "cloudbaseinit.plugins.windows.licensing.WindowsLicensingPlugin",
            "cloudbaseinit.plugins.windows.sshpublickeys.SetUserSSHPublicKeysPlugin",
        ]
    
    metadata_services_str = "\n".join([f"{i+1}={svc}" for i, svc in enumerate(metadata_services)])
    plugins_str = "\n".join([f"{i+1}={plugin}" for i, plugin in enumerate(plugins)])
    
    conf = f"""[DEFAULT]
# Username and groups
username={username}
groups={groups}
inject_user_password={str(inject_user_password).lower()}

# ConfigDrive datasource (Proxmox cloud-init drive)
config_drive_raw_hhd=true
config_drive_cdrom=true
config_drive_vfat=true

# Paths
bsdtar_path=C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\bin\\bsdtar.exe
mtools_path=C:\\Program Files\\Cloudbase Solutions\\Cloudbase-Init\\bin\\

# Logging
verbose=true
debug=true

# Metadata services
[metadata_services]
{metadata_services_str}

# Plugins
[plugins]
{plugins_str}
"""
    return conf


def generate_user_data_script(config: Dict[str, Any]) -> str:
    """
    Generate PowerShell user-data script for Cloudbase-Init
    
    Args:
        config: Configuration dictionary with:
            - hostname: Computer name
            - admin_password: Administrator password (optional, handled by Cloudbase-Init)
            - enable_rdp: Enable RDP (default: True)
            - disable_firewall: Disable Windows Firewall (default: True for cyber range)
            - static_ip: Static IP address (optional)
            - gateway: Default gateway (optional)
            - dns_servers: DNS servers list (optional)
            - custom_scripts: List of PowerShell commands to run
    
    Returns:
        PowerShell script as string
    """
    hostname = config.get("hostname", "glassdome-win")
    enable_rdp = config.get("enable_rdp", True)
    disable_firewall = config.get("disable_firewall", True)
    static_ip = config.get("static_ip")
    gateway = config.get("gateway", "192.168.3.1")
    dns_servers = config.get("dns_servers", ["8.8.8.8", "8.8.4.4"])
    custom_scripts = config.get("custom_scripts", [])
    
    script = f"""# PowerShell script for Cloudbase-Init
# Generated for Windows VM: {hostname}

# Set hostname
Rename-Computer -NewName "{hostname}" -Force

# Set network profile to Private
Set-NetConnectionProfile -NetworkCategory Private

"""
    
    # Static IP configuration
    if static_ip:
        dns_list = ",".join(dns_servers)
        script += f"""# Configure static IP
$adapter = Get-NetAdapter | Where-Object {{$_.Status -eq "Up"}} | Select-Object -First 1
if ($adapter) {{
    $interfaceAlias = $adapter.Name
    Remove-NetIPAddress -InterfaceAlias $interfaceAlias -Confirm:$false -ErrorAction SilentlyContinue
    New-NetIPAddress -InterfaceAlias $interfaceAlias -IPAddress {static_ip} -PrefixLength 24 -DefaultGateway {gateway}
    Set-DnsClientServerAddress -InterfaceAlias $interfaceAlias -ServerAddresses {dns_list}
    Write-Host "Static IP configured: {static_ip}"
}}

"""
    
    # RDP configuration
    if enable_rdp:
        script += """# Enable Remote Desktop
Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name "fDenyTSConnections" -Value 0 -Force
Enable-NetFirewallRule -DisplayGroup "Remote Desktop" -ErrorAction SilentlyContinue
Write-Host "RDP enabled"

"""
    
    # Firewall configuration
    if disable_firewall:
        script += """# Disable Windows Firewall (for cyber range)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
Write-Host "Windows Firewall disabled"

"""
    
    # Custom scripts
    if custom_scripts:
        script += "# Custom scripts\n"
        for i, cmd in enumerate(custom_scripts, 1):
            script += f"# Custom script {i}\n{cmd}\n\n"
    
    # Log completion
    script += """# Create initialization log
$logMessage = "Glassdome Windows Cloudbase-Init initialization completed at $(Get-Date)"
Add-Content -Path "C:\\glassdome-init.log" -Value $logMessage
Write-Host $logMessage

# Restart to apply hostname change
Restart-Computer -Force
"""
    
    return script


def generate_metadata_json(config: Dict[str, Any]) -> str:
    """
    Generate metadata.json for Cloudbase-Init (ConfigDrive format)
    
    Args:
        config: Configuration dictionary with:
            - instance_id: Instance ID
            - hostname: Hostname
            - network_config: Network configuration (optional)
    
    Returns:
        JSON string for metadata.json
    """
    instance_id = config.get("instance_id", "glassdome-instance-001")
    hostname = config.get("hostname", "glassdome-win")
    
    metadata = {
        "instance-id": instance_id,
        "local-hostname": hostname,
        "hostname": hostname,
    }
    
    # Add network configuration if provided
    network_config = config.get("network_config")
    if network_config:
        metadata["network_config"] = network_config
    
    return json.dumps(metadata, indent=2)


def create_cloudbase_init_config_files(
    output_dir: Path,
    config: Dict[str, Any]
) -> Dict[str, Path]:
    """
    Create all Cloudbase-Init configuration files
    
    Args:
        output_dir: Directory to write files
        config: Configuration dictionary
    
    Returns:
        Dictionary mapping file names to Path objects
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    files = {}
    
    # Generate cloudbase-init.conf
    conf_content = generate_cloudbase_init_conf(
        username=config.get("username", "Administrator"),
        groups=config.get("groups", "Administrators"),
        inject_user_password=config.get("inject_user_password", True)
    )
    conf_path = output_dir / "cloudbase-init.conf"
    conf_path.write_text(conf_content)
    files["cloudbase-init.conf"] = conf_path
    
    # Generate user-data script
    user_data = generate_user_data_script(config)
    user_data_path = output_dir / "user-data.ps1"
    user_data_path.write_text(user_data)
    files["user-data.ps1"] = user_data_path
    
    # Generate metadata.json
    metadata = generate_metadata_json(config)
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(metadata)
    files["metadata.json"] = metadata_path
    
    return files


if __name__ == "__main__":
    # Test generation
    test_config = {
        "hostname": "test-windows-vm",
        "enable_rdp": True,
        "disable_firewall": True,
        "static_ip": "192.168.3.100",
        "gateway": "192.168.3.1",
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
        "instance_id": "test-instance-001"
    }
    
    output = Path("/tmp/cloudbase-init-test")
    files = create_cloudbase_init_config_files(output, test_config)
    
    print("Generated files:")
    for name, path in files.items():
        print(f"  {name}: {path}")
        print(f"    Size: {path.stat().st_size} bytes")

