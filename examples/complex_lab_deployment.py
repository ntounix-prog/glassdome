#!/usr/bin/env python3
"""
Example: Complex Lab Deployment with Orchestrator

This demonstrates how the orchestrator collects and manages:
- VM resources (disk, memory, CPU)
- User account creation  
- Package installations
- Network configuration
- Dependencies between VMs
"""
import asyncio
from glassdome import ProxmoxClient
from glassdome.orchestration.lab_orchestrator import LabOrchestrator


# Complete lab specification with ALL details
LAB_SPEC = {
    "lab_id": "web_security_lab_001",
    "name": "Web Application Security Lab",
    "description": "Complete web security testing environment",
    
    # Networks
    "networks": [
        {
            "name": "attack_network",
            "vlan": 100,
            "subnet": "10.0.100.0/24",
            "isolated": True
        },
        {
            "name": "victim_network",
            "vlan": 200,
            "subnet": "10.0.200.0/24",
            "isolated": True
        }
    ],
    
    # VMs with COMPLETE configuration
    "vms": [
        {
            "vm_id": "kali_attacker",
            "name": "kali-attacker-01",
            "os_type": "kali",
            "os_version": "2025.1",
            "node": "pve",
            "purpose": "Attack machine for penetration testing",
            "tags": ["attacker", "kali", "security"],
            
            # Hardware resources - Orchestrator collects this
            "resources": {
                "cores": 4,
                "memory": 8192,  # 8GB RAM
                "disk_size": 80,  # 80GB disk
                "disk_type": "ssd",
                "storage": "local-lvm",
                "network_bridge": "vmbr0"
            },
            
            # User accounts - Orchestrator manages this
            "users": [
                {
                    "username": "pentester",
                    "password": "hashed_password_here",
                    "ssh_key": "ssh-rsa AAAAB3NzaC1...",
                    "sudo": True,
                    "groups": ["sudo", "docker"],
                    "shell": "/bin/zsh"
                },
                {
                    "username": "student",
                    "password": "student123",
                    "sudo": False,
                    "groups": ["users"]
                }
            ],
            
            # Packages - Orchestrator installs these
            "packages": {
                "system": [
                    "metasploit-framework",
                    "nmap",
                    "burpsuite",
                    "sqlmap",
                    "nikto",
                    "docker.io",
                    "git",
                    "vim",
                    "tmux"
                ],
                "python": [
                    "requests",
                    "beautifulsoup4",
                    "scapy",
                    "pwntools"
                ],
                "git_repos": [
                    "https://github.com/danielmiessler/SecLists.git",
                    "https://github.com/swisskyrepo/PayloadsAllTheThings.git"
                ],
                "custom_scripts": [
                    "echo 'export PATH=$PATH:/opt/tools' >> ~/.zshrc",
                    "mkdir -p /home/pentester/projects"
                ]
            },
            
            # Network configuration
            "network": {
                "type": "static",
                "ip_address": "10.0.100.10",
                "netmask": "255.255.255.0",
                "gateway": "10.0.100.1",
                "dns_servers": ["8.8.8.8", "1.1.1.1"],
                "vlan": 100
            },
            
            # Post-installation configuration
            "post_install": {
                "scripts": [
                    "/opt/setup_burp.sh",
                    "/opt/configure_metasploit.sh"
                ],
                "files": [
                    {"src": "/local/configs/tmux.conf", "dst": "~/.tmux.conf"},
                    {"src": "/local/configs/vimrc", "dst": "~/.vimrc"}
                ],
                "services": ["postgresql", "docker"],
                "firewall_rules": [
                    "allow from 10.0.200.0/24",
                    "deny from any"
                ]
            },
            
            # Dependencies
            "depends_on": ["network_attack_network"]
        },
        
        {
            "vm_id": "dvwa_target",
            "name": "dvwa-vulnerable-01",
            "os_type": "ubuntu",
            "os_version": "22.04",
            "node": "pve",
            "purpose": "Vulnerable web application for testing",
            "tags": ["target", "vulnerable", "web"],
            
            "resources": {
                "cores": 2,
                "memory": 4096,  # 4GB RAM
                "disk_size": 40,  # 40GB disk
                "disk_type": "ssd",
                "storage": "local-lvm"
            },
            
            "users": [
                {
                    "username": "webadmin",
                    "password": "admin123",
                    "sudo": True,
                    "groups": ["sudo", "www-data"]
                }
            ],
            
            "packages": {
                "system": [
                    "apache2",
                    "mysql-server",
                    "php",
                    "php-mysql",
                    "php-gd",
                    "git"
                ],
                "custom_scripts": [
                    "git clone https://github.com/digininja/DVWA.git /var/www/html/dvwa",
                    "mysql -e 'CREATE DATABASE dvwa;'",
                    "chown -R www-data:www-data /var/www/html/dvwa"
                ]
            },
            
            "network": {
                "type": "static",
                "ip_address": "10.0.200.10",
                "netmask": "255.255.255.0",
                "gateway": "10.0.200.1",
                "vlan": 200
            },
            
            "post_install": {
                "services": ["apache2", "mysql"],
                "firewall_rules": [
                    "allow 80/tcp",
                    "allow 443/tcp",
                    "allow from 10.0.100.0/24"
                ],
                "scripts": [
                    "/opt/configure_dvwa.sh"
                ]
            },
            
            "depends_on": ["network_victim_network"]
        },
        
        {
            "vm_id": "monitoring",
            "name": "monitoring-01",
            "os_type": "ubuntu",
            "os_version": "22.04",
            "node": "pve",
            "purpose": "Monitor lab activity and traffic",
            "tags": ["monitoring", "logging"],
            
            "resources": {
                "cores": 2,
                "memory": 4096,
                "disk_size": 100,  # Larger disk for logs
                "disk_type": "hdd"  # HDD is fine for logs
            },
            
            "users": [
                {
                    "username": "monitor",
                    "sudo": True,
                    "ssh_key": "ssh-rsa AAAAB3NzaC1..."
                }
            ],
            
            "packages": {
                "system": [
                    "wireshark",
                    "tcpdump",
                    "elasticsearch",
                    "kibana",
                    "filebeat"
                ],
                "docker": [
                    "grafana/grafana",
                    "prom/prometheus"
                ]
            },
            
            "network": {
                "type": "dhcp"
            },
            
            # Monitoring depends on both networks being up
            "depends_on": [
                "network_attack_network",
                "network_victim_network",
                "kali_attacker",
                "dvwa_target"
            ]
        }
    ],
    
    # Lab-wide post-deployment
    "post_deployment_scripts": [
        "/opt/verify_connectivity.sh",
        "/opt/generate_lab_report.sh",
        "/opt/send_notification.sh"
    ],
    
    # Settings
    "auto_start": True,
    "auto_shutdown_minutes": 240,  # Auto-shutdown after 4 hours
    "max_parallel": 2,  # Deploy 2 VMs in parallel max
    "fail_fast": False  # Continue even if one VM fails
}


async def deploy_complex_lab():
    """Deploy the complete lab with orchestrator"""
    print("=" * 60)
    print("Complex Lab Deployment Example")
    print("=" * 60)
    
    # Initialize Proxmox client
    proxmox = ProxmoxClient(
        host="your-proxmox-host",
        user="root@pam",
        password="your-password",
        verify_ssl=False
    )
    
    # Create orchestrator
    orchestrator = LabOrchestrator(proxmox)
    
    # Show execution plan
    print("\nExecution Plan:")
    print("-" * 60)
    plan = orchestrator.get_execution_plan()
    for i, layer in enumerate(plan, 1):
        print(f"Layer {i} (parallel): {', '.join(layer)}")
    
    # Deploy lab
    print("\nStarting deployment...")
    print("-" * 60)
    
    result = await orchestrator.deploy_lab(LAB_SPEC)
    
    # Show results
    print("\nDeployment Results:")
    print("-" * 60)
    print(f"Success: {result['success']}")
    print(f"Total tasks: {result['total_tasks']}")
    print(f"Completed: {result['completed']}")
    print(f"Failed: {result['failed']}")
    print(f"Duration: {result['duration_seconds']:.2f}s")
    
    # Show task details
    print("\nTask Details:")
    print("-" * 60)
    for task_id, task_info in result['tasks'].items():
        status = "✅" if task_info['status'] == 'completed' else "❌"
        print(f"{status} {task_id}: {task_info['status']}")
    
    print("\n" + "=" * 60)
    print("Lab deployed!")
    print(f"Access Kali: ssh pentester@10.0.100.10")
    print(f"Access DVWA: http://10.0.200.10/dvwa")
    print("=" * 60)


if __name__ == "__main__":
    print("\n")
    print("This example shows what the ORCHESTRATOR collects:")
    print("-" * 60)
    print("✅ VM Resources (disk size, memory, CPU cores)")
    print("✅ User Accounts (username, password, SSH keys, sudo)")
    print("✅ Package Installations (system, Python, Docker, Git)")
    print("✅ Network Configuration (static IPs, VLANs, DNS)")
    print("✅ Post-Install Scripts (configuration, services)")
    print("✅ Dependencies (what must be created first)")
    print("✅ Lab-wide Settings (auto-shutdown, parallelism)")
    print("-" * 60)
    print("\n")
    
    # Uncomment to run:
    # asyncio.run(deploy_complex_lab())
    
    print("Review LAB_SPEC in the code to see the complete configuration!")

