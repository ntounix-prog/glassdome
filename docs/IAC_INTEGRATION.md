# Infrastructure as Code (IaC) Integration

## Overview

Glassdome integrates **Ansible** and **Terraform** to provide declarative, version-controlled, and reproducible infrastructure and vulnerability deployment.

---

## Why IaC?

### **Before IaC**
```python
# Brittle SSH commands
await ssh.execute("apt-get install apache2")
await ssh.execute("wget http://...")
await ssh.execute("configure...")
# Hard to maintain, test, or version control
```

### **With IaC**
```yaml
# Ansible playbook - declarative, idempotent, testable
- name: Install DVWA
  apt:
    name: ['apache2', 'php', 'mysql']
    state: present
```

**Benefits:**
- ✅ Declarative (what, not how)
- ✅ Idempotent (safe to run multiple times)
- ✅ Version controlled (Git-friendly)
- ✅ Testable (test playbooks independently)
- ✅ Community contributions (standard formats)

---

## Architecture

### **Hybrid Approach**

```
┌────────────────────────────────────────────────┐
│           Research Agent (AI)                   │
│  Generates Infrastructure + Configuration       │
└───────────────┬────────────────────────────────┘
                │
     ┌──────────┴──────────┐
     │                     │
     ▼                     ▼
┌─────────────┐      ┌─────────────┐
│  Terraform  │      │   Ansible   │
│  (Infra)    │      │   (Config)  │
└──────┬──────┘      └──────┬──────┘
       │                    │
       ▼                    ▼
   Creates VM         Injects Vulnerability
```

### **What Uses What**

| Task | Tool | Reason |
|------|------|--------|
| **Proxmox deployment** | Custom API | Fast, direct, works well |
| **Azure deployment** | Terraform | Industry standard, mature |
| **AWS deployment** | Terraform | Industry standard, mature |
| **Vulnerability injection** | Ansible | Declarative, testable |
| **Configuration management** | Ansible | Idempotent, maintainable |

---

## Installation

### **Quick Install**

```bash
# Run the installer
bash scripts/setup/install_iac_tools.sh
```

This installs:
1. **Ansible** - Configuration management
2. **Terraform** - Infrastructure provisioning
3. **Python packages** - `ansible` and `python-terraform`

### **Verify Installation**

```bash
# Check installations
python scripts/tools/verify_iac_tools.py

# Or manually:
ansible --version
terraform version
```

---

## Directory Structure

```
glassdome/
├── vulnerabilities/
│   ├── playbooks/           # Ansible playbooks
│   │   ├── web/
│   │   │   ├── sql_injection.yml
│   │   │   ├── xss.yml
│   │   │   └── dvwa.yml
│   │   ├── network/
│   │   │   ├── smb_anonymous.yml
│   │   │   └── weak_ssh.yml
│   │   ├── system/
│   │   │   └── weak_sudo.yml
│   │   └── forensics/
│   │       └── log_tampering.yml
│   │
│   └── terraform/           # Terraform modules
│       ├── aws/
│       │   ├── vulnerable_web/
│       │   └── network_lab/
│       └── azure/
│           ├── vulnerable_web/
│           └── network_lab/
│
└── agents/
    ├── ansible_agent.py     # Executes Ansible playbooks
    └── terraform_agent.py   # Executes Terraform configs
```

---

## Usage Examples

### **Example 1: Deploy with Ansible**

```python
from glassdome.agents.ansible_agent import AnsibleAgent

# Initialize agent
ansible = AnsibleAgent()

# Run playbook
result = await ansible.run_playbook(
    playbook="glassdome/vulnerabilities/playbooks/web/sql_injection.yml",
    hosts=["192.168.1.100"],
    variables={
        "admin_password": "P@ssw0rd",
        "flag_content": "FLAG{sql_injection_found}"
    }
)

print(f"Playbook executed: {result['success']}")
print(f"Tasks run: {result['tasks_run']}")
print(f"Changed: {result['changed']}")
```

### **Example 2: Deploy with Terraform**

```python
from glassdome.agents.terraform_agent import TerraformAgent

# Initialize agent
terraform = TerraformAgent()

# Apply configuration
result = await terraform.apply(
    module="glassdome/vulnerabilities/terraform/aws/vulnerable_web",
    variables={
        "instance_type": "t2.micro",
        "region": "us-east-1",
        "lab_name": "CVE-2024-12345"
    }
)

print(f"Infrastructure created: {result['success']}")
print(f"Resources: {result['resources_created']}")
print(f"VM IP: {result['outputs']['vm_ip']}")
```

### **Example 3: Full Deployment (Research Agent → Terraform → Ansible)**

```python
from glassdome.agents.research import ResearchAgent
from glassdome.agents.terraform_agent import TerraformAgent
from glassdome.agents.ansible_agent import AnsibleAgent

# Step 1: Research CVE
research = ResearchAgent()
analysis = await research.research_vulnerability("CVE-2024-12345")

# Step 2: Deploy infrastructure (Terraform)
terraform = TerraformAgent()
infra = await terraform.apply(
    config=analysis["terraform_config"]
)

# Step 3: Inject vulnerability (Ansible)
ansible = AnsibleAgent()
vuln = await ansible.run_playbook(
    playbook_content=analysis["ansible_playbook"],
    hosts=[infra["vm_ip"]]
)

# Result: Fully deployed vulnerable environment
print(f"Lab ready at: {infra['vm_ip']}")
print(f"Vulnerabilities: {vuln['vulns_injected']}")
```

---

## Ansible Playbook Template

### **Example: SQL Injection Vulnerability**

```yaml
# glassdome/vulnerabilities/playbooks/web/sql_injection.yml
---
- name: Deploy SQL Injection Vulnerable Environment
  hosts: all
  become: yes
  
  vars:
    db_password: "{{ admin_password | default('password') }}"
    flag: "{{ flag_content | default('FLAG{default_flag}') }}"
  
  tasks:
    - name: Install Apache, PHP, MySQL
      apt:
        name:
          - apache2
          - php
          - php-mysql
          - mysql-server
        state: present
        update_cache: yes
    
    - name: Start services
      service:
        name: "{{ item }}"
        state: started
        enabled: yes
      loop:
        - apache2
        - mysql
    
    - name: Create vulnerable login script
      copy:
        dest: /var/www/html/login.php
        content: |
          <?php
          $conn = mysqli_connect("localhost", "root", "{{ db_password }}");
          
          // VULNERABLE: No input sanitization
          $username = $_POST['username'];
          $password = $_POST['password'];
          
          $query = "SELECT * FROM users WHERE username='$username' AND password='$password'";
          $result = mysqli_query($conn, $query);
          
          if (mysqli_num_rows($result) > 0) {
              echo "Login successful!";
          } else {
              echo "Login failed!";
          }
          ?>
        mode: '0644'
    
    - name: Create database and vulnerable table
      shell: |
        mysql -e "CREATE DATABASE IF NOT EXISTS vulnerable_app;"
        mysql -e "CREATE TABLE IF NOT EXISTS vulnerable_app.users (id INT, username VARCHAR(50), password VARCHAR(50));"
        mysql -e "INSERT INTO vulnerable_app.users VALUES (1, 'admin', 'admin');"
    
    - name: Plant CTF flag
      copy:
        content: "{{ flag }}"
        dest: /root/flag.txt
        mode: '0600'
    
    - name: Create answer key
      copy:
        dest: /root/answer_key.txt
        content: |
          SQL Injection Vulnerability Lab
          ================================
          
          Vulnerability: SQL Injection in login.php
          
          Exploitation:
          1. Navigate to http://{{ ansible_host }}/login.php
          2. Username: admin' OR '1'='1
          3. Password: anything
          4. Result: Authentication bypass
          
          Flag Location: /root/flag.txt
          Flag Value: {{ flag }}
          
          Detection:
          - Monitor MySQL query logs for OR statements
          - Check for authentication without valid credentials
          - WAF rules for SQL keywords in POST data
          
          Remediation:
          - Use prepared statements
          - Implement input validation
          - Apply least privilege to database users
        mode: '0600'

  handlers:
    - name: Restart Apache
      service:
        name: apache2
        state: restarted
```

---

## Terraform Module Template

### **Example: AWS Vulnerable Web Server**

```hcl
# glassdome/vulnerabilities/terraform/aws/vulnerable_web/main.tf

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "lab_name" {
  description = "Name of the lab"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "ssh_key_name" {
  description = "SSH key name for access"
  type        = string
}

provider "aws" {
  region = var.region
}

# Security group - intentionally permissive for lab
resource "aws_security_group" "vulnerable_web" {
  name        = "${var.lab_name}-sg"
  description = "Security group for vulnerable web lab"
  
  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Outbound
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name    = "${var.lab_name}-sg"
    Purpose = "vulnerability-lab"
    Managed = "glassdome"
  }
}

# EC2 instance
resource "aws_instance" "vulnerable_web" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  key_name      = var.ssh_key_name
  
  vpc_security_group_ids = [aws_security_group.vulnerable_web.id]
  
  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y python3 python3-pip
              # Prepare for Ansible
              EOF
  
  tags = {
    Name    = var.lab_name
    Purpose = "vulnerability-lab"
    Managed = "glassdome"
  }
}

# Data source for Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# Outputs
output "vm_ip" {
  description = "Public IP of the VM"
  value       = aws_instance.vulnerable_web.public_ip
}

output "vm_id" {
  description = "Instance ID"
  value       = aws_instance.vulnerable_web.id
}

output "ssh_command" {
  description = "SSH command to connect"
  value       = "ssh -i ~/.ssh/${var.ssh_key_name}.pem ubuntu@${aws_instance.vulnerable_web.public_ip}"
}
```

---

## Agent Implementation (Coming Soon)

### **AnsibleAgent**

```python
# glassdome/agents/ansible_agent.py

class AnsibleAgent(DeploymentAgent):
    """Execute Ansible playbooks for vulnerability injection"""
    
    async def run_playbook(
        self,
        playbook: str,
        hosts: List[str],
        variables: Dict = None
    ) -> Dict:
        """Run Ansible playbook"""
        # Implementation in next phase
        pass
```

### **TerraformAgent**

```python
# glassdome/agents/terraform_agent.py

class TerraformAgent(DeploymentAgent):
    """Execute Terraform for infrastructure provisioning"""
    
    async def apply(
        self,
        module: str,
        variables: Dict = None
    ) -> Dict:
        """Apply Terraform configuration"""
        # Implementation in next phase
        pass
```

---

## Roadmap

### **Phase 1: Foundation** ✅
- [x] Install Ansible and Terraform
- [x] Create directory structure
- [x] Verification tools

### **Phase 2: Ansible Integration** (Next)
- [ ] Implement `AnsibleAgent`
- [ ] Create 5 example playbooks
- [ ] Test on deployed VMs
- [ ] Documentation

### **Phase 3: Terraform Integration**
- [ ] Implement `TerraformAgent`
- [ ] Create AWS modules
- [ ] Create Azure modules
- [ ] Test cloud deployments

### **Phase 4: Research Agent Integration**
- [ ] Update Research Agent to generate playbooks
- [ ] Update Research Agent to generate Terraform
- [ ] End-to-end CVE deployment
- [ ] Answer key generation

### **Phase 5: Production**
- [ ] Convert existing vulnerabilities to playbooks
- [ ] Multi-cloud testing
- [ ] VP demo preparation
- [ ] Documentation completion

---

## Benefits

### **For Development**
- Faster iteration (test playbooks independently)
- Better testing (ansible-lint, terraform validate)
- Clear documentation (playbooks are self-documenting)

### **For Users**
- Reproducible environments
- Version-controlled labs
- Community contributions easy
- Standard tools (Ansible/Terraform skills transferable)

### **For Operations**
- Idempotent (safe to re-run)
- State management (Terraform tracks resources)
- Auditable (Git history)
- Rollback-friendly

---

## Next Steps

1. **Install tools:**
   ```bash
   bash scripts/setup/install_iac_tools.sh
   ```

2. **Verify:**
   ```bash
   python scripts/tools/verify_iac_tools.py
   ```

3. **Create first playbook:**
   - Start with a simple vulnerability
   - Test on a VM
   - Add to library

4. **Implement agents:**
   - Build `AnsibleAgent`
   - Build `TerraformAgent`
   - Integrate with orchestrator

---

**This integration will make Glassdome production-ready and enable the VP demo vision!** 🚀

