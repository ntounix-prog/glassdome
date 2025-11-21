# Current System State

**Last Updated:** 2025-11-21 08:15 UTC  
**Session:** Initial Development & Deployment  
**Status:** Operational, Phase 1 Complete

---

## Active Infrastructure

### Proxmox (192.168.3.2)
**Credentials:** root / xisxxisx  
**Network:** vmbr0 (192.168.2.77/24), vmbr0.2 (192.168.3.2/24 - VLAN tag 2)  
**Storage:** local-lvm  
**Template:** VM 9000 (ubuntu-2204-cloudinit-template)

**Active VMs:**
```
VM 100: glassdome-test-001 (running, 192.168.2.x)
VM 114: ubuntu-powerhouse (running, 192.168.3.50, VLAN tag 2)
  ├─ Specs: 16 cores, 32GB RAM, 1TB disk
  ├─ Services: Minecraft Bedrock (port 19132)
  ├─ Status: Healthy, 12+ players online
  └─ Purpose: Game server, performance testing

VM 113: glassdome-win-test (running, Windows test)
```

**Critical Network Config:**
- 192.168.3.x network requires VLAN tag 2 (`--net0 virtio,bridge=vmbr0,tag=2`)
- No DHCP on 192.168.3.x (static IPs only)
- Fallback IP pattern: x.x.x.254 → .253 → .252 for recovery

### ESXi (192.168.3.3)
**Credentials:** root / H-3a-7YP  
**Datastore:** NFSSTORE  
**Network:** Management on 192.168.3.x  
**Template:** Ubuntu cloud-init OVA (working)  
**Known Issue:** Management services can desync (restart hostd/SSH from console)

### AWS
**Region:** Flexible (tested us-east-1)  
**Credentials:** In ~/.bashrc  
**Tested:** Ubuntu + Windows Server 2022 on t4g.nano, t3.medium  
**Status:** Operational, credentials verified

### Azure
**Region:** eastus  
**Resource Group:** glassdome-rg  
**Credentials:** In ~/.bashrc  
**Service Principal:** glassdome-deploy-azure (Contributor role)  
**Status:** Operational, resource providers registered

---

## Completed Milestones

### ✅ Platform Integration (Week 1)
- Proxmox: Full support, template-based deployment
- ESXi: Standalone host support, cloud-init OVA workflow
- AWS: EC2 deployment, dynamic AMI selection, ARM64 support
- Azure: VM deployment, automatic provider registration

### ✅ Operating Systems
- Ubuntu 22.04: Template-based, cloud-init, static IPs working
- Windows Server 2022: Cloud (AWS/Azure) working, on-prem partial

### ✅ Real-World Deployment
- Minecraft Bedrock server migrated to VM 114
- 2.6GB full backup transferred and configured
- Systemd service created (auto-start on boot)
- Server operational: 192.168.3.50:19132

### ✅ Documentation
- 17 organized docs (down from 57 redundant files)
- Critical lessons captured for RAG
- Architecture documented
- Platform setup guides complete

---

## In-Progress Work

### 🔄 Windows Deployment (On-Prem)
**Status:** Blocked, decision needed  
**Issue:** autounattend.xml unreliable (SATA vs VirtIO, boot order issues)  
**Options:**
- A) Manual template creation (install once, sysprep, clone) - RECOMMENDED
- B) Continue debugging autounattend.xml
**Next Step:** Create Windows Server 2022 template manually

### 🔄 RAG System
**Status:** Design complete, implementation pending  
**Purpose:** Enable context transfer between AI sessions  
**Components:**
- Vector DB (FAISS or similar)
- Document indexing (all markdown, code, logs)
- Query interface for AI agents
**Next Step:** Build tomorrow (2025-11-22)

---

## Blocked / Pending

### ⏸️ Multi-Network Scenarios
**Dependency:** Windows deployment  
**Requirement:** 7-10 VMs across 4 VLANs (Attack, DMZ, Internal, Mgmt)  
**Priority:** High (needed for 12/8 presentation)

### ⏸️ React Dashboard
**Dependency:** Backend APIs stabilized  
**Requirement:** Scenario management, real-time monitoring, topology viz  
**Priority:** Medium

### ⏸️ Communications Container
**Dependency:** RAG system  
**Requirement:** Slack + Mailcow integration for team collaboration  
**Priority:** Medium

### ⏸️ Reaper Agent
**Dependency:** Working multi-VM scenarios  
**Requirement:** Autonomous vulnerability injection  
**Priority:** Phase 2

---

## Critical Lessons (For RAG Context)

### 1. Proxmox VLAN Configuration
**Issue:** VMs deployed to vmbr0 without VLAN tag reached 192.168.2.x instead of 192.168.3.x  
**Root Cause:** Proxmox uses vmbr0.2 subinterface for 192.168.3.x (VLAN 2)  
**Solution:** `qm set <vmid> --net0 virtio,bridge=vmbr0,tag=2`  
**When to Apply:** Always check `/etc/network/interfaces` for VLAN subinterfaces

### 2. Static IP Requirement
**Issue:** 192.168.3.x network has no DHCP  
**Solution:** Always configure static IPs via cloud-init for this network  
**Fallback Pattern:** If IP allocation fails, use x.x.x.254, then .253, .252...  
**Command:** `qm set <vmid> --ipconfig0 'ip=192.168.3.X/24,gw=192.168.3.1'`

### 3. Windows SATA vs VirtIO
**Issue:** Windows VMs failed to boot with VirtIO SCSI controller  
**Root Cause:** Windows Setup can't see VirtIO without driver injection  
**Solution:** Use SATA controller for Windows VMs (`sata0` instead of `scsi0`)  
**When to Apply:** All Windows deployments on Proxmox/ESXi

### 4. ESXi Management Service Desync
**Issue:** API/SSH InvalidLogin despite correct password  
**Root Cause:** hostd or SSH services crashed/desynced  
**Solution:** Restart services from ESXi console  
**Detection:** Console login works but SSH/API fails

### 5. Cloud-Init is Proper Method
**Issue:** Initial attempts used console automation for network config  
**Root Cause:** QEMU guest agent not always available immediately  
**Solution:** Use native cloud-init options (`qm set --ipconfig0`, `--nameserver`)  
**When to Apply:** All Linux VM configuration on Proxmox

### 6. Template > ISO for Speed
**Issue:** ISO + autounattend takes 20+ minutes, often fails  
**Solution:** Create template once, clone in 2-3 minutes  
**When to Apply:** Any OS deployed repeatedly (Windows, Ubuntu)

### 7. Network Download Restrictions
**Issue:** VMs couldn't download from minecraft.net, github.com  
**Root Cause:** Internal network policy/firewall  
**Solution:** Download on host machine, transfer via SCP  
**When to Apply:** Assume restricted networks for Fortune 50 deployments

### 8. Mailcow API > IMAP
**Issue:** IMAP polling is slow (30s), requires password auth  
**Solution:** Mailcow REST API is faster (10s), uses API keys, can auto-provision  
**When to Apply:** Email integration for communications

### 9. DGX + Qwen 480B Architecture
**Context:** Full AI cluster with 480B parameter model available on-premise  
**Implication:** No cost constraints for inference, full intelligence available  
**Architecture:** Primary AI (Qwen 480B) + RAG + specialized smaller agents  
**When to Apply:** All AI reasoning tasks can use full-intelligence model

### 10. Context Transfer Challenge
**Issue:** Communication agents need session context without 1M token window  
**Solution:** Comprehensive RAG system + structured state DB + event sourcing  
**Test Plan:** Close context window, start fresh, validate RAG effectiveness  
**When to Apply:** Tomorrow's test (2025-11-22)

---

## Configuration Files

### Environment Variables (~/.bashrc)
```
# Proxmox
PROXMOX_HOST=192.168.3.2
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=xisxxisx

# ESXi
ESXI_HOST=192.168.3.3
ESXI_USER=root
ESXI_PASSWORD=H-3a-7YP

# AWS (credentials in ~/.bashrc)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-1

# Azure (credentials in ~/.bashrc)
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...
AZURE_SUBSCRIPTION_ID=...
AZURE_REGION=eastus
AZURE_RESOURCE_GROUP=glassdome-rg

# Mailcow (future)
MAILCOW_URL=https://mailcow.yourdomain.com
MAILCOW_API_KEY=TBD
```

### SSH Keys
```
/tmp/glassdome_key (ed25519) → VM 114 access
ssh -i /tmp/glassdome_key ubuntu@192.168.3.50
```

---

## Next Session Priorities (2025-11-22)

### 1. RAG System Build (CRITICAL)
**Goal:** Enable context transfer for future sessions  
**Tasks:**
- Choose vector DB (FAISS, Pinecone, Chroma)
- Index all docs, code, session logs
- Create query interface
- Test retrieval quality

### 2. RAG Validation Test
**Goal:** Verify fresh agent can operate with only RAG context  
**Tests:**
- Deploy Ubuntu to Proxmox (should remember VLAN tag)
- Troubleshoot networking issue (should apply past learnings)
- Answer "why" questions (should retrieve decision rationale)

### 3. Windows Template Creation
**Goal:** Unblock multi-VM scenario development  
**Tasks:**
- Manual Windows Server 2022 install on Proxmox
- Configure, sysprep, convert to template
- Test cloning speed and reliability

### 4. Presentation Prep (12/8 Deadline)
**Goal:** Demo-ready system for Microsoft  
**Requirements:**
- Multi-VM scenario (7-10 VMs, 4 networks)
- Windows + Linux mixed environment
- One-command deployment
- Real-time monitoring

---

## Known Issues / Tech Debt

1. **Windows autounattend.xml unreliable** - Blocked on template approach
2. **No QEMU guest agent timeout handling** - Can cause hangs
3. **IP pool management manual** - Need automated allocation
4. **No VM lifecycle tracking** - Can't query "what VMs exist?"
5. **No cost tracking** - AWS/Azure charges not monitored
6. **No backup strategy** - VMs not automatically backed up
7. **No disaster recovery** - Single point of failure (each host)
8. **No monitoring/alerting** - Can't detect failures automatically
9. **No RBAC** - All users have full access
10. **No audit logging** - Can't track who did what

---

## Team Context

### User Preferences (Learned)
- Values planning over rapid execution
- Prefers asking questions to understand before coding
- Wants clean, well-documented code
- Emphasis on enterprise requirements (Fortune 50, Microsoft)
- Air-gapped deployment capability critical
- Ethical focus (cyber range for defense training)

### Communication Style
- Direct, technical
- Appreciates catching mistakes early
- Values strategic thinking
- Wants RAG-ready documentation (concise, structured)

### Project Constraints
- **Deadline:** 12/8 presentation
- **Scale:** Fortune 50 deployment
- **Budget:** DGX cluster + Qwen 480B available
- **Security:** On-premise, air-gapped capable
- **Team:** Knows Ansible/Terraform (must accept their outputs)

---

## Related Projects

### Peer Project: AI Training Pipeline
**Goal:** Train AI models through development cycle processes  
**Method:** Use session data (like this one) as training input  
**Test:** Tomorrow's RAG validation is also training data collection

---

**For RAG Query:** "What's the current state of the system?"  
**Last Session:** 2025-11-21 (Initial Development & Minecraft Deployment)  
**Next Session:** 2025-11-22 (RAG Build & Validation Test)

