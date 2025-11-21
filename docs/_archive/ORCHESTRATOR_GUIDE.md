# Orchestrator Guide

## What the Orchestrator Collects & Manages

The **Orchestrator** handles complex, multi-VM lab deployments with complete configuration. It collects and manages FAR MORE than individual agents.

---

## Individual Agent vs Orchestrator

### 🤖 **Individual Agent** (e.g., UbuntuInstallerAgent)

**Responsibility:** Create ONE VM

**Collects:**
- ✅ OS type and version
- ✅ Basic resources (CPU, memory, disk)
- ✅ Node to deploy on
- ✅ Template vs ISO

**Example:**
```python
# Simple VM creation
{
    "name": "ubuntu-vm",
    "os_type": "ubuntu",
    "version": "22.04",
    "cores": 2,
    "memory": 2048,
    "disk_size": 20
}
```

---

### 🎯 **Orchestrator** (LabOrchestrator)

**Responsibility:** Deploy ENTIRE LAB with multiple VMs and complete configuration

**Collects:**
- ✅ **VM Resources**
  - Disk size (20GB, 80GB, 100GB, etc.)
  - Memory size (2GB, 4GB, 8GB, etc.)
  - CPU cores (2, 4, 8, etc.)
  - Disk type (SSD vs HDD)
  - Storage location

- ✅ **User Account Creation**
  - Username
  - Password (hashed)
  - SSH public keys
  - Sudo access (yes/no)
  - User groups
  - Default shell

- ✅ **Package Installations**
  - System packages (apt/yum)
  - Python packages (pip)
  - Docker containers
  - Git repositories to clone
  - Custom installation scripts

- ✅ **Network Configuration**
  - Static IP vs DHCP
  - IP address
  - Netmask
  - Gateway
  - DNS servers
  - VLAN assignment
  - Network isolation

- ✅ **Post-Installation**
  - Configuration scripts
  - Files to copy
  - Services to enable
  - Firewall rules
  - SSH configuration

- ✅ **Dependencies**
  - What must be created first
  - What can run in parallel
  - Network dependencies
  - VM dependencies

- ✅ **Lab-Wide Settings**
  - Auto-start
  - Auto-shutdown timers
  - Parallelism limits
  - Failure handling

---

## Complete Lab Specification Example

```python
LAB_SPEC = {
    "lab_id": "web_security_lab",
    "name": "Web Application Security Lab",
    "description": "Complete penetration testing environment",
    
    # Networks - Orchestrator creates these
    "networks": [
        {
            "name": "attack_network",
            "vlan": 100,
            "subnet": "10.0.100.0/24",
            "isolated": True
        }
    ],
    
    # VMs with COMPLETE configuration
    "vms": [
        {
            "vm_id": "kali_attacker",
            "name": "kali-attacker-01",
            "os_type": "kali",
            "os_version": "2024.1",
            "node": "pve",
            
            # RESOURCES - Orchestrator collects disk size, memory, CPU
            "resources": {
                "cores": 4,              # CPU cores
                "memory": 8192,          # 8GB RAM
                "disk_size": 80,         # 80GB disk
                "disk_type": "ssd",      # SSD storage
                "storage": "local-lvm",  # Storage pool
                "network_bridge": "vmbr0"
            },
            
            # USERS - Orchestrator creates user accounts
            "users": [
                {
                    "username": "pentester",
                    "password": "hashed_password",
                    "ssh_key": "ssh-rsa AAAAB3...",
                    "sudo": True,                    # Sudo access
                    "groups": ["sudo", "docker"],    # User groups
                    "shell": "/bin/zsh"              # Default shell
                }
            ],
            
            # PACKAGES - Orchestrator installs software
            "packages": {
                "system": [                          # System packages
                    "metasploit-framework",
                    "nmap",
                    "burpsuite",
                    "docker.io"
                ],
                "python": [                          # Python packages
                    "requests",
                    "scapy"
                ],
                "git_repos": [                       # Clone repos
                    "https://github.com/user/repo.git"
                ],
                "custom_scripts": [                  # Custom commands
                    "echo 'export PATH=$PATH:/opt/tools' >> ~/.zshrc"
                ]
            },
            
            # NETWORK - Orchestrator configures networking
            "network": {
                "type": "static",                    # Static IP
                "ip_address": "10.0.100.10",
                "netmask": "255.255.255.0",
                "gateway": "10.0.100.1",
                "dns_servers": ["8.8.8.8"],
                "vlan": 100
            },
            
            # POST-INSTALL - Orchestrator runs these after creation
            "post_install": {
                "scripts": ["/opt/setup.sh"],        # Scripts to run
                "files": [                            # Files to copy
                    {"src": "/local/config", "dst": "~/.config"}
                ],
                "services": ["postgresql", "docker"], # Services to start
                "firewall_rules": [                   # Firewall config
                    "allow from 10.0.200.0/24"
                ]
            },
            
            # DEPENDENCIES - Orchestrator manages execution order
            "depends_on": ["network_attack_network"]
        }
    ],
    
    # LAB-WIDE post-deployment
    "post_deployment_scripts": [
        "/opt/verify_connectivity.sh",
        "/opt/generate_report.sh"
    ],
    
    # SETTINGS
    "auto_start": True,
    "auto_shutdown_minutes": 240,      # Auto-shutdown after 4 hours
    "max_parallel": 2,                 # Max parallel deployments
    "fail_fast": False                 # Continue on errors
}
```

---

## Orchestrator Flow

```
1. Parse Lab Specification
   ↓
2. Build Task Graph
   ├── Network creation tasks
   ├── VM creation tasks (with resources)
   ├── User creation tasks
   ├── Package installation tasks
   └── Post-configuration tasks
   ↓
3. Resolve Dependencies
   ↓
4. Execute in Parallel (respecting dependencies)
   ├── Layer 1: Networks
   ├── Layer 2: VMs (base creation via agents)
   ├── Layer 3: User accounts
   ├── Layer 4: Package installation
   └── Layer 5: Post-configuration
   ↓
5. Run Lab-Wide Post-Deployment
   ↓
6. Return Complete Results
```

---

## What Gets Created

### For Each VM, the Orchestrator:

1. **Creates the VM** (via agent)
   - Calls Ubuntu/Kali/Windows agent
   - Passes resource specifications
   - Gets back VM ID and IP

2. **Creates User Accounts**
   - SSHs into VM
   - Creates users with `useradd`
   - Sets passwords
   - Adds SSH keys
   - Configures sudo
   - Adds to groups

3. **Installs Packages**
   - Runs `apt install` for system packages
   - Runs `pip install` for Python packages
   - Clones git repositories
   - Runs custom installation scripts

4. **Configures Network**
   - Sets static IP (if specified)
   - Configures DNS
   - Sets up VLANs
   - Applies firewall rules

5. **Runs Post-Configuration**
   - Copies configuration files
   - Runs setup scripts
   - Enables services
   - Applies security settings

---

## Example: 3-VM Lab Deployment

```python
# Orchestrator manages this entire scenario:

LAB = {
    "vms": [
        {
            "vm_id": "attacker",
            "os_type": "kali",
            "resources": {"cores": 4, "memory": 8192, "disk_size": 80},
            "users": [{"username": "hacker", "sudo": True}],
            "packages": {"system": ["nmap", "metasploit"]},
            "depends_on": []  # Can start immediately
        },
        {
            "vm_id": "target",
            "os_type": "ubuntu",
            "resources": {"cores": 2, "memory": 4096, "disk_size": 40},
            "users": [{"username": "webadmin"}],
            "packages": {"system": ["apache2", "mysql-server"]},
            "depends_on": []  # Can start immediately
        },
        {
            "vm_id": "monitor",
            "os_type": "ubuntu",
            "resources": {"cores": 2, "memory": 4096, "disk_size": 100},
            "users": [{"username": "admin"}],
            "packages": {"docker": ["grafana/grafana"]},
            "depends_on": ["attacker", "target"]  # Waits for both
        }
    ]
}

# Execution plan:
# Layer 1 (parallel): attacker, target
# Layer 2 (waits): monitor
```

---

## Cloud-Init Integration

The Orchestrator generates **cloud-init** configuration from your specification:

```yaml
# Generated automatically from your config:
#cloud-config
hostname: kali-attacker-01
users:
  - name: pentester
    sudo: ALL=(ALL) NOPASSWD:ALL
    shell: /bin/zsh
    groups: [sudo, docker]
    ssh_authorized_keys:
      - ssh-rsa AAAAB3...

packages:
  - metasploit-framework
  - nmap
  - burpsuite
  - docker.io

runcmd:
  - pip3 install requests scapy
  - git clone https://github.com/user/repo.git /opt/repo
  - systemctl enable postgresql

network:
  version: 2
  ethernets:
    eth0:
      addresses: [10.0.100.10/24]
      gateway4: 10.0.100.1
      nameservers:
        addresses: [8.8.8.8]
```

---

## Key Differences

| What | Individual Agent | Orchestrator |
|------|-----------------|--------------|
| **Scope** | One VM | Entire lab |
| **Disk Size** | ✅ Collects | ✅ Collects (per VM) |
| **Memory** | ✅ Collects | ✅ Collects (per VM) |
| **CPU** | ✅ Collects | ✅ Collects (per VM) |
| **Users** | ❌ | ✅ Creates accounts |
| **Passwords** | ❌ | ✅ Sets passwords |
| **SSH Keys** | ❌ | ✅ Installs keys |
| **Packages** | ❌ | ✅ Installs software |
| **Network Config** | ❌ | ✅ Static IPs, VLANs |
| **Post-Install** | ❌ | ✅ Runs scripts |
| **Dependencies** | ❌ | ✅ Manages order |
| **Multi-VM** | ❌ | ✅ Coordinates all |

---

## Usage

### Direct API:

```bash
POST /api/labs/deploy
{
  "lab_spec": { ... complete configuration ... }
}
```

### Python:

```python
from glassdome.orchestration.lab_orchestrator import LabOrchestrator

orchestrator = LabOrchestrator(proxmox_client)
result = await orchestrator.deploy_lab(LAB_SPEC)
```

---

## Summary

**Individual Agents:**
- Create ONE VM
- Basic configuration only
- No user management
- No package installation
- Simple and focused

**Orchestrator:**
- ✅ Deploys ENTIRE labs
- ✅ Collects disk size, memory, CPU
- ✅ Creates user accounts with passwords/keys
- ✅ Installs packages (system + Python + Docker)
- ✅ Configures networks (static IPs, VLANs)
- ✅ Runs post-installation scripts
- ✅ Manages dependencies
- ✅ Coordinates multiple VMs
- ✅ Lab-wide configuration

**The Orchestrator is the "brain" that turns a complete lab specification into a running cyber range!**

---

See `examples/complex_lab_deployment.py` for a complete working example.

