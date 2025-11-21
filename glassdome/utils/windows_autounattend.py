"""
Windows Autounattend.xml Generator

Creates Windows answer files for unattended installation on Proxmox/ESXi.
Supports Windows Server 2022 and Windows 11.
"""
import base64
from typing import Dict, Any, Optional
from pathlib import Path


def generate_autounattend_xml(config: Dict[str, Any]) -> str:
    """
    Generate Windows autounattend.xml for unattended installation
    
    Args:
        config: Configuration dictionary with:
            - hostname: Computer name (default: "glassdome-win")
            - admin_password: Administrator password (default: "Glassdome123!")
            - windows_version: "server2022" or "win11" (default: "server2022")
            - timezone: Windows timezone (default: "Pacific Standard Time")
            - enable_rdp: Enable RDP (default: True)
            - virtio_drivers: Include VirtIO driver paths for Proxmox (default: True)
            - product_key: Windows product key (optional, will use eval if not provided)
            - static_ip: Static IP address (e.g., "192.168.3.30")
            - gateway: Default gateway (e.g., "192.168.3.1")
            - netmask: Network mask (default: "255.255.255.0")
            - dns: DNS servers (default: ["8.8.8.8", "8.8.4.4"])
    
    Returns:
        autounattend.xml content as string
    """
    hostname = config.get("hostname", "glassdome-win")
    admin_password = config.get("admin_password", "Glassdome123!")
    windows_version = config.get("windows_version", "server2022")
    timezone = config.get("timezone", "Pacific Standard Time")
    enable_rdp = config.get("enable_rdp", True)
    virtio_drivers = config.get("virtio_drivers", True)
    product_key = config.get("product_key", "")
    
    # Network configuration
    static_ip = config.get("static_ip")
    gateway = config.get("gateway", "192.168.3.1")
    netmask = config.get("netmask", "255.255.255.0")
    dns_servers = config.get("dns", ["8.8.8.8", "8.8.4.4"])
    
    # Encode admin password for Windows
    admin_password_b64 = base64.b64encode(f"{admin_password}AdministratorPassword".encode('utf-16-le')).decode('ascii')
    
    # Image index (1 = Standard, 2 = Datacenter for Server 2022)
    if windows_version == "server2022":
        image_index = "2"  # Datacenter
        image_name = "Windows Server 2022 SERVERDATACENTER"
    elif windows_version == "win11":
        image_index = "1"  # Windows 11 Enterprise
        image_name = "Windows 11 Enterprise"
    else:
        image_index = "2"
        image_name = "Windows Server 2022 SERVERDATACENTER"
    
    # Build driver paths for VirtIO (Proxmox)
    virtio_driver_paths = ""
    if virtio_drivers:
        virtio_driver_paths = """
            <!-- VirtIO Drivers for Proxmox/KVM -->
            <PathAndCredentials wcm:action="add" wcm:keyValue="1">
                <Path>E:\\vioscsi\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="2">
                <Path>E:\\NetKVM\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="3">
                <Path>E:\\Balloon\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="4">
                <Path>E:\\qemufwcfg\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="5">
                <Path>E:\\qemupciserial\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="6">
                <Path>E:\\vioinput\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="7">
                <Path>E:\\viorng\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="8">
                <Path>E:\\vioserial\\2k22\\amd64</Path>
            </PathAndCredentials>
            <PathAndCredentials wcm:action="add" wcm:keyValue="9">
                <Path>E:\\viostor\\2k22\\amd64</Path>
            </PathAndCredentials>"""
    
    # Product key section (empty for eval)
    product_key_xml = ""
    if product_key:
        product_key_xml = f"<ProductKey>{product_key}</ProductKey>"
    
    # RDP configuration
    rdp_config = ""
    if enable_rdp:
        rdp_config = """
            <!-- Enable Remote Desktop -->
            <RunSynchronousCommand wcm:action="add">
                <Order>5</Order>
                <Path>cmd.exe /c reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f</Path>
            </RunSynchronousCommand>
            <RunSynchronousCommand wcm:action="add">
                <Order>6</Order>
                <Path>cmd.exe /c netsh advfirewall firewall add rule name="Remote Desktop" protocol=TCP dir=in localport=3389 action=allow</Path>
            </RunSynchronousCommand>"""
    
    # Static IP configuration
    static_ip_config = ""
    if static_ip:
        dns_list = ",".join(dns_servers)
        static_ip_config = f"""
                <!-- Set Static IP -->
                <SynchronousCommand wcm:action="add">
                    <Order>5</Order>
                    <CommandLine>powershell.exe -Command "New-NetIPAddress -InterfaceAlias 'Ethernet*' -IPAddress {static_ip} -PrefixLength 24 -DefaultGateway {gateway}"</CommandLine>
                    <Description>Set Static IP</Description>
                </SynchronousCommand>
                <SynchronousCommand wcm:action="add">
                    <Order>6</Order>
                    <CommandLine>powershell.exe -Command "Set-DnsClientServerAddress -InterfaceAlias 'Ethernet*' -ServerAddresses {dns_list}"</CommandLine>
                    <Description>Set DNS Servers</Description>
                </SynchronousCommand>"""
    
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">
    <!-- Windows PE (Installation Phase) -->
    <settings pass="windowsPE">
        <component name="Microsoft-Windows-International-Core-WinPE" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <SetupUILanguage>
                <UILanguage>en-US</UILanguage>
            </SetupUILanguage>
            <InputLocale>en-US</InputLocale>
            <SystemLocale>en-US</SystemLocale>
            <UILanguage>en-US</UILanguage>
            <UserLocale>en-US</UserLocale>
        </component>
        
        <component name="Microsoft-Windows-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <DiskConfiguration>
                <Disk wcm:action="add">
                    <CreatePartitions>
                        <CreatePartition wcm:action="add">
                            <Order>1</Order>
                            <Type>Primary</Type>
                            <Extend>true</Extend>
                        </CreatePartition>
                    </CreatePartitions>
                    <ModifyPartitions>
                        <ModifyPartition wcm:action="add">
                            <Active>true</Active>
                            <Format>NTFS</Format>
                            <Label>Windows</Label>
                            <Order>1</Order>
                            <PartitionID>1</PartitionID>
                        </ModifyPartition>
                    </ModifyPartitions>
                    <DiskID>0</DiskID>
                    <WillWipeDisk>true</WillWipeDisk>
                </Disk>
            </DiskConfiguration>
            
            <ImageInstall>
                <OSImage>
                    <InstallFrom>
                        <MetaData wcm:action="add">
                            <Key>/IMAGE/INDEX</Key>
                            <Value>{image_index}</Value>
                        </MetaData>
                    </InstallFrom>
                    <InstallTo>
                        <DiskID>0</DiskID>
                        <PartitionID>1</PartitionID>
                    </InstallTo>
                </OSImage>
            </ImageInstall>
            
            <UserData>
                <AcceptEula>true</AcceptEula>
                <FullName>Glassdome Administrator</FullName>
                <Organization>Glassdome Cyber Range</Organization>
                {product_key_xml}
            </UserData>
            
            <!-- Driver Paths -->{virtio_driver_paths}
        </component>
    </settings>
    
    <!-- Specialize (System Configuration Phase) -->
    <settings pass="specialize">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <ComputerName>{hostname}</ComputerName>
            <TimeZone>{timezone}</TimeZone>
        </component>
        
        <component name="Microsoft-Windows-TerminalServices-LocalSessionManager" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <fDenyTSConnections>false</fDenyTSConnections>
        </component>
        
        <component name="Microsoft-Windows-TerminalServices-RDP-WinStationExtensions" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <UserAuthentication>0</UserAuthentication>
        </component>
        
        <component name="Networking-MPSSVC-Svc" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <FirewallGroups>
                <FirewallGroup wcm:action="add" wcm:keyValue="RemoteDesktop">
                    <Active>true</Active>
                    <Group>Remote Desktop</Group>
                    <Profile>all</Profile>
                </FirewallGroup>
            </FirewallGroups>
        </component>
    </settings>
    
    <!-- OOBE (Out-of-Box Experience Phase) -->
    <settings pass="oobeSystem">
        <component name="Microsoft-Windows-Shell-Setup" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
            <OOBE>
                <HideEULAPage>true</HideEULAPage>
                <HideLocalAccountScreen>true</HideLocalAccountScreen>
                <HideOEMRegistrationScreen>true</HideOEMRegistrationScreen>
                <HideOnlineAccountScreens>true</HideOnlineAccountScreens>
                <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
                <ProtectYourPC>3</ProtectYourPC>
            </OOBE>
            
            <UserAccounts>
                <AdministratorPassword>
                    <Value>{admin_password}</Value>
                    <PlainText>true</PlainText>
                </AdministratorPassword>
            </UserAccounts>
            
            <FirstLogonCommands>
                <!-- Disable Windows Firewall for cyber range -->
                <SynchronousCommand wcm:action="add">
                    <Order>1</Order>
                    <CommandLine>cmd.exe /c netsh advfirewall set allprofiles state off</CommandLine>
                    <Description>Disable Windows Firewall</Description>
                </SynchronousCommand>
                
                <!-- Enable RDP -->
                <SynchronousCommand wcm:action="add">
                    <Order>2</Order>
                    <CommandLine>cmd.exe /c reg add "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f</CommandLine>
                    <Description>Enable Remote Desktop</Description>
                </SynchronousCommand>
                
                <!-- Set network to Private -->
                <SynchronousCommand wcm:action="add">
                    <Order>3</Order>
                    <CommandLine>powershell.exe -Command "Set-NetConnectionProfile -NetworkCategory Private"</CommandLine>
                    <Description>Set network profile to Private</Description>
                </SynchronousCommand>
                
                <!-- Create initialization log -->
                <SynchronousCommand wcm:action="add">
                    <Order>4</Order>
                    <CommandLine>cmd.exe /c echo Glassdome Windows initialization completed at %date% %time% > C:\\glassdome-init.log</CommandLine>
                    <Description>Create init log</Description>
                </SynchronousCommand>{static_ip_config}{rdp_config}
            </FirstLogonCommands>
        </component>
    </settings>
</unattend>"""
    
    return xml


def create_autounattend_iso(autounattend_xml: str, output_path: Path) -> Path:
    """
    Create an ISO file containing autounattend.xml
    
    Args:
        autounattend_xml: The XML content
        output_path: Path where ISO should be created
    
    Returns:
        Path to created ISO file
    """
    import tempfile
    import subprocess
    import shutil
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write autounattend.xml
        xml_file = temp_path / "autounattend.xml"
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(autounattend_xml)
        
        # Create ISO using genisoimage
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            'genisoimage',
            '-o', str(output_path),
            '-J',  # Joliet extensions
            '-r',  # Rock Ridge extensions
            '-V', 'AUTOUNATTEND',  # Volume label
            str(temp_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create ISO: {result.stderr}")
    
    return output_path


def create_autounattend_floppy(autounattend_xml: str, output_path: Path) -> Path:
    """
    Create a floppy image containing autounattend.xml
    Windows Setup RELIABLY checks A:\ for autounattend.xml
    
    Args:
        autounattend_xml: The XML content
        output_path: Path where floppy image should be created (.img)
    
    Returns:
        Path to created floppy image
    """
    import tempfile
    import subprocess
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Write autounattend.xml
        xml_file = temp_path / "autounattend.xml"
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(autounattend_xml)
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create 1.44MB floppy image
        subprocess.run([
            'dd', 'if=/dev/zero', f'of={output_path}',
            'bs=1024', 'count=1440'
        ], check=True, capture_output=True)
        
        # Format as FAT12 (floppy filesystem)
        subprocess.run([
            'mkfs.vfat', '-F', '12', '-n', 'AUTOUNATT',  # Max 11 chars for FAT label
            str(output_path)
        ], check=True, capture_output=True)
        
        # Mount and copy file
        mount_point = temp_path / "mount"
        mount_point.mkdir()
        
        try:
            subprocess.run([
                'sudo', 'mount', '-o', 'loop',
                str(output_path), str(mount_point)
            ], check=True, capture_output=True)
            
            # Copy autounattend.xml
            subprocess.run([
                'sudo', 'cp', str(xml_file),
                str(mount_point / 'autounattend.xml')
            ], check=True, capture_output=True)
            
        finally:
            # Unmount
            subprocess.run([
                'sudo', 'umount', str(mount_point)
            ], check=True, capture_output=True)
    
    return output_path


if __name__ == "__main__":
    # Test generation
    config = {
        "hostname": "test-win-server",
        "admin_password": "Glassdome123!",
        "windows_version": "server2022",
        "enable_rdp": True,
        "virtio_drivers": True
    }
    
    xml = generate_autounattend_xml(config)
    print(xml)

