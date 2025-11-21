# Glassdome Agents

**Agentic Framework:** Autonomous, specialized agents for deployment, research, and vulnerability injection.

---

## Agent Types

```
BaseAgent (Abstract)
├── UbuntuInstallerAgent    - Deploy Ubuntu VMs
├── WindowsInstallerAgent   - Deploy Windows VMs  
├── OverseerAgent           - Monitor infrastructure
├── ReaperAgent             - Inject vulnerabilities
└── ResearchAgent           - AI-powered CVE analysis
```

---

## Base Agent

**Purpose:** Shared logic for all agents

**Location:** `glassdome/agents/base.py`

**Interface:**
```python
class BaseAgent(ABC):
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        self.error = None
        
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task - implemented by subclasses"""
        pass
        
    def validate(self, task: Dict[str, Any]) -> bool:
        """Validate task parameters"""
        required_fields = self.get_required_fields()
        return all(field in task for field in required_fields)
        
    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Return required task fields"""
        pass
```

**Agent Status:**
- `IDLE` - Waiting for task
- `VALIDATING` - Checking parameters
- `RUNNING` - Executing task
- `COMPLETED` - Success
- `FAILED` - Error occurred

**Agent Type:**
- `DEPLOYMENT` - VM/infrastructure creation
- `MONITORING` - Status tracking
- `RESEARCH` - AI-powered analysis
- `VULNERABILITY` - Exploit injection

---

## Ubuntu Installer Agent

**Purpose:** Deploy Ubuntu VMs across all platforms

**Location:** `glassdome/agents/ubuntu_installer.py`

**Supported Versions:**
- Ubuntu 22.04 (Jammy)
- Ubuntu 20.04 (Focal)
- Ubuntu 24.04 (Noble) - future

**Platforms:**
- ✅ Proxmox (template clone + cloud-init)
- ✅ ESXi (VMDK + NoCloud ISO)
- ✅ AWS (EC2 + UserData)
- ✅ Azure (VM + Custom Data)

**Usage:**
```python
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
from glassdome.platforms.proxmox_client import ProxmoxClient

# Initialize
client = ProxmoxClient(...)
agent = UbuntuInstallerAgent(client)

# Execute
task = {
    "name": "web-server-01",
    "version": "22.04",
    "cores": 2,
    "memory": 4096,
    "disk_size_gb": 20,
    "ssh_user": "ubuntu",
    "ssh_public_key": "ssh-rsa AAAA...",
    "packages": ["nginx", "certbot"],
    "network": "vmbr0",
    "ip_address": "192.168.3.50",  # Static IP (optional)
}

result = await agent.execute(task)
# Returns: {"vm_id": 123, "ip_address": "192.168.3.50", "status": "completed"}
```

**Task Parameters:**
- `name` (required): VM hostname
- `version` (required): Ubuntu version (22.04, 20.04)
- `cores` (optional): CPU cores (default: 2)
- `memory` (optional): RAM in MB (default: 2048)
- `disk_size_gb` (optional): Disk size (default: 20)
- `ssh_user` (optional): Username to create
- `ssh_public_key` (optional): SSH key for user
- `packages` (optional): List of apt packages to install
- `network` (optional): Network/bridge name
- `ip_address` (optional): Static IP (otherwise DHCP)
- `gateway` (optional): Gateway for static IP
- `dns_servers` (optional): DNS servers list

**Cloud-Init Integration:**
- User creation with SSH keys
- Package installation
- Network configuration
- Hostname setting
- Run custom scripts

**Status:** ✅ Fully implemented and tested

---

## Windows Installer Agent

**Purpose:** Deploy Windows VMs across all platforms

**Location:** `glassdome/agents/windows_installer.py`

**Supported Versions:**
- Windows Server 2022
- Windows 11 (future)

**Platforms:**
- ✅ AWS (pre-built AMI + EC2Launch)
- ✅ Azure (pre-built image + Custom Data)
- ⚠️ Proxmox (ISO + autounattend - unreliable)
- ⚠️ ESXi (ISO + autounattend - unreliable)

**Current Blocker:** Autounattend.xml approach for Proxmox/ESXi

**Recommended:** Template-based approach
1. Manual Windows install (one-time, 15 min)
2. Sysprep and convert to template
3. Clone for future deployments (2-3 min, reliable)

**Usage (AWS/Azure):**
```python
from glassdome.agents.windows_installer import WindowsInstallerAgent
from glassdome.platforms.aws_client import AWSClient

client = AWSClient(...)
agent = WindowsInstallerAgent(client)

task = {
    "name": "win-server-01",
    "os_version": "2022",
    "cores": 2,
    "memory": 4096,
    "disk_size_gb": 80,
    "password": "Glassdome123!",
    "instance_type": "t3.medium",  # AWS
    "region": "us-east-1",
}

result = await agent.execute(task)
```

**Key Learnings:**
- Use SATA controller (not SCSI) on Proxmox/ESXi
- SATA is Windows-native (no driver injection)
- RDP automatically enabled (port 3389)
- Azure reserves "Administrator" username (use "gdadmin")

**Status:** ✅ Cloud working, ⚠️ On-prem in progress

---

## Overseer Agent

**Purpose:** Continuous monitoring of deployed infrastructure

**Location:** `glassdome/agents/overseer.py`

**Features:**
- Health checks (ping, SSH, HTTP)
- Resource monitoring (CPU, memory, disk)
- Log collection
- Alerting on failures
- Auto-remediation (restart services)

**Monitoring Targets:**
- Individual VMs
- Networks
- Services (web, database, etc.)
- Overall scenario health

**Usage:**
```python
from glassdome.agents.overseer import OverseerAgent

agent = OverseerAgent()

# Monitor single VM
await agent.monitor_vm(vm_id="123", checks=["ping", "ssh", "http"])

# Monitor entire deployment
await agent.monitor_deployment(deployment_id="abc123")

# Get health report
report = await agent.get_health_report(deployment_id="abc123")
```

**Check Types:**
- `ping` - ICMP reachability
- `ssh` - SSH service availability
- `http` - Web service health
- `resources` - CPU/memory/disk usage
- `logs` - Error log scanning

**Status:** 🔨 Designed, not implemented

---

## Reaper Agent

**Purpose:** Inject vulnerabilities into clean VMs for cybersecurity training

**Location:** `glassdome/agents/reaper.py`

**🔴 ETHICS WARNING:**
- **100% ethical use only**
- Training blue teams for defense
- Never for unauthorized access
- Explicit consent required
- Isolated lab environments only

**Process:**
1. Receive target VM and vulnerability specification
2. Query Research Agent for exploit details
3. Install vulnerability package (.deb)
4. Verify vulnerability is exploitable
5. Document for training purposes

**Vulnerability Types:**
- SQL injection (DVWA)
- Cross-site scripting (XSS)
- SMB exploits (EternalBlue)
- Weak credentials
- Privilege escalation (sudo misconfig)
- Kerberoasting (Active Directory)

**Usage:**
```python
from glassdome.agents.reaper import ReaperAgent

agent = ReaperAgent()

task = {
    "vm_id": "123",
    "vulnerability": "sql-injection",
    "package": "glassdome-vuln-sql-injection",
    "verify": True,  # Test exploit after install
}

result = await agent.execute(task)
# Returns: {
#   "status": "completed",
#   "vulnerability_id": "vuln-001",
#   "exploit_verified": True,
#   "documentation": "/path/to/exploit-guide.md"
# }
```

**Integration with Research Agent:**
- Reaper requests exploit research for CVE
- Research Agent queries AI + NVD
- Returns step-by-step exploitation procedure
- Reaper packages as .deb file
- Stores in local APT repository

**Vulnerability Packages:**
```bash
# Install vulnerability
apt install glassdome-vuln-sql-injection

# Uninstall (remediation practice)
apt remove glassdome-vuln-sql-injection
```

**Status:** 🔨 Designed, not implemented

---

## Research Agent

**Purpose:** AI-powered CVE analysis and exploit generation

**Location:** `glassdome/agents/research.py`

**Multi-LLM Strategy:**

```
CVE Request (e.g., CVE-2021-44228)
            ↓
    Research Agent
            ↓
   ┌────────┴────────────┬────────────┬──────────────┐
   ↓                     ↓            ↓              ↓
OpenAI API          Grok API    Perplexity   Local FAISS RAG
(GPT-4)            (X.AI)       (Search)      (Project Memory)
   ↓                     ↓            ↓              ↓
"Log4j RCE..."     "Widespread"  "CVSS 10.0"   "Attempted before"
   └────────┬────────────┴────────────┴──────────────┘
            ↓
    Synthesize Best Answer
            ↓
    Generate Exploit Steps
```

**Data Sources:**
- OpenAI (GPT-4): Deep technical reasoning
- Grok (X.AI): Real-time data, trending exploits
- Perplexity: Search-enhanced, latest information
- NVD API: Official CVE database
- Local RAG: Project history, past attempts

**Usage:**
```python
from glassdome.agents.research import ResearchAgent

agent = ResearchAgent()

task = {
    "cve_id": "CVE-2021-44228",
    "research_depth": "detailed",  # quick, standard, detailed
    "include_exploit": True,
    "target_os": "ubuntu-22.04",
}

result = await agent.execute(task)
# Returns: {
#   "cve_id": "CVE-2021-44228",
#   "summary": "Apache Log4j RCE vulnerability...",
#   "cvss_score": 10.0,
#   "affected_versions": ["2.0-beta9 to 2.14.1"],
#   "exploit_steps": [
#     "1. Set up LDAP server...",
#     "2. Craft malicious string...",
#     "3. Trigger logging..."
#   ],
#   "package_name": "glassdome-vuln-log4shell",
#   "remediation": "Upgrade to 2.15.0 or later",
#   "sources": ["OpenAI", "Grok", "NVD"]
# }
```

**Cost Optimization:**
- OpenAI: $0.03/request (GPT-4)
- Grok: $0.01/request (estimate)
- Perplexity: $0.005/request
- **Total:** ~$0.05 per CVE analysis
- **Annual (1000 CVEs):** ~$50

**Local LLM Fallback:**
- Llama 3 8B for air-gapped deployments
- Lower quality but zero cost
- Privacy-preserving

**Status:** 🔨 Designed, not implemented

---

## Agent Orchestration

**Orchestrator Pattern:**

```python
# Multi-agent scenario deployment
from glassdome.orchestration.engine import Orchestrator

orchestrator = Orchestrator()

scenario = {
    "name": "Enterprise Web App",
    "networks": [
        {"name": "attack", "cidr": "192.168.100.0/24"},
        {"name": "dmz", "cidr": "10.0.1.0/24"},
    ],
    "vms": [
        {
            "name": "console",
            "network": "attack",
            "agent": "UbuntuInstallerAgent",
            "config": {"version": "22.04", "packages": ["nmap", "metasploit"]},
        },
        {
            "name": "web-server",
            "network": "dmz",
            "agent": "UbuntuInstallerAgent",
            "config": {"version": "22.04", "packages": ["nginx"]},
            "vulnerabilities": ["sql-injection", "xss"],
        },
    ],
}

# Deploy entire scenario
deployment = await orchestrator.deploy_scenario(scenario)
```

**Orchestrator Responsibilities:**
1. Parse scenario YAML
2. Validate dependencies
3. Create networks
4. Spawn agent tasks (parallel)
5. Track deployment state
6. Handle failures (rollback)
7. Send real-time updates (WebSocket)

**Status:** 🔨 Designed, not implemented

---

## Agent Communication

**Internal (Agent → Platform Client):**
```python
# Direct method calls
result = await platform_client.create_vm(config)
```

**External (API → Agent):**
```python
# Via Celery task queue
from celery import Celery

app = Celery('glassdome')

@app.task
def deploy_ubuntu_vm(task_config):
    agent = UbuntuInstallerAgent(...)
    result = asyncio.run(agent.execute(task_config))
    return result
```

**Real-Time Updates:**
```python
# Via WebSocket
from fastapi import WebSocket

async def deployment_status(websocket: WebSocket):
    await websocket.accept()
    while True:
        status = agent.get_status()
        await websocket.send_json(status)
        await asyncio.sleep(1)
```

---

## Testing Agents

**Unit Tests:**
```bash
pytest tests/agents/test_ubuntu_installer.py
```

**Integration Tests:**
```bash
# Test with real Proxmox
python scripts/testing/test_proxmox_quick.py

# Test all platforms
python scripts/testing/test_all_platforms.py
```

**Mock Platform Client:**
```python
from unittest.mock import AsyncMock

# Mock platform for testing
mock_client = AsyncMock(spec=PlatformClient)
mock_client.create_vm.return_value = {"vm_id": "123", "ip": "192.168.1.100"}

agent = UbuntuInstallerAgent(mock_client)
result = await agent.execute(task)
```

---

## Agent Status Summary

| Agent | Status | Platforms | Notes |
|-------|--------|-----------|-------|
| UbuntuInstaller | ✅ Working | 4/4 | Fully tested |
| WindowsInstaller | ⚠️ Partial | 2/4 | Cloud working, on-prem blocked |
| Overseer | 🔨 Designed | N/A | Monitoring framework defined |
| Reaper | 🔨 Designed | N/A | Ethics framework established |
| Research | 🔨 Designed | N/A | Multi-LLM strategy defined |

---

**Next:** See `docs/PROJECT_STATUS.md` for implementation priorities.

