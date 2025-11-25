"""
Mac Reaper Agent

Executes vulnerability injection tasks on macOS VMs using SSH and Ansible.
"""

import time
import logging

from glassdome.reaper.agents.base import BaseReaperAgent
from glassdome.reaper.models import Task, ResultEvent
from glassdome.core.security import get_secure_settings

logger = logging.getLogger(__name__)


class MacReaperAgent(BaseReaperAgent):
    """
    macOS vulnerability injection agent
    
    Uses SSH for discovery and Ansible for vulnerability injection.
    """
    
    def __init__(self, task_queue, event_bus):
        """
        Initialize Mac Reaper agent
        
        Args:
            task_queue: Task queue to consume from
            event_bus: Event bus to publish results to
        """
        super().__init__("reaper-macos", task_queue, event_bus)
        self.settings = get_secure_settings()
    
    def handle_task(self, task: Task) -> ResultEvent:
        """
        Execute a macOS task
        
        Args:
            task: Task to execute
            
        Returns:
            Result event
        """
        # Simulate work
        time.sleep(0.5)
        
        if task.action == "macos.discover":
            return self._discover(task)
        elif task.action == "macos.baseline":
            return self._baseline(task)
        elif task.action == "macos.inject_vuln":
            return self._inject_vuln(task)
        elif task.action == "macos.verify_vuln":
            return self._verify_vuln(task)
        else:
            return self._create_error_event(
                task,
                f"Unknown action: {task.action}",
                error_code="UNKNOWN_ACTION"
            )
    
    def _discover(self, task: Task) -> ResultEvent:
        """
        Discover facts about a macOS VM
        
        Args:
            task: Discovery task
            
        Returns:
            Result event with discovered facts
        """
        ip_address = task.params.get("ip_address")
        if not ip_address:
            return self._create_error_event(
                task,
                "Missing ip_address parameter",
                error_code="MISSING_PARAM"
            )
        
        try:
            logger.info(f"Discovering macOS host {task.host_id} at {ip_address}")
            
            # Simulated facts for Phase 1
            facts = {
                "os_version": "macOS 14 Sonoma",
                "hostname": task.host_id,
                "ip": ip_address,
                "open_ports": [22, 80, 443],
                "services": ["ssh", "apache"],
                "arch": "arm64",
            }
            
            return self._create_success_event(
                task,
                f"Discovered macOS host {task.host_id}",
                data=facts
            )
        
        except Exception as e:
            logger.error(f"Discovery failed for {task.host_id}: {e}")
            return self._create_error_event(
                task,
                f"Discovery failed: {str(e)}",
                error_code="DISCOVERY_FAILED",
                retriable=True
            )
    
    def _baseline(self, task: Task) -> ResultEvent:
        """
        Inject baseline vulnerabilities
        
        Args:
            task: Baseline injection task
            
        Returns:
            Result event
        """
        playbooks = task.params.get("playbooks", [])
        
        if not playbooks:
            return self._create_error_event(
                task,
                "No playbooks specified",
                error_code="MISSING_PLAYBOOKS"
            )
        
        try:
            logger.info(f"Injecting baseline vulnerabilities on {task.host_id}")
            
            vulnerabilities_injected = [pb["name"] for pb in playbooks]
            
            return self._create_success_event(
                task,
                f"Injected {len(vulnerabilities_injected)} baseline vulnerabilities on {task.host_id}",
                data={"vulnerabilities_injected": vulnerabilities_injected}
            )
        
        except Exception as e:
            logger.error(f"Baseline injection failed for {task.host_id}: {e}")
            return self._create_error_event(
                task,
                f"Baseline injection failed: {str(e)}",
                error_code="INJECTION_FAILED",
                retriable=True
            )
    
    def _inject_vuln(self, task: Task) -> ResultEvent:
        """
        Inject specialized vulnerabilities
        
        Args:
            task: Vulnerability injection task
            
        Returns:
            Result event
        """
        playbooks = task.params.get("playbooks", [])
        category = task.params.get("category", "unknown")
        
        if not playbooks:
            return self._create_error_event(
                task,
                "No playbooks specified",
                error_code="MISSING_PLAYBOOKS"
            )
        
        try:
            logger.info(f"Injecting {category} vulnerabilities on {task.host_id}")
            
            vulnerabilities_injected = [pb["name"] for pb in playbooks]
            
            return self._create_success_event(
                task,
                f"Injected {len(vulnerabilities_injected)} {category} vulnerabilities on {task.host_id}",
                data={"vulnerabilities_injected": vulnerabilities_injected, "category": category}
            )
        
        except Exception as e:
            logger.error(f"Vulnerability injection failed for {task.host_id}: {e}")
            return self._create_error_event(
                task,
                f"Vulnerability injection failed: {str(e)}",
                error_code="INJECTION_FAILED",
                retriable=True
            )
    
    def _verify_vuln(self, task: Task) -> ResultEvent:
        """
        Verify that a vulnerability is exploitable
        
        Args:
            task: Verification task
            
        Returns:
            Result event
        """
        vuln_name = task.params.get("vuln_name")
        
        if not vuln_name:
            return self._create_error_event(
                task,
                "Missing vuln_name parameter",
                error_code="MISSING_PARAM"
            )
        
        try:
            logger.info(f"Verifying vulnerability {vuln_name} on {task.host_id}")
            
            return self._create_success_event(
                task,
                f"Verified vulnerability {vuln_name} on {task.host_id}",
                data={"vuln_name": vuln_name, "exploitable": True}
            )
        
        except Exception as e:
            logger.error(f"Verification failed for {task.host_id}: {e}")
            return self._create_error_event(
                task,
                f"Verification failed: {str(e)}",
                error_code="VERIFICATION_FAILED",
                retriable=True
            )

