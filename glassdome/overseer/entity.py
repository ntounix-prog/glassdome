"""
Entity module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from glassdome.overseer.state import SystemState, VM, Host, Service, PendingRequest, VMStatus, HostStatus
from glassdome.knowledge import RAGHelper
from glassdome.platforms import ProxmoxClient, ESXiClient, AWSClient, AzureClient
from glassdome.reaper.engine import MissionEngine
from glassdome.reaper.planner import VulnerabilityPlanner
from glassdome.reaper.task_queue import InMemoryTaskQueue
from glassdome.reaper.event_bus import InMemoryEventBus
from glassdome.reaper.mission_store import InMemoryMissionStore
from glassdome.reaper.models import MissionState, HostState as ReaperHostState


class OverseerEntity:
    """
    Autonomous system administrator
    
    Not a reactive API - a proactive entity that:
    - Watches everything 24/7
    - Validates all requests
    - Prevents disasters
    - Learns from history
    """
    
    def __init__(self, settings = None):
        if settings is None:
            from glassdome.core.security import get_secure_settings
            settings = get_secure_settings()
        self.settings = settings
        self.state = SystemState()
        self.rag = RAGHelper()
        
        # Request queue (approved but not yet executed)
        self.request_queue = asyncio.Queue()
        
        # Control flags
        self.monitoring_active = True
        self.execution_active = True
        
        # Platform clients (initialized lazily)
        self._proxmox = None
        self._esxi = None
        self._aws = None
        self._azure = None
        
        # Statistics
        self.stats = {
            'requests_received': 0,
            'requests_approved': 0,
            'requests_denied': 0,
            'requests_completed': 0,
            'requests_failed': 0,
            'issues_detected': 0,
            'issues_resolved': 0
        }
        
        # Reaper mission management
        self.reaper_missions: Dict[str, MissionEngine] = {}
        self.reaper_task_queue = InMemoryTaskQueue()
        self.reaper_event_bus = InMemoryEventBus()
        self.reaper_mission_store = InMemoryMissionStore()
        self.reaper_planner = VulnerabilityPlanner()
    
    # ═══════════════════════════════════════════════════
    # Platform Clients (Lazy Loading)
    # ═══════════════════════════════════════════════════
    
    @property
    def proxmox(self):
        if not self._proxmox:
            from glassdome.core.secrets_backend import get_secret
            self._proxmox = ProxmoxClient(
                host=self.settings.proxmox_host,
                username=self.settings.proxmox_username,
                password=get_secret('proxmox_password'),
                node=self.settings.proxmox_node
            )
        return self._proxmox
    
    @property
    def esxi(self):
        if not self._esxi:
            from glassdome.core.secrets_backend import get_secret
            self._esxi = ESXiClient(
                host=self.settings.esxi_host,
                username=self.settings.esxi_username,
                password=get_secret('esxi_password')
            )
        return self._esxi
    
    @property
    def aws(self):
        if not self._aws:
            from glassdome.core.secrets_backend import get_secret
            self._aws = AWSClient(
                access_key_id=get_secret('aws_access_key_id'),
                secret_access_key=get_secret('aws_secret_access_key'),
                region=self.settings.aws_region
            )
        return self._aws
    
    @property
    def azure(self):
        if not self._azure:
            from glassdome.core.secrets_backend import get_secret
            self._azure = AzureClient(
                tenant_id=self.settings.azure_tenant_id,
                client_id=self.settings.azure_client_id,
                client_secret=get_secret('azure_client_secret'),
                subscription_id=self.settings.azure_subscription_id
            )
        return self._azure
    
    # ═══════════════════════════════════════════════════
    # MAIN ENTRY POINT - Start All Loops
    # ═══════════════════════════════════════════════════
    
    async def run(self):
        """
        Start all autonomous loops
        This is the main entry point - runs forever
        """
        print("\n" + "="*70)
        print("🧠 GLASSDOME OVERSEER - AUTONOMOUS ENTITY")
        print("="*70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"State file: {self.state.state_file}")
        print("\nInitial State:")
        print(f"  VMs: {len(self.state.vms)}")
        print(f"  Hosts: {len(self.state.hosts)}")
        print(f"  Services: {len(self.state.services)}")
        print("="*70 + "\n")
        
        # Start all loops concurrently
        await asyncio.gather(
            self.monitor_loop(),         # Continuous monitoring
            self.execution_loop(),       # Execute approved requests
            self.state_sync_loop(),      # Keep state current
            self.health_check_loop(),    # Self-monitoring
            return_exceptions=True
        )
    
    # ═══════════════════════════════════════════════════
    # LOOP 1: Continuous Monitoring
    # ═══════════════════════════════════════════════════
    
    async def monitor_loop(self):
        """
        Runs continuously, watching everything
        Like a sysadmin checking dashboards 24/7
        """
        print("🔍 [Monitor] Starting continuous monitoring loop...")
        
        while self.monitoring_active:
            try:
                # Check all platforms
                await self._check_all_platforms()
                
                # Detect issues
                issues = await self._detect_issues()
                
                if issues:
                    print(f"\n⚠️ [Monitor] Detected {len(issues)} issues:")
                    for issue in issues:
                        print(f"  - {issue['severity']}: {issue['description']}")
                    
                    # Attempt to handle
                    for issue in issues:
                        await self._handle_issue(issue)
                
                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"❌ [Monitor] Error in monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_all_platforms(self):
        """Check health of all configured platforms"""
        # Note: This will check platforms that are configured
        # For now, just logging - actual health checks to be implemented
        pass
    
    async def _detect_issues(self) -> List[Dict[str, Any]]:
        """
        Detect problems in current state
        Returns list of issues with severity
        """
        issues = []
        
        # Check for VMs with unknown status
        for vm_id, vm in self.state.vms.items():
            if vm.status == VMStatus.UNKNOWN:
                issues.append({
                    'type': 'vm_unknown_status',
                    'severity': 'warning',
                    'description': f"VM {vm_id} ({vm.name}) has unknown status",
                    'vm_id': vm_id
                })
        
        # Check for deploying VMs stuck too long
        # TODO: Add timestamp checks
        
        # Check for hosts with degraded status
        for host_key, host in self.state.hosts.items():
            if host.status == HostStatus.DEGRADED:
                issues.append({
                    'type': 'host_degraded',
                    'severity': 'warning',
                    'description': f"Host {host.platform}:{host.identifier} is degraded",
                    'host_key': host_key
                })
            elif host.status == HostStatus.DOWN:
                issues.append({
                    'type': 'host_down',
                    'severity': 'critical',
                    'description': f"Host {host.platform}:{host.identifier} is DOWN",
                    'host_key': host_key
                })
        
        return issues
    
    async def _handle_issue(self, issue: Dict[str, Any]):
        """
        Attempt to handle a detected issue
        Consult RAG for similar past issues
        """
        print(f"\n🔧 [Monitor] Attempting to handle: {issue['description']}")
        
        # Consult RAG for similar issues
        rag_context = {
            'error_message': issue['description'],
            'issue_type': issue['type'],
            'severity': issue['severity']
        }
        
        rag_result = self.rag.consult_rag(rag_context)
        
        if rag_result:
            print(f"📚 [Monitor] RAG found similar issue:")
            print(f"  Query: {rag_result['query']}")
            if rag_result['results']:
                print(f"  Best match: {rag_result['results'][0]['content'][:200]}...")
        
        # TODO: Implement actual resolution strategies
        self.stats['issues_detected'] += 1
    
    # ═══════════════════════════════════════════════════
    # LOOP 2: Execution Engine
    # ═══════════════════════════════════════════════════
    
    async def execution_loop(self):
        """
        Process approved requests from queue
        Execute safely with monitoring
        """
        print("⚙️ [Executor] Starting execution loop...")
        
        while self.execution_active:
            try:
                # Get next approved request (waits if queue empty)
                approved_request = await asyncio.wait_for(
                    self.request_queue.get(),
                    timeout=5.0
                )
                
                print(f"\n🚀 [Executor] Executing request: {approved_request['request_id']}")
                
                # Execute the request
                result = await self._execute_request(approved_request)
                
                # Update state
                if result['status'] == 'success':
                    self.stats['requests_completed'] += 1
                    print(f"✅ [Executor] Request completed successfully")
                else:
                    self.stats['requests_failed'] += 1
                    print(f"❌ [Executor] Request failed: {result.get('error')}")
                
                # Update request in state
                self.state.update_request_status(
                    approved_request['request_id'],
                    'completed' if result['status'] == 'success' else 'failed',
                    completed_at=datetime.now().isoformat(),
                    result=result
                )
                
            except asyncio.TimeoutError:
                # No requests in queue, continue
                await asyncio.sleep(1)
            except Exception as e:
                print(f"❌ [Executor] Error in execution loop: {e}")
                await asyncio.sleep(5)
    
    async def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an approved request
        Returns result dict with status
        """
        action = request['action']
        params = request['params']
        
        try:
            # Route to appropriate handler
            if action == 'deploy_vm':
                return await self._execute_deploy_vm(params)
            elif action == 'destroy_vm':
                return await self._execute_destroy_vm(params)
            elif action == 'start_vm':
                return await self._execute_start_vm(params)
            elif action == 'stop_vm':
                return await self._execute_stop_vm(params)
            else:
                return {'status': 'error', 'error': f'Unknown action: {action}'}
                
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    async def _execute_deploy_vm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM deployment"""
        # TODO: Implement actual deployment logic
        # For now, just a placeholder
        return {
            'status': 'success',
            'vm_id': f"vm-{uuid.uuid4().hex[:8]}",
            'message': 'VM deployment placeholder'
        }
    
    async def _execute_destroy_vm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM destruction"""
        vm_id = params['vm_id']
        
        # Remove from state
        self.state.remove_vm(vm_id)
        
        return {
            'status': 'success',
            'vm_id': vm_id,
            'message': 'VM destroyed'
        }
    
    async def _execute_start_vm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM start"""
        return {'status': 'success', 'message': 'VM start placeholder'}
    
    async def _execute_stop_vm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute VM stop"""
        return {'status': 'success', 'message': 'VM stop placeholder'}
    
    # ═══════════════════════════════════════════════════
    # LOOP 3: State Synchronization
    # ═══════════════════════════════════════════════════
    
    async def state_sync_loop(self):
        """
        Periodically sync state with actual infrastructure
        Discover new VMs, update statuses, etc.
        """
        print("🔄 [StateSync] Starting state synchronization loop...")
        
        while True:
            try:
                # Sync every 60 seconds
                await asyncio.sleep(60)
                
                # TODO: Implement actual state discovery
                # For now, just log
                # print("[StateSync] State sync (placeholder)")
                
            except Exception as e:
                print(f"❌ [StateSync] Error in state sync loop: {e}")
                await asyncio.sleep(120)
    
    # ═══════════════════════════════════════════════════
    # LOOP 4: Self Health Check
    # ═══════════════════════════════════════════════════
    
    async def health_check_loop(self):
        """
        Monitor Overseer's own health
        Check memory, CPU, responsiveness
        """
        print("💚 [Health] Starting health check loop...")
        
        while True:
            try:
                # Check every 5 minutes
                await asyncio.sleep(300)
                
                # Simple health report
                summary = self.state.get_summary()
                print(f"\n💚 [Health] Overseer Status:")
                print(f"  VMs: {summary['running_vms']}/{summary['total_vms']} running")
                print(f"  Hosts: {summary['healthy_hosts']}/{summary['total_hosts']} healthy")
                print(f"  Queue: {summary['pending_requests']} pending, {summary['approved_requests']} approved")
                print(f"  Stats: {self.stats['requests_completed']} completed, {self.stats['requests_failed']} failed")
                
            except Exception as e:
                print(f"❌ [Health] Error in health check loop: {e}")
                await asyncio.sleep(300)
    
    # ═══════════════════════════════════════════════════
    # REQUEST GATING (Safety Layer)
    # ═══════════════════════════════════════════════════
    
    async def receive_request(self, action: str, params: Dict[str, Any], user: str = "unknown") -> Dict[str, Any]:
        """
        Someone wants to do something
        I decide if it's safe
        
        Returns:
        {
            'approved': bool,
            'request_id': str (if approved),
            'reason': str (if denied),
            'queue_position': int (if approved)
        }
        """
        request_id = f"req-{uuid.uuid4().hex[:8]}"
        self.stats['requests_received'] += 1
        
        print(f"\n📥 [Gate] Received request: {action} from {user}")
        
        # Create request object
        request = PendingRequest(
            request_id=request_id,
            action=action,
            user=user,
            params=params,
            status='pending',
            submitted_at=datetime.now().isoformat()
        )
        self.state.add_request(request)
        
        # 1. Validate request format
        if not self._is_valid_request(action, params):
            return await self._deny_request(request_id, "Invalid request format")
        
        # 2. Safety checks
        safety_check = await self._safety_check(action, params)
        if not safety_check['safe']:
            return await self._deny_request(request_id, safety_check['reason'])
        
        # 3. Resource validation
        if action == 'deploy_vm':
            if not self._check_resources(params):
                return await self._deny_request(request_id, "Insufficient resources")
        
        # 4. Production protection
        if action in ['destroy_vm', 'stop_vm']:
            vm_id = params.get('vm_id')
            if vm_id and self.state.is_production(vm_id):
                if not params.get('force_production'):
                    return await self._deny_request(
                        request_id,
                        f"VM {vm_id} is production. Add --force-production to confirm."
                    )
        
        # 5. Consult RAG - have we seen this fail before?
        rag_context = {
            'user_message': f"Action: {action}, Params: {params}",
            'task': action
        }
        rag_result = self.rag.consult_rag(rag_context)
        
        if rag_result and 'priority' in rag_result and rag_result['priority'] == 'high':
            # RAG flagged this as problematic
            print(f"📚 [Gate] RAG warning: {rag_result['reason']}")
            print(f"  Context: {rag_result['results'][0]['content'][:150] if rag_result['results'] else 'N/A'}...")
            
            # For now, just warn but still approve
            # In production, might require explicit confirmation
        
        # APPROVED - add to execution queue
        return await self._approve_request(request_id)
    
    async def _deny_request(self, request_id: str, reason: str) -> Dict[str, Any]:
        """Deny a request"""
        self.state.update_request_status(
            request_id,
            'denied',
            denial_reason=reason
        )
        self.stats['requests_denied'] += 1
        print(f"❌ [Gate] DENIED: {reason}")
        return {
            'approved': False,
            'request_id': request_id,
            'reason': reason
        }
    
    async def _approve_request(self, request_id: str) -> Dict[str, Any]:
        """Approve a request and queue for execution"""
        self.state.update_request_status(
            request_id,
            'approved',
            approved_at=datetime.now().isoformat()
        )
        
        # Get the request and add to execution queue
        request = self.state.requests[request_id]
        await self.request_queue.put({
            'request_id': request_id,
            'action': request.action,
            'params': request.params,
            'user': request.user
        })
        
        self.stats['requests_approved'] += 1
        queue_size = self.request_queue.qsize()
        print(f"✅ [Gate] APPROVED - Queue position: {queue_size}")
        
        return {
            'approved': True,
            'request_id': request_id,
            'queue_position': queue_size
        }
    
    def _is_valid_request(self, action: str, params: Dict[str, Any]) -> bool:
        """Validate request format"""
        valid_actions = ['deploy_vm', 'destroy_vm', 'start_vm', 'stop_vm']
        return action in valid_actions
    
    async def _safety_check(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform safety checks on request
        Can prevent dangerous operations
        """
        # Example: Don't allow destroying all VMs at once
        if action == 'destroy_vm' and params.get('all'):
            return {
                'safe': False,
                'reason': "Mass VM destruction not allowed. Destroy VMs individually."
            }
        
        # Example: Don't allow deploying 100 VMs at once
        if action == 'deploy_vm' and params.get('count', 1) > 20:
            return {
                'safe': False,
                'reason': "Cannot deploy more than 20 VMs at once."
            }
        
        return {'safe': True}
    
    def _check_resources(self, params: Dict[str, Any]) -> bool:
        """Check if resources are available"""
        # TODO: Implement actual resource checking
        return True
    
    # ═══════════════════════════════════════════════════
    # Status & Control
    # ═══════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Get current Overseer status"""
        return {
            'monitoring_active': self.monitoring_active,
            'execution_active': self.execution_active,
            'state': self.state.get_summary(),
            'stats': self.stats,
            'queue_size': self.request_queue.qsize()
        }
    
    def shutdown(self):
        """Graceful shutdown"""
        print("\n🛑 Shutting down Overseer...")
        self.monitoring_active = False
        self.execution_active = False
        
        # Stop all Reaper missions
        for mission_id, engine in self.reaper_missions.items():
            print(f"  Stopping Reaper mission: {mission_id}")
            engine.stop()
        
        self.state.save()
    
    # ═══════════════════════════════════════════════════
    # Reaper Mission Management
    # ═══════════════════════════════════════════════════
    
    def create_reaper_mission(
        self,
        mission_id: str,
        lab_id: str,
        mission_type: str,
        target_vms: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Create a Reaper vulnerability injection mission
        
        Args:
            mission_id: Unique mission identifier
            lab_id: Lab deployment ID (from LabOrchestrator)
            mission_type: Mission type (e.g., "web-security-lab")
            target_vms: List of VMs to target [{"host_id": str, "os": str, "ip_address": str}]
            
        Returns:
            Mission creation result
        """
        print(f"\n[Overseer] Creating Reaper mission: {mission_id}")
        print(f"  Lab ID: {lab_id}")
        print(f"  Type: {mission_type}")
        print(f"  Targets: {len(target_vms)} VMs")
        
        # Validate mission doesn't already exist
        if mission_id in self.reaper_missions:
            return {
                "success": False,
                "error": f"Mission {mission_id} already exists"
            }
        
        # Create host states
        hosts = {}
        for vm in target_vms:
            hosts[vm["host_id"]] = ReaperHostState(
                host_id=vm["host_id"],
                os=vm["os"],
                ip_address=vm.get("ip_address")
            )
        
        # Create mission state
        initial_state = MissionState(
            mission_id=mission_id,
            lab_id=lab_id,
            mission_type=mission_type,
            hosts=hosts
        )
        
        # Create mission engine
        engine = MissionEngine(
            mission_id,
            self.reaper_mission_store,
            self.reaper_task_queue,
            self.reaper_event_bus,
            self.reaper_planner
        )
        
        # Store engine
        self.reaper_missions[mission_id] = engine
        
        # Start mission
        engine.start_mission(initial_state)
        
        # Start event loop in background
        engine.start_event_loop_background()
        
        print(f"✅ [Overseer] Reaper mission {mission_id} started")
        
        return {
            "success": True,
            "mission_id": mission_id,
            "lab_id": lab_id,
            "status": "running",
            "target_hosts": len(hosts)
        }
    
    def get_reaper_mission_status(self, mission_id: str) -> Dict[str, Any]:
        """
        Get status of a Reaper mission
        
        Args:
            mission_id: Mission ID
            
        Returns:
            Mission status
        """
        if mission_id not in self.reaper_missions:
            return {"error": f"Mission {mission_id} not found"}
        
        engine = self.reaper_missions[mission_id]
        return engine.get_status()
    
    def get_reaper_mission_detailed_status(self, mission_id: str) -> Dict[str, Any]:
        """
        Get detailed status of a Reaper mission including host states
        
        Args:
            mission_id: Mission ID
            
        Returns:
            Detailed mission status
        """
        if mission_id not in self.reaper_missions:
            return {"error": f"Mission {mission_id} not found"}
        
        engine = self.reaper_missions[mission_id]
        return engine.get_detailed_status()
    
    def list_reaper_missions(self) -> List[Dict[str, Any]]:
        """
        List all Reaper missions
        
        Returns:
            List of mission summaries
        """
        missions = []
        for mission_id, engine in self.reaper_missions.items():
            status = engine.get_status()
            missions.append(status)
        return missions
    
    def cancel_reaper_mission(self, mission_id: str) -> Dict[str, Any]:
        """
        Cancel a running Reaper mission
        
        Args:
            mission_id: Mission ID
            
        Returns:
            Cancellation result
        """
        if mission_id not in self.reaper_missions:
            return {
                "success": False,
                "error": f"Mission {mission_id} not found"
            }
        
        engine = self.reaper_missions[mission_id]
        engine.stop()
        
        # Update mission status
        mission = self.reaper_mission_store.load(mission_id)
        if mission:
            mission.status = "cancelled"
            self.reaper_mission_store.save(mission)
        
        # Remove from active missions
        del self.reaper_missions[mission_id]
        
        print(f"✅ [Overseer] Reaper mission {mission_id} cancelled")
        
        return {
            "success": True,
            "mission_id": mission_id,
            "status": "cancelled"
        }


if __name__ == "__main__":
    # Test the entity
    async def test_overseer():
        overseer = OverseerEntity()
        
        # Submit a test request
        result = await overseer.receive_request(
            action='deploy_vm',
            params={'platform': 'proxmox', 'os': 'ubuntu'},
            user='test-user'
        )
        print(f"\nRequest result: {result}")
        
        # Run for 10 seconds
        try:
            await asyncio.wait_for(overseer.run(), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n✅ Test completed")
        finally:
            overseer.shutdown()
    
    asyncio.run(test_overseer())

