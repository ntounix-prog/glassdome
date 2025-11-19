# Glassdome Feature Backlog

## 🔴 Critical Priority

### 1. API Key Management System
**Status:** Not Started  
**Effort:** 2 weeks  
**Depends On:** Database, User Auth

**Description:** Centralized management for API keys and credentials for all external services.

**Services Needed:**
- ✅ Virtualization (Proxmox, VMware, Hyper-V)
- ✅ Cloud Providers (Azure, AWS, Google Cloud)
- ✅ AI Services (OpenAI, Anthropic, LangChain, Ollama)
- ✅ Container Orchestration (Kubernetes, Docker)
- ✅ Monitoring (Prometheus, Grafana)
- ✅ Version Control (GitHub, GitLab)

**Features:**
- Web UI for credential management
- Encrypted storage
- Credential testing/validation
- Usage tracking
- Expiration/rotation
- Multi-user support
- Audit logging

**See:** `docs/FEATURE_API_KEY_MANAGEMENT.md`

---

## 🟠 High Priority

### 2. Cloud-Init Integration
**Status:** Partially Done (generates config, doesn't apply)  
**Effort:** 3-4 days

- Generate cloud-init ISO
- Attach to VMs during creation
- User account creation
- Package installation
- Network configuration

### 3. Database Persistence
**Status:** Schema exists, not used  
**Effort:** 1 week

- Lab configurations
- Deployment history
- VM tracking
- User data
- Credential storage

### 4. User Authentication
**Status:** Not Started  
**Effort:** 1 week

- User login/registration
- JWT tokens
- Role-based access
- Multi-tenant support

### 5. Azure Client Implementation
**Status:** Stub only  
**Effort:** 1-2 weeks

- Complete Azure SDK integration
- VM creation
- Network management
- Resource group management

### 6. AWS Client Implementation
**Status:** Stub only  
**Effort:** 1-2 weeks

- Complete boto3 integration
- EC2 instance creation
- VPC/subnet management
- Security group management

---

## 🟡 Medium Priority

### 7. SSH Operations
**Status:** Not Started  
**Effort:** 3-4 days

- SSH into created VMs
- Execute commands
- Copy files
- Install packages

### 8. Network Management
**Status:** Designed, not implemented  
**Effort:** 1 week

- VLAN creation
- Isolated networks
- Network bridges
- Firewall rules

### 9. Kali Linux Agent
**Status:** Not Started  
**Effort:** 2-3 days

- Similar to Ubuntu agent
- Kali-specific templates
- Pre-installed tools

### 10. Windows Agent
**Status:** Not Started  
**Effort:** 1 week

- Windows VM creation
- PowerShell automation
- Windows-specific configuration

### 11. Deployment Monitoring
**Status:** Not Started  
**Effort:** 1 week

- Real-time deployment status
- WebSocket updates
- Progress tracking
- Error notifications

### 12. Lab Templates Library
**Status:** 3 templates defined  
**Effort:** Ongoing

- Pre-built lab configurations
- Import/export
- Sharing between users
- Community templates

---

## 🟢 Low Priority

### 13. Advanced Orchestration
**Status:** Basic orchestration done  
**Effort:** 2 weeks

- Complex dependency graphs
- Conditional execution
- Rollback on failure
- Partial deployment recovery

### 14. Cost Tracking
**Status:** Not Started  
**Effort:** 1 week

- Track cloud costs
- Budget alerts
- Usage reports
- Cost optimization suggestions

### 15. Snapshot Management
**Status:** Not Started  
**Effort:** 3-4 days

- VM snapshots
- Backup/restore
- Scheduled snapshots

### 16. Lab Scheduling
**Status:** Not Started  
**Effort:** 1 week

- Auto-start labs
- Auto-shutdown (timer-based)
- Scheduled deployments
- Resource optimization

### 17. Collaboration Features
**Status:** Not Started  
**Effort:** 2 weeks

- Share labs with team
- Role-based access to labs
- Comments/annotations
- Lab templates sharing

### 18. Metrics & Analytics
**Status:** Not Started  
**Effort:** 1 week

- Deployment success rates
- Resource utilization
- Performance metrics
- User analytics

### 19. Terraform Export
**Status:** Not Started  
**Effort:** 1 week

- Export lab as Terraform
- Export as Ansible playbook
- Export as Docker Compose

### 20. Plugin System
**Status:** Not Started  
**Effort:** 2-3 weeks

- Custom agents
- Custom platforms
- Custom UI components
- Extension marketplace

---

## 🔵 Future/Ideas

### 21. AI-Powered Lab Design
**Depends On:** AI API keys (#1)

- "Create a web security lab" → AI generates config
- Intelligent VM sizing
- Automatic vulnerability injection
- Guided lab creation

### 22. Mobile App
**Status:** Not Started

- Monitor deployments
- Start/stop labs
- View VM status

### 23. GitOps Integration
**Status:** Not Started

- Store labs in Git
- Version control for labs
- CI/CD for lab deployments

### 24. Kubernetes Support
**Status:** Not Started

- Deploy to K8s clusters
- Containerized labs
- Helm chart generation

### 25. Security Scanning
**Status:** Not Started

- Scan VMs for vulnerabilities
- Compliance checking
- Security reports

---

## Implementation Order (Recommended)

1. ✅ **API Key Management** (#1) - Blocks cloud & AI features
2. ✅ **Database Persistence** (#3) - Foundation for everything
3. ✅ **User Authentication** (#4) - Required for multi-user
4. ✅ **Cloud-Init Integration** (#2) - Complete VM automation
5. ✅ **Azure Client** (#5) - Multi-cloud support
6. ✅ **AWS Client** (#6) - Multi-cloud support
7. ✅ **SSH Operations** (#7) - Post-deployment config
8. ✅ **Network Management** (#8) - Advanced networking
9. ⏳ Other agents, monitoring, templates, etc.

---

## Current Sprint Focus

**Sprint 1: Foundation (Current)**
- ✅ Proxmox integration
- ✅ Ubuntu agent
- ✅ Basic orchestration
- ⏳ Testing with real Proxmox

**Sprint 2: Credentials & Multi-Cloud (Next)**
- 🔴 API Key Management (#1)
- 🟠 Database Persistence (#3)
- 🟠 User Authentication (#4)

**Sprint 3: Cloud Providers**
- 🟠 Azure Client (#5)
- 🟠 AWS Client (#6)
- 🟠 Cloud-Init (#2)

**Sprint 4: Automation**
- 🟡 SSH Operations (#7)
- 🟡 Network Management (#8)
- 🟡 Deployment Monitoring (#11)

---

## Community Requests

*Add user-requested features here*

---

## Notes

- Features marked ✅ are prerequisites for others
- Effort estimates are approximate
- Priority can shift based on user needs
- Some features may be combined during implementation

