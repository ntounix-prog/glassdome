"""
Ansible Executor module

Author: Brett Turner (ntounix-prog)
Created: November 2024
Copyright (c) 2024 Brett Turner. All rights reserved.
"""
import subprocess
import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

from glassdome.integrations.ansible_bridge import AnsibleBridge

logger = logging.getLogger(__name__)


class AnsibleExecutor:
    """
    Execute Ansible playbooks against Glassdome deployments
    
    This class provides a clean interface for running Ansible playbooks,
    whether they're stored in the Glassdome repository or externally.
    """
    
    def __init__(self, playbook_dir: Optional[str] = None, ansible_cfg_path: Optional[str] = None):
        """
        Initialize Ansible executor
        
        Args:
            playbook_dir: Base directory for playbooks (default: glassdome/vulnerabilities/playbooks)
            ansible_cfg_path: Path to ansible.cfg (optional)
        """
        if playbook_dir:
            self.playbook_dir = Path(playbook_dir)
        else:
            # Default to glassdome's vulnerability playbooks
            self.playbook_dir = Path(__file__).parent.parent / "vulnerabilities" / "playbooks"
        
        self.ansible_cfg_path = ansible_cfg_path
        logger.info(f"Ansible executor initialized with playbook dir: {self.playbook_dir}")
    
    async def run_playbook(
        self,
        playbook_name: str,
        inventory_path: str,
        extra_vars: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        skip_tags: Optional[List[str]] = None,
        limit: Optional[str] = None,
        verbose: int = 0
    ) -> Dict[str, Any]:
        """
        Run an Ansible playbook
        
        Args:
            playbook_name: Name of playbook file (e.g., "web/install_apache.yml")
            inventory_path: Path to Ansible inventory file
            extra_vars: Extra variables to pass to playbook
            tags: Run only tasks tagged with these tags
            skip_tags: Skip tasks tagged with these tags
            limit: Limit playbook execution to specific hosts
            verbose: Verbosity level (0-4, corresponds to -v, -vv, etc.)
        
        Returns:
            Dictionary with execution results:
                - success: bool (True if playbook succeeded)
                - return_code: int (0 = success)
                - stdout: str (command output)
                - stderr: str (error output)
                - stats: dict (parsed task statistics)
                - duration: float (execution time in seconds)
        
        Example:
            executor = AnsibleExecutor()
            result = await executor.run_playbook(
                playbook_name="web/inject_sqli.yml",
                inventory_path="/tmp/inventory.ini",
                extra_vars={"cve_id": "CVE-2023-12345"}
            )
            
            if result["success"]:
                print(f"✓ Tasks: {result['stats']['tasks']}")
            else:
                print(f"✗ Failed: {result['stderr']}")
        """
        # Resolve playbook path
        playbook_path = self.playbook_dir / playbook_name
        
        if not playbook_path.exists():
            raise FileNotFoundError(f"Playbook not found: {playbook_path}")
        
        # Build ansible-playbook command
        cmd = [
            "ansible-playbook",
            str(playbook_path),
            "-i", inventory_path,
        ]
        
        # Add extra vars (convert dict to JSON)
        if extra_vars:
            cmd.extend(["--extra-vars", json.dumps(extra_vars)])
        
        # Add tags
        if tags:
            cmd.extend(["--tags", ",".join(tags)])
        
        # Add skip tags
        if skip_tags:
            cmd.extend(["--skip-tags", ",".join(skip_tags)])
        
        # Add limit
        if limit:
            cmd.extend(["--limit", limit])
        
        # Add verbosity
        if verbose > 0:
            cmd.append("-" + "v" * min(verbose, 4))
        
        # Add ansible.cfg if specified
        env = None
        if self.ansible_cfg_path:
            import os
            env = os.environ.copy()
            env["ANSIBLE_CONFIG"] = self.ansible_cfg_path
        
        logger.info(f"Running Ansible playbook: {playbook_name}")
        logger.debug(f"Command: {' '.join(cmd)}")
        
        # Execute playbook (async)
        start_time = asyncio.get_event_loop().time()
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        stdout, stderr = await process.communicate()
        
        duration = asyncio.get_event_loop().time() - start_time
        
        # Decode output
        stdout_str = stdout.decode('utf-8', errors='replace')
        stderr_str = stderr.decode('utf-8', errors='replace')
        
        # Parse results
        success = process.returncode == 0
        stats = AnsibleBridge.parse_ansible_results(stdout_str)
        
        result = {
            "success": success,
            "return_code": process.returncode,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "stats": stats,
            "duration": duration,
            "playbook": playbook_name
        }
        
        if success:
            logger.info(f"✓ Playbook '{playbook_name}' completed successfully in {duration:.2f}s")
            logger.info(f"  Tasks: {stats['tasks']}")
        else:
            logger.error(f"✗ Playbook '{playbook_name}' failed (return code: {process.returncode})")
            logger.error(f"  Error: {stderr_str[:500]}")  # Log first 500 chars of error
        
        return result
    
    async def run_playbooks(
        self,
        playbooks: List[Dict[str, Any]],
        inventory_path: str,
        stop_on_failure: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Run multiple Ansible playbooks in sequence
        
        Args:
            playbooks: List of playbook configurations:
                - name: Playbook name (required)
                - vars: Extra variables (optional)
                - tags: Tags to run (optional)
                - skip_tags: Tags to skip (optional)
                - limit: Host limit (optional)
            inventory_path: Path to Ansible inventory
            stop_on_failure: Stop execution if a playbook fails
        
        Returns:
            List of results (one per playbook)
        
        Example:
            results = await executor.run_playbooks([
                {"name": "web/install_apache.yml", "vars": {"version": "2.4"}},
                {"name": "web/inject_sqli.yml", "vars": {"cve": "CVE-2023-12345"}},
                {"name": "database/install_mysql.yml"}
            ], inventory_path="/tmp/inventory.ini")
        """
        results = []
        
        for playbook_config in playbooks:
            playbook_name = playbook_config.get("name")
            
            if not playbook_name:
                logger.warning("Skipping playbook with no name")
                continue
            
            result = await self.run_playbook(
                playbook_name=playbook_name,
                inventory_path=inventory_path,
                extra_vars=playbook_config.get("vars"),
                tags=playbook_config.get("tags"),
                skip_tags=playbook_config.get("skip_tags"),
                limit=playbook_config.get("limit"),
                verbose=playbook_config.get("verbose", 0)
            )
            
            results.append(result)
            
            # Stop on failure if configured
            if not result["success"] and stop_on_failure:
                logger.error(f"Stopping playbook execution due to failure in: {playbook_name}")
                break
        
        return results
    
    async def run_command(
        self,
        command: str,
        inventory_path: str,
        pattern: str = "all",
        extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Run an ad-hoc Ansible command
        
        Args:
            command: Shell command to run
            inventory_path: Path to Ansible inventory
            pattern: Host pattern (default: "all")
            extra_args: Additional ansible arguments
        
        Returns:
            Command execution results
        
        Example:
            result = await executor.run_command(
                command="systemctl status apache2",
                inventory_path="/tmp/inventory.ini",
                pattern="web_servers"
            )
        """
        cmd = [
            "ansible",
            pattern,
            "-i", inventory_path,
            "-m", "shell",
            "-a", command
        ]
        
        if extra_args:
            cmd.extend(extra_args)
        
        logger.info(f"Running ad-hoc command on '{pattern}': {command}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        return {
            "success": process.returncode == 0,
            "return_code": process.returncode,
            "stdout": stdout.decode('utf-8', errors='replace'),
            "stderr": stderr.decode('utf-8', errors='replace'),
            "command": command,
            "pattern": pattern
        }
    
    def list_playbooks(self, category: Optional[str] = None) -> List[Dict[str, str]]:
        """
        List available playbooks
        
        Args:
            category: Filter by category (e.g., "web", "database", "network")
        
        Returns:
            List of playbooks with name, category, and path
        
        Example:
            playbooks = executor.list_playbooks(category="web")
            for pb in playbooks:
                print(f"- {pb['name']} ({pb['path']})")
        """
        playbooks = []
        
        # Search for .yml and .yaml files
        for playbook_path in self.playbook_dir.rglob("*.y*ml"):
            if playbook_path.is_file():
                # Get category from directory structure
                try:
                    relative_path = playbook_path.relative_to(self.playbook_dir)
                    pb_category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
                    
                    # Filter by category if specified
                    if category and pb_category != category:
                        continue
                    
                    playbooks.append({
                        "name": str(relative_path),
                        "category": pb_category,
                        "path": str(playbook_path),
                        "size": playbook_path.stat().st_size
                    })
                except ValueError:
                    continue
        
        return sorted(playbooks, key=lambda x: x["name"])

