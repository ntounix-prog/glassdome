# Glassdome Architecture

**Design Philosophy:** Agentic, platform-agnostic, air-gappable, enterprise-ready

---

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard (Frontend)               │
│  Home │ Scenarios │ Deployments │ Network Topology │ Logs   │
└────────────────────────┬────────────────────────────────────┘
                         │ WebSocket + REST API
┌────────────────────────┴────────────────────────────────────┐
│                     FastAPI Backend                          │
│  ┌──────────────┬──────────────┬────────────────────────┐  │
│  │ API Endpoints│ Auth/RBAC    │ WebSocket Notifier     │  │
│  └──────────────┴──────────────┴────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Orchestration Layer                         │  │
│  │  - Scenario Parser (YAML)                            │  │
│  │  - Multi-VM Deployer (Parallel)                       │  │
│  │  - Network Manager (4 VLANs)                          │  │
│  │  - State Tracker (SQLAlchemy)                         │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│                    Agent Framework                           │
│  ┌─────────────┬──────────────┬────────────┬─────────────┐ │
│  │ Ubuntu      │ Windows      │ Reaper     │ Research    │ │
│  │ Installer   │ Installer    │ (Vuln)     │ (AI/CVE)    │ │
│  └─────────────┴──────────────┴────────────┴─────────────┘ │
│  └─────────────── BaseAgent (Abstract) ───────────────────┘ │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│            Platform Abstraction Layer                        │
│  ┌──────────┬──────────┬──────────┬──────────┬───────────┐ │
│  │ Proxmox  │  ESXi    │   AWS    │  Azure   │  Future   │ │
│  │ Client   │ Client   │ Client   │ Client   │  (GCP)    │ │
│  └──────────┴──────────┴──────────┴──────────┴───────────┘ │
│  └──────────── PlatformClient (Abstract) ──────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Frontend (React)

**Tech Stack:**
- React 18 + TypeScript
- Vite (build tool)
- TailwindCSS (styling)
- React Flow (network topology)
- WebSocket (real-time updates)

**Pages:**
- **Home:** Dashboard with stats, recent activity
- **Scenarios:** Library of pre-built labs (cards with deploy button)
- **Deployments:** Active/historical deployments with live status
- **Topology:** Visual network diagram (React Flow)
- **Logs:** Real-time deployment logs

**Key Features:**
- Dark theme by default
- Mobile responsive
- Real-time VM status updates
- Drag-and-drop scenario builder (future)

**Status:** 25% complete (foundation only)

### 2. Backend (FastAPI)

**Tech Stack:**
- FastAPI (Python 3.12)
- SQLAlchemy (ORM)
- Alembic (migrations)
- Celery + Redis (async tasks)
- WebSocket (notifications)
- Pydantic (validation)

**API Structure:**
```
/api/
  /health              - Health check
  /labs                - Lab definitions (CRUD)
  /deployments         - Deployment operations
  /agents              - Agent management
  /platforms           - Platform status
  /scenarios           - Scenario library
```

**Key Features:**
- JWT authentication (future)
- Role-based access control (future)
- Async task queue (Celery)
- Real-time notifications (WebSocket)
- Comprehensive logging

**Status:** 60% complete (core endpoints working)

### 3. Orchestration Layer

**Purpose:** Coordinate complex multi-VM, multi-network deployments

**Components:**

**Scenario Parser:**
- Parses YAML scenario definitions
- Validates schema
- Resolves dependencies (VM order, network dependencies)

**Multi-VM Deployer:**
- Parallel VM creation (up to 10 concurrent)
- Dependency resolution (e.g., DNS before web server)
- Progress tracking
- Rollback on failure

**Network Manager:**
- Creates isolated VLANs/bridges
- Assigns VMs to networks
- Configures routing (if needed)
- Teardown on cleanup

**State Tracker:**
- SQLAlchemy models
- Tracks deployment state
- Enables resume after failure

**Status:** 20% complete (design done, implementation started)

### 4. Agent Framework

**Design Decision:** Hybrid architecture

**Why Hybrid?**
- **Base Class:** Shared logic (validation, status, error handling)
- **Specialized Agents:** Platform/OS-specific implementations
- **Best of Both:** Code reuse + flexibility

**Base Agent (`glassdome.agents.base.BaseAgent`):**
```python
class BaseAgent(ABC):
    def __init__(self, agent_id: str, agent_type: AgentType):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.status = AgentStatus.IDLE
        
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task - implemented by subclasses"""
        pass
        
    def validate(self, task: Dict[str, Any]) -> bool:
        """Shared validation logic"""
        pass
```

**Specialized Agents:**
- **UbuntuInstallerAgent:** Deploy Ubuntu VMs (all platforms)
- **WindowsInstallerAgent:** Deploy Windows VMs (all platforms)
- **ReaperAgent:** Inject vulnerabilities for training
- **ResearchAgent:** AI-powered CVE analysis
- **OverseerAgent:** Monitor deployed infrastructure

**Agent Lifecycle:**
1. **IDLE** → Waiting for task
2. **VALIDATING** → Check task parameters
3. **RUNNING** → Executing deployment
4. **COMPLETED** → Success
5. **FAILED** → Error occurred

**Status:** 70% complete (Ubuntu/Windows working, Reaper/Research pending)

### 5. Platform Abstraction Layer

**Purpose:** Decouple OS logic from platform APIs

**Base Interface (`glassdome.platforms.base.PlatformClient`):**
```python
class PlatformClient(ABC):
    @abstractmethod
    async def create_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create VM - platform-specific implementation"""
        pass
        
    @abstractmethod
    async def delete_vm(self, vm_id: str) -> bool:
        """Delete VM"""
        pass
        
    @abstractmethod
    async def get_vm_status(self, vm_id: str) -> VMStatus:
        """Get VM status"""
        pass
```

**Platform Implementations:**

**ProxmoxClient:**
- Uses `proxmoxer` library
- API token authentication
- Template cloning for fast deployment
- Cloud-init for configuration

**ESXiClient:**
- Uses `pyvmomi` (VMware SDK)
- Direct ESXi API (no vCenter needed)
- VMDK conversion for cloud images
- NoCloud ISO for cloud-init

**AWSClient:**
- Uses `boto3` SDK
- EC2 + VPC management
- Dynamic AMI selection (ARM64/x86_64)
- UserData for cloud-init

**AzureClient:**
- Uses `azure-mgmt-*` SDKs
- Resource group management
- Auto-registers resource providers
- Custom Data for configuration

**Key Design:**
- **Agents** handle OS-specific logic (packages, users, configs)
- **Platforms** handle infrastructure (VMs, networks, storage)
- **Clean separation** enables easy platform addition

**Status:** 90% complete (all 4 platforms working)

---

## Network Architecture

**Design:** 4 isolated VLANs for realistic cyber range scenarios

```
┌────────────────────────────────────────────────────────────┐
│                      Attack Network                         │
│               192.168.100.0/24 (vmbr100)                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Glassdome Security Console (Kali-like)              │  │
│  │  IP: 192.168.100.10                                  │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│                        DMZ Network                          │
│                  10.0.1.0/24 (vmbr101)                      │
│  ┌───────────────────┐  ┌────────────────────────────┐    │
│  │ Web Server        │  │ DNS Server                 │    │
│  │ IP: 10.0.1.10     │  │ IP: 10.0.1.11              │    │
│  │ Vulns: SQLi, XSS  │  │ Vuln: Zone Transfer        │    │
│  └───────────────────┘  └────────────────────────────┘    │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│                    Internal Network                         │
│                 10.0.2.0/24 (vmbr102)                       │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐    │
│  │ App Server │  │ DB Server  │  │ File Server       │    │
│  │ 10.0.2.10  │  │ 10.0.2.11  │  │ 10.0.2.12         │    │
│  │            │  │            │  │ Vuln: EternalBlue  │    │
│  └────────────┘  └────────────┘  └──────────────────┘    │
└────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────┐
│                  Management Network                         │
│                 10.0.3.0/24 (vmbr103)                       │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │ Domain Controller    │  │ Admin Workstation        │  │
│  │ IP: 10.0.3.10        │  │ IP: 10.0.3.11            │  │
│  │ Vuln: Kerberoasting  │  │                          │  │
│  └──────────────────────┘  └──────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

**Network Creation:**
- Proxmox: `pvesh create /nodes/{node}/network --iface vmbr100 --type bridge`
- ESXi: Port Groups on vSwitch
- AWS: VPC + Subnets + Security Groups
- Azure: VNet + Subnets + NSGs

**Status:** Design complete, implementation 0%

---

## Data Flow

**Scenario Deployment Flow:**

```
1. User clicks "Deploy" in React UI
   ↓
2. POST /api/deployments
   ↓
3. Orchestrator parses YAML scenario
   ↓
4. Orchestrator creates networks (Network Manager)
   ↓
5. Orchestrator spawns agent tasks (Multi-VM Deployer)
   ↓
6. Agents call Platform Clients (parallel)
   ↓
7. Platform Clients create VMs
   ↓
8. Cloud-init configures VMs (users, packages, SSH keys)
   ↓
9. Reaper Agent injects vulnerabilities (if specified)
   ↓
10. Orchestrator updates state (SQLAlchemy)
    ↓
11. WebSocket pushes status to UI
    ↓
12. User sees real-time progress
```

**VM Creation Flow (Single VM):**

```
1. Agent validates task parameters
   ↓
2. Agent calls PlatformClient.create_vm(config)
   ↓
3. Platform Client:
   a. Proxmox: Clone template, configure cloud-init
   b. ESXi: Clone template, attach NoCloud ISO
   c. AWS: Launch EC2, UserData
   d. Azure: Create VM, Custom Data
   ↓
4. Wait for IP assignment (DHCP or static)
   ↓
5. Wait for cloud-init completion
   ↓
6. Return VM details (ID, IP, status)
```

---

## AI Integration

**Research Agent Architecture:**

```
User Request: "Analyze CVE-2021-44228"
            ↓
    Research Agent
            ↓
   ┌────────┴────────────┬────────────┬──────────────┐
   ↓                     ↓            ↓              ↓
OpenAI API          Grok API    Perplexity   Local FAISS RAG
(GPT-4)            (X.AI)       (Search)      (Project Docs)
   ↓                     ↓            ↓              ↓
"Log4j RCE..."     "Widespread"  "CVSS 10.0"   "We tried..."
   └────────┬────────────┴────────────┴──────────────┘
            ↓
    Aggregate & Synthesize
            ↓
    Generate Exploit Steps
            ↓
   Create .deb Package
            ↓
    Store in Local Repo
```

**Multi-LLM Strategy:**
- **OpenAI:** Deep reasoning, code generation
- **Grok:** Real-time data, trending exploits
- **Perplexity:** Search-enhanced, latest CVE info
- **Local RAG:** Project history, avoid repeat mistakes

**Status:** Design complete, implementation 0%

---

## Deployment Models

**1. Development (Current):**
- Run locally: `glassdome serve`
- SQLite database
- No containerization

**2. Production (OVA Appliance):**
- Single VM containing:
  - FastAPI backend
  - PostgreSQL database
  - Redis (Celery)
  - Local LLM (Llama 3)
  - NVD database snapshot
- First-boot wizard for configuration
- Air-gapped capable

**3. Kubernetes (Future):**
- Helm chart
- Microservices architecture
- Horizontal scaling
- Cloud-native

---

## Security Considerations

**Authentication:**
- JWT tokens (future)
- API key management (encrypted)
- Service principal credentials

**Network Isolation:**
- VLANs for scenario networks
- Firewall rules
- No internet access from lab VMs (optional)

**Secrets Management:**
- `.env` file for local dev
- Encrypted database storage
- HashiCorp Vault integration (future)

**Audit Logging:**
- All API calls logged
- Deployment actions tracked
- User actions recorded

---

## Performance Targets

**Single VM Deployment:**
- Proxmox/ESXi: 2-3 minutes (template clone)
- AWS/Azure: 3-5 minutes (instance launch)

**9-VM Scenario Deployment:**
- Target: < 5 minutes (parallel deployment)
- Networks: 4 VLANs created first
- VMs: Deployed in parallel (up to 10 concurrent)

**Scaling:**
- Support: 100+ concurrent VMs
- Database: PostgreSQL for production
- Celery workers: Configurable based on load

---

## Technology Stack Summary

| Component | Technology | Status |
|-----------|-----------|--------|
| Backend | FastAPI + Python 3.12 | ✅ Working |
| Frontend | React 18 + TypeScript | 🔨 In Progress |
| Database | SQLAlchemy + SQLite/PostgreSQL | ✅ Working |
| Task Queue | Celery + Redis | 🔨 Designed |
| Proxmox | proxmoxer | ✅ Working |
| ESXi | pyvmomi | ✅ Working |
| AWS | boto3 | ✅ Working |
| Azure | azure-mgmt-* | ✅ Working |
| AI | OpenAI, Grok, Perplexity, Local | 🔨 Designed |
| Packaging | Docker, OVA | ❌ Not Started |

---

**Next:** See `docs/AGENTS.md` for agent-specific details.
