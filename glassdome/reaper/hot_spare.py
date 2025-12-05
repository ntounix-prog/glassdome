"""
Hot Spare module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import asyncio
import logging

from glassdome.core.database import Base

logger = logging.getLogger(__name__)


class SpareStatus(str, Enum):
    """Status of a hot spare VM"""
    PROVISIONING = "provisioning"  # Being cloned/configured
    BOOTING = "booting"            # Cloned, waiting for boot
    READY = "ready"                # Running, IP assigned, ready for use
    IN_USE = "in_use"              # Assigned to a mission
    RESETTING = "resetting"        # Being reset for reuse
    FAILED = "failed"              # Something went wrong
    DESTROYING = "destroying"      # Being deleted


class HotSpare(Base):
    """
    Hot spare VM in the pool.
    
    These are pre-provisioned VMs ready to be grabbed by Reaper missions.
    """
    __tablename__ = "hot_spares"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # VM identification
    vmid = Column(Integer, nullable=False)           # Proxmox VM ID
    name = Column(String(100), nullable=False)       # VM name (e.g., "spare-ubuntu-001")
    
    # Platform info
    platform = Column(String(50), default="proxmox") # Platform type
    platform_instance = Column(String(10), nullable=False)  # Which Proxmox (01, 02) - from config
    node = Column(String(50), nullable=False)        # Proxmox node name - from config
    
    # VM details
    os_type = Column(String(50), default="ubuntu")   # ubuntu, windows, kali, etc.
    template_id = Column(Integer)                     # Source template VMID
    ip_address = Column(String(50))                   # Assigned IP (once known)
    
    # Status tracking
    status = Column(String(20), default=SpareStatus.PROVISIONING.value)
    assigned_to_mission = Column(String(100))        # mission_id when in_use
    
    # Health tracking
    last_health_check = Column(DateTime)
    health_check_failures = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    ready_at = Column(DateTime)                      # When it became ready
    assigned_at = Column(DateTime)                   # When assigned to mission
    
    def __repr__(self):
        return f"<HotSpare {self.name} ({self.status}) IP={self.ip_address}>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "vmid": self.vmid,
            "name": self.name,
            "platform": self.platform,
            "platform_instance": self.platform_instance,
            "node": self.node,
            "os_type": self.os_type,
            "template_id": self.template_id,
            "ip_address": self.ip_address,
            "status": self.status,
            "assigned_to_mission": self.assigned_to_mission,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ready_at": self.ready_at.isoformat() if self.ready_at else None,
        }


class HotSparePoolConfig:
    """Configuration for the hot spare pool"""
    
    def __init__(
        self,
        min_spares: int = 3,
        max_spares: int = 6,
        os_type: str = "ubuntu",
        platform_instance: Optional[str] = None,  # From config - no default
        template_id: int = 9001,  # Template with qemu-guest-agent pre-installed
        ip_range_start: str = "192.168.3.100",
        ip_range_end: str = "192.168.3.120",
        vm_cores: int = 2,
        vm_memory: int = 2048,
        health_check_interval: int = 60,  # seconds
    ):
        # Get platform instance from config if not provided
        if platform_instance is None:
            from glassdome.core.config import settings
            platform_instance = settings.get_hot_spare_proxmox_instance()
        
        self.min_spares = min_spares
        self.max_spares = max_spares
        self.os_type = os_type
        self.platform_instance = platform_instance
        self.template_id = template_id
        self.ip_range_start = ip_range_start
        self.ip_range_end = ip_range_end
        self.vm_cores = vm_cores
        self.vm_memory = vm_memory
        self.health_check_interval = health_check_interval
    
    def get_ip_range(self) -> List[str]:
        """Get list of IPs in the configured range"""
        start_parts = self.ip_range_start.split(".")
        end_parts = self.ip_range_end.split(".")
        
        # Assume same /24 subnet
        prefix = ".".join(start_parts[:3])
        start = int(start_parts[3])
        end = int(end_parts[3])
        
        return [f"{prefix}.{i}" for i in range(start, end + 1)]


class HotSparePool:
    """
    Manages the hot spare pool.
    
    Responsibilities:
    - Maintain minimum number of ready spares
    - Provision new spares when pool is low
    - Health check spares periodically
    - Provide spares to Reaper missions
    - Clean up or reset spares after use
    """
    
    def __init__(self, config: Optional[HotSparePoolConfig] = None):
        self.config = config or HotSparePoolConfig()
        self._running = False
        self._task = None
        logger.info(f"HotSparePool initialized: min={self.config.min_spares}, os={self.config.os_type}")
    
    async def start(self):
        """Start the pool manager background task"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._pool_manager_loop())
        logger.info("HotSparePool manager started")
    
    async def stop(self):
        """Stop the pool manager"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("HotSparePool manager stopped")
    
    async def _pool_manager_loop(self):
        """Background loop to maintain pool"""
        from glassdome.core.database import AsyncSessionLocal
        
        while self._running:
            try:
                async with AsyncSessionLocal() as session:
                    await self._maintain_pool(session)
                    await self._health_check_spares(session)
            except Exception as e:
                logger.error(f"Pool manager error: {e}")
            
            await asyncio.sleep(self.config.health_check_interval)
    
    async def _maintain_pool(self, session):
        """Ensure we have minimum spares ready"""
        from sqlalchemy import select
        
        # Count ready spares
        result = await session.execute(
            select(HotSpare).where(
                HotSpare.status == SpareStatus.READY.value,
                HotSpare.os_type == self.config.os_type,
                HotSpare.platform_instance == self.config.platform_instance
            )
        )
        ready_spares = result.scalars().all()
        ready_count = len(ready_spares)
        
        # Count provisioning spares
        result = await session.execute(
            select(HotSpare).where(
                HotSpare.status.in_([SpareStatus.PROVISIONING.value, SpareStatus.BOOTING.value]),
                HotSpare.os_type == self.config.os_type,
                HotSpare.platform_instance == self.config.platform_instance
            )
        )
        provisioning_count = len(result.scalars().all())
        
        total_available = ready_count + provisioning_count
        
        if total_available < self.config.min_spares:
            needed = self.config.min_spares - total_available
            logger.info(f"Pool low: {ready_count} ready, {provisioning_count} provisioning. Need {needed} more.")
            
            for _ in range(needed):
                await self._provision_spare(session)
    
    async def _provision_spare(self, session) -> Optional[HotSpare]:
        """Provision a new spare VM"""
        from glassdome.platforms.proxmox_client import ProxmoxClient
        from glassdome.core.config import Settings
        from sqlalchemy import select
        
        settings = Settings()
        pve_config = settings.get_proxmox_config(self.config.platform_instance)
        
        # Find next available IP
        used_ips = set()
        result = await session.execute(select(HotSpare.ip_address))
        for row in result.scalars().all():
            if row:
                used_ips.add(row)
        
        available_ips = [ip for ip in self.config.get_ip_range() if ip not in used_ips]
        if not available_ips:
            logger.error("No available IPs in pool range!")
            return None
        
        assigned_ip = available_ips[0]
        
        # Get next VMID from Proxmox (not our own calculation!)
        from glassdome.platforms.proxmox_client import ProxmoxClient
        node_name = f"pve{self.config.platform_instance}"
        
        client = ProxmoxClient(
            host=pve_config["host"],
            user=pve_config["user"],
            password=pve_config.get("password"),
            token_name=pve_config.get("token_name"),
            token_value=pve_config.get("token_value"),
            verify_ssl=pve_config.get("verify_ssl", False),
            default_node=node_name
        )
        
        new_vmid = await client.get_next_vmid()
        
        # Create spare record with the ACTUAL VMID from Proxmox
        spare_name = f"spare-{self.config.os_type}-{new_vmid}"
        spare = HotSpare(
            vmid=new_vmid,
            name=spare_name,
            platform="proxmox",
            platform_instance=self.config.platform_instance,
            node=node_name,
            os_type=self.config.os_type,
            template_id=self.config.template_id,
            ip_address=assigned_ip,
            status=SpareStatus.PROVISIONING.value,
        )
        session.add(spare)
        await session.commit()
        
        logger.info(f"Provisioning spare: {spare_name} (VMID {new_vmid}, IP {assigned_ip})")
        
        # Clone VM in background (don't block the pool manager)
        # Pass the actual VMID so it uses the same one
        asyncio.create_task(self._clone_spare_vm(spare.id, pve_config, assigned_ip, new_vmid))
        
        return spare
    
    async def _clone_spare_vm(self, spare_id: int, pve_config: Dict, assigned_ip: str, vmid: int = None):
        """Clone and configure a spare VM (runs in background)"""
        from glassdome.platforms.proxmox_client import ProxmoxClient
        from glassdome.core.database import AsyncSessionLocal
        from sqlalchemy import select
        
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(HotSpare).where(HotSpare.id == spare_id))
            spare = result.scalar_one_or_none()
            if not spare:
                return
            
            try:
                node_name = f"pve{self.config.platform_instance}"
                
                client = ProxmoxClient(
                    host=pve_config["host"],
                    user=pve_config["user"],
                    password=pve_config.get("password"),
                    token_name=pve_config.get("token_name"),
                    token_value=pve_config.get("token_value"),
                    verify_ssl=pve_config.get("verify_ssl", False),
                    default_node=node_name
                )
                
                # Clone from template with static IP
                # Use the pre-allocated VMID from Proxmox
                vm_config = {
                    "name": spare.name,
                    "vmid": vmid or spare.vmid,  # Use pre-allocated VMID
                    "os_type": spare.os_type,
                    "template_id": spare.template_id,
                    "cores": self.config.vm_cores,
                    "memory": self.config.vm_memory,
                    "ip_address": assigned_ip,
                    "gateway": "192.168.3.1",
                    "netmask": "255.255.255.0",
                    "network": "vmbr2",
                    "vlan_tag": 2,
                }
                
                result = await client.create_vm(vm_config)
                
                if result.get("ip_address"):
                    spare.ip_address = result["ip_address"]
                
                spare.status = SpareStatus.READY.value
                spare.ready_at = datetime.utcnow()  # Use naive datetime for DB compatibility
                await session.commit()
                
                logger.info(f"Spare {spare.name} ready at {spare.ip_address}")
                
            except Exception as e:
                logger.error(f"Failed to provision spare {spare.name}: {e}")
                spare.status = SpareStatus.FAILED.value
                await session.commit()
    
    async def _health_check_spares(self, session):
        """Health check ready spares"""
        from sqlalchemy import select
        import subprocess
        
        result = await session.execute(
            select(HotSpare).where(HotSpare.status == SpareStatus.READY.value)
        )
        spares = result.scalars().all()
        
        for spare in spares:
            if not spare.ip_address:
                continue
            
            # Simple ping check
            try:
                proc = await asyncio.create_subprocess_exec(
                    "ping", "-c", "1", "-W", "2", spare.ip_address,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL
                )
                await proc.wait()
                
                if proc.returncode == 0:
                    spare.last_health_check = datetime.utcnow()  # Use naive datetime for DB compatibility
                    spare.health_check_failures = 0
                else:
                    spare.health_check_failures += 1
                    if spare.health_check_failures >= 3:
                        logger.warning(f"Spare {spare.name} failed health checks, marking failed")
                        spare.status = SpareStatus.FAILED.value
            except Exception as e:
                logger.error(f"Health check error for {spare.name}: {e}")
        
        await session.commit()
    
    async def acquire_spare(
        self, 
        session,
        os_type: str = "ubuntu",
        mission_id: Optional[str] = None
    ) -> Optional[HotSpare]:
        """
        Acquire a ready spare for a mission.
        
        Uses SELECT FOR UPDATE to prevent race conditions - the row is locked
        until the transaction commits, so no other mission can grab the same spare.
        
        Immediately dispatches a replacement provisioning task to the orchestrator.
        
        Returns:
            HotSpare if available, None if pool empty
        """
        from sqlalchemy import select
        
        # Find and LOCK a ready spare (FOR UPDATE prevents race conditions)
        # SKIP LOCKED allows other transactions to skip locked rows and grab different spares
        result = await session.execute(
            select(HotSpare).where(
                HotSpare.status == SpareStatus.READY.value,
                HotSpare.os_type == os_type,
                HotSpare.platform_instance == self.config.platform_instance
            ).order_by(HotSpare.ready_at).limit(1).with_for_update(skip_locked=True)
        )
        spare = result.scalar_one_or_none()
        
        if spare:
            # Row is locked - safe to update
            spare.status = SpareStatus.IN_USE.value
            spare.assigned_to_mission = mission_id
            spare.assigned_at = datetime.utcnow()  # Use naive datetime for DB compatibility
            await session.commit()  # Releases the lock
            logger.info(f"Acquired spare {spare.name} for mission {mission_id}")
            
            # IMMEDIATELY dispatch replacement provisioning (don't wait for background loop)
            asyncio.create_task(self._dispatch_replacement(os_type))
            
            return spare
        
        logger.warning(f"No ready spares available for os_type={os_type}")
        return None
    
    async def _dispatch_replacement(self, os_type: str):
        """
        Dispatch a replacement spare provisioning task.
        
        Called immediately when a spare is acquired to maintain pool levels.
        Runs in background - doesn't block the mission.
        """
        from glassdome.core.database import AsyncSessionLocal
        from glassdome.core.config import Settings
        
        try:
            logger.info(f"🔄 Dispatching replacement spare for {os_type}")
            
            async with AsyncSessionLocal() as session:
                # Check if we need a replacement (might have enough provisioning already)
                from sqlalchemy import select, func
                
                result = await session.execute(
                    select(func.count(HotSpare.id)).where(
                        HotSpare.status.in_([SpareStatus.READY.value, SpareStatus.PROVISIONING.value, SpareStatus.BOOTING.value]),
                        HotSpare.os_type == os_type,
                        HotSpare.platform_instance == self.config.platform_instance
                    )
                )
                available_count = result.scalar() or 0
                
                if available_count >= self.config.min_spares:
                    logger.info(f"Pool already at minimum ({available_count} available), skipping replacement")
                    return
                
                # Provision a replacement
                settings = Settings()
                pve_config = settings.get_proxmox_config(self.config.platform_instance)
                
                spare = await self._provision_spare(session)
                if spare:
                    logger.info(f"✅ Replacement spare queued: {spare.name}")
                else:
                    logger.warning(f"⚠️ Failed to queue replacement spare")
                    
        except Exception as e:
            logger.error(f"Error dispatching replacement: {e}")
    
    async def release_spare(
        self,
        session,
        spare_id: int,
        destroy: bool = True
    ):
        """
        Release a spare after mission completion.
        
        Args:
            spare_id: Spare ID
            destroy: If True, destroy VM and remove from pool.
                    If False, reset VM for reuse (not implemented yet).
        """
        from sqlalchemy import select
        from glassdome.platforms.proxmox_client import ProxmoxClient
        from glassdome.core.config import Settings
        
        result = await session.execute(select(HotSpare).where(HotSpare.id == spare_id))
        spare = result.scalar_one_or_none()
        
        if not spare:
            logger.warning(f"Spare {spare_id} not found")
            return
        
        if destroy:
            spare.status = SpareStatus.DESTROYING.value
            await session.commit()
            
            try:
                settings = Settings()
                pve_config = settings.get_proxmox_config(spare.platform_instance)
                
                client = ProxmoxClient(
                    host=pve_config["host"],
                    user=pve_config["user"],
                    password=pve_config.get("password"),
                    verify_ssl=False,
                    default_node=spare.node
                )
                
                # Stop and delete VM
                await client.stop_vm(str(spare.vmid))
                await asyncio.sleep(5)  # Wait for stop
                await client.delete_vm_raw(spare.node, spare.vmid)
                
                # Remove from database
                await session.delete(spare)
                await session.commit()
                logger.info(f"Destroyed spare {spare.name}")
                
            except Exception as e:
                logger.error(f"Failed to destroy spare {spare.name}: {e}")
                spare.status = SpareStatus.FAILED.value
                await session.commit()
        else:
            # TODO: Implement VM reset (snapshot revert or re-clone)
            logger.warning("VM reset not implemented, destroying instead")
            await self.release_spare(session, spare_id, destroy=True)
    
    async def get_pool_status(self, session) -> Dict[str, Any]:
        """Get current pool status"""
        from sqlalchemy import select, func
        
        result = await session.execute(
            select(HotSpare.status, func.count(HotSpare.id))
            .where(HotSpare.platform_instance == self.config.platform_instance)
            .group_by(HotSpare.status)
        )
        
        counts = {row[0]: row[1] for row in result.all()}
        
        return {
            "platform_instance": self.config.platform_instance,
            "os_type": self.config.os_type,
            "min_spares": self.config.min_spares,
            "max_spares": self.config.max_spares,
            "counts": {
                "ready": counts.get(SpareStatus.READY.value, 0),
                "in_use": counts.get(SpareStatus.IN_USE.value, 0),
                "provisioning": counts.get(SpareStatus.PROVISIONING.value, 0),
                "booting": counts.get(SpareStatus.BOOTING.value, 0),
                "failed": counts.get(SpareStatus.FAILED.value, 0),
            },
            "ip_range": f"{self.config.ip_range_start} - {self.config.ip_range_end}",
        }


# Global pool instances - one per OS type
_pools: Dict[str, HotSparePool] = {}

# Default pool configuration parameters (configs created lazily to avoid settings lookup at import time)
POOL_CONFIG_PARAMS = {
    "ubuntu": {
        "min_spares": 5,
        "max_spares": 8,
        "os_type": "ubuntu",
        "template_id": 9003,  # Ubuntu 22.04 with QEMU guest agent
        "ip_range_start": "192.168.3.100",
        "ip_range_end": "192.168.3.119",
    },
    "windows10": {
        "min_spares": 5,
        "max_spares": 8,
        "os_type": "windows10",
        "template_id": 9011,  # Windows 10 Enterprise template
        "ip_range_start": "192.168.3.120",
        "ip_range_end": "192.168.3.139",
    },
}

# Lazy-loaded configs
_pool_configs: Dict[str, HotSparePoolConfig] = {}


def get_pool_config(os_type: str) -> Optional[HotSparePoolConfig]:
    """Get or create pool config for an OS type (lazy initialization)"""
    if os_type not in _pool_configs:
        params = POOL_CONFIG_PARAMS.get(os_type)
        if params:
            _pool_configs[os_type] = HotSparePoolConfig(**params)
    return _pool_configs.get(os_type)


# For backwards compatibility
POOL_CONFIGS = POOL_CONFIG_PARAMS  # Just expose the param dict, not instantiated configs


def get_hot_spare_pool(os_type: str = "ubuntu") -> HotSparePool:
    """
    Get the hot spare pool for a specific OS type.
    
    Args:
        os_type: OS type to get pool for ("ubuntu", "windows10", etc.)
    
    Returns:
        HotSparePool instance for the specified OS type
    """
    global _pools
    
    if os_type not in _pools:
        config = get_pool_config(os_type)
        if config is None:
            # Create default config for unknown OS types
            config = HotSparePoolConfig(
                min_spares=2,
                max_spares=4,
                os_type=os_type,
            )
            logger.warning(f"No predefined config for OS type '{os_type}', using defaults")
        
        _pools[os_type] = HotSparePool(config)
    
    return _pools[os_type]


def get_all_pools() -> Dict[str, HotSparePool]:
    """Get all initialized hot spare pools"""
    return _pools


async def initialize_pool(os_type: str = None):
    """
    Initialize and start hot spare pool(s).
    
    Args:
        os_type: Specific OS type to initialize, or None for all configured pools
    
    Returns:
        Single pool if os_type specified, dict of all pools otherwise
    """
    if os_type:
        pool = get_hot_spare_pool(os_type)
        await pool.start()
        return pool
    
    # Initialize all configured pools
    pools = {}
    for os_name in POOL_CONFIG_PARAMS.keys():
        pool = get_hot_spare_pool(os_name)
        await pool.start()
        pools[os_name] = pool
        logger.info(f"Started hot spare pool for {os_name}")
    
    return pools


async def initialize_all_pools():
    """Initialize and start all configured hot spare pools"""
    return await initialize_pool(os_type=None)

