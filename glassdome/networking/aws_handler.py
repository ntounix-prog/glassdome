"""
AWS Network Handler

Implements platform-agnostic network operations for AWS.
Maps abstract NetworkDefinition to AWS VPC/Subnet/SecurityGroup.

Architecture:
=============
User Browser → Guacamole (public subnet) → Kali (attack subnet) → Lab VMs (private subnets)

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import boto3
from botocore.exceptions import ClientError

from glassdome.networking.orchestrator import PlatformNetworkHandler
from glassdome.networking.models import NetworkDefinition, NetworkType
from glassdome.networking.address_allocator import (
    LabNetworkAllocation,
    SubnetType,
    get_address_allocator
)
from glassdome.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AWSLabInfrastructure:
    """Complete AWS infrastructure for a lab"""
    lab_id: str
    region: str
    vpc_id: str
    internet_gateway_id: Optional[str] = None
    nat_gateway_id: Optional[str] = None
    
    # Subnet IDs
    subnets: Dict[SubnetType, str] = None
    
    # Security Group IDs
    security_groups: Dict[str, str] = None
    
    # Route Table IDs
    route_tables: Dict[str, str] = None
    
    def __post_init__(self):
        if self.subnets is None:
            self.subnets = {}
        if self.security_groups is None:
            self.security_groups = {}
        if self.route_tables is None:
            self.route_tables = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "lab_id": self.lab_id,
            "region": self.region,
            "vpc_id": self.vpc_id,
            "internet_gateway_id": self.internet_gateway_id,
            "nat_gateway_id": self.nat_gateway_id,
            "subnets": {k.value: v for k, v in self.subnets.items()},
            "security_groups": self.security_groups,
            "route_tables": self.route_tables
        }


class AWSNetworkHandler(PlatformNetworkHandler):
    """
    AWS-specific network operations.
    
    AWS Networking Model:
    - VPC = Isolated network space (one per lab)
    - Subnet = Network segment (public, attack, dmz, internal)
    - Security Group = Stateful firewall rules between segments
    - Internet Gateway = Public internet access (for Guacamole)
    - NAT Gateway = Outbound-only internet for private subnets (optional)
    
    Lab Network Flow:
    =================
    Internet → IGW → Public Subnet (Guacamole:443)
                          ↓
                    Attack Subnet (Kali - VNC/RDP from Guac only)
                          ↓
                    Lab Subnets (VMs - all traffic from Kali only)
    """
    
    def __init__(self, region: str = None):
        """
        Initialize AWS Network Handler.
        
        Args:
            region: AWS region (defaults to settings.aws_region or us-east-1)
        """
        self.region = region or getattr(settings, 'aws_region', None) or "us-east-1"
        self._ec2_client = None
        self._ec2_resource = None
        
        # Track created infrastructure per lab
        self._lab_infrastructure: Dict[str, AWSLabInfrastructure] = {}
    
    @property
    def ec2_client(self):
        """Lazy-loaded EC2 client"""
        if self._ec2_client is None:
            self._ec2_client = boto3.client(
                'ec2',
                aws_access_key_id=getattr(settings, 'aws_access_key_id', None),
                aws_secret_access_key=getattr(settings, 'aws_secret_access_key', None),
                region_name=self.region
            )
        return self._ec2_client
    
    @property
    def ec2_resource(self):
        """Lazy-loaded EC2 resource"""
        if self._ec2_resource is None:
            self._ec2_resource = boto3.resource(
                'ec2',
                aws_access_key_id=getattr(settings, 'aws_access_key_id', None),
                aws_secret_access_key=getattr(settings, 'aws_secret_access_key', None),
                region_name=self.region
            )
        return self._ec2_resource
    
    # =========================================================================
    # High-Level Lab Infrastructure Creation
    # =========================================================================
    
    async def create_lab_infrastructure(
        self,
        lab_id: str,
        allocation: LabNetworkAllocation
    ) -> AWSLabInfrastructure:
        """
        Create complete AWS infrastructure for a lab.
        
        This is the main entry point for lab deployment.
        Creates VPC, subnets, security groups, and gateways.
        
        Args:
            lab_id: Unique lab identifier
            allocation: Network allocation from address allocator
        
        Returns:
            AWSLabInfrastructure with all resource IDs
        """
        logger.info(f"Creating AWS infrastructure for lab {lab_id} in {self.region}")
        
        # 1. Create VPC
        vpc_id = await self._create_vpc(lab_id, allocation.vpc_cidr)
        
        infra = AWSLabInfrastructure(
            lab_id=lab_id,
            region=self.region,
            vpc_id=vpc_id
        )
        
        # 2. Create Internet Gateway (for public subnet)
        infra.internet_gateway_id = await self._create_internet_gateway(lab_id, vpc_id)
        
        # 3. Create subnets
        for subnet_type, subnet_alloc in allocation.subnets.items():
            subnet_id = await self._create_subnet(
                lab_id=lab_id,
                vpc_id=vpc_id,
                cidr=subnet_alloc.cidr,
                subnet_type=subnet_type,
                is_public=subnet_alloc.is_public
            )
            infra.subnets[subnet_type] = subnet_id
        
        # 4. Create route tables
        await self._setup_route_tables(infra, allocation)
        
        # 5. Create security groups
        await self._create_security_groups(infra)
        
        # 6. Configure security group rules (Guacamole → Kali → Lab chain)
        await self._configure_security_rules(infra)
        
        self._lab_infrastructure[lab_id] = infra
        
        logger.info(f"✅ Created AWS infrastructure for lab {lab_id}")
        logger.info(f"   VPC: {vpc_id}")
        logger.info(f"   Subnets: {len(infra.subnets)}")
        logger.info(f"   Security Groups: {len(infra.security_groups)}")
        
        return infra
    
    async def delete_lab_infrastructure(self, lab_id: str) -> bool:
        """
        Delete all AWS infrastructure for a lab.
        
        Cleans up in reverse order: instances → NAT → IGW → subnets → SGs → VPC
        
        Args:
            lab_id: Lab to clean up
        
        Returns:
            True if successful
        """
        infra = self._lab_infrastructure.get(lab_id)
        if not infra:
            # Try to find by tag
            logger.warning(f"No tracked infrastructure for lab {lab_id}, searching by tag...")
            return await self._cleanup_lab_by_tag(lab_id)
        
        logger.info(f"Deleting AWS infrastructure for lab {lab_id}")
        
        try:
            # Delete in dependency order
            
            # 1. Terminate instances (done by caller before this)
            
            # 2. Delete NAT Gateway (if exists)
            if infra.nat_gateway_id:
                await self._delete_nat_gateway(infra.nat_gateway_id)
            
            # 3. Delete subnets
            for subnet_type, subnet_id in infra.subnets.items():
                await self._delete_subnet(subnet_id)
            
            # 4. Delete security groups (except default)
            for sg_name, sg_id in infra.security_groups.items():
                await self._delete_security_group(sg_id)
            
            # 5. Detach and delete Internet Gateway
            if infra.internet_gateway_id:
                await self._delete_internet_gateway(
                    infra.internet_gateway_id,
                    infra.vpc_id
                )
            
            # 6. Delete VPC
            await self._delete_vpc(infra.vpc_id)
            
            # Clean up tracking
            del self._lab_infrastructure[lab_id]
            
            logger.info(f"✅ Deleted all AWS infrastructure for lab {lab_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete infrastructure for lab {lab_id}: {e}")
            return False
    
    # =========================================================================
    # VPC Operations
    # =========================================================================
    
    async def _create_vpc(self, lab_id: str, cidr_block: str) -> str:
        """Create VPC for lab"""
        try:
            response = self.ec2_client.create_vpc(
                CidrBlock=cidr_block,
                TagSpecifications=[{
                    'ResourceType': 'vpc',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'glassdome-{lab_id}'},
                        {'Key': 'lab_id', 'Value': lab_id},
                        {'Key': 'ManagedBy', 'Value': 'glassdome'},
                        {'Key': 'Platform', 'Value': 'glassdome-aws'}
                    ]
                }]
            )
            
            vpc_id = response['Vpc']['VpcId']
            
            # Wait for VPC to be available
            waiter = self.ec2_client.get_waiter('vpc_available')
            waiter.wait(VpcIds=[vpc_id])
            
            # Enable DNS hostnames and DNS support
            self.ec2_client.modify_vpc_attribute(
                VpcId=vpc_id,
                EnableDnsHostnames={'Value': True}
            )
            self.ec2_client.modify_vpc_attribute(
                VpcId=vpc_id,
                EnableDnsSupport={'Value': True}
            )
            
            logger.info(f"Created VPC {vpc_id} for lab {lab_id}")
            return vpc_id
            
        except ClientError as e:
            logger.error(f"Failed to create VPC: {e}")
            raise
    
    async def _delete_vpc(self, vpc_id: str) -> None:
        """Delete VPC"""
        try:
            self.ec2_client.delete_vpc(VpcId=vpc_id)
            logger.info(f"Deleted VPC {vpc_id}")
        except ClientError as e:
            logger.error(f"Failed to delete VPC {vpc_id}: {e}")
            raise
    
    # =========================================================================
    # Internet Gateway Operations
    # =========================================================================
    
    async def _create_internet_gateway(self, lab_id: str, vpc_id: str) -> str:
        """Create and attach Internet Gateway"""
        try:
            response = self.ec2_client.create_internet_gateway(
                TagSpecifications=[{
                    'ResourceType': 'internet-gateway',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'glassdome-{lab_id}-igw'},
                        {'Key': 'lab_id', 'Value': lab_id},
                        {'Key': 'ManagedBy', 'Value': 'glassdome'}
                    ]
                }]
            )
            
            igw_id = response['InternetGateway']['InternetGatewayId']
            
            # Attach to VPC
            self.ec2_client.attach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            
            logger.info(f"Created and attached Internet Gateway {igw_id}")
            return igw_id
            
        except ClientError as e:
            logger.error(f"Failed to create Internet Gateway: {e}")
            raise
    
    async def _delete_internet_gateway(self, igw_id: str, vpc_id: str) -> None:
        """Detach and delete Internet Gateway"""
        try:
            self.ec2_client.detach_internet_gateway(
                InternetGatewayId=igw_id,
                VpcId=vpc_id
            )
            self.ec2_client.delete_internet_gateway(InternetGatewayId=igw_id)
            logger.info(f"Deleted Internet Gateway {igw_id}")
        except ClientError as e:
            logger.error(f"Failed to delete Internet Gateway {igw_id}: {e}")
    
    # =========================================================================
    # Subnet Operations
    # =========================================================================
    
    async def _create_subnet(
        self,
        lab_id: str,
        vpc_id: str,
        cidr: str,
        subnet_type: SubnetType,
        is_public: bool = False
    ) -> str:
        """Create subnet within VPC"""
        try:
            response = self.ec2_client.create_subnet(
                VpcId=vpc_id,
                CidrBlock=cidr,
                TagSpecifications=[{
                    'ResourceType': 'subnet',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'glassdome-{lab_id}-{subnet_type.value}'},
                        {'Key': 'lab_id', 'Value': lab_id},
                        {'Key': 'subnet_type', 'Value': subnet_type.value},
                        {'Key': 'ManagedBy', 'Value': 'glassdome'}
                    ]
                }]
            )
            
            subnet_id = response['Subnet']['SubnetId']
            
            # Enable auto-assign public IP for public subnets
            if is_public:
                self.ec2_client.modify_subnet_attribute(
                    SubnetId=subnet_id,
                    MapPublicIpOnLaunch={'Value': True}
                )
            
            logger.info(f"Created subnet {subnet_id} ({subnet_type.value}: {cidr})")
            return subnet_id
            
        except ClientError as e:
            logger.error(f"Failed to create subnet: {e}")
            raise
    
    async def _delete_subnet(self, subnet_id: str) -> None:
        """Delete subnet"""
        try:
            self.ec2_client.delete_subnet(SubnetId=subnet_id)
            logger.info(f"Deleted subnet {subnet_id}")
        except ClientError as e:
            logger.error(f"Failed to delete subnet {subnet_id}: {e}")
    
    # =========================================================================
    # Route Table Operations
    # =========================================================================
    
    async def _setup_route_tables(
        self,
        infra: AWSLabInfrastructure,
        allocation: LabNetworkAllocation
    ) -> None:
        """Set up route tables for public and private subnets"""
        
        # Create route table for public subnet
        public_rt = self.ec2_client.create_route_table(
            VpcId=infra.vpc_id,
            TagSpecifications=[{
                'ResourceType': 'route-table',
                'Tags': [
                    {'Key': 'Name', 'Value': f'glassdome-{infra.lab_id}-public-rt'},
                    {'Key': 'lab_id', 'Value': infra.lab_id},
                    {'Key': 'ManagedBy', 'Value': 'glassdome'}
                ]
            }]
        )
        public_rt_id = public_rt['RouteTable']['RouteTableId']
        infra.route_tables['public'] = public_rt_id
        
        # Add route to Internet Gateway
        self.ec2_client.create_route(
            RouteTableId=public_rt_id,
            DestinationCidrBlock='0.0.0.0/0',
            GatewayId=infra.internet_gateway_id
        )
        
        # Associate public subnet with public route table
        if SubnetType.PUBLIC in infra.subnets:
            self.ec2_client.associate_route_table(
                SubnetId=infra.subnets[SubnetType.PUBLIC],
                RouteTableId=public_rt_id
            )
        
        logger.info(f"Created route tables for lab {infra.lab_id}")
    
    # =========================================================================
    # Security Group Operations
    # =========================================================================
    
    async def _create_security_groups(self, infra: AWSLabInfrastructure) -> None:
        """Create security groups for each subnet type"""
        
        sg_configs = [
            ('guacamole', 'Guacamole gateway - HTTPS from internet'),
            ('attack', 'Attack console - VNC/RDP/SSH from Guacamole only'),
            ('lab', 'Lab VMs - All traffic from attack console only'),
        ]
        
        for sg_name, description in sg_configs:
            try:
                response = self.ec2_client.create_security_group(
                    GroupName=f'glassdome-{infra.lab_id}-{sg_name}',
                    Description=description,
                    VpcId=infra.vpc_id,
                    TagSpecifications=[{
                        'ResourceType': 'security-group',
                        'Tags': [
                            {'Key': 'Name', 'Value': f'glassdome-{infra.lab_id}-{sg_name}'},
                            {'Key': 'lab_id', 'Value': infra.lab_id},
                            {'Key': 'sg_type', 'Value': sg_name},
                            {'Key': 'ManagedBy', 'Value': 'glassdome'}
                        ]
                    }]
                )
                
                infra.security_groups[sg_name] = response['GroupId']
                logger.info(f"Created security group: {sg_name} ({response['GroupId']})")
                
            except ClientError as e:
                logger.error(f"Failed to create security group {sg_name}: {e}")
                raise
    
    async def _configure_security_rules(self, infra: AWSLabInfrastructure) -> None:
        """
        Configure security group rules for the Guacamole → Kali → Lab chain.
        
        Flow:
        - Internet → Guacamole (443)
        - Guacamole → Attack Console (VNC 5900-5910, RDP 3389, SSH 22)
        - Attack Console → Lab VMs (all traffic)
        """
        sg_guac = infra.security_groups.get('guacamole')
        sg_attack = infra.security_groups.get('attack')
        sg_lab = infra.security_groups.get('lab')
        
        # 1. Guacamole: HTTPS from anywhere
        if sg_guac:
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_guac,
                IpPermissions=[{
                    'IpProtocol': 'tcp',
                    'FromPort': 443,
                    'ToPort': 443,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTPS from internet'}]
                }, {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0', 'Description': 'HTTP redirect'}]
                }]
            )
            logger.info("Configured Guacamole SG: HTTPS from internet")
        
        # 2. Attack console: VNC/RDP/SSH from Guacamole only
        if sg_attack and sg_guac:
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_attack,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 5900,
                        'ToPort': 5910,
                        'UserIdGroupPairs': [{'GroupId': sg_guac, 'Description': 'VNC from Guacamole'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 3389,
                        'ToPort': 3389,
                        'UserIdGroupPairs': [{'GroupId': sg_guac, 'Description': 'RDP from Guacamole'}]
                    },
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'UserIdGroupPairs': [{'GroupId': sg_guac, 'Description': 'SSH from Guacamole'}]
                    }
                ]
            )
            logger.info("Configured Attack SG: VNC/RDP/SSH from Guacamole")
        
        # 3. Lab VMs: All traffic from attack console
        if sg_lab and sg_attack:
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_lab,
                IpPermissions=[{
                    'IpProtocol': '-1',  # All traffic
                    'UserIdGroupPairs': [{'GroupId': sg_attack, 'Description': 'All from attack console'}]
                }]
            )
            logger.info("Configured Lab SG: All traffic from attack console")
        
        # 4. Allow internal communication within lab subnet
        if sg_lab:
            self.ec2_client.authorize_security_group_ingress(
                GroupId=sg_lab,
                IpPermissions=[{
                    'IpProtocol': '-1',
                    'UserIdGroupPairs': [{'GroupId': sg_lab, 'Description': 'Internal lab traffic'}]
                }]
            )
    
    async def _delete_security_group(self, sg_id: str) -> None:
        """Delete security group"""
        try:
            self.ec2_client.delete_security_group(GroupId=sg_id)
            logger.info(f"Deleted security group {sg_id}")
        except ClientError as e:
            if 'InvalidGroup.NotFound' in str(e):
                logger.debug(f"Security group {sg_id} already deleted")
            else:
                logger.error(f"Failed to delete security group {sg_id}: {e}")
    
    # =========================================================================
    # NAT Gateway Operations (for private subnet internet access)
    # =========================================================================
    
    async def create_nat_gateway(
        self,
        lab_id: str,
        public_subnet_id: str
    ) -> str:
        """
        Create NAT Gateway for private subnet internet access.
        
        Optional - only needed if lab VMs need outbound internet access
        (e.g., for package installation).
        """
        # Allocate Elastic IP
        eip = self.ec2_client.allocate_address(Domain='vpc')
        
        response = self.ec2_client.create_nat_gateway(
            SubnetId=public_subnet_id,
            AllocationId=eip['AllocationId'],
            TagSpecifications=[{
                'ResourceType': 'natgateway',
                'Tags': [
                    {'Key': 'Name', 'Value': f'glassdome-{lab_id}-nat'},
                    {'Key': 'lab_id', 'Value': lab_id},
                    {'Key': 'ManagedBy', 'Value': 'glassdome'}
                ]
            }]
        )
        
        nat_id = response['NatGateway']['NatGatewayId']
        
        # Wait for NAT Gateway to be available
        waiter = self.ec2_client.get_waiter('nat_gateway_available')
        waiter.wait(NatGatewayIds=[nat_id])
        
        logger.info(f"Created NAT Gateway {nat_id}")
        return nat_id
    
    async def _delete_nat_gateway(self, nat_id: str) -> None:
        """Delete NAT Gateway and release EIP"""
        try:
            # Get EIP allocation ID before deleting
            nat_info = self.ec2_client.describe_nat_gateways(NatGatewayIds=[nat_id])
            if nat_info['NatGateways']:
                for addr in nat_info['NatGateways'][0].get('NatGatewayAddresses', []):
                    if addr.get('AllocationId'):
                        self.ec2_client.release_address(AllocationId=addr['AllocationId'])
            
            self.ec2_client.delete_nat_gateway(NatGatewayId=nat_id)
            logger.info(f"Deleted NAT Gateway {nat_id}")
        except ClientError as e:
            logger.error(f"Failed to delete NAT Gateway {nat_id}: {e}")
    
    # =========================================================================
    # Cleanup by Tag
    # =========================================================================
    
    async def _cleanup_lab_by_tag(self, lab_id: str) -> bool:
        """Clean up lab resources by searching for lab_id tag"""
        try:
            # Find VPC by tag
            vpcs = self.ec2_client.describe_vpcs(
                Filters=[{'Name': 'tag:lab_id', 'Values': [lab_id]}]
            )
            
            for vpc in vpcs.get('Vpcs', []):
                vpc_id = vpc['VpcId']
                logger.info(f"Found VPC {vpc_id} for lab {lab_id}")
                
                # Build infrastructure object and delete
                infra = AWSLabInfrastructure(
                    lab_id=lab_id,
                    region=self.region,
                    vpc_id=vpc_id
                )
                
                # Find associated resources
                # ... (would need full implementation)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup lab {lab_id} by tag: {e}")
            return False
    
    # =========================================================================
    # PlatformNetworkHandler Interface Implementation
    # =========================================================================
    
    async def generate_network_config(
        self,
        network: NetworkDefinition,
        platform_instance: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AWS-specific config from abstract network definition"""
        is_public = network.network_type in [NetworkType.NAT, NetworkType.BRIDGED]
        
        return {
            "cidr_block": network.cidr,
            "public": is_public,
            "network_type": network.network_type,
            "region": platform_instance or self.region
        }
    
    async def create_network(
        self,
        network: NetworkDefinition,
        config: Dict[str, Any],
        platform_instance: Optional[str] = None
    ) -> bool:
        """
        Create network (subnet) in AWS.
        
        Note: For full lab deployment, use create_lab_infrastructure() instead.
        This method is for individual subnet creation.
        """
        # This would need vpc_id passed in config
        vpc_id = config.get('vpc_id')
        if not vpc_id:
            raise ValueError("vpc_id required in config for AWS subnet creation")
        
        subnet_id = await self._create_subnet(
            lab_id=network.lab_id,
            vpc_id=vpc_id,
            cidr=config['cidr_block'],
            subnet_type=SubnetType.INTERNAL,  # Default
            is_public=config.get('public', False)
        )
        
        return True
    
    async def delete_network(
        self,
        config: Dict[str, Any],
        platform_instance: Optional[str] = None
    ) -> bool:
        """Delete network (subnet)"""
        subnet_id = config.get('subnet_id')
        if subnet_id:
            await self._delete_subnet(subnet_id)
        return True
    
    async def get_vm_interfaces(
        self,
        vm_id: str,
        platform_instance: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get network interfaces for an EC2 instance"""
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[vm_id])
            
            interfaces = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    for idx, eni in enumerate(instance.get('NetworkInterfaces', [])):
                        interfaces.append({
                            'index': idx,
                            'interface_id': eni['NetworkInterfaceId'],
                            'mac_address': eni.get('MacAddress'),
                            'private_ip': eni.get('PrivateIpAddress'),
                            'public_ip': eni.get('Association', {}).get('PublicIp'),
                            'subnet_id': eni.get('SubnetId'),
                            'security_groups': [sg['GroupId'] for sg in eni.get('Groups', [])]
                        })
            
            return interfaces
            
        except ClientError as e:
            logger.error(f"Failed to get interfaces for {vm_id}: {e}")
            return []
    
    def get_lab_infrastructure(self, lab_id: str) -> Optional[AWSLabInfrastructure]:
        """Get tracked infrastructure for a lab"""
        return self._lab_infrastructure.get(lab_id)


# ============================================================================
# Factory Function
# ============================================================================

_handler: Optional[AWSNetworkHandler] = None


def get_aws_network_handler(region: str = None) -> AWSNetworkHandler:
    """Get or create the AWS network handler singleton"""
    global _handler
    if _handler is None or (region and _handler.region != region):
        _handler = AWSNetworkHandler(region=region)
    return _handler

