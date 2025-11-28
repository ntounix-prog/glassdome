"""
Overseer module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from glassdome.agents.base import DeploymentAgent, AgentStatus, AgentType
from glassdome.platforms.proxmox_client import ProxmoxClient
from glassdome.agents.guest_agent_fixer import GuestAgentFixer

logger = logging.getLogger(__name__)


class OverseerAgent(DeploymentAgent):
    """
    Overseer Agent - Watches over all deployed infrastructure
    
    Monitors:
    - VM health (running, stopped, crashed)
    - Resource usage (CPU, RAM, disk)
    - Network connectivity
    - Service availability
    - Template availability
    - Storage capacity
    
    Actions:
    - Alert on issues
    - Auto-restart failed VMs
    - Collect metrics
    - Generate reports
    - Enforce policies
    """
    
    def __init__(self, agent_id: str, proxmox_client: ProxmoxClient):
        """
        Initialize Overseer Agent
        
        Args:
            agent_id: Unique agent identifier
            proxmox_client: Proxmox client for infrastructure access
        """
        super().__init__(agent_id, proxmox_client)
        self.proxmox = proxmox_client
        self.guest_agent_fixer = GuestAgentFixer(proxmox_client)
        self.inventory: Dict[str, Any] = {}
        self.metrics: List[Dict[str, Any]] = []
        self.alerts: List[Dict[str, Any]] = []
        self.last_check: Optional[datetime] = None
        
        # Monitoring configuration
        self.check_interval = 60  # seconds
        self.alert_threshold = {
            "cpu_percent": 90,
            "memory_percent": 90,
            "disk_percent": 85,
            "uptime_min": 60  # Alert if VM was restarted recently
        }
        
        logger.info(f"Overseer Agent {agent_id} initialized")
    
    async def start_monitoring(self, nodes: List[str], interval: int = 60):
        """
        Start continuous monitoring loop
        
        Args:
            nodes: List of Proxmox nodes to monitor
            interval: Check interval in seconds
        """
        logger.info(f"Overseer starting monitoring (interval: {interval}s)")
        self.check_interval = interval
        
        while True:
            try:
                for node in nodes:
                    await self.check_node(node)
                
                self.last_check = datetime.now()
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)
    
    async def check_node(self, node: str) -> Dict[str, Any]:
        """
        Check all VMs on a node
        
        Args:
            node: Node name
            
        Returns:
            Node health report
        """
        logger.info(f"Checking node: {node}")
        
        # Get all VMs
        vms = await self.proxmox.list_vms(node)
        
        report = {
            "node": node,
            "timestamp": datetime.now().isoformat(),
            "total_vms": len(vms),
            "running": 0,
            "stopped": 0,
            "issues": [],
            "vms": []
        }
        
        for vm in vms:
            vm_status = await self.check_vm(node, vm["vmid"])
            report["vms"].append(vm_status)
            
            if vm_status["status"] == "running":
                report["running"] += 1
            else:
                report["stopped"] += 1
            
            # Check for issues
            if vm_status.get("issues"):
                report["issues"].extend(vm_status["issues"])
        
        # Update inventory
        self.inventory[node] = report
        
        # Generate alerts if needed
        if report["issues"]:
            await self.generate_alerts(node, report["issues"])
        
        return report
    
    async def check_vm(self, node: str, vmid: int) -> Dict[str, Any]:
        """
        Check individual VM health
        
        Args:
            node: Node name
            vmid: VM ID
            
        Returns:
            VM health status
        """
        status_result = await self.proxmox.get_vm_status(node, vmid)
        
        if not status_result.get("success"):
            return {
                "vmid": vmid,
                "status": "unknown",
                "error": status_result.get("error"),
                "issues": [f"Cannot get status for VM {vmid}"]
            }
        
        vm_status = status_result["status"]
        
        vm_report = {
            "vmid": vmid,
            "name": vm_status.get("name", f"vm-{vmid}"),
            "status": vm_status.get("status", "unknown"),
            "uptime": vm_status.get("uptime", 0),
            "cpus": vm_status.get("cpus", 0),
            "memory_mb": vm_status.get("mem", 0) // (1024 * 1024) if vm_status.get("mem") else 0,
            "memory_max_mb": vm_status.get("maxmem", 0) // (1024 * 1024) if vm_status.get("maxmem") else 0,
            "disk_read": vm_status.get("diskread", 0),
            "disk_write": vm_status.get("diskwrite", 0),
            "network_in": vm_status.get("netin", 0),
            "network_out": vm_status.get("netout", 0),
            "issues": [],
            "checked_at": datetime.now().isoformat()
        }
        
        # Calculate resource usage percentages
        if vm_report["memory_max_mb"] > 0:
            vm_report["memory_percent"] = (vm_report["memory_mb"] / vm_report["memory_max_mb"]) * 100
        else:
            vm_report["memory_percent"] = 0
        
        # Check for issues
        issues = self._check_vm_issues(vm_report)
        vm_report["issues"] = issues
        
        # Try to get IP address
        if vm_status.get("status") == "running":
            ip = await self.proxmox.get_vm_ip(node, vmid, timeout=10)
            vm_report["ip_address"] = ip
            
            if not ip and vm_report["uptime"] > 300:
                # VM running >5 minutes but no IP
                vm_report["issues"].append("No IP address after 5 minutes uptime")
        
        return vm_report
    
    def _check_vm_issues(self, vm_report: Dict[str, Any]) -> List[str]:
        """
        Check for VM issues based on thresholds
        
        Args:
            vm_report: VM status report
            
        Returns:
            List of issues found
        """
        issues = []
        
        # Status checks
        if vm_report["status"] == "stopped":
            issues.append("VM is stopped (expected to be running?)")
        elif vm_report["status"] not in ["running", "stopped"]:
            issues.append(f"VM in unexpected state: {vm_report['status']}")
        
        # Resource checks
        if vm_report.get("memory_percent", 0) > self.alert_threshold["memory_percent"]:
            issues.append(f"High memory usage: {vm_report['memory_percent']:.1f}%")
        
        # Uptime checks
        if vm_report["uptime"] < self.alert_threshold["uptime_min"] and vm_report["status"] == "running":
            issues.append(f"VM recently restarted (uptime: {vm_report['uptime']}s)")
        
        return issues
    
    async def generate_alerts(self, node: str, issues: List[str]):
        """
        Generate alerts for detected issues
        
        Args:
            node: Node name
            issues: List of issues
        """
        for issue in issues:
            alert = {
                "timestamp": datetime.now().isoformat(),
                "node": node,
                "severity": self._get_severity(issue),
                "message": issue,
                "acknowledged": False
            }
            
            self.alerts.append(alert)
            logger.warning(f"ALERT [{node}]: {issue}")
            
            # TODO: Send to notification system
            # - Email
            # - Slack
            # - PagerDuty
            # - WebSocket to frontend
    
    def _get_severity(self, issue: str) -> str:
        """Determine alert severity"""
        if "crashed" in issue.lower() or "failed" in issue.lower():
            return "critical"
        elif "high" in issue.lower() or "stopped" in issue.lower():
            return "warning"
        else:
            return "info"
    
    async def _deploy_element(self, element_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Overseer doesn't deploy - this is a stub to satisfy abstract method
        
        Args:
            element_type: Element type
            config: Configuration
            
        Returns:
            Error - overseer doesn't deploy
        """
        return {
            "success": False,
            "error": "Overseer Agent does not deploy elements - use deployment agents instead"
        }
    
    async def get_inventory(self) -> Dict[str, Any]:
        """
        Get current infrastructure inventory
        
        Returns:
            Complete inventory
        """
        return {
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "nodes": self.inventory,
            "total_vms": sum(node["total_vms"] for node in self.inventory.values()),
            "running_vms": sum(node["running"] for node in self.inventory.values()),
            "stopped_vms": sum(node["stopped"] for node in self.inventory.values()),
            "total_issues": len(self.alerts),
            "unacknowledged_alerts": len([a for a in self.alerts if not a["acknowledged"]])
        }
    
    async def get_vm_history(self, node: str, vmid: int, hours: int = 24) -> List[Dict[str, Any]]:
        """
        Get VM history over time period
        
        Args:
            node: Node name
            vmid: VM ID
            hours: Hours of history
            
        Returns:
            Historical metrics
        """
        # TODO: Implement time-series storage
        # For now, return recent metrics from memory
        cutoff = datetime.now() - timedelta(hours=hours)
        
        history = [
            m for m in self.metrics
            if m.get("vmid") == vmid and 
            datetime.fromisoformat(m["timestamp"]) > cutoff
        ]
        
        return history
    
    async def auto_remediate(self, node: str, vmid: int, issue: str) -> Dict[str, Any]:
        """
        Attempt automatic remediation
        
        Args:
            node: Node name
            vmid: VM ID
            issue: Issue description
            
        Returns:
            Remediation result
        """
        logger.info(f"Attempting auto-remediation for VM {vmid}: {issue}")
        
        # Stopped VM - try to start
        if "stopped" in issue.lower():
            logger.info(f"Starting stopped VM {vmid}")
            result = await self.proxmox.start_vm(node, vmid)
            
            if result.get("success"):
                return {
                    "success": True,
                    "action": "started_vm",
                    "vmid": vmid,
                    "message": f"VM {vmid} started successfully"
                }
        
        # High memory - could restart services, scale resources, etc.
        # Not implemented yet
        
        return {
            "success": False,
            "action": "none",
            "message": "No auto-remediation available for this issue"
        }
    
    async def generate_report(self, node: Optional[str] = None) -> str:
        """
        Generate infrastructure health report
        
        Args:
            node: Specific node, or None for all
            
        Returns:
            Formatted report
        """
        inventory = await self.get_inventory()
        
        report = []
        report.append("=" * 70)
        report.append("INFRASTRUCTURE HEALTH REPORT")
        report.append("=" * 70)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append(f"Last Check: {inventory['last_check']}")
        report.append("")
        
        report.append(f"Total VMs: {inventory['total_vms']}")
        report.append(f"  Running: {inventory['running_vms']}")
        report.append(f"  Stopped: {inventory['stopped_vms']}")
        report.append(f"  Issues: {inventory['total_issues']}")
        report.append("")
        
        # Per-node details
        for node_name, node_data in self.inventory.items():
            if node and node_name != node:
                continue
            
            report.append(f"Node: {node_name}")
            report.append("-" * 70)
            report.append(f"  VMs: {node_data['total_vms']} (Running: {node_data['running']}, Stopped: {node_data['stopped']})")
            
            if node_data["issues"]:
                report.append(f"  Issues: {len(node_data['issues'])}")
                for issue in node_data["issues"][:5]:
                    report.append(f"    - {issue}")
            else:
                report.append("  ✅ No issues")
            
            report.append("")
        
        # Recent alerts
        if self.alerts:
            report.append("Recent Alerts:")
            report.append("-" * 70)
            for alert in self.alerts[-10:]:
                ack = "✓" if alert["acknowledged"] else " "
                report.append(f"[{ack}] [{alert['severity'].upper()}] {alert['message']}")
            report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)
    
    async def validate(self, task: Dict[str, Any]) -> bool:
        """Validate monitoring task"""
        return task.get("task_type") == "monitor"
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute monitoring task
        
        Args:
            task: Task definition
            
        Returns:
            Execution result
        """
        task_type = task.get("task_type")
        
        if task_type == "monitor":
            nodes = task.get("nodes", ["pve01"])
            report = {}
            
            for node in nodes:
                report[node] = await self.check_node(node)
            
            return {
                "success": True,
                "agent_id": self.agent_id,
                "task_type": "monitor",
                "report": report
            }
        
        elif task_type == "remediate":
            node = task.get("node")
            vmid = task.get("vmid")
            issue = task.get("issue")
            
            result = await self.auto_remediate(node, vmid, issue)
            return {
                "success": result["success"],
                "agent_id": self.agent_id,
                "task_type": "remediate",
                **result
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown task type: {task_type}"
            }

