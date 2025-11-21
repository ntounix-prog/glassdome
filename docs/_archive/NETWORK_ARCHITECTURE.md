# Network Architecture for Cyber Range Scenarios

## Overview

Glassdome needs to support **complex multi-VM scenarios** with proper network isolation, not just single VM deployments.

---

## Requirements Analysis

### **Scenario Scale**
- **7-10 VMs per "game"** (cyber range scenario)
- **Multiple isolated networks** per scenario
- **Attack console** (Parrot, Kali, or custom Ubuntu-based)
- **Network segmentation** mimicking real enterprise environments

### **vApp-like Deployment**
Deploy entire network topologies as a single unit:
- All VMs in the scenario
- Virtual networks connecting them
- Routing/firewall rules
- Pre-configured for specific training objectives

---

## Network Topology Concepts

### **Typical Cyber Range Scenario**

```
┌─────────────────────────────────────────────────────────────────┐
│                    Cyber Range Scenario                         │
│                  "Enterprise Web Application"                   │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│  Attack Network (192.168.100.0/24)                                │
│  ┌──────────────────┐                                            │
│  │  Kali/Parrot     │  ← Attacker console                        │
│  │  192.168.100.10  │                                            │
│  └──────────────────┘                                            │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ (Routed/Firewalled)
             │
┌────────────▼──────────────────────────────────────────────────────┐
│  DMZ Network (10.0.1.0/24)                                        │
│  ┌───────────────┐  ┌───────────────┐                            │
│  │  Web Server   │  │  DNS Server   │                            │
│  │  10.0.1.10    │  │  10.0.1.53    │                            │
│  │  (vulnerable) │  │  (vulnerable) │                            │
│  └───────────────┘  └───────────────┘                            │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │ (Firewall rules)
             │
┌────────────▼──────────────────────────────────────────────────────┐
│  Internal Network (10.0.2.0/24)                                   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐        │
│  │  App Server   │  │  DB Server    │  │  File Server  │        │
│  │  10.0.2.10    │  │  10.0.2.20    │  │  10.0.2.30    │        │
│  │  (vulnerable) │  │  (vulnerable) │  │  (SMB vuln)   │        │
│  └───────────────┘  └───────────────┘  └───────────────┘        │
└────────────┬──────────────────────────────────────────────────────┘
             │
             │
┌────────────▼──────────────────────────────────────────────────────┐
│  Management Network (10.0.3.0/24)                                 │
│  ┌───────────────┐  ┌───────────────┐                            │
│  │  Domain Ctrl  │  │  Admin WS     │                            │
│  │  10.0.3.10    │  │  10.0.3.20    │                            │
│  │  (AD vuln)    │  │  (client)     │                            │
│  └───────────────┘  └───────────────┘                            │
└───────────────────────────────────────────────────────────────────┘

Total: 9 VMs, 4 networks
```

---

## Key Architectural Decisions

### **1. Network Isolation**

#### **Proxmox Implementation**
```bash
# Create isolated bridges for each network
pvesh create /nodes/pve01/network --iface vmbr100 --type bridge --comments "Attack Network"
pvesh create /nodes/pve01/network --iface vmbr101 --type bridge --comments "DMZ"
pvesh create /nodes/pve01/network --iface vmbr102 --type bridge --comments "Internal"
pvesh create /nodes/pve01/network --iface vmbr103 --type bridge --comments "Management"

# VMs attach to specific bridges
# No routing between bridges unless explicitly configured
```

#### **AWS Implementation**
```hcl
# VPC with multiple subnets
resource "aws_vpc" "cyber_range" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "attack" {
  cidr_block = "10.0.1.0/24"
}

resource "aws_subnet" "dmz" {
  cidr_block = "10.0.2.0/24"
}

resource "aws_subnet" "internal" {
  cidr_block = "10.0.3.0/24"
}

# Security groups for isolation
```

#### **Azure Implementation**
```hcl
# Virtual Network with subnets
resource "azurerm_virtual_network" "cyber_range" {
  address_space = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "attack" {
  address_prefixes = ["10.0.1.0/24"]
}

# Network Security Groups for isolation
```

---

### **2. Attack Console Options**

#### **Option A: Kali Linux** ✅
**Pros:**
- Industry standard
- All tools pre-installed
- Well-known by users
- Community support

**Cons:**
- Large (20GB+)
- Bloated with tools you may not need
- Updates can break things

#### **Option B: Parrot Security** ✅
**Pros:**
- Lighter than Kali
- Good tool selection
- Nice UI

**Cons:**
- Less well-known
- Smaller community

#### **Option C: Custom Ubuntu-Based "Glassdome Console"** ⭐ RECOMMENDED
**Pros:**
- ✅ **Tight deployment** - Only what you need
- ✅ **Consistent** - Same base as vulnerable VMs
- ✅ **Branded** - "Glassdome Security Console"
- ✅ **Fast** - Minimal bloat
- ✅ **Controlled** - You choose the tools
- ✅ **Easy updates** - Ubuntu LTS base

**Cons:**
- Need to maintain tool list
- Need to create/document

**Recommended Tool List:**
```yaml
# glassdome/vulnerabilities/playbooks/console/glassdome_console.yml
---
- name: Install Glassdome Security Console
  hosts: console
  become: yes
  
  tasks:
    # Base system
    - name: Install base desktop
      apt:
        name:
          - ubuntu-desktop-minimal  # Or xfce4 for lighter
          - firefox
          - terminator
        state: present
    
    # Reconnaissance
    - name: Install recon tools
      apt:
        name:
          - nmap
          - masscan
          - nikto
          - dirb
          - gobuster
          - enum4linux
          - smbclient
          - ldapsearch
        state: present
    
    # Exploitation
    - name: Install exploitation frameworks
      apt:
        name:
          - metasploit-framework
          - sqlmap
          - john
          - hashcat
          - hydra
        state: present
    
    # Post-exploitation
    - name: Install post-exploitation tools
      apt:
        name:
          - netcat
          - socat
          - proxychains4
          - sshuttle
        state: present
    
    # Forensics/Analysis
    - name: Install analysis tools
      apt:
        name:
          - wireshark
          - tcpdump
          - binwalk
          - foremost
        state: present
    
    # Development/Scripting
    - name: Install dev tools
      apt:
        name:
          - python3-pip
          - git
          - vim
          - tmux
          - curl
          - jq
        state: present
    
    # Custom tools
    - name: Install Glassdome CLI
      pip:
        name: glassdome
        state: present
```

**Result:** ~5-8GB instead of 20GB+

---

### **3. Vulnerability as Package** 💡 BRILLIANT IDEA!

#### **Concept: Installable Vulnerability Packages**

Instead of:
```bash
# Complex Ansible playbook that might fail
ansible-playbook inject_sql_injection.yml
```

Do this:
```bash
# Install vulnerability as a package
apt install glassdome-vuln-sql-injection-dvwa
```

#### **How It Works**

**Create a `.deb` package:**
```
glassdome-vuln-sql-injection-dvwa_1.0_all.deb
├── DEBIAN/
│   ├── control              # Package metadata
│   ├── postinst             # Post-install script
│   └── prerm                # Pre-removal script
├── etc/
│   └── glassdome/
│       └── vulns/
│           └── sql-injection-dvwa.conf
├── var/www/html/
│   └── dvwa/                # Vulnerable web app
└── usr/share/doc/glassdome-vuln-sql-injection-dvwa/
    ├── README.md            # Vulnerability description
    ├── exploitation.md      # How to exploit
    └── detection.md         # How to detect
```

**DEBIAN/control:**
```
Package: glassdome-vuln-sql-injection-dvwa
Version: 1.0
Architecture: all
Maintainer: Glassdome Team <team@glassdome.local>
Depends: apache2, php, php-mysql, mysql-server
Description: DVWA SQL Injection Vulnerability
 Installs Damn Vulnerable Web Application configured with
 SQL injection vulnerabilities for training purposes.
 .
 WARNING: This package intentionally installs vulnerable
 software. Only use in isolated training environments.
```

**DEBIAN/postinst:**
```bash
#!/bin/bash
set -e

# Configure Apache
a2enmod php
systemctl restart apache2

# Setup database
mysql -e "CREATE DATABASE IF NOT EXISTS dvwa;"
mysql -e "CREATE USER IF NOT EXISTS 'dvwa'@'localhost' IDENTIFIED BY 'password';"
mysql -e "GRANT ALL PRIVILEGES ON dvwa.* TO 'dvwa'@'localhost';"

# Configure DVWA
cat > /var/www/html/dvwa/config/config.inc.php <<EOF
<?php
\$_DVWA['db_server'] = 'localhost';
\$_DVWA['db_database'] = 'dvwa';
\$_DVWA['db_user'] = 'dvwa';
\$_DVWA['db_password'] = 'password';
\$_DVWA['default_security_level'] = 'low';
EOF

echo "✅ SQL Injection vulnerability installed"
echo "Access at: http://$(hostname -I | awk '{print $1}')/dvwa"
echo "Username: admin"
echo "Password: password"
```

#### **Benefits of Vulnerability Packages**

✅ **Simple deployment:**
```bash
apt install glassdome-vuln-*  # Install all vulnerabilities
```

✅ **Version control:**
```bash
apt list --installed | grep glassdome-vuln
```

✅ **Easy removal:**
```bash
apt remove glassdome-vuln-sql-injection-dvwa
```

✅ **Dependencies handled:**
```
Depends: apache2, php, mysql-server
```

✅ **Documentation included:**
```bash
cat /usr/share/doc/glassdome-vuln-sql-injection-dvwa/exploitation.md
```

✅ **Reproducible:**
- Same .deb package = same vulnerability every time

✅ **Distributable:**
- Host your own APT repository
- `add-apt-repository ppa:glassdome/vulnerabilities`

---

### **4. vApp-like Deployment Model**

#### **Scenario Definition File**

```yaml
# scenarios/enterprise_web_app.yml
---
name: "Enterprise Web Application"
description: "Multi-tier web application with various vulnerabilities"
difficulty: intermediate
estimated_time: "2-3 hours"
objectives:
  - "Gain initial foothold via SQL injection"
  - "Escalate privileges on web server"
  - "Pivot to internal network"
  - "Compromise domain controller"
  - "Extract sensitive data"

networks:
  - name: attack
    cidr: "192.168.100.0/24"
    type: isolated
  
  - name: dmz
    cidr: "10.0.1.0/24"
    type: isolated
    routes:
      - to: attack
        ports: [80, 443, 53]
  
  - name: internal
    cidr: "10.0.2.0/24"
    type: isolated
    routes:
      - to: dmz
        ports: [3306, 1433]
  
  - name: management
    cidr: "10.0.3.0/24"
    type: isolated
    routes:
      - to: internal
        ports: [389, 88, 445]

machines:
  - name: attacker-console
    template: glassdome-console  # Custom Ubuntu console
    network: attack
    ip: 192.168.100.10
    cpu: 2
    memory: 4096
    packages: []  # No vulnerabilities
  
  - name: web-server
    template: ubuntu-22.04
    network: dmz
    ip: 10.0.1.10
    cpu: 2
    memory: 2048
    packages:
      - glassdome-vuln-sql-injection-dvwa
      - glassdome-vuln-xss-basic
      - glassdome-vuln-weak-sudo
  
  - name: dns-server
    template: ubuntu-22.04
    network: dmz
    ip: 10.0.1.53
    cpu: 1
    memory: 1024
    packages:
      - glassdome-vuln-dns-zone-transfer
  
  - name: app-server
    template: ubuntu-22.04
    network: internal
    ip: 10.0.2.10
    cpu: 2
    memory: 2048
    packages:
      - glassdome-vuln-java-deserialization
  
  - name: database-server
    template: ubuntu-22.04
    network: internal
    ip: 10.0.2.20
    cpu: 2
    memory: 4096
    packages:
      - glassdome-vuln-mysql-weak-auth
      - glassdome-vuln-mysql-priv-esc
  
  - name: file-server
    template: ubuntu-22.04
    network: internal
    ip: 10.0.2.30
    cpu: 2
    memory: 2048
    packages:
      - glassdome-vuln-smb-anonymous
      - glassdome-vuln-smb-eternal-blue
  
  - name: domain-controller
    template: ubuntu-22.04  # Or Windows Server
    network: management
    ip: 10.0.3.10
    cpu: 4
    memory: 4096
    packages:
      - glassdome-vuln-ad-kerberoast
      - glassdome-vuln-ad-weak-acls
  
  - name: admin-workstation
    template: ubuntu-22.04
    network: management
    ip: 10.0.3.20
    cpu: 2
    memory: 2048
    packages:
      - glassdome-vuln-weak-password

flags:
  - name: web_shell
    location: /var/www/html/flag1.txt
    content: "FLAG{sql_injection_successful}"
    machine: web-server
  
  - name: database_access
    location: /root/flag2.txt
    content: "FLAG{database_compromised}"
    machine: database-server
  
  - name: domain_admin
    location: /root/flag3.txt
    content: "FLAG{domain_admin_achieved}"
    machine: domain-controller

answer_key:
  path_1:
    - "1. SQL injection on web server (10.0.1.10/dvwa)"
    - "2. Upload web shell via file upload vulnerability"
    - "3. Reverse shell to attacker machine"
    - "4. Pivot to database server (10.0.2.20)"
    - "5. Extract credentials from database"
    - "6. Use credentials to access domain controller"
  
  detection_methods:
    - "Monitor for SQL injection patterns in web logs"
    - "Detect unusual database queries"
    - "Monitor for Kerberoasting activity"
    - "Detect lateral movement via SMB"
```

#### **Deployment Command**

```bash
# Deploy entire scenario
glassdome deploy scenario enterprise_web_app.yml

# Output:
# ✓ Creating networks (4)
# ✓ Deploying VMs (8)
# ✓ Installing vulnerability packages
# ✓ Configuring routing rules
# ✓ Planting flags
# ✓ Generating answer key
# 
# 🎯 Scenario deployed successfully!
# 
# Access console: ssh glassdome@192.168.100.10
# Objectives: 5
# Flags: 3
# Answer key: /tmp/enterprise_web_app_answer_key.pdf
```

---

## Implementation Strategy

### **Phase 1: Single Network (Current)**
- ✅ Single VM deployment
- ✅ Basic Proxmox integration
- Simple scenarios

### **Phase 2: Multiple Networks** (Next 2 weeks)
- Network creation in Proxmox/Cloud
- Multi-VM deployment
- Basic routing

### **Phase 3: Vulnerability Packages** (3-4 weeks)
- Create `.deb` package builder
- Package 5-10 common vulnerabilities
- Host APT repository

### **Phase 4: vApp Scenarios** (VP Demo)
- YAML scenario definitions
- Full orchestration
- Answer key generation
- Console VM with tools

---

## Technical Considerations

### **Network Isolation in Proxmox**
```bash
# Create VLANs
pvesh create /nodes/pve01/network --iface vmbr0.100 --type vlan
pvesh create /nodes/pve01/network --iface vmbr0.101 --type vlan

# Or separate bridges
pvesh create /nodes/pve01/network --iface vmbr100 --type bridge
```

### **Routing Between Networks**
```bash
# Use a VM as a router/firewall
# Install: iptables, nftables, or pfSense
iptables -A FORWARD -s 10.0.1.0/24 -d 10.0.2.0/24 -p tcp --dport 3306 -j ACCEPT
iptables -A FORWARD -s 10.0.1.0/24 -d 10.0.2.0/24 -j DROP
```

### **Package Repository**
```bash
# Create local APT repository
mkdir -p /var/www/html/glassdome/dists/stable/main/binary-amd64
dpkg-scanpackages . | gzip -9c > Packages.gz

# Client configuration
echo "deb [trusted=yes] http://repo.glassdome.local/glassdome stable main" > /etc/apt/sources.list.d/glassdome.list
apt update
apt install glassdome-vuln-*
```

---

## Advantages of This Architecture

### **For Users:**
1. **Simple deployment** - One command deploys entire scenario
2. **Realistic** - Multi-tier networks like real environments
3. **Progressive** - Start simple, add networks as needed
4. **Fast** - Vulnerability packages install in seconds

### **For Development:**
1. **Modular** - Vulnerabilities are independent packages
2. **Testable** - Test packages independently
3. **Maintainable** - Update one package without affecting others
4. **Distributable** - Share packages easily

### **For VP Demo:**
1. **Impressive** - Deploy 9-VM scenario in < 5 minutes
2. **Professional** - Industry-standard packaging
3. **Scalable** - Add more scenarios easily
4. **Unique** - No one else packages vulnerabilities like this!

---

## Questions to Consider

1. **Console Distribution:**
   - ISO download?
   - Template on deployment?
   - Pre-built on Proxmox?

2. **Package Repository:**
   - Self-hosted?
   - Public repo?
   - Built-in to Glassdome?

3. **Windows Support:**
   - Need Windows VMs for AD scenarios?
   - How to handle licensing?
   - Chocolatey packages for Windows vulnerabilities?

4. **Scenario Library:**
   - Pre-built scenarios?
   - Community contributions?
   - Marketplace?

5. **Networking Complexity:**
   - Simple (isolated subnets)?
   - Advanced (VLANs, VRF)?
   - Firewall rules?

---

## Recommendation

**Build in this order:**

1. **Week 1-2:** Multi-network support (multiple VLANs/subnets)
2. **Week 3:** Custom console VM (Ubuntu + tools list)
3. **Week 4-5:** Vulnerability packaging system (5 example packages)
4. **Week 6:** Scenario orchestration (vApp-like deployment)
5. **Week 7-8:** Polish for VP demo

**This gives you a complete, impressive system for the 12/8 presentation!**

---

*This architecture transforms Glassdome from a "VM deployer" to a "complete cyber range platform"* 🚀

