"""
Linux Agent module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

import asyncio
import time
from pathlib import Path
import logging

from glassdome.reaper.agents.base import BaseReaperAgent
from glassdome.reaper.models import Task, ResultEvent
from glassdome.core.ssh_client import SSHClient
from glassdome.integrations.ansible_executor import AnsibleExecutor
from glassdome.integrations.ansible_bridge import AnsibleBridge
from glassdome.core.security import get_secure_settings

logger = logging.getLogger(__name__)


class LinuxReaperAgent(BaseReaperAgent):
    """
    Linux vulnerability injection agent
    
    Uses SSH for discovery and Ansible for vulnerability injection.
    """
    
    def __init__(self, task_queue, event_bus):
        """
        Initialize Linux Reaper agent
        
        Args:
            task_queue: Task queue to consume from
            event_bus: Event bus to publish results to
        """
        super().__init__("reaper-linux", task_queue, event_bus)
        self.ansible_executor = AnsibleExecutor()
        self.settings = get_secure_settings()
    
    def handle_task(self, task: Task) -> ResultEvent:
        """
        Execute a Linux task
        
        Args:
            task: Task to execute
            
        Returns:
            Result event
        """
        # Simulate work (in production, would actually execute)
        time.sleep(0.5)
        
        if task.action == "linux.discover":
            return self._discover(task)
        elif task.action == "linux.baseline":
            return self._baseline(task)
        elif task.action == "linux.inject_vuln":
            return self._inject_vuln(task)
        elif task.action == "linux.verify_vuln":
            return self._verify_vuln(task)
        else:
            return self._create_error_event(
                task,
                f"Unknown action: {task.action}",
                error_code="UNKNOWN_ACTION"
            )
    
    def _discover(self, task: Task) -> ResultEvent:
        """
        Discover facts about a Linux VM
        
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
            logger.info(f"Discovering Linux host {task.host_id} at {ip_address}")
            
            # Get machine credentials
            cred = self.settings.get_machine_credential(task.host_id)
            if not cred:
                # Try default credentials
                cred = self.settings.get_machine_credential("linux_default")
            
            if not cred:
                return self._create_error_event(
                    task,
                    f"No credentials found for {task.host_id}",
                    error_code="NO_CREDENTIALS",
                    retriable=False
                )
            
            # Connect via SSH and gather facts
            # For now, return simulated facts
            # In production, would use SSHClient to execute commands
            
            facts = {
                "os_version": "Ubuntu 22.04",
                "hostname": task.host_id,
                "ip": ip_address,
                "open_ports": [22, 80, 443],
                "services": ["ssh", "apache", "mysql"],
                "kernel": "5.15.0-generic",
                "uptime": "2 days",
            }
            
            return self._create_success_event(
                task,
                f"Discovered Linux host {task.host_id}",
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
        ip_address = task.params.get("ip_address")
        
        if not playbooks:
            return self._create_error_event(
                task,
                "No playbooks specified",
                error_code="MISSING_PLAYBOOKS"
            )
        
        try:
            logger.info(f"Injecting baseline vulnerabilities on {task.host_id}")
            
            # For Phase 1, simulate Ansible execution
            # In production, would:
            # 1. Create Ansible inventory for this host
            # 2. Execute playbooks via AnsibleExecutor
            # 3. Parse results and return
            
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
        ip_address = task.params.get("ip_address")
        
        if not playbooks:
            return self._create_error_event(
                task,
                "No playbooks specified",
                error_code="MISSING_PLAYBOOKS"
            )
        
        try:
            logger.info(f"Injecting {category} vulnerabilities on {task.host_id}")
            
            # For Phase 1, simulate Ansible execution
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
        ip_address = task.params.get("ip_address")
        
        if not vuln_name:
            return self._create_error_event(
                task,
                "Missing vuln_name parameter",
                error_code="MISSING_PARAM"
            )
        
        try:
            logger.info(f"Verifying vulnerability {vuln_name} on {task.host_id}")
            
            # For Phase 1, simulate verification
            # In production, would execute actual exploit attempts
            
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

