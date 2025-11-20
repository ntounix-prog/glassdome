"""
Ansible Bridge
Converts Glassdome deployments to Ansible inventory formats

This is the BRIDGE between Glassdome's VM deployments and your team's Ansible playbooks.
It generates inventory files (INI or JSON) from deployed VMs, enabling:
1. Automatic playbook execution after VM deployment
2. Manual Ansible usage with Glassdome-managed infrastructure
3. Integration with existing Ansible workflows
"""
from typing import Dict, List, Any, Optional
import json
import tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AnsibleBridge:
    """
    Bridge between Glassdome and Ansible
    
    Generates Ansible inventory files from Glassdome VM deployments.
    Supports both INI and JSON inventory formats.
    """
    
    @staticmethod
    def create_inventory_ini(vms: List[Dict[str, Any]], groups: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Generate Ansible inventory in INI format
        
        This is the format most teams are familiar with.
        
        Args:
            vms: List of VM deployment results from platform clients
            groups: Optional group mappings (group_name -> [vm_ids])
        
        Returns:
            Path to generated inventory file
        
        Example Output:
            [web_servers]
            vm-100 ansible_host=192.168.3.100 ansible_user=ubuntu ansible_ssh_private_key_file=/root/.ssh/id_rsa
            
            [database_servers]
            vm-101 ansible_host=192.168.3.101 ansible_user=ubuntu ansible_ssh_private_key_file=/root/.ssh/id_rsa
        """
        inventory_lines = []
        
        # Group VMs by their specified group
        vm_groups = {}
        for vm in vms:
            group = vm.get("group", "ungrouped")
            if group not in vm_groups:
                vm_groups[group] = []
            vm_groups[group].append(vm)
        
        # Generate inventory sections for each group
        for group_name, group_vms in vm_groups.items():
            inventory_lines.append(f"[{group_name}]")
            
            for vm in group_vms:
                ansible_conn = vm.get("ansible_connection", {})
                
                # Build host line with connection details
                host_line_parts = [
                    vm['vm_id'],
                    f"ansible_host={ansible_conn.get('host', 'unknown')}",
                    f"ansible_user={ansible_conn.get('user', 'ubuntu')}",
                    f"ansible_port={ansible_conn.get('port', 22)}",
                ]
                
                # Add SSH key if specified
                if ansible_conn.get('ssh_key_path'):
                    host_line_parts.append(f"ansible_ssh_private_key_file={ansible_conn['ssh_key_path']}")
                
                # Add platform and OS info as host variables
                host_line_parts.append(f"platform={vm.get('platform', 'unknown')}")
                
                if vm.get('os_type'):
                    host_line_parts.append(f"os_type={vm['os_type']}")
                if vm.get('os_version'):
                    host_line_parts.append(f"os_version={vm['os_version']}")
                
                inventory_lines.append(" ".join(host_line_parts))
            
            inventory_lines.append("")  # Blank line between groups
        
        # Add custom groups if specified
        if groups:
            for group_name, vm_ids in groups.items():
                inventory_lines.append(f"[{group_name}]")
                for vm_id in vm_ids:
                    inventory_lines.append(vm_id)
                inventory_lines.append("")
        
        # Write to temporary file
        inventory_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.ini',
            prefix='glassdome_inventory_',
            delete=False
        )
        inventory_content = "\n".join(inventory_lines)
        inventory_file.write(inventory_content)
        inventory_file.close()
        
        logger.info(f"Generated Ansible inventory (INI): {inventory_file.name}")
        logger.debug(f"Inventory content:\n{inventory_content}")
        
        return inventory_file.name
    
    @staticmethod
    def create_inventory_json(vms: List[Dict[str, Any]], groups: Optional[Dict[str, List[str]]] = None) -> str:
        """
        Generate Ansible inventory in JSON format (dynamic inventory)
        
        This format is useful for programmatic inventory generation
        and integration with dynamic inventory scripts.
        
        Args:
            vms: List of VM deployment results
            groups: Optional group mappings
        
        Returns:
            Path to generated JSON inventory file
        
        Example Output:
            {
              "web_servers": {
                "hosts": ["vm-100", "vm-102"]
              },
              "_meta": {
                "hostvars": {
                  "vm-100": {
                    "ansible_host": "192.168.3.100",
                    "ansible_user": "ubuntu",
                    ...
                  }
                }
              }
            }
        """
        inventory = {
            "_meta": {
                "hostvars": {}
            }
        }
        
        # Process VMs into groups and hostvars
        for vm in vms:
            vm_id = vm['vm_id']
            group = vm.get("group", "ungrouped")
            ansible_conn = vm.get("ansible_connection", {})
            
            # Add host to group
            if group not in inventory:
                inventory[group] = {"hosts": []}
            inventory[group]["hosts"].append(vm_id)
            
            # Build hostvars
            hostvars = {
                "ansible_host": ansible_conn.get('host', 'unknown'),
                "ansible_user": ansible_conn.get('user', 'ubuntu'),
                "ansible_port": ansible_conn.get('port', 22),
                "platform": vm.get("platform", "unknown"),
                "vm_status": vm.get("status", "unknown"),
            }
            
            # Add SSH key if specified
            if ansible_conn.get('ssh_key_path'):
                hostvars["ansible_ssh_private_key_file"] = ansible_conn['ssh_key_path']
            
            # Add OS info
            if vm.get('os_type'):
                hostvars["os_type"] = vm['os_type']
            if vm.get('os_version'):
                hostvars["os_version"] = vm['os_version']
            
            # Add platform-specific details
            if vm.get('platform_specific'):
                hostvars["platform_specific"] = vm['platform_specific']
            
            inventory["_meta"]["hostvars"][vm_id] = hostvars
        
        # Add custom groups
        if groups:
            for group_name, vm_ids in groups.items():
                if group_name not in inventory:
                    inventory[group_name] = {"hosts": []}
                inventory[group_name]["hosts"].extend(vm_ids)
        
        # Write to temporary file
        inventory_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            prefix='glassdome_inventory_',
            delete=False
        )
        json.dump(inventory, inventory_file, indent=2)
        inventory_file.close()
        
        logger.info(f"Generated Ansible inventory (JSON): {inventory_file.name}")
        
        return inventory_file.name
    
    @staticmethod
    def create_inventory(vms: List[Dict[str, Any]], 
                        format: str = "ini",
                        groups: Optional[Dict[str, List[str]]] = None,
                        output_path: Optional[str] = None) -> str:
        """
        Generate Ansible inventory in the specified format
        
        This is the main entry point for inventory generation.
        
        Args:
            vms: List of VM deployment results
            format: "ini" or "json"
            groups: Optional group mappings
            output_path: Optional custom output path (otherwise uses temp file)
        
        Returns:
            Path to generated inventory file
        
        Raises:
            ValueError: If format is invalid
        """
        if format.lower() == "ini":
            inventory_path = AnsibleBridge.create_inventory_ini(vms, groups)
        elif format.lower() == "json":
            inventory_path = AnsibleBridge.create_inventory_json(vms, groups)
        else:
            raise ValueError(f"Invalid inventory format: {format}. Use 'ini' or 'json'.")
        
        # Move to custom path if specified
        if output_path:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            Path(inventory_path).rename(output_file)
            logger.info(f"Moved inventory to: {output_file}")
            return str(output_file)
        
        return inventory_path
    
    @staticmethod
    def parse_ansible_results(stdout: str) -> Dict[str, Any]:
        """
        Parse Ansible playbook output into structured format
        
        Extracts task statistics (ok, changed, failed, etc.)
        
        Args:
            stdout: Ansible playbook stdout
        
        Returns:
            Dictionary with parsed results
        """
        results = {
            "tasks": {
                "ok": 0,
                "changed": 0,
                "failed": 0,
                "unreachable": 0,
                "skipped": 0,
                "rescued": 0,
                "ignored": 0
            },
            "hosts": {}
        }
        
        # Parse task statistics
        for line in stdout.splitlines():
            # Look for lines like: "ok=5 changed=3 unreachable=0 failed=0 skipped=2 rescued=0 ignored=0"
            if "ok=" in line and "changed=" in line:
                parts = line.split()
                host_stats = {}
                
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=")
                        try:
                            host_stats[key] = int(value)
                            # Aggregate to overall totals
                            if key in results["tasks"]:
                                results["tasks"][key] += int(value)
                        except ValueError:
                            pass
                
                # Extract hostname (usually at start of line)
                if ":" in parts[0]:
                    hostname = parts[0].rstrip(":")
                    results["hosts"][hostname] = host_stats
        
        return results

