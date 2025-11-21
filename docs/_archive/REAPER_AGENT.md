# Reaper Agent - Vulnerability Injection for Cyber Range Training

## Purpose

The **Reaper Agent** is responsible for taking clean VM deployments and intentionally introducing vulnerabilities, misconfigurations, and training scenarios for defensive cybersecurity training (blue team).

> **ETHICAL STATEMENT:** This system uses legitimate credentials and superuser access to create controlled training environments. It is designed exclusively for defensive security training in isolated lab environments. This is identical to platforms like Hack The Box, TryHackMe, Cyber Range, and Cloud Range.

---

## Complete Deployment Pipeline

```
1. Ubuntu Agent    → Deploy clean VM
2. Cloud-Init      → Configure users, packages
3. Reaper Agent    → Inject vulnerabilities ← YOU ARE HERE
4. Overseer Agent  → Monitor for training
```

---

## What the Reaper Agent Does

### Core Responsibilities

1. **Vulnerability Injection**
   - Install intentionally vulnerable software
   - Create security misconfigurations
   - Introduce weak credentials
   - Plant backdoors (for training detection)

2. **Scenario Creation**
   - CTF flags placement
   - Log manipulation for forensics training
   - Network misconfigurations
   - Web application vulnerabilities

3. **Documentation Generation**
   - "Answer key" for instructors
   - Vulnerability manifest
   - Expected detection methods
   - Remediation steps

4. **Reversibility**
   - Clean removal of training artifacts
   - VM reset to baseline
   - Snapshot management

---

## Agent Architecture

### Base Class Integration

```python
from glassdome.agents.base import DeploymentAgent

class ReaperAgent(DeploymentAgent):
    """
    Injects vulnerabilities into clean VMs for training scenarios.
    
    This agent uses SSH and API credentials to intentionally create
    security issues in isolated training environments.
    """
    
    def __init__(self):
        super().__init__(
            name="Reaper",
            version="1.0.0",
            capabilities=[
                "vulnerability_injection",
                "misconfiguration",
                "ctf_setup",
                "scenario_creation"
            ]
        )
        self.vulnerability_library = VulnerabilityLibrary()
        self.scenario_templates = ScenarioTemplates()
    
    async def inject_vulnerabilities(
        self,
        vm_id: str,
        scenario_type: str,
        difficulty: str = "medium",
        custom_vulns: List[str] = None
    ) -> Dict[str, Any]:
        """
        Inject vulnerabilities based on scenario type.
        
        Args:
            vm_id: Target VM identifier
            scenario_type: Type of training (web, network, forensics, etc.)
            difficulty: easy, medium, hard, expert
            custom_vulns: Specific vulnerabilities to include
            
        Returns:
            Dictionary containing:
            - vulnerabilities_injected: List of vulnerabilities
            - flags_planted: CTF flags (if applicable)
            - answer_key: Instructor documentation
            - reset_procedure: How to clean up
        """
        pass
```

---

## Vulnerability Categories

### 1. Web Application Vulnerabilities

**Easy:**
- SQL injection (basic)
- Cross-site scripting (XSS)
- Directory traversal
- Weak passwords on web admin

**Medium:**
- Command injection
- File upload bypass
- Authentication bypass
- Session hijacking setup

**Hard:**
- Deserialization exploits
- Server-side template injection
- Advanced SQLi (blind, time-based)
- XXE (XML External Entity)

**Expert:**
- Race conditions
- Type confusion
- Prototype pollution
- Advanced authentication bypass

### 2. Network Vulnerabilities

**Easy:**
- Open SMB shares
- Telnet enabled
- FTP anonymous login
- Weak WPA2 keys (WiFi scenarios)

**Medium:**
- Misconfigured NFS
- SNMP weak community strings
- RDP exposed with weak creds
- Vulnerable VPN configs

**Hard:**
- VLAN hopping setup
- Man-in-the-middle scenarios
- DNS spoofing/cache poisoning
- IPsec misconfigurations

### 3. System Misconfigurations

**Easy:**
- World-writable files
- Sudo misconfigurations
- Weak file permissions
- Unpatched services

**Medium:**
- SUID binary exploitation
- Cron job abuse
- PATH hijacking setups
- Kernel exploit conditions

**Hard:**
- Container escape scenarios
- Privilege escalation chains
- Advanced persistence mechanisms

### 4. Forensics & Incident Response

**Easy:**
- Planted log files
- Simple malware samples (benign)
- Modified system files
- Suspicious user accounts

**Medium:**
- Log tampering (incomplete deletion)
- Memory artifacts
- Network traffic captures
- File carving scenarios

**Hard:**
- Anti-forensics techniques
- Rootkit detection scenarios
- Timeline reconstruction
- Steganography

---

## Scenario Templates

### Web Security Lab (DVWA-style)

```python
{
    "name": "Web Application Security",
    "difficulty": "medium",
    "vms": [
        {
            "role": "vulnerable_web_server",
            "vulnerabilities": [
                "sql_injection_basic",
                "xss_reflected",
                "command_injection",
                "file_upload_bypass",
                "weak_admin_password"
            ],
            "services": [
                "apache2",
                "mysql",
                "php"
            ],
            "flags": [
                {"name": "flag1", "location": "/var/www/html/secret.txt"},
                {"name": "flag2", "location": "database:users:admin:notes"},
                {"name": "flag3", "location": "/root/proof.txt"}
            ]
        }
    ],
    "learning_objectives": [
        "Identify SQL injection vulnerabilities",
        "Exploit XSS for session hijacking",
        "Escalate privileges via command injection",
        "Understand secure coding practices"
    ]
}
```

### Network Defense Lab

```python
{
    "name": "Network Security Monitoring",
    "difficulty": "medium",
    "vms": [
        {
            "role": "vulnerable_file_server",
            "vulnerabilities": [
                "smb_anonymous_access",
                "weak_ftp_credentials",
                "nfs_misconfiguration",
                "outdated_samba_version"
            ]
        },
        {
            "role": "attacker_simulation",
            "purpose": "Generates realistic attack traffic",
            "behaviors": [
                "port_scanning",
                "smb_enumeration",
                "brute_force_attempts",
                "exfiltration_simulation"
            ]
        },
        {
            "role": "siem_monitor",
            "purpose": "Blue team monitoring station",
            "tools": [
                "security_onion",
                "splunk",
                "wireshark"
            ]
        }
    ]
}
```

### CTF Lab

```python
{
    "name": "Capture The Flag Challenge",
    "difficulty": "hard",
    "vms": [
        {
            "role": "ctf_target",
            "flags": 10,
            "vulnerability_chain": [
                "web_recon → sqli → file_read → ssh_key → privilege_escalation → root_flag"
            ],
            "hints": {
                "level1": "Check robots.txt",
                "level2": "SQL injection in login form",
                "level3": "Look for backup files",
                "level4": "Check sudo permissions",
                "level5": "SUID binaries"
            }
        }
    ],
    "time_limit": "2 hours",
    "scoring": {
        "flag1": 10,
        "flag2": 15,
        "flag3": 20,
        "flag4": 25,
        "flag5": 30
    }
}
```

---

## Implementation Phases

### Phase 1: Basic Vulnerability Injection (Sprint 1)

**Must-Have for VP Demo:**

1. **Web Vulnerabilities** (2 days)
   - Install DVWA or similar
   - Plant SQLi vulnerability
   - Configure weak passwords
   - Add XSS examples

2. **System Misconfigurations** (1 day)
   - Weak sudo permissions
   - World-writable files
   - Exposed configuration files

3. **CTF Flag Planting** (1 day)
   - Text-based flags in files
   - Database flags
   - Hidden directory flags

**Deliverable:** Deploy vulnerable web server with 3 exploitable issues

---

### Phase 2: Advanced Scenarios (Sprint 2)

1. **Network Vulnerabilities**
   - SMB misconfigurations
   - Weak SSH configs
   - FTP anonymous access

2. **Multi-VM Attack Chains**
   - Initial foothold on VM1
   - Lateral movement to VM2
   - Privilege escalation on VM3

3. **Forensics Scenarios**
   - Planted log files
   - Modified timestamps
   - Hidden artifacts

---

### Phase 3: Automation & Templates (Sprint 3)

1. **Scenario Library**
   - 5+ pre-built scenarios
   - Configurable difficulty
   - Instructor answer keys

2. **Custom Scenario Builder**
   - Mix-and-match vulnerabilities
   - Custom flag placement
   - Learning objectives

3. **Reset & Cleanup**
   - Automated VM reset
   - Snapshot management
   - Student progress tracking

---

## Technical Implementation

### Vulnerability Library Structure

```python
# glassdome/vulnerabilities/library.py

class VulnerabilityLibrary:
    """
    Centralized library of injectable vulnerabilities.
    """
    
    def __init__(self):
        self.vulnerabilities = {
            "web": {
                "sql_injection_basic": SQLInjectionBasic(),
                "xss_reflected": XSSReflected(),
                "command_injection": CommandInjection(),
                # ... more
            },
            "network": {
                "smb_anonymous": SMBAnonymousAccess(),
                "weak_ssh": WeakSSHConfig(),
                # ... more
            },
            "system": {
                "weak_sudo": WeakSudoConfig(),
                "suid_exploit": SUIDExploitSetup(),
                # ... more
            }
        }
    
    def get_vulnerability(self, category: str, name: str):
        """Retrieve a specific vulnerability handler."""
        return self.vulnerabilities[category][name]
    
    def list_by_difficulty(self, difficulty: str):
        """Get all vulnerabilities of a given difficulty."""
        pass
```

### Individual Vulnerability Modules

```python
# glassdome/vulnerabilities/web/sql_injection.py

from glassdome.vulnerabilities.base import VulnerabilityBase

class SQLInjectionBasic(VulnerabilityBase):
    """
    Injects a basic SQL injection vulnerability.
    """
    
    metadata = {
        "name": "Basic SQL Injection",
        "category": "web",
        "difficulty": "easy",
        "cvss": 8.5,
        "cwe": "CWE-89",
        "description": "Login form vulnerable to SQL injection (1=1 bypass)",
        "learning_objectives": [
            "Identify SQL injection points",
            "Understand authentication bypass",
            "Practice input validation"
        ],
        "detection_methods": [
            "Web application firewall logs",
            "Database query monitoring",
            "Abnormal authentication patterns"
        ],
        "remediation": [
            "Use parameterized queries",
            "Implement input validation",
            "Apply least privilege to database users"
        ]
    }
    
    async def inject(self, ssh_client, vm_config):
        """
        Inject SQL injection vulnerability into web application.
        """
        # Install vulnerable web app
        await ssh_client.execute(
            "apt-get install -y apache2 php mysql-server php-mysql"
        )
        
        # Deploy vulnerable PHP code
        vulnerable_code = """
        <?php
        $username = $_POST['username'];
        $password = $_POST['password'];
        
        // VULNERABLE: No input sanitization
        $query = "SELECT * FROM users WHERE username='$username' AND password='$password'";
        $result = mysqli_query($conn, $query);
        
        if (mysqli_num_rows($result) > 0) {
            echo "Login successful!";
        }
        ?>
        """
        
        await ssh_client.put_file(
            content=vulnerable_code,
            remote_path="/var/www/html/login.php"
        )
        
        # Create flag
        await ssh_client.execute(
            "echo 'FLAG{sql_1nj3ct10n_1s_d4ng3r0us}' > /var/www/html/flag1.txt"
        )
        
        # Set permissions
        await ssh_client.execute(
            "chmod 600 /var/www/html/flag1.txt"
        )
        
        return {
            "vulnerability": "sql_injection_basic",
            "location": "/var/www/html/login.php",
            "exploit_hint": "Try: admin' OR '1'='1",
            "flag_location": "/var/www/html/flag1.txt",
            "flag_value": "FLAG{sql_1nj3ct10n_1s_d4ng3r0us}"
        }
    
    def generate_answer_key(self):
        """
        Generate instructor documentation.
        """
        return {
            "vulnerability": self.metadata["name"],
            "location": "/var/www/html/login.php",
            "exploitation_steps": [
                "1. Navigate to http://VM_IP/login.php",
                "2. Enter username: admin' OR '1'='1",
                "3. Enter any password",
                "4. Authentication bypass successful",
                "5. Access flag at /var/www/html/flag1.txt"
            ],
            "expected_blue_team_actions": [
                "Identify suspicious SQL query in logs",
                "Block IP address attempting injection",
                "Patch vulnerable code",
                "Implement WAF rules",
                "Alert on authentication anomalies"
            ],
            "remediation": self.metadata["remediation"]
        }
```

---

## API Endpoints

### Reaper Agent REST API

```python
# glassdome/api/reaper.py

from fastapi import APIRouter, HTTPException
from glassdome.agents.reaper import ReaperAgent
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/reaper", tags=["reaper"])
reaper = ReaperAgent()

class VulnerabilityInjectionRequest(BaseModel):
    vm_id: str
    scenario_type: str  # "web", "network", "forensics", "ctf"
    difficulty: str = "medium"
    custom_vulnerabilities: List[str] = []
    generate_answer_key: bool = True

@router.post("/inject")
async def inject_vulnerabilities(request: VulnerabilityInjectionRequest):
    """
    Inject vulnerabilities into a VM for training.
    """
    try:
        result = await reaper.inject_vulnerabilities(
            vm_id=request.vm_id,
            scenario_type=request.scenario_type,
            difficulty=request.difficulty,
            custom_vulns=request.custom_vulnerabilities
        )
        
        return {
            "status": "success",
            "vm_id": request.vm_id,
            "vulnerabilities_injected": result["vulnerabilities"],
            "flags_planted": result.get("flags", []),
            "answer_key_id": result.get("answer_key_id") if request.generate_answer_key else None,
            "scenario_url": f"http://{result['vm_ip']}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scenarios")
async def list_scenarios():
    """
    List all available training scenarios.
    """
    return reaper.scenario_templates.list_all()

@router.get("/vulnerabilities")
async def list_vulnerabilities(
    category: str = None,
    difficulty: str = None
):
    """
    List available vulnerabilities.
    """
    return reaper.vulnerability_library.filter(
        category=category,
        difficulty=difficulty
    )

@router.get("/answer-key/{scenario_id}")
async def get_answer_key(scenario_id: str):
    """
    Retrieve instructor answer key for a scenario.
    """
    return await reaper.get_answer_key(scenario_id)

@router.post("/reset/{vm_id}")
async def reset_vm(vm_id: str):
    """
    Reset VM to clean state (remove all vulnerabilities).
    """
    return await reaper.reset_vm(vm_id)
```

---

## Complete Deployment Flow

### With Reaper Agent

```python
# Example: Deploy vulnerable web security lab

from glassdome.orchestration.lab_orchestrator import LabOrchestrator
from glassdome.agents.reaper import ReaperAgent

# Step 1: Deploy clean VM
orchestrator = LabOrchestrator()
deployment = await orchestrator.deploy_lab({
    "name": "Web Security Training Lab",
    "vms": [
        {
            "hostname": "web-vulnerable-001",
            "template_id": 9000,
            "memory": 2048,
            "cores": 2
        }
    ]
})

vm_id = deployment["vms"][0]["id"]

# Step 2: Inject vulnerabilities
reaper = ReaperAgent()
vuln_result = await reaper.inject_vulnerabilities(
    vm_id=vm_id,
    scenario_type="web_security",
    difficulty="medium",
    custom_vulns=["sql_injection_basic", "xss_reflected", "command_injection"]
)

# Step 3: Generate instructor materials
answer_key = reaper.generate_answer_key(vuln_result["scenario_id"])

print(f"Lab ready at: http://{vuln_result['vm_ip']}")
print(f"Flags planted: {vuln_result['flags_planted']}")
print(f"Answer key: {answer_key['url']}")
```

---

## Security & Ethical Considerations

### Isolation Requirements

1. **Network Isolation**
   - All vulnerable VMs must be in isolated networks
   - No direct internet access
   - Firewall rules prevent escape

2. **Access Controls**
   - Only authorized instructors can deploy
   - Student access restricted to training VMs
   - Audit logging of all actions

3. **Vulnerability Constraints**
   - No actual malware deployment
   - No real exploitation tools on attack VMs
   - Simulated attacks only

4. **Data Protection**
   - No real user data in training VMs
   - Synthetic data only
   - GDPR/compliance friendly

### Legal & Compliance

- **Purpose:** Defensive training only (blue team)
- **Authorization:** All actions performed with legitimate credentials
- **Isolation:** Lab environments completely isolated
- **Similarity:** Identical to Hack The Box, TryHackMe, Cyber Range platforms
- **Documentation:** All vulnerabilities documented for instructors

---

## VP Demo Integration

### Updated Demo Flow

**Scenario 1: Deploy Vulnerable Web Lab (5 minutes)**

1. Select "Web Security Training Lab" template
2. Click "Deploy with Vulnerabilities"
3. Watch:
   - Clean VM deployment (30 sec)
   - Reaper agent injects SQLi, XSS, weak passwords (2 min)
   - Flags planted automatically
   - Answer key generated
4. Show:
   - Live vulnerable web app
   - Instructor dashboard with answer key
   - Student instructions

**Key Talking Points:**
- "From zero to vulnerable training environment in 3 minutes"
- "Automatically generates instructor materials"
- "Students get hands-on practice, not just slides"
- "Reset and redeploy in seconds"

---

## Priority for Roadmap

### Critical for VP Demo (Sprint 1)

**Days 3-4: Reaper Agent Basics**
- [ ] Implement base vulnerability injection
- [ ] Create DVWA-style web vulnerabilities
- [ ] Plant 3-5 CTF flags
- [ ] Generate simple answer key

**Deliverable:** Deploy web server with injectable SQLi + XSS

### Sprint 2: Expand Scenarios

- [ ] Network vulnerabilities (SMB, SSH)
- [ ] System misconfigurations
- [ ] Multi-VM attack chains
- [ ] Forensics scenarios

### Sprint 3: Polish

- [ ] Scenario templates library
- [ ] Instructor dashboard
- [ ] Answer key system
- [ ] Reset/cleanup automation

---

## This Is The Differentiator!

**Why Glassdome is unique:**
- NOT just VM deployment (commodity)
- NOT just lab management (existing tools do this)
- **COMPLETE training pipeline** (deploy → inject vulns → monitor → reset)

**Competitive advantage:**
- Hack The Box: Manual CTF creation
- TryHackMe: Curated content only
- Cyber Range: Expensive proprietary
- **Glassdome: Automated, customizable, self-service** ✨

---

## Next Steps

1. Implement basic `ReaperAgent` class
2. Create first vulnerability module (SQLi)
3. Test injection on deployed VM
4. Generate answer key
5. Integrate with orchestrator

**This is what will make the VP say "wow!"** 🚀

