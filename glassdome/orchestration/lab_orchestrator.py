"""
Lab Orchestrator module

Author: Brett Turner (ntounix)
Created: November 2025
Copyright (c) 2025 Brett Turner. All rights reserved.
"""
from typing import Dict, Any, List, Optional
import asyncio
import logging
from glassdome.orchestration.engine import OrchestrationEngine, TaskStatus
from glassdome.agents.os_installer_factory import OSInstallerFactory
from glassdome.platforms.base import PlatformClient
from glassdome.integrations.ansible_bridge import AnsibleBridge
from glassdome.integrations.ansible_executor import AnsibleExecutor

logger = logging.getLogger(__name__)


class LabConfiguration:
    """
    Complete lab configuration including all details
    
    This is what the orchestrator collects and manages
    """
    
    def __init__(self, lab_spec: Dict[str, Any]):
        self.lab_id = lab_spec.get("lab_id")
        self.name = lab_spec.get("name")
        self.description = lab_spec.get("description")
        
        # VMs with full configuration
        self.vms: List[VMConfiguration] = []
        for vm_spec in lab_spec.get("vms", []):
            self.vms.append(VMConfiguration(vm_spec))
        
        # Networks
        self.networks = lab_spec.get("networks", [])
        
        # Global settings
        self.auto_start = lab_spec.get("auto_start", True)
        self.auto_shutdown_minutes = lab_spec.get("auto_shutdown_minutes")
        
        # Post-deployment actions
        self.post_deployment_scripts = lab_spec.get("post_deployment_scripts", [])


class VMConfiguration:
    """
    Complete VM configuration
    
    Everything the orchestrator collects about a VM
    """
    
    def __init__(self, vm_spec: Dict[str, Any]):
        # Basic info
        self.vm_id = vm_spec.get("vm_id")
        self.name = vm_spec["name"]
        self.os_type = vm_spec["os_type"]
        self.os_version = vm_spec.get("os_version")
        self.node = vm_spec.get("node", "pve")
        
        # Hardware resources
        self.resources = VMResources(vm_spec.get("resources", {}))
        
        # User accounts
        self.users = [UserAccount(u) for u in vm_spec.get("users", [])]
        
        # Software packages
        self.packages = PackageConfiguration(vm_spec.get("packages", {}))
        
        # Network configuration
        self.network = NetworkConfiguration(vm_spec.get("network", {}))
        
        # Post-installation
        self.post_install = PostInstallConfiguration(vm_spec.get("post_install", {}))
        
        # Dependencies
        self.depends_on = vm_spec.get("depends_on", [])
        
        # Metadata
        self.tags = vm_spec.get("tags", [])
        self.purpose = vm_spec.get("purpose", "")


class VMResources:
    """VM hardware resources"""
    
    def __init__(self, resources: Dict[str, Any]):
        self.cores = resources.get("cores", 2)
        self.memory = resources.get("memory", 2048)  # MB
        self.disk_size = resources.get("disk_size", 20)  # GB
        self.disk_type = resources.get("disk_type", "ssd")
        self.storage = resources.get("storage", "local-lvm")
        self.network_bridge = resources.get("network_bridge", "vmbr0")
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cores": self.cores,
            "memory": self.memory,
            "disk_size": self.disk_size,
            "disk_type": self.disk_type,
            "storage": self.storage,
            "network": self.network_bridge
        }


class UserAccount:
    """User account to be created on VM"""
    
    def __init__(self, user_spec: Dict[str, Any]):
        self.username = user_spec["username"]
        self.password = user_spec.get("password")
        self.ssh_key = user_spec.get("ssh_key")
        self.sudo = user_spec.get("sudo", False)
        self.groups = user_spec.get("groups", [])
        self.shell = user_spec.get("shell", "/bin/bash")
        
    def to_cloud_init(self) -> Dict[str, Any]:
        """Convert to cloud-init format"""
        user = {
            "name": self.username,
            "shell": self.shell,
            "groups": self.groups,
        }
        if self.sudo:
            user["sudo"] = "ALL=(ALL) NOPASSWD:ALL"
        if self.password:
            user["passwd"] = self.password
            user["lock_passwd"] = False
        if self.ssh_key:
            user["ssh_authorized_keys"] = [self.ssh_key]
        return user


class PackageConfiguration:
    """Package installation configuration"""
    
    def __init__(self, packages: Dict[str, Any]):
        # System packages (apt/yum)
        self.system_packages = packages.get("system", [])
        
        # Python packages (pip)
        self.python_packages = packages.get("python", [])
        
        # Docker containers
        self.docker_containers = packages.get("docker", [])
        
        # Git repositories to clone
        self.git_repos = packages.get("git_repos", [])
        
        # Custom scripts to run
        self.custom_scripts = packages.get("custom_scripts", [])
        
    def to_cloud_init(self) -> Dict[str, Any]:
        """Convert to cloud-init format"""
        config = {}
        
        if self.system_packages:
            config["packages"] = self.system_packages
            
        if self.python_packages or self.custom_scripts:
            runcmd = []
            if self.python_packages:
                runcmd.append(f"pip3 install {' '.join(self.python_packages)}")
            runcmd.extend(self.custom_scripts)
            config["runcmd"] = runcmd
            
        return config


class NetworkConfiguration:
    """Network configuration for VM"""
    
    def __init__(self, network: Dict[str, Any]):
        self.type = network.get("type", "dhcp")  # dhcp or static
        self.ip_address = network.get("ip_address")
        self.netmask = network.get("netmask", "255.255.255.0")
        self.gateway = network.get("gateway")
        self.dns_servers = network.get("dns_servers", ["192.168.3.1", "8.8.8.8"])
        self.vlan = network.get("vlan")
        self.isolated = network.get("isolated", False)


class PostInstallConfiguration:
    """Post-installation configuration"""
    
    def __init__(self, post_install: Dict[str, Any]):
        # Scripts to run after installation
        self.scripts = post_install.get("scripts", [])
        
        # Files to copy to VM
        self.files = post_install.get("files", [])
        
        # Services to enable/start
        self.services = post_install.get("services", [])
        
        # Firewall rules
        self.firewall_rules = post_install.get("firewall_rules", [])
        
        # SSH configuration
        self.ssh_config = post_install.get("ssh_config", {})


class LabOrchestrator:
    """
    Lab Orchestrator (Platform-Agnostic with Ansible Integration)
    
    Manages complex multi-VM lab deployments with:
    - Platform-agnostic VM deployment (Proxmox, AWS, Azure, GCP, ESX)
    - Full VM configuration
    - User account creation (cloud-init or Ansible)
    - Package installation (cloud-init or Ansible)
    - Network setup
    - Ansible playbook execution (vulnerability injection, configuration)
    - Post-deployment configuration
    - Dependency management
    
    ANSIBLE INTEGRATION:
    After VMs are deployed, the orchestrator:
    1. Generates Ansible inventory from deployed VMs
    2. Runs specified Ansible playbooks (vulnerability injection, config, etc.)
    3. Returns combined results (VM deployment + Ansible execution)
    """
    
    def __init__(self, platform_client: PlatformClient, playbook_dir: Optional[str] = None):
        """
        Initialize Lab Orchestrator
        
        Args:
            platform_client: Platform client (Proxmox, AWS, Azure, etc.)
            playbook_dir: Optional custom directory for Ansible playbooks
        """
        self.platform_client = platform_client
        self.engine = OrchestrationEngine()
        self.factory = OSInstallerFactory
        
        # Ansible integration
        self.ansible_executor = AnsibleExecutor(playbook_dir=playbook_dir)
        
        # Track deployed VMs for Ansible inventory
        self.deployed_vms: List[Dict[str, Any]] = []
        
    async def deploy_lab(self, lab_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy a complete lab with full configuration + Ansible integration
        
        COMPLETE DEPLOYMENT FLOW:
        1. Deploy VMs (platform-agnostic)
        2. Wait for VMs to be ready
        3. Generate Ansible inventory
        4. Run Ansible playbooks (if specified)
        5. Run post-deployment scripts
        6. Return combined results
        
        Args:
            lab_spec: Complete lab specification with keys:
                - name: Lab name
                - vms: List of VM configurations
                - networks: List of network configurations
                - ansible_playbooks: List of Ansible playbooks to run (optional)
                - post_deployment_scripts: Scripts to run after deployment
                
        Returns:
            Deployment result with VM details and Ansible results
        """
        logger.info(f"Starting lab deployment: {lab_spec.get('name')}")
        
        # Clear previous deployment tracking
        self.deployed_vms = []
        
        # Parse configuration
        lab_config = LabConfiguration(lab_spec)
        
        # PHASE 1: Build orchestration tasks
        await self._build_tasks(lab_config)
        
        # PHASE 2: Execute orchestration (VM deployment)
        result = await self.engine.run(
            executor_func=self._execute_task,
            max_parallel=lab_spec.get("max_parallel", 3),
            fail_fast=lab_spec.get("fail_fast", False)
        )
        
        if not result["success"]:
            logger.error("Lab deployment failed during VM creation")
            return result
        
        logger.info(f"✓ VM deployment successful: {len(self.deployed_vms)} VMs deployed")
        
        # PHASE 3: Ansible integration (if playbooks specified)
        ansible_results = []
        inventory_path = None
        
        if lab_spec.get("ansible_playbooks") and self.deployed_vms:
            logger.info(f"Running Ansible playbooks: {len(lab_spec['ansible_playbooks'])} playbooks")
            
            # Generate Ansible inventory
            inventory_path = AnsibleBridge.create_inventory(
                vms=self.deployed_vms,
                format=lab_spec.get("inventory_format", "ini")
            )
            
            logger.info(f"✓ Generated Ansible inventory: {inventory_path}")
            
            # Run playbooks
            ansible_results = await self.ansible_executor.run_playbooks(
                playbooks=lab_spec["ansible_playbooks"],
                inventory_path=inventory_path,
                stop_on_failure=lab_spec.get("ansible_stop_on_failure", True)
            )
            
            # Check for Ansible failures
            failed_playbooks = [r for r in ansible_results if not r["success"]]
            if failed_playbooks:
                logger.warning(f"⚠ {len(failed_playbooks)} Ansible playbooks failed")
        
        # PHASE 4: Post-deployment configuration
        if lab_config.post_deployment_scripts:
            await self._run_post_deployment(lab_config, result)
        
        # Return combined results
        return {
            **result,
            "deployed_vms": self.deployed_vms,
            "ansible_results": ansible_results,
            "ansible_inventory": inventory_path,
            "lab_name": lab_spec.get("name"),
            "summary": {
                "vms_deployed": len(self.deployed_vms),
                "ansible_playbooks_run": len(ansible_results),
                "ansible_playbooks_success": sum(1 for r in ansible_results if r["success"]),
                "ansible_playbooks_failed": sum(1 for r in ansible_results if not r["success"])
            }
        }
    
    async def _build_tasks(self, lab_config: LabConfiguration) -> None:
        """
        Build orchestration tasks from lab configuration
        
        Tasks include:
        1. Network creation
        2. VM creation with resources
        3. User account setup
        4. Package installation
        5. Post-configuration
        """
        # Create network tasks first
        for network in lab_config.networks:
            self.engine.add_task(
                task_id=f"network_{network['name']}",
                task_def={
                    "type": "create_network",
                    "config": network
                }
            )
        
        # Create VM tasks
        for vm in lab_config.vms:
            # Dependencies include networks and other VMs
            dependencies = []
            
            # Depend on networks
            if vm.network.isolated:
                dependencies.append(f"network_{vm.network.vlan}")
            
            # Depend on other VMs
            dependencies.extend(vm.depends_on)
            
            # Add VM creation task
            self.engine.add_task(
                task_id=f"vm_{vm.vm_id}",
                task_def={
                    "type": "create_vm",
                    "vm_config": vm
                },
                dependencies=dependencies
            )
            
            # Add user creation task (depends on VM)
            if vm.users:
                self.engine.add_task(
                    task_id=f"users_{vm.vm_id}",
                    task_def={
                        "type": "create_users",
                        "vm_id": vm.vm_id,
                        "users": vm.users
                    },
                    dependencies=[f"vm_{vm.vm_id}"]
                )
            
            # Add package installation task (depends on users)
            if vm.packages.system_packages or vm.packages.python_packages:
                self.engine.add_task(
                    task_id=f"packages_{vm.vm_id}",
                    task_def={
                        "type": "install_packages",
                        "vm_id": vm.vm_id,
                        "packages": vm.packages
                    },
                    dependencies=[f"users_{vm.vm_id}"] if vm.users else [f"vm_{vm.vm_id}"]
                )
            
            # Add post-install configuration
            if vm.post_install.scripts or vm.post_install.files:
                self.engine.add_task(
                    task_id=f"configure_{vm.vm_id}",
                    task_def={
                        "type": "post_configure",
                        "vm_id": vm.vm_id,
                        "config": vm.post_install
                    },
                    dependencies=[f"packages_{vm.vm_id}"]
                )
    
    async def _execute_task(self, task_def: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a single orchestration task
        
        Args:
            task_def: Task definition
            
        Returns:
            Task result
        """
        task_type = task_def["type"]
        
        if task_type == "create_vm":
            return await self._create_vm(task_def["vm_config"])
        elif task_type == "create_network":
            return await self._create_network(task_def["config"])
        elif task_type == "create_users":
            return await self._create_users(task_def["vm_id"], task_def["users"])
        elif task_type == "install_packages":
            return await self._install_packages(task_def["vm_id"], task_def["packages"])
        elif task_type == "post_configure":
            return await self._post_configure(task_def["vm_id"], task_def["config"])
        else:
            return {"success": False, "error": f"Unknown task type: {task_type}"}
    
    async def _create_vm(self, vm_config: VMConfiguration) -> Dict[str, Any]:
        """
        Create VM with full configuration
        
        This delegates to the appropriate OS agent (platform-agnostic)
        and tracks the deployed VM for Ansible inventory generation.
        """
        logger.info(f"Creating VM: {vm_config.name}")
        
        # Get appropriate agent (platform-agnostic)
        agent = self.factory.get_agent(vm_config.os_type, self.platform_client)
        
        # Build cloud-init configuration
        cloud_init = self._build_cloud_init(vm_config)
        
        # Build task
        task = {
            "element_type": f"{vm_config.os_type}_vm",
            "config": {
                "name": vm_config.name,
                "node": vm_config.node,
                f"{vm_config.os_type}_version": vm_config.os_version,
                **vm_config.resources.to_dict(),
                "cloud_init": cloud_init,
                "use_template": True
            }
        }
        
        # Execute via agent
        result = await agent.run(task)
        
        # Track deployed VM for Ansible inventory
        if result.get("success"):
            vm_info = {
                "vm_id": result.get("resource_id"),
                "name": vm_config.name,
                "ip_address": result.get("ip_address"),
                "platform": result.get("platform"),
                "os_type": vm_config.os_type,
                "os_version": vm_config.os_version,
                "group": vm_config.purpose or "ungrouped",  # Ansible inventory group
                "ansible_connection": result.get("ansible_connection"),
                "status": result.get("status")
            }
            self.deployed_vms.append(vm_info)
            logger.info(f"✓ VM tracked for Ansible: {vm_config.name} ({result.get('ip_address')})")
        
        return result
    
    def _build_cloud_init(self, vm_config: VMConfiguration) -> Dict[str, Any]:
        """
        Build cloud-init configuration from VM config
        
        Cloud-init handles:
        - User creation
        - Package installation
        - Network configuration
        - SSH keys
        - Post-installation scripts
        """
        cloud_init = {
            "hostname": vm_config.name,
            "manage_etc_hosts": True,
        }
        
        # Add users
        if vm_config.users:
            cloud_init["users"] = [user.to_cloud_init() for user in vm_config.users]
        
        # Add packages
        if vm_config.packages:
            cloud_init.update(vm_config.packages.to_cloud_init())
        
        # Add network configuration
        if vm_config.network.type == "static":
            cloud_init["network"] = {
                "version": 2,
                "ethernets": {
                    "eth0": {
                        "addresses": [f"{vm_config.network.ip_address}/{vm_config.network.netmask}"],
                        "gateway4": vm_config.network.gateway,
                        "nameservers": {
                            "addresses": vm_config.network.dns_servers
                        }
                    }
                }
            }
        
        return cloud_init
    
    async def _create_network(self, network_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create virtual network"""
        logger.info(f"Creating network: {network_config['name']}")
        
        # Delegate to platform client
        result = await self.platform_client.create_network(
            node=network_config.get("node", "pve"),
            config=network_config
        )
        
        return result
    
    async def _create_users(self, vm_id: str, users: List[UserAccount]) -> Dict[str, Any]:
        """Create user accounts on VM"""
        logger.info(f"Creating users on VM {vm_id}: {[u.username for u in users]}")
        
        # This would SSH into the VM and create users
        # For now, simulated
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "users_created": len(users)
        }
    
    async def _install_packages(self, vm_id: str, packages: PackageConfiguration) -> Dict[str, Any]:
        """Install packages on VM"""
        logger.info(f"Installing packages on VM {vm_id}")
        
        # This would SSH into VM and run apt/yum/pip
        # For now, simulated
        await asyncio.sleep(2)
        
        return {
            "success": True,
            "packages_installed": len(packages.system_packages) + len(packages.python_packages)
        }
    
    async def _post_configure(self, vm_id: str, config: PostInstallConfiguration) -> Dict[str, Any]:
        """Run post-installation configuration"""
        logger.info(f"Running post-configuration on VM {vm_id}")
        
        # This would:
        # 1. Copy files to VM
        # 2. Run scripts
        # 3. Configure services
        # 4. Set up firewall
        
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "scripts_run": len(config.scripts),
            "files_copied": len(config.files)
        }
    
    async def _run_post_deployment(self, lab_config: LabConfiguration, result: Dict[str, Any]) -> None:
        """Run lab-wide post-deployment scripts"""
        logger.info("Running post-deployment scripts")
        
        for script in lab_config.post_deployment_scripts:
            # Execute script
            logger.info(f"Running: {script}")
            await asyncio.sleep(0.5)
    
    def get_execution_plan(self) -> List[List[str]]:
        """Get the execution plan (what will run in parallel)"""
        return self.engine.get_execution_plan()

