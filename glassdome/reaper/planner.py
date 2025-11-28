"""
Planner module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import uuid
import logging

from glassdome.reaper.models import MissionState, Task, ResultEvent

logger = logging.getLogger(__name__)


class MissionPlanner(ABC):
    """Abstract base class for mission planning strategies"""
    
    @abstractmethod
    def initial_tasks(self, state: MissionState) -> List[Task]:
        """
        Return initial tasks for mission start
        
        Args:
            state: Current mission state
            
        Returns:
            List of tasks to execute
        """
        pass
    
    @abstractmethod
    def next_tasks(
        self, 
        state: MissionState, 
        last_result: Optional[ResultEvent] = None
    ) -> List[Task]:
        """
        Decide next tasks based on current state and last result
        
        Args:
            state: Current mission state
            last_result: Most recent task result (optional)
            
        Returns:
            List of tasks to execute next
        """
        pass


class VulnerabilityPlanner(MissionPlanner):
    """
    Rule-based planner for vulnerability injection
    
    Strategy:
    1. Discovery phase: Gather facts about each VM
    2. Baseline phase: Inject standard training vulnerabilities
    3. Specialized phase: Inject OS/service-specific vulnerabilities
    
    Rules:
    - After discovery succeeds → inject baseline vulnerabilities
    - If web server detected → inject SQLi/XSS
    - If SSH detected → inject weak credentials
    - If locked host → skip it
    """
    
    def __init__(self, playbook_mapping: Optional[dict] = None):
        """
        Initialize vulnerability planner
        
        Args:
            playbook_mapping: Optional mapping of vulnerability types to playbooks
        """
        self.playbook_mapping = playbook_mapping or self._default_playbook_mapping()
        logger.info("VulnerabilityPlanner initialized")
    
    def _default_playbook_mapping(self) -> dict:
        """Default mapping of vulnerability types to Ansible playbooks"""
        return {
            "baseline_linux": [
                {"playbook": "system/weak_ssh.yml", "name": "weak_ssh"},
                {"playbook": "system/weak_sudo.yml", "name": "weak_sudo"},
            ],
            "baseline_windows": [
                {"playbook": "system/weak_rdp.yml", "name": "weak_rdp"},
                {"playbook": "system/unpatched_smb.yml", "name": "unpatched_smb"},
            ],
            "web_linux": [
                {"playbook": "web/inject_sqli.yml", "name": "sqli"},
                {"playbook": "web/inject_xss.yml", "name": "xss"},
            ],
            "network_linux": [
                {"playbook": "network/open_ports.yml", "name": "open_ports"},
                {"playbook": "network/weak_firewall.yml", "name": "weak_firewall"},
            ],
        }
    
    def initial_tasks(self, state: MissionState) -> List[Task]:
        """
        Create discovery tasks for all hosts
        
        Args:
            state: Current mission state
            
        Returns:
            List of discovery tasks
        """
        tasks = []
        for host_id, host in state.hosts.items():
            if host.locked:
                logger.info(f"Skipping locked host {host_id}")
                continue
            
            agent_type = self._os_to_agent_type(host.os)
            task = Task(
                task_id=f"t-{uuid.uuid4().hex[:8]}",
                mission_id=state.mission_id,
                host_id=host_id,
                agent_type=agent_type,
                action=f"{host.os}.discover",
                params={"ip_address": host.ip_address}
            )
            tasks.append(task)
            logger.info(f"Created discovery task for {host_id} ({host.os})")
        
        return tasks
    
    def next_tasks(
        self, 
        state: MissionState, 
        last_result: Optional[ResultEvent] = None
    ) -> List[Task]:
        """
        Decide next tasks based on rules
        
        Args:
            state: Current mission state
            last_result: Most recent task result
            
        Returns:
            List of tasks to execute next
        """
        if not last_result:
            return []
        
        host = state.hosts.get(last_result.host_id)
        if not host or host.locked:
            logger.info(f"Skipping next tasks for {last_result.host_id} (locked or not found)")
            return []
        
        tasks = []
        
        # Rule 1: After successful discovery → inject baseline vulnerabilities
        if last_result.action.endswith(".discover") and last_result.status == "success":
            tasks.extend(self._plan_baseline_vulnerabilities(state, host, last_result))
        
        # Rule 2: After baseline → inject specialized vulnerabilities based on facts
        elif last_result.action.endswith(".baseline") and last_result.status == "success":
            tasks.extend(self._plan_specialized_vulnerabilities(state, host, last_result))
        
        # Rule 3: If injection failed but retriable → retry with different parameters
        elif last_result.status == "error" and last_result.retriable:
            tasks.extend(self._plan_retry(state, host, last_result))
        
        return tasks
    
    def _plan_baseline_vulnerabilities(
        self, 
        state: MissionState, 
        host, 
        last_result: ResultEvent
    ) -> List[Task]:
        """
        Plan baseline vulnerability injection tasks
        
        Args:
            state: Mission state
            host: Host state
            last_result: Discovery result
            
        Returns:
            List of baseline vulnerability tasks
        """
        tasks = []
        agent_type = self._os_to_agent_type(host.os)
        
        # Get baseline playbooks for this OS
        baseline_key = f"baseline_{host.os}"
        if baseline_key not in self.playbook_mapping:
            logger.warning(f"No baseline playbooks for {host.os}")
            return tasks
        
        # Create a single task to inject all baseline vulnerabilities
        task = Task(
            task_id=f"t-{uuid.uuid4().hex[:8]}",
            mission_id=state.mission_id,
            host_id=host.host_id,
            agent_type=agent_type,
            action=f"{host.os}.baseline",
            params={
                "playbooks": self.playbook_mapping[baseline_key],
                "ip_address": host.ip_address
            }
        )
        tasks.append(task)
        logger.info(f"Planned baseline vulnerability injection for {host.host_id}")
        
        return tasks
    
    def _plan_specialized_vulnerabilities(
        self, 
        state: MissionState, 
        host, 
        last_result: ResultEvent
    ) -> List[Task]:
        """
        Plan specialized vulnerability injection based on discovered services
        
        Args:
            state: Mission state
            host: Host state
            last_result: Baseline result
            
        Returns:
            List of specialized vulnerability tasks
        """
        tasks = []
        agent_type = self._os_to_agent_type(host.os)
        
        # Check discovered facts for services
        facts = host.facts
        
        # If web server detected → inject web vulnerabilities
        if self._has_web_server(facts):
            web_key = f"web_{host.os}"
            if web_key in self.playbook_mapping:
                task = Task(
                    task_id=f"t-{uuid.uuid4().hex[:8]}",
                    mission_id=state.mission_id,
                    host_id=host.host_id,
                    agent_type=agent_type,
                    action=f"{host.os}.inject_vuln",
                    params={
                        "playbooks": self.playbook_mapping[web_key],
                        "category": "web",
                        "ip_address": host.ip_address
                    }
                )
                tasks.append(task)
                logger.info(f"Planned web vulnerability injection for {host.host_id}")
        
        # If network services detected → inject network vulnerabilities
        if self._has_network_services(facts):
            network_key = f"network_{host.os}"
            if network_key in self.playbook_mapping:
                task = Task(
                    task_id=f"t-{uuid.uuid4().hex[:8]}",
                    mission_id=state.mission_id,
                    host_id=host.host_id,
                    agent_type=agent_type,
                    action=f"{host.os}.inject_vuln",
                    params={
                        "playbooks": self.playbook_mapping[network_key],
                        "category": "network",
                        "ip_address": host.ip_address
                    }
                )
                tasks.append(task)
                logger.info(f"Planned network vulnerability injection for {host.host_id}")
        
        return tasks
    
    def _plan_retry(
        self, 
        state: MissionState, 
        host, 
        last_result: ResultEvent
    ) -> List[Task]:
        """
        Plan retry for failed but retriable tasks
        
        Args:
            state: Mission state
            host: Host state
            last_result: Failed result
            
        Returns:
            List of retry tasks
        """
        # For now, don't auto-retry (avoid infinite loops)
        # In production, would implement exponential backoff and max retries
        logger.info(f"Task {last_result.task_id} failed but retriable (not auto-retrying)")
        return []
    
    def _os_to_agent_type(self, os: str) -> str:
        """Convert OS to agent type"""
        return f"reaper-{os}"
    
    def _has_web_server(self, facts: dict) -> bool:
        """Check if facts indicate a web server is present"""
        if not facts:
            return False
        
        # Check for common web server indicators
        ports = facts.get("open_ports", [])
        services = facts.get("services", [])
        
        web_ports = {80, 443, 8080, 8443}
        web_services = {"apache", "nginx", "httpd", "tomcat", "iis"}
        
        has_web_port = any(p in web_ports for p in ports)
        has_web_service = any(s in services for s in web_services)
        
        return has_web_port or has_web_service
    
    def _has_network_services(self, facts: dict) -> bool:
        """Check if facts indicate network services are present"""
        if not facts:
            return False
        
        # Check for common network services
        ports = facts.get("open_ports", [])
        services = facts.get("services", [])
        
        network_ports = {21, 22, 23, 25, 53, 110, 143, 445, 3389}
        network_services = {"ssh", "ftp", "telnet", "smb", "dns", "smtp"}
        
        has_network_port = any(p in network_ports for p in ports)
        has_network_service = any(s in services for s in network_services)
        
        return has_network_port or has_network_service

