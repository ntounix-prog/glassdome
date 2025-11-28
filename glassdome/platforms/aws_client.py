"""
Platform client for Aws

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
import boto3
import asyncio
import time
from typing import Dict, Any, List, Optional
import logging

from glassdome.platforms.base import PlatformClient, VMStatus

logger = logging.getLogger(__name__)


# Ubuntu AMI mappings (arm64 for t4g, amd64 for t2/t3)
UBUNTU_AMIS = {
    # Ubuntu 22.04 LTS (Jammy) - ARM64 (for t4g instances)
    "22.04-arm64": {
        "us-east-1": "ami-0c7217cdde317cfec",  # Ubuntu 22.04 ARM
        "us-east-2": "ami-0ea18256de20ecdfc",
        "us-west-1": "ami-0ce2cb35386fc22e9",
        "us-west-2": "ami-0f1a5f5ada0e7da53",
        "eu-west-1": "ami-0905a3c97561e0b69",
        "eu-central-1": "ami-065deacbcaac64cf2",
        "ap-southeast-1": "ami-0dc2d3e4c0f9ebd18",
        "ap-southeast-2": "ami-0310483fb2b488153",
        "ap-northeast-1": "ami-0bba69335379e17f8",
    },
    # Ubuntu 22.04 LTS (Jammy) - AMD64 (for t2/t3 instances)
    "22.04-amd64": {
        "us-east-1": "ami-0c7217cdde317cfec",
        "us-east-2": "ami-0ea18256de20ecdfc",
        "us-west-1": "ami-0ce2cb35386fc22e9",
        "us-west-2": "ami-0f1a5f5ada0e7da53",
        "eu-west-1": "ami-0905a3c97561e0b69",
        "eu-central-1": "ami-065deacbcaac64cf2",
        "ap-southeast-1": "ami-0dc2d3e4c0f9ebd18",
        "ap-southeast-2": "ami-0310483fb2b488153",
        "ap-northeast-1": "ami-0bba69335379e17f8",
    }
}


class AWSClient(PlatformClient):
    """
    AWS EC2 Platform Client
    
    Implements the PlatformClient interface for AWS deployments.
    Supports dynamic region selection, auto AMI lookup, and cloud-init.
    """
    
    def __init__(self, access_key_id: str, secret_access_key: str,
                 region: str = "us-east-1", default_vpc: bool = True):
        """
        Initialize AWS client
        
        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            region: AWS region (can deploy to any region globally)
            default_vpc: Use default VPC (True) or create custom VPC (False)
        """
        self.region = region
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.default_vpc = default_vpc
        
        # Initialize EC2 client
        self.ec2_client = boto3.client(
            'ec2',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        
        # Initialize EC2 resource (higher-level interface)
        self.ec2_resource = boto3.resource(
            'ec2',
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region
        )
        
        logger.info(f"AWS client initialized for region {region}")
    
    # =========================================================================
    # CORE VM OPERATIONS (PlatformClient Interface)
    # =========================================================================
    
    async def create_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create and start an EC2 instance (Linux or Windows)
        
        Args:
            config: VM configuration with keys:
                - name: VM name (required)
                - os_type: "linux" or "windows" (default: "linux")
                - os_version: Ubuntu version (default: "22.04") or windows_version
                - windows_version: "server2022" or "win11" (for Windows VMs)
                - cores: CPU cores (maps to instance type)
                - memory: RAM in MB (maps to instance type)
                - ssh_user: SSH username (default: "ubuntu")
                - instance_type: Override instance type (optional)
                - packages: List of packages to install
                - users: List of user accounts to create
        
        Returns:
            Dict with vm_id, ip_address, platform, status, ansible_connection
        """
        name = config.get("name", f"glassdome-vm-{int(time.time())}")
        os_type = config.get("os_type", "linux")
        os_version = config.get("os_version", "22.04")
        instance_type = config.get("instance_type") or self._map_instance_type(config, os_type)
        
        logger.info(f"Creating AWS EC2 instance: {name} ({os_type}, {instance_type}) in {self.region}")
        
        # 1. Get AMI (Linux or Windows)
        if os_type == "windows":
            windows_version = config.get("windows_version", "server2022")
            ami_id = await self._get_windows_ami(windows_version)
        else:
            ami_id = await self._get_ubuntu_ami(os_version, instance_type)
        
        # 2. Get/Create VPC and Subnet
        vpc_id, subnet_id = await self._get_vpc_and_subnet()
        
        # 3. Get/Create Security Group
        sg_id = await self._get_or_create_security_group(vpc_id, name, os_type)
        
        # 4. Build user-data (cloud-init for Linux, EC2Launch for Windows)
        if os_type == "windows":
            user_data = self._build_windows_userdata(config)
        else:
            user_data = self._build_cloud_init(config)
        
        # 5. Launch instance
        try:
            # Don't specify subnet - let AWS choose AZ that supports the instance type
            response = self.ec2_client.run_instances(
                ImageId=ami_id,
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                UserData=user_data,
                SecurityGroupIds=[sg_id],
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': name},
                        {'Key': 'Project', 'Value': 'glassdome'},
                        {'Key': 'ManagedBy', 'Value': 'glassdome-platform'}
                    ]
                }]
            )
            
            instance = response['Instances'][0]
            instance_id = instance['InstanceId']
            
            logger.info(f"Instance {instance_id} launched, waiting for running state...")
            
            # 6. Wait for instance to be running
            waiter = self.ec2_client.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            
            # 7. Get IP address
            ip_address = await self.get_vm_ip(instance_id, timeout=120)
            
            logger.info(f"✅ AWS instance {instance_id} created @ {ip_address}")
            
            return {
                "vm_id": instance_id,
                "ip_address": ip_address,
                "platform": "aws",
                "status": VMStatus.RUNNING.value,
                "ansible_connection": {
                    "host": ip_address,
                    "user": config.get("ssh_user", "ubuntu"),
                    "ssh_key_path": config.get("ssh_key_path"),
                    "port": 22
                },
                "platform_specific": {
                    "region": self.region,
                    "instance_type": instance_type,
                    "ami_id": ami_id,
                    "vpc_id": vpc_id,
                    "subnet_id": subnet_id,
                    "security_group_id": sg_id
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create instance: {e}")
            raise
    
    async def start_vm(self, vm_id: str) -> bool:
        """Start a stopped EC2 instance"""
        try:
            self.ec2_client.start_instances(InstanceIds=[vm_id])
            logger.info(f"Started instance {vm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start instance {vm_id}: {e}")
            return False
    
    async def stop_vm(self, vm_id: str, force: bool = False) -> bool:
        """Stop a running EC2 instance"""
        try:
            if force:
                self.ec2_client.stop_instances(InstanceIds=[vm_id], Force=True)
            else:
                self.ec2_client.stop_instances(InstanceIds=[vm_id])
            logger.info(f"Stopped instance {vm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop instance {vm_id}: {e}")
            return False
    
    async def delete_vm(self, vm_id: str) -> bool:
        """Terminate (delete) an EC2 instance"""
        try:
            self.ec2_client.terminate_instances(InstanceIds=[vm_id])
            logger.info(f"Terminated instance {vm_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to terminate instance {vm_id}: {e}")
            return False
    
    async def get_vm_status(self, vm_id: str) -> VMStatus:
        """Get EC2 instance status"""
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[vm_id])
            state = response['Reservations'][0]['Instances'][0]['State']['Name']
            return self._standardize_vm_status(state)
        except Exception as e:
            logger.error(f"Failed to get instance status {vm_id}: {e}")
            return VMStatus.UNKNOWN
    
    async def get_vm_ip(self, vm_id: str, timeout: int = 120) -> Optional[str]:
        """
        Get EC2 instance public IP address
        
        Waits up to timeout seconds for IP to be assigned
        """
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                response = self.ec2_client.describe_instances(InstanceIds=[vm_id])
                instance = response['Reservations'][0]['Instances'][0]
                
                # Try public IP first, fallback to private
                public_ip = instance.get('PublicIpAddress')
                if public_ip:
                    return public_ip
                
                private_ip = instance.get('PrivateIpAddress')
                if private_ip:
                    logger.warning(f"No public IP for {vm_id}, using private IP: {private_ip}")
                    return private_ip
                
                # Wait and retry
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error getting IP for {vm_id}: {e}")
                await asyncio.sleep(2)
        
        logger.warning(f"Timeout waiting for IP address for {vm_id}")
        return None
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _map_instance_type(self, config: Dict[str, Any], os_type: str = "linux") -> str:
        """
        Map cores/memory to AWS instance type
        
        For Linux: Use t4g (ARM) instances (cheapest!)
        For Windows: Use t3 (x86) instances (Windows needs more resources)
        """
        cores = config.get("cores", 1)
        memory_mb = config.get("memory", 4096 if os_type == "windows" else 512)
        
        if os_type == "windows":
            # Windows instances (x86-based, need more resources)
            # Minimum for Windows: 2 cores, 4GB RAM
            if cores <= 2 and memory_mb <= 4096:
                return "t3.medium"  # 2 vCPU, 4 GB RAM
            elif cores <= 2 and memory_mb <= 8192:
                return "t3.large"  # 2 vCPU, 8 GB RAM
            elif cores <= 4:
                return "t3.xlarge"  # 4 vCPU, 16 GB RAM
            else:
                return "t3.2xlarge"  # 8 vCPU, 32 GB RAM
        else:
            # Linux instances (ARM-based Graviton2) - cheapest!
            if cores == 1 and memory_mb <= 512:
                return "t4g.nano"  # $0.0042/hour
            elif cores == 1 and memory_mb <= 1024:
                return "t4g.micro"  # $0.0084/hour
            elif cores == 1 and memory_mb <= 2048:
                return "t4g.small"  # $0.0168/hour
            elif cores == 2:
                return "t4g.medium"  # $0.0336/hour
            elif cores == 4:
                return "t4g.large"  # $0.0672/hour
        
        # Default
        return "t4g.nano" if os_type == "linux" else "t3.medium"
    
    async def _get_ubuntu_ami(self, version: str, instance_type: str) -> str:
        """
        Get Ubuntu AMI ID for the current region
        
        Args:
            version: Ubuntu version (e.g., "22.04")
            instance_type: Instance type to determine architecture
        
        Returns:
            AMI ID
        """
        # Determine architecture from instance type
        arch = "arm64" if instance_type.startswith("t4g") else "amd64"
        
        # Always lookup latest AMI (ensures correct architecture)
        logger.info(f"Looking up latest Ubuntu {version} AMI ({arch}) for {self.region}...")
        try:
            # Canonical's owner ID: 099720109477
            # Fix the name pattern for jammy
            if arch == "arm64":
                name_pattern = f'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-arm64-server-*'
            else:
                name_pattern = f'ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*'
            
            filters = [
                {'Name': 'owner-id', 'Values': ['099720109477']},
                {'Name': 'name', 'Values': [name_pattern]},
                {'Name': 'state', 'Values': ['available']},
                {'Name': 'architecture', 'Values': ['arm64' if arch == 'arm64' else 'x86_64']}
            ]
            
            response = self.ec2_client.describe_images(Filters=filters)
            
            if not response['Images']:
                logger.error(f"No images found. Filters: {filters}")
                raise ValueError(f"No Ubuntu {version} AMI found for {arch} in {self.region}")
            
            # Sort by creation date, get latest
            images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
            ami_id = images[0]['ImageId']
            ami_name = images[0]['Name']
            
            logger.info(f"✅ Found AMI {ami_id} ({ami_name})")
            return ami_id
            
        except Exception as e:
            logger.error(f"Failed to lookup AMI: {e}")
            raise
    
    async def _get_windows_ami(self, version: str) -> str:
        """
        Get Windows AMI ID for the current region
        
        Args:
            version: Windows version ("server2022" or "win11")
        
        Returns:
            AMI ID
        """
        logger.info(f"Looking up Windows {version} AMI for {self.region}...")
        
        try:
            # Amazon's Windows AMIs owner ID: 801119661308
            if version == "server2022":
                name_pattern = 'Windows_Server-2022-English-Full-Base-*'
            elif version == "win11":
                name_pattern = 'Windows_Server-2022-English-Core-Base-*'  # Win11 not in AWS, use Server Core
            else:
                raise ValueError(f"Unknown Windows version: {version}")
            
            filters = [
                {'Name': 'owner-id', 'Values': ['801119661308']},  # Amazon
                {'Name': 'name', 'Values': [name_pattern]},
                {'Name': 'state', 'Values': ['available']},
                {'Name': 'architecture', 'Values': ['x86_64']}
            ]
            
            response = self.ec2_client.describe_images(Filters=filters)
            
            if not response['Images']:
                logger.error(f"No Windows images found. Filters: {filters}")
                raise ValueError(f"No Windows {version} AMI found in {self.region}")
            
            # Sort by creation date, get latest
            images = sorted(response['Images'], key=lambda x: x['CreationDate'], reverse=True)
            ami_id = images[0]['ImageId']
            ami_name = images[0]['Name']
            
            logger.info(f"✅ Found Windows AMI {ami_id} ({ami_name})")
            return ami_id
            
        except Exception as e:
            logger.error(f"Failed to lookup Windows AMI: {e}")
            raise
    
    async def _get_vpc_and_subnet(self) -> tuple:
        """
        Get VPC and subnet for deployment
        
        Returns:
            (vpc_id, subnet_id)
        """
        if self.default_vpc:
            # Use default VPC
            try:
                vpcs = self.ec2_client.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
                if not vpcs['Vpcs']:
                    raise ValueError("No default VPC found")
                
                vpc_id = vpcs['Vpcs'][0]['VpcId']
                
                # Get first available subnet
                subnets = self.ec2_client.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])
                if not subnets['Subnets']:
                    raise ValueError(f"No subnets found in VPC {vpc_id}")
                
                subnet_id = subnets['Subnets'][0]['SubnetId']
                
                logger.info(f"Using default VPC {vpc_id}, subnet {subnet_id}")
                return (vpc_id, subnet_id)
                
            except Exception as e:
                logger.error(f"Failed to get default VPC: {e}")
                raise
        else:
            # TODO: Create custom VPC (Phase 2)
            raise NotImplementedError("Custom VPC creation not yet implemented")
    
    async def _get_or_create_security_group(self, vpc_id: str, vm_name: str, os_type: str = "linux") -> str:
        """
        Get existing or create new security group for Glassdome
        
        Args:
            vpc_id: VPC ID
            vm_name: VM name (for tagging)
            os_type: "linux" or "windows" (adds RDP for Windows)
        
        Returns:
            Security group ID
        """
        sg_name = f"glassdome-{self.region}"
        sg_description = "Glassdome cyber range security group - SSH/RDP access"
        
        try:
            # Check if security group already exists
            response = self.ec2_client.describe_security_groups(
                Filters=[
                    {'Name': 'group-name', 'Values': [sg_name]},
                    {'Name': 'vpc-id', 'Values': [vpc_id]}
                ]
            )
            
            if response['SecurityGroups']:
                sg_id = response['SecurityGroups'][0]['GroupId']
                logger.info(f"Using existing security group {sg_id}")
                
                # Ensure Windows RDP rule exists if os_type is windows
                if os_type == "windows":
                    await self._ensure_rdp_rule(sg_id)
                
                return sg_id
            
            # Create new security group
            response = self.ec2_client.create_security_group(
                GroupName=sg_name,
                Description=sg_description,
                VpcId=vpc_id,
                TagSpecifications=[{
                    'ResourceType': 'security-group',
                    'Tags': [
                        {'Key': 'Name', 'Value': sg_name},
                        {'Key': 'Project', 'Value': 'glassdome'},
                        {'Key': 'ManagedBy', 'Value': 'glassdome-platform'}
                    ]
                }]
            )
            
            sg_id = response['GroupId']
            logger.info(f"Created security group {sg_id}")
            
            # Add SSH ingress rule (always)
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'SSH access'}]
                }]
            )
            logger.info(f"Added SSH rule to security group {sg_id}")
            
            # Add RDP ingress rule for Windows
            if os_type == "windows":
                await self._ensure_rdp_rule(sg_id)
            
            return sg_id
            
        except Exception as e:
            logger.error(f"Failed to get/create security group: {e}")
            raise
    
    async def _ensure_rdp_rule(self, sg_id: str):
        """Ensure RDP port 3389 is open in security group"""
        try:
            # Check if RDP rule already exists
            response = self.ec2_client.describe_security_groups(GroupIds=[sg_id])
            sg = response['SecurityGroups'][0]
            
            for rule in sg['IpPermissions']:
                if rule.get('FromPort') == 3389 and rule.get('ToPort') == 3389:
                    logger.info(f"RDP rule already exists in security group {sg_id}")
                    return
            
            # Add RDP rule
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_id,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 3389,
                    'ToPort': 3389,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'RDP access'}]
                }]
            )
            logger.info(f"Added RDP rule to security group {sg_id}")
            
        except Exception as e:
            logger.warning(f"Failed to ensure RDP rule: {e}")
    
    def _build_cloud_init(self, config: Dict[str, Any]) -> str:
        """
        Build cloud-init user-data script
        
        Args:
            config: VM configuration
        
        Returns:
            Cloud-init user-data string
        """
        name = config.get("name", "glassdome-vm")
        ssh_user = config.get("ssh_user", "ubuntu")
        password = config.get("password", "glassdome123")
        
        user_data = f"""#cloud-config
hostname: {name}
fqdn: {name}.local
manage_etc_hosts: true

users:
  - name: {ssh_user}
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: users, admin
    home: /home/{ssh_user}
    shell: /bin/bash
    lock_passwd: false

chpasswd:
  list: |
    {ssh_user}:{password}
  expire: false

ssh_pwauth: true
disable_root: false
"""
        
        # Add packages if specified
        if config.get('packages'):
            user_data += "\npackages:\n"
            for pkg in config['packages']:
                user_data += f"  - {pkg}\n"
        
        # Add runcmd if specified
        user_data += """
runcmd:
  - echo "Cloud-init completed at $(date)" > /var/log/glassdome-init.log
"""
        
        return user_data
    
    def _build_windows_userdata(self, config: Dict[str, Any]) -> str:
        """
        Build Windows EC2Launch user-data script (PowerShell)
        
        Args:
            config: VM configuration
        
        Returns:
            Windows user-data string (PowerShell script)
        """
        name = config.get("name", "glassdome-vm")
        admin_password = config.get("admin_password", "Glassdome123!")
        
        # EC2Launch user data (PowerShell)
        user_data = f"""<powershell>
# Set hostname
Rename-Computer -NewName "{name}" -Force

# Set Administrator password
$Password = ConvertTo-SecureString "{admin_password}" -AsPlainText -Force
Get-LocalUser -Name "Administrator" | Set-LocalUser -Password $Password

# Enable RDP
Set-ItemProperty -Path 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server' -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"

# Disable Windows Firewall (for cyber range testing)
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False

# Create log
$logMessage = "Glassdome Windows initialization completed at $(Get-Date)"
Add-Content -Path "C:\\glassdome-init.log" -Value $logMessage

# Restart to apply hostname change
Restart-Computer -Force
</powershell>
<persist>true</persist>
"""
        
        return user_data
    
    def _standardize_vm_status(self, aws_state: str) -> VMStatus:
        """
        Map AWS instance state to VMStatus
        
        AWS states: pending, running, stopping, stopped, shutting-down, terminated
        """
        state_map = {
            "pending": VMStatus.CREATING,
            "running": VMStatus.RUNNING,
            "stopping": VMStatus.CREATING,  # Transitioning
            "stopped": VMStatus.STOPPED,
            "shutting-down": VMStatus.DELETING,
            "terminated": VMStatus.DELETING
        }
        return state_map.get(aws_state, VMStatus.UNKNOWN)
    
    # =========================================================================
    # PLATFORM INFO
    # =========================================================================
    
    async def test_connection(self) -> bool:
        """Test connection to AWS"""
        try:
            self.ec2_client.describe_regions()
            logger.info("Successfully connected to AWS")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AWS: {str(e)}")
            return False
    
    async def get_platform_info(self) -> Dict[str, Any]:
        """Get AWS platform information"""
        return {
            "platform": "aws",
            "region": self.region,
            "version": "ec2"
        }
    
    def get_platform_name(self) -> str:
        """Get platform name"""
        return "aws"
