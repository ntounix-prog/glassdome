"""
Proxmox API Gateway
Executes commands directly on Proxmox host via SSH

This enables the agentic framework to:
- Create templates automatically
- Configure Proxmox settings
- Manage storage
- Execute maintenance tasks
- Setup infrastructure
"""
import logging
from typing import Dict, Any, Optional, List
from glassdome.core.ssh_client import SSHClient

logger = logging.getLogger(__name__)


class ProxmoxGateway:
    """
    API Gateway for Proxmox Host Operations
    
    Executes commands directly on Proxmox via SSH to:
    - Create VM templates from cloud images
    - Configure storage
    - Manage networks
    - Setup automation
    - Perform maintenance
    """
    
    def __init__(
        self,
        host: str,
        username: str = "root",
        password: Optional[str] = None,
        key_filename: Optional[str] = None
    ):
        """
        Initialize Proxmox Gateway
        
        Args:
            host: Proxmox host address
            username: SSH username (usually root)
            password: SSH password
            key_filename: Path to SSH private key
        """
        self.host = host
        self.ssh = SSHClient(
            host=host,
            username=username,
            password=password,
            key_filename=key_filename
        )
        
    async def connect(self) -> bool:
        """Establish SSH connection to Proxmox"""
        return await self.ssh.connect()
    
    async def create_ubuntu_template(
        self,
        template_id: int = 9000,
        ubuntu_version: str = "22.04",
        node: Optional[str] = None,
        storage: str = "local-lvm"
    ) -> Dict[str, Any]:
        """
        Automatically create Ubuntu cloud-init template
        
        This is the command that we were telling users to run manually!
        Now the agent can do it automatically.
        
        Args:
            template_id: VM ID for template (default: 9000)
            ubuntu_version: Ubuntu version (22.04, 20.04, etc.)
            node: Proxmox node (None = auto-detect)
            storage: Storage location
            
        Returns:
            Result with template details
        """
        logger.info(f"Creating Ubuntu {ubuntu_version} template (ID {template_id})")
        
        # Build template creation script
        script = f"""#!/bin/bash
set -e

echo "🔧 Creating Ubuntu {ubuntu_version} cloud-init template..."

# Change to ISO storage directory
cd /var/lib/vz/template/iso

# Check if image already exists
IMAGE_FILE="ubuntu-{ubuntu_version}-server-cloudimg-amd64.img"
if [ ! -f "$IMAGE_FILE" ]; then
    echo "📥 Downloading Ubuntu {ubuntu_version} cloud image..."
    wget -q https://cloud-images.ubuntu.com/releases/{ubuntu_version}/release/ubuntu-{ubuntu_version}-server-cloudimg-amd64.img
    echo "✅ Download complete"
else
    echo "✅ Image already exists: $IMAGE_FILE"
fi

# Check if template already exists
if qm status {template_id} > /dev/null 2>&1; then
    echo "⚠️  Template {template_id} already exists, destroying..."
    qm destroy {template_id}
fi

echo "🔨 Creating VM {template_id}..."
qm create {template_id} \\
    --name ubuntu-{ubuntu_version.replace('.', '')}-cloudinit-template \\
    --memory 2048 \\
    --cores 2 \\
    --net0 virtio,bridge=vmbr0

echo "💾 Importing disk..."
qm importdisk {template_id} $IMAGE_FILE {storage} > /dev/null

echo "⚙️  Configuring VM..."
qm set {template_id} \\
    --scsihw virtio-scsi-pci \\
    --scsi0 {storage}:vm-{template_id}-disk-0

qm set {template_id} --ide2 {storage}:cloudinit

qm set {template_id} \\
    --boot c \\
    --bootdisk scsi0

qm set {template_id} \\
    --serial0 socket \\
    --vga serial0

qm set {template_id} --agent enabled=1

echo "📦 Converting to template..."
qm template {template_id}

echo "✅ Template {template_id} created successfully!"
qm list | grep {template_id}
"""
        
        # Execute script
        result = await self.ssh.execute_script(script, timeout=600)
        
        if result["success"]:
            logger.info(f"✅ Template {template_id} created successfully")
            return {
                "success": True,
                "template_id": template_id,
                "ubuntu_version": ubuntu_version,
                "name": f"ubuntu-{ubuntu_version.replace('.', '')}-cloudinit-template",
                "storage": storage,
                "output": result["stdout"]
            }
        else:
            logger.error(f"❌ Failed to create template: {result['stderr']}")
            return {
                "success": False,
                "error": result["stderr"],
                "output": result["stdout"]
            }
    
    async def list_templates(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all VM templates
        
        Returns:
            List of templates with details
        """
        result = await self.ssh.execute("qm list | grep template")
        
        if not result["success"]:
            return []
        
        templates = []
        for line in result["stdout"].strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    templates.append({
                        "vmid": int(parts[0]),
                        "name": parts[1] if len(parts) > 1 else "unnamed",
                        "status": parts[2] if len(parts) > 2 else "unknown"
                    })
        
        return templates
    
    async def delete_template(self, template_id: int) -> Dict[str, Any]:
        """
        Delete a VM template
        
        Args:
            template_id: Template VM ID
            
        Returns:
            Result of deletion
        """
        logger.info(f"Deleting template {template_id}")
        result = await self.ssh.execute(f"qm destroy {template_id}")
        
        return {
            "success": result["success"],
            "template_id": template_id,
            "output": result["stdout"],
            "error": result.get("stderr")
        }
    
    async def get_storage_info(self) -> Dict[str, Any]:
        """
        Get storage information
        
        Returns:
            Storage details
        """
        result = await self.ssh.execute("pvesm status")
        
        if result["success"]:
            return {
                "success": True,
                "output": result["stdout"]
            }
        return {
            "success": False,
            "error": result["stderr"]
        }
    
    async def get_node_info(self) -> Dict[str, Any]:
        """
        Get node information
        
        Returns:
            Node details
        """
        result = await self.ssh.execute("pvesh get /nodes")
        
        if result["success"]:
            return {
                "success": True,
                "output": result["stdout"]
            }
        return {
            "success": False,
            "error": result["stderr"]
        }
    
    async def install_package(self, package: str) -> Dict[str, Any]:
        """
        Install package on Proxmox host
        
        Args:
            package: Package name
            
        Returns:
            Installation result
        """
        logger.info(f"Installing package: {package}")
        result = await self.ssh.execute(f"apt-get update && apt-get install -y {package}")
        
        return {
            "success": result["success"],
            "package": package,
            "output": result["stdout"]
        }
    
    async def create_network_bridge(
        self,
        bridge_name: str,
        ports: Optional[str] = None,
        vlan_aware: bool = False
    ) -> Dict[str, Any]:
        """
        Create network bridge
        
        Args:
            bridge_name: Bridge name (e.g., vmbr1)
            ports: Physical ports to attach
            vlan_aware: Enable VLAN awareness
            
        Returns:
            Creation result
        """
        logger.info(f"Creating network bridge: {bridge_name}")
        
        # This would modify /etc/network/interfaces
        # Simplified version here
        script = f"""#!/bin/bash
cat >> /etc/network/interfaces << EOF

auto {bridge_name}
iface {bridge_name} inet manual
    bridge-ports {ports or 'none'}
    bridge-stp off
    bridge-fd 0
    {'bridge-vlan-aware yes' if vlan_aware else ''}
EOF

ifreload -a
"""
        result = await self.ssh.execute_script(script)
        
        return {
            "success": result["success"],
            "bridge": bridge_name,
            "output": result["stdout"]
        }
    
    async def backup_config(self, destination: str) -> Dict[str, Any]:
        """
        Backup Proxmox configuration
        
        Args:
            destination: Backup destination path
            
        Returns:
            Backup result
        """
        logger.info(f"Backing up Proxmox config to {destination}")
        
        script = f"""#!/bin/bash
mkdir -p {destination}
cp -r /etc/pve {destination}/pve_backup_$(date +%Y%m%d_%H%M%S)
tar -czf {destination}/proxmox_backup_$(date +%Y%m%d_%H%M%S).tar.gz {destination}/pve_backup_*
echo "Backup completed: $(ls -lh {destination}/*.tar.gz | tail -1)"
"""
        result = await self.ssh.execute_script(script)
        
        return {
            "success": result["success"],
            "destination": destination,
            "output": result["stdout"]
        }
    
    async def execute_custom(self, command: str) -> Dict[str, Any]:
        """
        Execute custom command on Proxmox host
        
        Args:
            command: Command to execute
            
        Returns:
            Execution result
        """
        logger.warning(f"Executing custom command: {command[:50]}...")
        result = await self.ssh.execute(command)
        
        return {
            "success": result["success"],
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"]
        }
    
    async def disconnect(self):
        """Close SSH connection"""
        await self.ssh.disconnect()

