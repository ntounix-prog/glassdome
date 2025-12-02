"""
Registry Reconciler Module

Keeps Redis registry in sync with actual infrastructure across all platforms.
Scans Proxmox, AWS, Azure and updates Redis to match reality.

Author: Brett Turner (ntounix)
Created: December 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

import redis.asyncio as redis

from glassdome.core.config import settings

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    VM = "vm"
    TEMPLATE = "template"
    LAB_VM = "lab_vm"
    NETWORK = "network"


@dataclass
class Resource:
    """Represents a resource on any platform"""
    platform: str           # proxmox, aws, azure
    instance: str           # 01, 02, us-west-2, etc.
    resource_type: ResourceType
    resource_id: str        # VM ID, instance ID, etc.
    name: str
    status: str             # running, stopped, terminated
    lab_id: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    
    @property
    def redis_key(self) -> str:
        """Generate Redis key for this resource"""
        return f"registry:resource:{self.platform}:{self.instance}:{self.resource_type.value}:{self.resource_id}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "instance": self.instance,
            "type": self.resource_type.value,
            "id": self.resource_id,
            "name": self.name,
            "status": self.status,
            "lab_id": self.lab_id,
            "tags": self.tags,
            "last_seen": datetime.utcnow().isoformat()
        }


class PlatformScanner:
    """Base class for platform-specific scanning"""
    
    async def scan(self) -> List[Resource]:
        raise NotImplementedError


class ProxmoxScanner(PlatformScanner):
    """Scans Proxmox instances for VMs and templates"""
    
    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self.config = settings.get_proxmox_config(instance_id)
    
    async def scan(self) -> List[Resource]:
        """Scan Proxmox instance for all VMs and templates"""
        resources = []
        
        if not self.config.get("host"):
            logger.warning(f"Proxmox instance {self.instance_id} not configured, skipping scan")
            return resources
        
        try:
            from proxmoxer import ProxmoxAPI
            
            # Connect to Proxmox
            pve = ProxmoxAPI(
                self.config["host"],
                user=self.config.get("user"),
                password=self.config.get("password"),
                token_name=self.config.get("token_name"),
                token_value=self.config.get("token_value"),
                verify_ssl=self.config.get("verify_ssl", False)
            )
            
            # Get node name
            node = self.config.get("node", "pve")
            
            # Scan VMs
            for vm in pve.nodes(node).qemu.get():
                vmid = str(vm["vmid"])
                name = vm.get("name", f"vm-{vmid}")
                status = vm.get("status", "unknown")
                
                # Check if it's a template
                is_template = vm.get("template", 0) == 1
                
                # Try to get tags from description
                lab_id = None
                tags = {}
                try:
                    config = pve.nodes(node).qemu(vmid).config.get()
                    description = config.get("description", "")
                    if "glassdome:lab_id=" in description:
                        lab_id = description.split("glassdome:lab_id=")[1].split()[0]
                        tags["lab_id"] = lab_id
                except:
                    pass
                
                resource_type = ResourceType.TEMPLATE if is_template else (
                    ResourceType.LAB_VM if lab_id else ResourceType.VM
                )
                
                resources.append(Resource(
                    platform="proxmox",
                    instance=self.instance_id,
                    resource_type=resource_type,
                    resource_id=vmid,
                    name=name,
                    status=status,
                    lab_id=lab_id,
                    tags=tags
                ))
            
            logger.info(f"Proxmox {self.instance_id}: Found {len(resources)} resources")
            
        except ImportError:
            logger.warning("proxmoxer not installed, skipping Proxmox scan")
        except Exception as e:
            logger.error(f"Error scanning Proxmox {self.instance_id}: {e}")
        
        return resources


class AWSScanner(PlatformScanner):
    """Scans AWS regions for EC2 instances"""
    
    def __init__(self, region: str = "us-west-2"):
        self.region = region
    
    async def scan(self) -> List[Resource]:
        """Scan AWS region for EC2 instances"""
        resources = []
        
        from glassdome.core.secrets_backend import get_secret
        aws_key = get_secret('aws_access_key_id')
        aws_secret = get_secret('aws_secret_access_key')
        
        if not aws_key:
            logger.warning("AWS not configured, skipping scan")
            return resources
        
        try:
            import boto3
            
            ec2 = boto3.client(
                'ec2',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=self.region
            )
            
            # Get all instances (not terminated)
            response = ec2.describe_instances(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running', 'stopping', 'stopped']}
                ]
            )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    
                    # Get name from tags
                    name = instance_id
                    lab_id = None
                    tags = {}
                    
                    for tag in instance.get('Tags', []):
                        if tag['Key'] == 'Name':
                            name = tag['Value']
                        elif tag['Key'] == 'glassdome:lab_id':
                            lab_id = tag['Value']
                        tags[tag['Key']] = tag['Value']
                    
                    status = instance['State']['Name']
                    
                    resource_type = ResourceType.LAB_VM if lab_id else ResourceType.VM
                    
                    resources.append(Resource(
                        platform="aws",
                        instance=self.region,
                        resource_type=resource_type,
                        resource_id=instance_id,
                        name=name,
                        status=status,
                        lab_id=lab_id,
                        tags=tags
                    ))
            
            logger.info(f"AWS {self.region}: Found {len(resources)} resources")
            
        except ImportError:
            logger.warning("boto3 not installed, skipping AWS scan")
        except Exception as e:
            logger.error(f"Error scanning AWS {self.region}: {e}")
        
        return resources


class RegistryReconciler:
    """
    Keeps Redis registry in sync with actual infrastructure.
    
    Responsibilities:
    - Periodically scan all configured platforms
    - Compare actual state with Redis state
    - Update Redis to match reality
    - Create drift alerts for unexpected changes
    - Clean up orphaned records
    """
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
        self._running = False
        self._last_reconcile: Optional[datetime] = None
        
        # Configure scanners
        self.scanners: List[PlatformScanner] = []
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection"""
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis
    
    def _configure_scanners(self):
        """Configure platform scanners based on settings"""
        self.scanners = []
        
        # Add Proxmox scanners for configured instances
        for instance_id in settings.list_proxmox_instances():
            config = settings.get_proxmox_config(instance_id)
            if config.get("host"):
                self.scanners.append(ProxmoxScanner(instance_id))
                logger.info(f"Added Proxmox scanner for instance {instance_id}")
        
        # Add AWS scanner if configured
        from glassdome.core.secrets_backend import get_secret
        if get_secret('aws_access_key_id'):
            # Scan common regions
            for region in ["us-west-2", "us-east-1"]:
                self.scanners.append(AWSScanner(region))
                logger.info(f"Added AWS scanner for region {region}")
    
    async def scan_all_platforms(self) -> List[Resource]:
        """Scan all configured platforms and return resources"""
        all_resources = []
        
        for scanner in self.scanners:
            try:
                resources = await scanner.scan()
                all_resources.extend(resources)
            except Exception as e:
                logger.error(f"Scanner error: {e}")
        
        return all_resources
    
    async def get_redis_state(self) -> Dict[str, Dict]:
        """Get current state from Redis"""
        r = await self._get_redis()
        
        state = {}
        
        # Get all resource keys
        keys = await r.keys("registry:resource:*")
        
        for key in keys:
            data = await r.hgetall(key)
            if data:
                state[key] = data
        
        return state
    
    async def reconcile(self) -> Dict[str, Any]:
        """
        Main reconciliation logic.
        
        Returns:
            Summary of changes made
        """
        logger.info("Starting registry reconciliation...")
        
        r = await self._get_redis()
        
        # Scan all platforms
        actual_resources = await self.scan_all_platforms()
        actual_keys = {res.redis_key: res for res in actual_resources}
        
        # Get Redis state
        redis_state = await self.get_redis_state()
        redis_keys = set(redis_state.keys())
        
        # Calculate differences
        actual_key_set = set(actual_keys.keys())
        
        added = actual_key_set - redis_keys      # New resources not in Redis
        removed = redis_keys - actual_key_set    # Stale resources in Redis
        existing = actual_key_set & redis_keys   # Resources to update
        
        stats = {
            "scanned": len(actual_resources),
            "added": 0,
            "updated": 0,
            "removed": 0,
            "drifts_created": 0,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add new resources to Redis
        for key in added:
            resource = actual_keys[key]
            await r.hset(key, mapping=resource.to_dict())
            await self._update_indexes(r, resource)
            stats["added"] += 1
            logger.debug(f"Added: {key}")
        
        # Update existing resources
        for key in existing:
            resource = actual_keys[key]
            await r.hset(key, mapping=resource.to_dict())
            stats["updated"] += 1
        
        # Remove stale resources
        for key in removed:
            old_data = redis_state.get(key, {})
            
            # Create drift alert if this was a lab VM
            if ":lab_vm:" in key or old_data.get("lab_id"):
                await self._create_drift_alert(r, key, old_data, "resource_deleted")
                stats["drifts_created"] += 1
            
            # Remove from Redis
            await r.delete(key)
            await self._remove_from_indexes(r, key)
            stats["removed"] += 1
            logger.info(f"Removed stale: {key}")
        
        # Update reconciliation timestamp
        await r.set("registry:reconciler:last_run", datetime.utcnow().isoformat())
        await r.hset("registry:reconciler:stats", mapping=stats)
        
        self._last_reconcile = datetime.utcnow()
        
        logger.info(
            f"Reconciliation complete: "
            f"scanned={stats['scanned']}, added={stats['added']}, "
            f"updated={stats['updated']}, removed={stats['removed']}, "
            f"drifts={stats['drifts_created']}"
        )
        
        return stats
    
    async def _update_indexes(self, r: redis.Redis, resource: Resource):
        """Update type indexes for a resource"""
        index_key = f"registry:index:type:{resource.resource_type.value}"
        await r.sadd(index_key, resource.redis_key)
        
        # Also index by lab if applicable
        if resource.lab_id:
            lab_index = f"registry:lab:{resource.lab_id}:resources"
            await r.sadd(lab_index, resource.redis_key)
    
    async def _remove_from_indexes(self, r: redis.Redis, key: str):
        """Remove resource from all indexes"""
        # Determine type from key
        for rtype in ResourceType:
            index_key = f"registry:index:type:{rtype.value}"
            await r.srem(index_key, key)
        
        # Remove from lab indexes
        lab_keys = await r.keys("registry:lab:*:resources")
        for lab_key in lab_keys:
            await r.srem(lab_key, key)
    
    async def _create_drift_alert(
        self, 
        r: redis.Redis, 
        key: str, 
        old_data: Dict, 
        drift_type: str
    ):
        """Create a drift alert for unexpected changes"""
        drift_key = f"registry:drift:{key.replace('registry:resource:', '')}"
        
        drift_data = {
            "type": drift_type,
            "resource_key": key,
            "old_data": str(old_data),
            "detected_at": datetime.utcnow().isoformat(),
            "resolved": "false"
        }
        
        await r.hset(drift_key, mapping=drift_data)
        await r.sadd("registry:drift:active", drift_key)
        
        logger.warning(f"Drift detected: {drift_type} for {key}")
    
    async def start_background_reconciliation(self, interval_seconds: int = 300):
        """Start background reconciliation loop"""
        self._running = True
        self._configure_scanners()
        
        logger.info(f"Starting background reconciliation (interval: {interval_seconds}s)")
        
        while self._running:
            try:
                await self.reconcile()
            except Exception as e:
                logger.error(f"Reconciliation error: {e}")
            
            await asyncio.sleep(interval_seconds)
    
    async def stop(self):
        """Stop background reconciliation"""
        self._running = False
        if self._redis:
            await self._redis.close()
    
    async def force_reconcile(self) -> Dict[str, Any]:
        """Force immediate reconciliation"""
        self._configure_scanners()
        return await self.reconcile()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get reconciler status"""
        r = await self._get_redis()
        
        last_run = await r.get("registry:reconciler:last_run")
        stats = await r.hgetall("registry:reconciler:stats")
        
        return {
            "running": self._running,
            "last_reconcile": last_run,
            "last_stats": stats,
            "scanners": [
                f"{type(s).__name__}({getattr(s, 'instance_id', getattr(s, 'region', 'unknown'))})"
                for s in self.scanners
            ]
        }


# Global reconciler instance
_reconciler: Optional[RegistryReconciler] = None


def get_reconciler() -> RegistryReconciler:
    """Get or create the global reconciler instance"""
    global _reconciler
    if _reconciler is None:
        _reconciler = RegistryReconciler()
    return _reconciler


async def start_reconciler(interval_seconds: int = 300):
    """Start the background reconciler"""
    reconciler = get_reconciler()
    await reconciler.start_background_reconciliation(interval_seconds)


async def force_reconcile() -> Dict[str, Any]:
    """Force immediate reconciliation"""
    reconciler = get_reconciler()
    return await reconciler.force_reconcile()

