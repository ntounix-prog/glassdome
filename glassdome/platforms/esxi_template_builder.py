"""
ESXi Cloud-Init Template Builder

This module provides a robust workflow for creating ESXi-compatible
Ubuntu cloud-init templates. It handles all the quirks of ESXi standalone
(no vCenter) deployment.

PROVEN WORKING: 2024-11-20
- VM: glassdome-ubuntu-test @ 192.168.3.207
- Credentials: ubuntu / glassdome123
- Status: SSH working, cloud-init complete
"""

import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import urllib3

from glassdome.platforms.esxi_client import ESXiClient
from pyVmomi import vim

urllib3.disable_warnings()
logger = logging.getLogger(__name__)


class ESXiTemplateBuilder:
    """
    Builds ESXi-compatible Ubuntu templates with cloud-init support.
    
    Workflow:
    1. Download Ubuntu cloud image
    2. Convert to monolithicFlat (qemu-img)
    3. Create NoCloud seed.iso (genisoimage)
    4. Upload to ESXi
    5. Convert to ESXi-native (vmkfstools via SSH)
    6. Template ready for cloning
    """
    
    def __init__(
        self,
        esxi_host: str,
        esxi_user: str,
        esxi_password: str,
        datastore: str,
        network: str = "VM Network",
        verify_ssl: bool = False
    ):
        self.esxi_host = esxi_host
        self.esxi_user = esxi_user
        self.esxi_password = esxi_password
        self.datastore = datastore
        self.network = network
        self.verify_ssl = verify_ssl
        
        self.client = ESXiClient(
            host=esxi_host,
            user=esxi_user,
            password=esxi_password,
            datastore_name=datastore,
            network_name=network,
            verify_ssl=verify_ssl
        )
        
        self.working_dir = Path(tempfile.gettempdir()) / "glassdome-esxi-template"
        self.working_dir.mkdir(exist_ok=True)
    
    def download_cloud_image(self, ubuntu_version: str = "22.04") -> Path:
        """
        Download Ubuntu cloud image.
        
        Args:
            ubuntu_version: Ubuntu version (22.04, 24.04, etc.)
            
        Returns:
            Path to downloaded VMDK
        """
        logger.info(f"Downloading Ubuntu {ubuntu_version} cloud image...")
        
        # Use jammy (22.04) as default
        codename = "jammy" if ubuntu_version == "22.04" else "noble"
        url = f"https://cloud-images.ubuntu.com/{codename}/current/{codename}-server-cloudimg-amd64.vmdk"
        
        output_file = self.working_dir / f"ubuntu-{ubuntu_version}-cloud.vmdk"
        
        if output_file.exists():
            logger.info(f"Cloud image already exists: {output_file}")
            return output_file
        
        response = requests.get(url, stream=True, timeout=300)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total_size > 0:
                    percent = (downloaded / total_size) * 100
                    if downloaded % (10 * 1024 * 1024) == 0:  # Log every 10MB
                        logger.info(f"Download progress: {percent:.1f}%")
        
        logger.info(f"Downloaded: {output_file} ({downloaded / 1024 / 1024:.1f} MB)")
        return output_file
    
    def convert_vmdk(self, source_vmdk: Path) -> Path:
        """
        Convert cloud VMDK to monolithicFlat format for ESXi.
        
        Args:
            source_vmdk: Path to source VMDK
            
        Returns:
            Path to converted VMDK descriptor
        """
        logger.info("Converting VMDK to ESXi-compatible format...")
        
        output_vmdk = self.working_dir / "ubuntu-flat.vmdk"
        
        cmd = [
            "qemu-img", "convert",
            "-f", "vmdk",
            "-O", "vmdk",
            "-o", "adapter_type=lsilogic,subformat=monolithicFlat",
            str(source_vmdk),
            str(output_vmdk)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            raise RuntimeError(f"VMDK conversion failed: {result.stderr}")
        
        logger.info(f"Converted VMDK: {output_vmdk}")
        
        # Verify both descriptor and flat file exist
        flat_file = output_vmdk.parent / f"{output_vmdk.stem}-flat.vmdk"
        if not output_vmdk.exists() or not flat_file.exists():
            raise FileNotFoundError(f"Conversion incomplete. Expected: {output_vmdk} and {flat_file}")
        
        return output_vmdk
    
    def create_cloud_init_iso(
        self,
        hostname: str = "glassdome-template",
        username: str = "ubuntu",
        password: str = "glassdome123",
        ssh_authorized_keys: Optional[list] = None
    ) -> Path:
        """
        Create NoCloud cloud-init ISO.
        
        Args:
            hostname: VM hostname
            username: Default user
            password: Default password (plain text)
            ssh_authorized_keys: Optional list of SSH public keys
            
        Returns:
            Path to seed.iso
        """
        logger.info("Creating cloud-init seed.iso...")
        
        seed_dir = self.working_dir / "seed"
        seed_dir.mkdir(exist_ok=True)
        
        # Create user-data
        user_data = f"""#cloud-config
hostname: {hostname}
fqdn: {hostname}.local
manage_etc_hosts: true

users:
  - name: {username}
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    home: /home/{username}
    shell: /bin/bash
    lock_passwd: false
"""
        
        # Add SSH keys if provided
        if ssh_authorized_keys:
            user_data += f"""    ssh_authorized_keys:
"""
            for key in ssh_authorized_keys:
                user_data += f"""      - {key}
"""
        
        # Add password using chpasswd (more reliable than hashed passwords)
        user_data += f"""
chpasswd:
  list: |
    {username}:{password}
  expire: false

ssh_pwauth: true
disable_root: false

packages:
  - qemu-guest-agent
  - open-vm-tools
  - cloud-init

runcmd:
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent
  - systemctl enable open-vm-tools
  - systemctl start open-vm-tools
  - echo "Cloud-init completed at $(date)" > /var/log/glassdome-init.log

# Optional: reboot after first config
# power_state:
#   mode: reboot
#   condition: true
"""
        
        # Create meta-data
        meta_data = f"""instance-id: {hostname}-001
local-hostname: {hostname}
"""
        
        # Write files
        (seed_dir / "user-data").write_text(user_data)
        (seed_dir / "meta-data").write_text(meta_data)
        
        # Create ISO
        iso_file = self.working_dir / "seed.iso"
        
        cmd = [
            "genisoimage",
            "-output", str(iso_file),
            "-volid", "cidata",
            "-joliet",
            "-rock",
            str(seed_dir)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            raise RuntimeError(f"ISO creation failed: {result.stderr}")
        
        logger.info(f"Created seed.iso: {iso_file}")
        return iso_file
    
    def upload_to_esxi(
        self,
        local_file: Path,
        remote_path: str
    ) -> bool:
        """
        Upload file to ESXi datastore via HTTP.
        
        Args:
            local_file: Local file path
            remote_path: Remote path (e.g., "templates/ubuntu/file.vmdk")
            
        Returns:
            True if successful
        """
        logger.info(f"Uploading {local_file.name} to ESXi...")
        
        url = f"https://{self.esxi_host}/folder/{remote_path}?dcPath=ha-datacenter&dsName={self.datastore}"
        
        with open(local_file, 'rb') as f:
            response = requests.put(
                url,
                data=f,
                auth=(self.esxi_user, self.esxi_password),
                verify=self.verify_ssl,
                headers={'Content-Type': 'application/octet-stream'},
                timeout=600
            )
        
        if response.status_code not in [200, 201]:
            raise RuntimeError(f"Upload failed ({response.status_code}): {response.text[:200]}")
        
        logger.info(f"Uploaded: {remote_path}")
        return True
    
    def convert_to_esxi_native(
        self,
        remote_vmdk_path: str,
        output_vmdk_path: str
    ) -> bool:
        """
        Convert VMDK to ESXi-native format using vmkfstools via SSH.
        
        Args:
            remote_vmdk_path: Source VMDK path on ESXi (without datastore brackets)
            output_vmdk_path: Output VMDK path on ESXi (without datastore brackets)
            
        Returns:
            True if successful
        """
        logger.info("Converting to ESXi-native format with vmkfstools...")
        
        # Check if sshpass is available
        sshpass_check = subprocess.run(
            ["which", "sshpass"],
            capture_output=True,
            timeout=5
        )
        
        if sshpass_check.returncode != 0:
            raise RuntimeError("sshpass not installed. Run: sudo apt-get install sshpass")
        
        # Build vmkfstools command
        vmkfs_cmd = f"vmkfstools -i /vmfs/volumes/{self.datastore}/{remote_vmdk_path} /vmfs/volumes/{self.datastore}/{output_vmdk_path} -d thin"
        
        # Execute via SSH
        ssh_cmd = [
            "sshpass", "-p", self.esxi_password,
            "ssh",
            "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null",
            f"{self.esxi_user}@{self.esxi_host}",
            vmkfs_cmd
        ]
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"vmkfstools failed: {result.stderr}")
        
        # Check for success message
        if "Clone: 100% done" not in result.stdout:
            logger.warning(f"vmkfstools output: {result.stdout}")
        
        logger.info("ESXi-native VMDK created")
        return True
    
    def build_template(
        self,
        template_name: str = "ubuntu-2204-glassdome",
        ubuntu_version: str = "22.04",
        username: str = "ubuntu",
        password: str = "glassdome123",
        ssh_keys: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Complete workflow: Build ESXi template from Ubuntu cloud image.
        
        Args:
            template_name: Name for the template folder on ESXi
            ubuntu_version: Ubuntu version to use
            username: Default username
            password: Default password
            ssh_keys: Optional SSH public keys
            
        Returns:
            Dict with template information
        """
        logger.info(f"Building ESXi template: {template_name}")
        
        try:
            # Step 1: Download cloud image
            cloud_vmdk = self.download_cloud_image(ubuntu_version)
            
            # Step 2: Convert to monolithicFlat
            flat_vmdk = self.convert_vmdk(cloud_vmdk)
            flat_data = flat_vmdk.parent / f"{flat_vmdk.stem}-flat.vmdk"
            
            # Step 3: Create cloud-init ISO
            seed_iso = self.create_cloud_init_iso(
                hostname=template_name,
                username=username,
                password=password,
                ssh_authorized_keys=ssh_keys
            )
            
            # Step 4: Upload to ESXi
            self.upload_to_esxi(flat_vmdk, f"{template_name}/ubuntu-flat.vmdk")
            self.upload_to_esxi(flat_data, f"{template_name}/ubuntu-flat-flat.vmdk")
            self.upload_to_esxi(seed_iso, f"{template_name}/seed.iso")
            
            # Step 5: Convert to ESXi-native
            self.convert_to_esxi_native(
                f"{template_name}/ubuntu-flat.vmdk",
                f"{template_name}/{template_name}.vmdk"
            )
            
            result = {
                "template_name": template_name,
                "vmdk_path": f"[{self.datastore}] {template_name}/{template_name}.vmdk",
                "iso_path": f"[{self.datastore}] {template_name}/seed.iso",
                "username": username,
                "password": password,
                "ubuntu_version": ubuntu_version,
                "status": "ready"
            }
            
            logger.info(f"✅ Template ready: {template_name}")
            return result
            
        except Exception as e:
            logger.error(f"Template build failed: {e}")
            raise
    
    def create_vm_from_template(
        self,
        vm_name: str,
        template_info: Dict[str, Any],
        cores: int = 2,
        memory_mb: int = 2048
    ) -> Dict[str, Any]:
        """
        Create a VM from the template.
        
        Args:
            vm_name: Name for the new VM
            template_info: Template info from build_template()
            cores: Number of CPU cores
            memory_mb: Memory in MB
            
        Returns:
            Dict with VM information
        """
        logger.info(f"Creating VM from template: {vm_name}")
        
        # Create VM shell
        vm_config = vim.vm.ConfigSpec(
            name=vm_name,
            memoryMB=memory_mb,
            numCPUs=cores,
            guestId='ubuntu64Guest',
            files=vim.vm.FileInfo(
                vmPathName=f"[{self.datastore}] {vm_name}"
            )
        )
        
        # Add controllers
        scsi_controller = vim.vm.device.VirtualDeviceSpec()
        scsi_controller.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        scsi_controller.device = vim.vm.device.ParaVirtualSCSIController()
        scsi_controller.device.key = 1000
        scsi_controller.device.sharedBus = vim.vm.device.VirtualSCSIController.Sharing.noSharing
        scsi_controller.device.busNumber = 0
        
        ide_controller = vim.vm.device.VirtualDeviceSpec()
        ide_controller.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        ide_controller.device = vim.vm.device.VirtualIDEController()
        ide_controller.device.key = 200
        ide_controller.device.busNumber = 0
        
        # Add network
        network = None
        for net in self.client.compute_resource.network:
            if net.name == self.network:
                network = net
                break
        
        device_changes = [scsi_controller, ide_controller]
        
        if network:
            network_spec = vim.vm.device.VirtualDeviceSpec()
            network_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
            network_spec.device = vim.vm.device.VirtualVmxnet3()
            network_spec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
            network_spec.device.backing.network = network
            network_spec.device.backing.deviceName = network.name
            network_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            network_spec.device.connectable.startConnected = True
            network_spec.device.connectable.allowGuestControl = True
            device_changes.append(network_spec)
        
        vm_config.deviceChange = device_changes
        
        # Create VM
        task = self.client.datacenter.vmFolder.CreateVM_Task(
            config=vm_config,
            pool=self.client.resource_pool
        )
        self.client._wait_for_task(task)
        
        # Get VM
        vm = self.client._get_vm_by_name(vm_name)
        
        # Attach VMDK
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        disk_spec.device.backing.fileName = template_info["vmdk_path"]
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.controllerKey = 1000
        disk_spec.device.unitNumber = 0
        
        reconfig_spec = vim.vm.ConfigSpec()
        reconfig_spec.deviceChange = [disk_spec]
        task = vm.ReconfigVM_Task(spec=reconfig_spec)
        self.client._wait_for_task(task)
        
        # Attach ISO
        cdrom_spec = vim.vm.device.VirtualDeviceSpec()
        cdrom_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        cdrom_spec.device = vim.vm.device.VirtualCdrom()
        cdrom_spec.device.key = 3000
        cdrom_spec.device.controllerKey = 200
        cdrom_spec.device.unitNumber = 0
        cdrom_spec.device.backing = vim.vm.device.VirtualCdrom.IsoBackingInfo()
        cdrom_spec.device.backing.fileName = template_info["iso_path"]
        cdrom_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        cdrom_spec.device.connectable.startConnected = True
        cdrom_spec.device.connectable.allowGuestControl = False
        
        reconfig_spec = vim.vm.ConfigSpec()
        reconfig_spec.deviceChange = [cdrom_spec]
        task = vm.ReconfigVM_Task(spec=reconfig_spec)
        self.client._wait_for_task(task)
        
        # Power on
        task = vm.PowerOn()
        self.client._wait_for_task(task)
        
        logger.info(f"✅ VM created and powered on: {vm_name}")
        
        return {
            "vm_name": vm_name,
            "status": "poweredOn",
            "credentials": {
                "username": template_info["username"],
                "password": template_info["password"]
            }
        }

