# Glassdome Build Plan - What We're Actually Building

**VP Demo:** December 8, 2024  
**Goal:** Deploy 9-VM cyber range scenarios with one command, completely air-gapped

---

## What We're Building

**An on-premise cyber range platform that:**
- Deploys complete network scenarios (7-10 VMs, 4 networks) in < 5 minutes
- Works completely offline (air-gapped)
- Uses AI to analyze CVEs and generate training labs
- Has a professional web dashboard
- Packages vulnerabilities as installable .deb files

---

## Core Components to Build

### 1. Multi-Network Orchestration
**What:** Deploy 9 VMs across 4 isolated networks with one command

**Tasks:**
- [ ] Create 4 VLANs/bridges in Proxmox (Attack, DMZ, Internal, Management)
- [ ] Build network creation API
- [ ] Deploy multiple VMs in parallel
- [ ] Configure VM network assignments
- [ ] Test: Deploy 9 VMs across 4 networks in < 5 min

**Files:**
- `glassdome/orchestration/network_manager.py`
- `glassdome/orchestration/multi_vm_deployer.py`

---

### 2. Scenario Definition Format
**What:** YAML files that define complete scenarios

**Tasks:**
- [ ] Define YAML schema for scenarios
- [ ] Build YAML parser
- [ ] Validate scenario files
- [ ] Test: Parse `enterprise-web-app.yml` successfully

**Example:**
```yaml
name: "Enterprise Web Application"
networks:
  - name: attack
    cidr: 192.168.100.0/24
  - name: dmz
    cidr: 10.0.1.0/24
machines:
  - name: kali-01
    network: attack
    template: ubuntu-22.04
    ip: 192.168.100.10
  - name: web-01
    network: dmz
    ip: 10.0.1.10
    packages:
      - glassdome-vuln-sql-injection
```

**Files:**
- `glassdome/models/scenario.py`
- `glassdome/orchestration/scenario_parser.py`

---

### 3. React Control Dashboard
**What:** Professional web UI for deploying and monitoring scenarios

**Views to Build:**
- [ ] Home dashboard (stats, activity feed)
- [ ] Scenario library (grid of cards, deploy button)
- [ ] Active deployments (live status, VM list)
- [ ] Network topology (visual diagram with React Flow)
- [ ] Infrastructure monitor (Proxmox resource usage)

**Key Features:**
- [ ] WebSocket for real-time updates
- [ ] API integration (scenarios, deployments, VMs)
- [ ] Dark theme
- [ ] Mobile responsive

**Files:**
- `frontend/src/pages/Home.tsx`
- `frontend/src/pages/Scenarios.tsx`
- `frontend/src/pages/Deployments.tsx`
- `frontend/src/components/NetworkTopology.tsx`

---

### 4. Offline Bundle
**What:** 50-100GB package with everything needed for air-gapped deployment

**Contents:**
- [ ] All Docker images (export and package)
- [ ] Python packages (500+ dependencies)
- [ ] System packages (Ansible, Terraform, etc.)
- [ ] Local LLM model (Llama 3 8B - 5GB)
- [ ] NVD CVE database snapshot
- [ ] OS templates (Ubuntu 22.04, 20.04)
- [ ] Installation script

**Test:** Install from bundle with zero internet connectivity

**Files:**
- `scripts/packaging/create_offline_bundle.sh`
- `scripts/packaging/install_offline.sh`

---

### 5. Local LLM Integration
**What:** Research Agent works offline using local Llama 3 model

**Tasks:**
- [ ] Download Llama 3 8B model (5GB)
- [ ] Setup Ollama or llama.cpp
- [ ] Update Research Agent to use local LLM
- [ ] Test: Analyze CVE-2021-44228 (Log4Shell) offline

**Files:**
- `glassdome/ai/local_llm.py`
- `glassdome/research/agent.py` (update)

---

### 6. Vulnerability Packages
**What:** Install vulnerabilities like software packages

**Tasks:**
- [ ] Build .deb package creator script
- [ ] Create 5 vulnerability packages:
  - [ ] SQL injection (DVWA)
  - [ ] XSS (basic)
  - [ ] SMB EternalBlue
  - [ ] Weak sudo
  - [ ] SSH weak passwords
- [ ] Setup local APT repository
- [ ] Test: `apt install glassdome-vuln-sql-injection`

**Files:**
- `scripts/packaging/build_vuln_package.sh`
- `glassdome/vulnerabilities/packages/sql-injection-dvwa/`
- `glassdome/vulnerabilities/packages/smb-eternalblue/`

---

### 7. Custom Security Console
**What:** Branded Ubuntu-based attack VM (lighter than Kali)

**Tasks:**
- [ ] Create Ansible playbook for tool installation
- [ ] Install essential tools (nmap, metasploit, sqlmap, wireshark, etc.)
- [ ] Pre-install Glassdome CLI
- [ ] Build Proxmox template
- [ ] Test: Deploy console VM, verify tools work

**Target size:** 5-8GB (vs Kali's 20GB)

**Files:**
- `glassdome/vulnerabilities/playbooks/console/glassdome_console.yml`

---

### 8. OVA/OVF Appliance
**What:** Single-file deployment of complete platform

**Tasks:**
- [ ] Create management VM with all services
- [ ] Pre-load AI model
- [ ] Pre-load vulnerability database
- [ ] Create first-boot wizard
- [ ] Export as OVA
- [ ] Test: Import OVA, boot, deploy scenario

**Files:**
- `scripts/packaging/create_appliance.sh`

---

### 9. Demo Scenario
**What:** "Enterprise Web Application" - 9 VMs, 4 networks, 5 vulnerabilities

**Scenario Details:**
```
Networks:
  - Attack (192.168.100.0/24): Glassdome Console
  - DMZ (10.0.1.0/24): Web Server, DNS Server
  - Internal (10.0.2.0/24): App Server, DB Server, File Server
  - Management (10.0.3.0/24): Domain Controller, Admin Workstation

Vulnerabilities:
  - Web Server: SQL injection, XSS
  - DNS Server: Zone transfer
  - File Server: SMB EternalBlue
  - Domain Controller: Kerberoasting

Flags: 3 hidden CTF flags
```

**Tasks:**
- [ ] Write scenario YAML file
- [ ] Create all VM templates
- [ ] Install vulnerabilities
- [ ] Plant flags
- [ ] Generate answer key
- [ ] Test end-to-end 10 times

**Files:**
- `scenarios/enterprise-web-app.yml`

---

### 10. Compliance Documentation
**What:** Documents that save buyers 6-12 months of work

**Tasks:**
- [ ] System Security Plan (SSP) - FedRAMP template
- [ ] Security architecture diagram
- [ ] Data flow diagram
- [ ] Access control matrix (RBAC)
- [ ] Audit logging documentation

**Files:**
- `docs/compliance/SSP.pdf`
- `docs/compliance/architecture-diagram.png`
- `docs/compliance/data-flow-diagram.png`

---

## Priority Order

### Week 1 (Nov 20-27) - Core Infrastructure
1. Multi-network orchestration
2. Scenario YAML format
3. React dashboard (basic views)

### Week 2 (Nov 27-Dec 4) - Enterprise Features
4. Offline bundle
5. Local LLM
6. Vulnerability packages
7. Custom console VM

### Week 3 (Dec 4-8) - Demo Ready
8. OVA appliance
9. Demo scenario
10. Compliance docs

---

## Demo Must-Haves (Non-Negotiable)

For the Dec 8 VP demo, we MUST show:

1. ✅ **Web UI** - Click "Deploy" button, not terminal commands
2. ✅ **9-VM deployment** - Complete in < 5 minutes
3. ✅ **Real-time monitoring** - Watch VMs appear live
4. ✅ **Network topology** - Visual diagram of scenario
5. ✅ **Air-gapped** - Disconnect internet during demo
6. ✅ **Professional** - Looks like a $250K product

---

## What We're NOT Building (Deferred)

- Azure/AWS deployment (Proxmox only)
- Windows VM support (Linux only)
- Full RBAC/SSO (document only)
- Kubernetes Helm chart (OVA only)
- Advanced networking (basic VLANs sufficient)

---

## Current Status

### ✅ Done (40%)
- Project structure
- FastAPI backend foundation
- Proxmox API integration
- Single VM deployment (working)
- Template creation (automated)
- SSH automation
- Git repository

### 🔨 In Progress (20%)
- Multi-VM orchestration
- Network creation
- React dashboard skeleton

### ❌ Not Started (40%)
- Scenario YAML parser
- Offline bundle
- Local LLM
- Vulnerability packages
- Custom console VM
- OVA appliance
- Demo scenario

---

## Testing Checklist

Before the demo, verify:

- [ ] Deploy scenario from web UI (no CLI)
- [ ] 9 VMs deploy in < 5 minutes
- [ ] All VMs get correct IPs
- [ ] Networks are isolated (ping tests)
- [ ] Web UI updates in real-time
- [ ] Topology diagram renders correctly
- [ ] Works with zero internet (air-gapped test)
- [ ] OVA import works on fresh Proxmox
- [ ] Demo runs 5 times without errors

---

## Files to Create/Modify

### New Files Needed
```
glassdome/orchestration/
  ├── network_manager.py          # Multi-network creation
  ├── multi_vm_deployer.py        # Parallel VM deployment
  └── scenario_parser.py          # YAML parsing

glassdome/models/
  └── scenario.py                  # Scenario data model

glassdome/ai/
  └── local_llm.py                 # Local LLM client

frontend/src/
  ├── pages/
  │   ├── Home.tsx
  │   ├── Scenarios.tsx
  │   └── Deployments.tsx
  └── components/
      └── NetworkTopology.tsx

scenarios/
  └── enterprise-web-app.yml       # Demo scenario

scripts/packaging/
  ├── create_offline_bundle.sh     # Offline bundle creator
  ├── install_offline.sh           # Offline installer
  ├── build_vuln_package.sh        # .deb package builder
  └── create_appliance.sh          # OVA creator

glassdome/vulnerabilities/packages/
  ├── sql-injection-dvwa/
  ├── xss-basic/
  ├── smb-eternalblue/
  ├── weak-sudo/
  └── ssh-weak-passwords/

glassdome/vulnerabilities/playbooks/console/
  └── glassdome_console.yml        # Console VM playbook

docs/compliance/
  ├── SSP.pdf
  ├── architecture-diagram.png
  └── data-flow-diagram.png
```

---

## Quick Start (Tomorrow Morning)

**First things to do:**

1. **Multi-network test:**
   ```bash
   # Create 4 bridges in Proxmox
   ssh root@192.168.3.2
   pvesh create /nodes/pve01/network --iface vmbr100 --type bridge
   pvesh create /nodes/pve01/network --iface vmbr101 --type bridge
   pvesh create /nodes/pve01/network --iface vmbr102 --type bridge
   pvesh create /nodes/pve01/network --iface vmbr103 --type bridge
   ```

2. **Initialize React project:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. **Create first scenario file:**
   ```bash
   mkdir scenarios
   touch scenarios/enterprise-web-app.yml
   ```

4. **Start building:**
   - Backend: `glassdome/orchestration/network_manager.py`
   - Frontend: `frontend/src/pages/Home.tsx`

---

## Success = VP Says "Yes"

**That's it. Everything else is noise.**

If we can:
1. Click "Deploy" in a web UI
2. Watch 9 VMs appear in < 5 minutes
3. See them on a network diagram
4. Do it all air-gapped

**We win.** 🎯

---

*This is the build. Let's go.*

