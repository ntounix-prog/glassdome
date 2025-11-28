"""
State module

Author: Brett Turner (ntounix-prog)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

from glassdome.core.paths import OVERSEER_STATE_FILE


class VMStatus(Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    DEPLOYING = "deploying"
    FAILED = "failed"


class HostStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass
class VM:
    """Represents a deployed VM"""
    id: str
    name: str
    platform: str  # proxmox, esxi, aws, azure
    status: VMStatus
    ip: Optional[str] = None
    specs: Optional[Dict[str, Any]] = None
    services: List[str] = None
    is_production: bool = False
    deployed_at: Optional[str] = None
    deployed_by: Optional[str] = None
    last_checked: Optional[str] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = []
        if isinstance(self.status, str):
            self.status = VMStatus(self.status)


@dataclass
class Host:
    """Represents a host platform"""
    platform: str  # proxmox, esxi, aws, azure
    identifier: str  # IP or account ID
    status: HostStatus
    resources: Dict[str, Any]  # CPU, RAM, disk
    vms: List[str]  # VM IDs on this host
    last_checked: Optional[str] = None
    
    def __post_init__(self):
        if isinstance(self.status, str):
            self.status = HostStatus(self.status)


@dataclass
class Service:
    """Represents a running service"""
    name: str
    vm_id: str
    port: Optional[int] = None
    status: str = "unknown"
    url: Optional[str] = None
    last_checked: Optional[str] = None


@dataclass
class PendingRequest:
    """Represents a request awaiting approval/execution"""
    request_id: str
    action: str
    user: str
    params: Dict[str, Any]
    status: str  # pending, approved, executing, completed, failed, denied
    submitted_at: str
    approved_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    denial_reason: Optional[str] = None


class SystemState:
    """
    Central state management for Overseer
    
    Knows everything about:
    - All VMs across all platforms
    - All hosts and their health
    - All running services
    - All pending/executing requests
    """
    
    def __init__(self, state_file: str = None):
        self.state_file = Path(state_file) if state_file else OVERSEER_STATE_FILE
        
        self.vms: Dict[str, VM] = {}
        self.hosts: Dict[str, Host] = {}
        self.services: Dict[str, Service] = {}
        self.requests: Dict[str, PendingRequest] = {}
        
        # Load persisted state if exists
        self.load()
    
    # ═══════════════════════════════════════════════════
    # VM Management
    # ═══════════════════════════════════════════════════
    
    def add_vm(self, vm: VM):
        """Register a new VM"""
        self.vms[vm.id] = vm
        self.save()
    
    def update_vm(self, vm_id: str, **kwargs):
        """Update VM attributes"""
        if vm_id in self.vms:
            vm = self.vms[vm_id]
            for key, value in kwargs.items():
                if hasattr(vm, key):
                    setattr(vm, key, value)
            vm.last_checked = datetime.now().isoformat()
            self.save()
    
    def get_vm(self, vm_id: str) -> Optional[VM]:
        """Get VM by ID"""
        return self.vms.get(vm_id)
    
    def remove_vm(self, vm_id: str):
        """Remove VM from state"""
        if vm_id in self.vms:
            del self.vms[vm_id]
            self.save()
    
    def is_production(self, vm_id: str) -> bool:
        """Check if VM is marked as production"""
        vm = self.get_vm(vm_id)
        return vm.is_production if vm else False
    
    def get_vms_by_platform(self, platform: str) -> List[VM]:
        """Get all VMs on a platform"""
        return [vm for vm in self.vms.values() if vm.platform == platform]
    
    def get_running_vms(self) -> List[VM]:
        """Get all running VMs"""
        return [vm for vm in self.vms.values() if vm.status == VMStatus.RUNNING]
    
    # ═══════════════════════════════════════════════════
    # Host Management
    # ═══════════════════════════════════════════════════
    
    def add_host(self, host: Host):
        """Register a host"""
        key = f"{host.platform}:{host.identifier}"
        self.hosts[key] = host
        self.save()
    
    def update_host(self, platform: str, identifier: str, **kwargs):
        """Update host attributes"""
        key = f"{platform}:{identifier}"
        if key in self.hosts:
            host = self.hosts[key]
            for k, v in kwargs.items():
                if hasattr(host, k):
                    setattr(host, k, v)
            host.last_checked = datetime.now().isoformat()
            self.save()
    
    def get_host(self, platform: str, identifier: str) -> Optional[Host]:
        """Get host"""
        key = f"{platform}:{identifier}"
        return self.hosts.get(key)
    
    def get_healthy_hosts(self) -> List[Host]:
        """Get all healthy hosts"""
        return [h for h in self.hosts.values() if h.status == HostStatus.HEALTHY]
    
    # ═══════════════════════════════════════════════════
    # Service Management
    # ═══════════════════════════════════════════════════
    
    def add_service(self, service: Service):
        """Register a service"""
        key = f"{service.vm_id}:{service.name}"
        self.services[key] = service
        self.save()
    
    def get_services_on_vm(self, vm_id: str) -> List[Service]:
        """Get all services running on a VM"""
        return [s for s in self.services.values() if s.vm_id == vm_id]
    
    # ═══════════════════════════════════════════════════
    # Request Management
    # ═══════════════════════════════════════════════════
    
    def add_request(self, request: PendingRequest):
        """Add a pending request"""
        self.requests[request.request_id] = request
        self.save()
    
    def update_request_status(self, request_id: str, status: str, **kwargs):
        """Update request status"""
        if request_id in self.requests:
            req = self.requests[request_id]
            req.status = status
            for k, v in kwargs.items():
                if hasattr(req, k):
                    setattr(req, k, v)
            self.save()
    
    def get_pending_requests(self) -> List[PendingRequest]:
        """Get all pending requests"""
        return [r for r in self.requests.values() if r.status == "pending"]
    
    def get_approved_requests(self) -> List[PendingRequest]:
        """Get all approved requests waiting execution"""
        return [r for r in self.requests.values() if r.status == "approved"]
    
    # ═══════════════════════════════════════════════════
    # Resource Calculations
    # ═══════════════════════════════════════════════════
    
    def has_resources(self, platform: str, identifier: str, required: Dict[str, Any]) -> bool:
        """Check if host has sufficient resources"""
        host = self.get_host(platform, identifier)
        if not host or not host.resources:
            return False
        
        # Simple resource check
        if 'cpu' in required and 'cpu_available' in host.resources:
            if required['cpu'] > host.resources['cpu_available']:
                return False
        
        if 'memory' in required and 'memory_available' in host.resources:
            if required['memory'] > host.resources['memory_available']:
                return False
        
        if 'disk' in required and 'disk_available' in host.resources:
            if required['disk'] > host.resources['disk_available']:
                return False
        
        return True
    
    # ═══════════════════════════════════════════════════
    # Persistence
    # ═══════════════════════════════════════════════════
    
    def save(self):
        """Persist state to disk"""
        # Custom serializer for enums
        def enum_serializer(obj):
            if isinstance(obj, Enum):
                return obj.value
            return str(obj)
        
        state = {
            'vms': {k: asdict(v) for k, v in self.vms.items()},
            'hosts': {k: asdict(v) for k, v in self.hosts.items()},
            'services': {k: asdict(v) for k, v in self.services.items()},
            'requests': {k: asdict(v) for k, v in self.requests.items()},
            'last_saved': datetime.now().isoformat()
        }
        
        # Convert enums to their values for JSON serialization
        state_json = json.loads(json.dumps(state, default=enum_serializer))
        
        with open(self.state_file, 'w') as f:
            json.dump(state_json, f, indent=2)
    
    def load(self):
        """Load state from disk"""
        if not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
            
            # Reconstruct objects - __post_init__ will handle enum conversion from strings
            self.vms = {k: VM(**v) for k, v in state.get('vms', {}).items()}
            self.hosts = {k: Host(**v) for k, v in state.get('hosts', {}).items()}
            self.services = {k: Service(**v) for k, v in state.get('services', {}).items()}
            self.requests = {k: PendingRequest(**v) for k, v in state.get('requests', {}).items()}
            
            print(f"✅ Loaded state: {len(self.vms)} VMs, {len(self.hosts)} hosts, {len(self.services)} services")
            
        except Exception as e:
            print(f"⚠️ Could not load state: {e}")
    
    # ═══════════════════════════════════════════════════
    # Summary / Status
    # ═══════════════════════════════════════════════════
    
    def get_summary(self) -> Dict[str, Any]:
        """Get current state summary"""
        return {
            'total_vms': len(self.vms),
            'running_vms': len([v for v in self.vms.values() if v.status == VMStatus.RUNNING]),
            'production_vms': len([v for v in self.vms.values() if v.is_production]),
            'total_hosts': len(self.hosts),
            'healthy_hosts': len([h for h in self.hosts.values() if h.status == HostStatus.HEALTHY]),
            'total_services': len(self.services),
            'pending_requests': len(self.get_pending_requests()),
            'approved_requests': len(self.get_approved_requests())
        }


if __name__ == "__main__":
    # Test state management
    state = SystemState()
    
    # Add test VM
    vm = VM(
        id="114",
        name="ubuntu-powerhouse",
        platform="proxmox",
        status=VMStatus.RUNNING,
        ip="192.168.3.50",
        specs={"cpu": 16, "memory": "32GB", "disk": "1TB"},
        services=["minecraft"],
        is_production=True,
        deployed_at=datetime.now().isoformat()
    )
    state.add_vm(vm)
    
    # Add test host
    host = Host(
        platform="proxmox",
        identifier="192.168.3.2",
        status=HostStatus.HEALTHY,
        resources={"cpu_total": 32, "cpu_available": 16, "memory_total": "128GB"},
        vms=["114"]
    )
    state.add_host(host)
    
    print("\n" + "="*70)
    print("STATE MANAGEMENT TEST")
    print("="*70)
    print(json.dumps(state.get_summary(), indent=2))
    print("\nState saved to:", state.state_file)

