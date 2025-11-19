"""
AWS API Integration
"""
import boto3
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class AWSClient:
    """
    Client for interacting with AWS API
    Handles EC2 instances, VPCs, security groups, and networking
    """
    
    def __init__(self, access_key_id: str, secret_access_key: str,
                 region: str = "us-east-1"):
        """
        Initialize AWS client
        
        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            region: AWS region
        """
        self.region = region
        
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
    
    async def test_connection(self) -> bool:
        """Test connection to AWS"""
        try:
            self.ec2_client.describe_regions()
            logger.info("Successfully connected to AWS")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AWS: {str(e)}")
            return False
    
    async def create_vpc(self, cidr_block: str = "10.0.0.0/16",
                        name: Optional[str] = None) -> Dict[str, Any]:
        """Create a VPC"""
        try:
            vpc = self.ec2_resource.create_vpc(CidrBlock=cidr_block)
            vpc.wait_until_available()
            
            if name:
                vpc.create_tags(Tags=[{"Key": "Name", "Value": name}])
            
            logger.info(f"VPC {vpc.id} created")
            return {"success": True, "vpc_id": vpc.id}
        except Exception as e:
            logger.error(f"Failed to create VPC: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_subnet(self, vpc_id: str, cidr_block: str,
                           availability_zone: Optional[str] = None) -> Dict[str, Any]:
        """Create a subnet"""
        try:
            params = {
                "VpcId": vpc_id,
                "CidrBlock": cidr_block
            }
            if availability_zone:
                params["AvailabilityZone"] = availability_zone
            
            subnet = self.ec2_resource.create_subnet(**params)
            
            logger.info(f"Subnet {subnet.id} created in VPC {vpc_id}")
            return {"success": True, "subnet_id": subnet.id}
        except Exception as e:
            logger.error(f"Failed to create subnet: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_security_group(self, vpc_id: str, name: str,
                                   description: str) -> Dict[str, Any]:
        """Create a security group"""
        try:
            response = self.ec2_client.create_security_group(
                GroupName=name,
                Description=description,
                VpcId=vpc_id
            )
            
            sg_id = response['GroupId']
            logger.info(f"Security group {sg_id} created")
            return {"success": True, "security_group_id": sg_id}
        except Exception as e:
            logger.error(f"Failed to create security group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def launch_instance(self, image_id: str, instance_type: str = "t2.micro",
                             subnet_id: Optional[str] = None,
                             security_group_ids: Optional[List[str]] = None,
                             key_name: Optional[str] = None,
                             user_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Launch an EC2 instance
        
        Args:
            image_id: AMI ID
            instance_type: Instance type (t2.micro, t2.small, etc.)
            subnet_id: Subnet ID
            security_group_ids: List of security group IDs
            key_name: SSH key pair name
            user_data: User data script
            
        Returns:
            Instance details
        """
        try:
            params = {
                "ImageId": image_id,
                "InstanceType": instance_type,
                "MinCount": 1,
                "MaxCount": 1
            }
            
            if subnet_id:
                params["SubnetId"] = subnet_id
            if security_group_ids:
                params["SecurityGroupIds"] = security_group_ids
            if key_name:
                params["KeyName"] = key_name
            if user_data:
                params["UserData"] = user_data
            
            response = self.ec2_client.run_instances(**params)
            instance = response['Instances'][0]
            instance_id = instance['InstanceId']
            
            logger.info(f"EC2 instance {instance_id} launched")
            return {
                "success": True,
                "instance_id": instance_id,
                "state": instance['State']['Name']
            }
        except Exception as e:
            logger.error(f"Failed to launch instance: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def list_instances(self) -> List[Dict[str, Any]]:
        """List all EC2 instances"""
        try:
            response = self.ec2_client.describe_instances()
            instances = []
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        "instance_id": instance['InstanceId'],
                        "state": instance['State']['Name'],
                        "type": instance['InstanceType'],
                        "public_ip": instance.get('PublicIpAddress')
                    })
            
            return instances
        except Exception as e:
            logger.error(f"Failed to list instances: {str(e)}")
            return []
    
    async def terminate_instance(self, instance_id: str) -> Dict[str, Any]:
        """Terminate an EC2 instance"""
        try:
            response = self.ec2_client.terminate_instances(
                InstanceIds=[instance_id]
            )
            
            logger.info(f"Instance {instance_id} terminated")
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"Failed to terminate instance: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_instance_status(self, instance_id: str) -> Dict[str, Any]:
        """Get instance status"""
        try:
            response = self.ec2_client.describe_instances(
                InstanceIds=[instance_id]
            )
            
            instance = response['Reservations'][0]['Instances'][0]
            return {
                "success": True,
                "state": instance['State']['Name'],
                "public_ip": instance.get('PublicIpAddress'),
                "private_ip": instance.get('PrivateIpAddress')
            }
        except Exception as e:
            logger.error(f"Failed to get instance status: {str(e)}")
            return {"success": False, "error": str(e)}

