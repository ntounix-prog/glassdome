# Enterprise Deployment Architecture

## Executive Summary

Glassdome is designed for **Fortune 50 companies and global financial institutions** requiring on-premise or private cloud cyber range infrastructure.

**Critical Requirements:**
- ✅ **On-premise deployment** (no external dependencies)
- ✅ **Air-gapped environment support** (classified/regulated networks)
- ✅ **Single-package deployment** (entire platform)
- ✅ **Enterprise compliance** (SOC2, FedRAMP, PCI-DSS ready)
- ✅ **High availability** (production-grade)
- ✅ **Zero-trust architecture** (assume hostile network)

---

## Target Markets

### **Fortune 50 Enterprises**
- On-premise data centers
- Strict data sovereignty requirements
- Custom tech stack testing
- Large security teams (50-500+ people)
- Budget: $500K - $5M+ for security training infrastructure

### **Global Financial Institutions**
- Regulatory compliance (PCI-DSS, GDPR, SOX)
- Air-gapped trading floors
- Zero external connectivity
- Audit trail requirements
- Incident response training

### **Government/Defense**
- Classified networks (SIPR, JWICS)
- FedRAMP compliance required
- No cloud connectivity allowed
- Mandatory STIG compliance
- IL4-IL6 clearance requirements

### **Healthcare Systems**
- HIPAA compliance
- PHI data protection
- On-premise only (patient data regulations)
- Medical device vulnerability testing
- Ransomware response training

---

## Deployment Models

### **Model 1: Complete Appliance (Recommended)** ⭐

**What:** Pre-configured hardware/VM appliance, plug-and-play

**Delivery:**
```
Glassdome-Enterprise-Appliance-v1.0.ova
├── Management VM (8 vCPU, 16GB RAM)
│   ├── Glassdome control plane
│   ├── Web UI
│   ├── API server
│   ├── Database (PostgreSQL)
│   └── Package repository
├── Proxmox Host (32 vCPU, 64GB RAM)
│   └── Hypervisor for cyber range VMs
└── Documentation
    ├── Installation guide
    ├── Compliance documentation
    └── Security hardening guide
```

**Deployment time:** < 2 hours  
**Technical skill required:** Medium  
**Best for:** Rapid deployment, POC, small teams

---

### **Model 2: Kubernetes/Container Platform** ⭐⭐⭐

**What:** Cloud-native deployment on existing K8s infrastructure

**Delivery:**
```bash
# Single Helm chart deploys everything
helm install glassdome ./glassdome-enterprise \
  --namespace glassdome \
  --set airgapped=true \
  --set compliance.mode=fedramp \
  --set storage.class=enterprise-ssd
```

**Components:**
```
glassdome-enterprise/
├── charts/
│   ├── control-plane/       # Management services
│   ├── api-gateway/         # API & Web UI
│   ├── research-agent/      # AI/LLM services
│   ├── orchestrator/        # Deployment engine
│   ├── reaper/              # Vulnerability injection
│   ├── overseer/            # Monitoring
│   └── database/            # PostgreSQL HA
├── values.yaml              # Configuration
├── values-airgapped.yaml    # Air-gapped config
└── values-fedramp.yaml      # FedRAMP config
```

**Deployment time:** 30 minutes  
**Technical skill required:** High (K8s experience)  
**Best for:** Large enterprises, existing K8s infrastructure, HA requirements

---

### **Model 3: Bare Metal / Private Cloud** ⭐⭐

**What:** Terraform/Ansible deployment on existing infrastructure

**Delivery:**
```
glassdome-enterprise-installer/
├── terraform/
│   ├── proxmox/             # Proxmox deployment
│   ├── vmware/              # VMware vSphere
│   ├── openstack/           # OpenStack
│   └── bare-metal/          # Direct server deployment
├── ansible/
│   ├── deploy.yml           # Main deployment playbook
│   ├── airgapped.yml        # Air-gapped config
│   └── compliance.yml       # Compliance hardening
├── installer.sh             # One-command installer
└── configs/
    ├── offline-packages/    # All dependencies bundled
    ├── ai-models/           # LLM models (offline)
    └── vulnerability-db/    # CVE database snapshot
```

**Deployment command:**
```bash
# One command deploys entire platform
./installer.sh --platform proxmox \
               --airgapped true \
               --compliance fedramp \
               --nodes pve01,pve02,pve03
```

**Deployment time:** 1-2 hours  
**Technical skill required:** Medium-High  
**Best for:** Custom infrastructure, specific compliance needs

---

### **Model 4: Docker Compose (Development/Small Teams)**

**What:** Single-server deployment for development or small teams

**Delivery:**
```yaml
# docker-compose.enterprise.yml
version: '3.8'

services:
  glassdome-api:
    image: glassdome/api:enterprise-v1.0
    environment:
      - AIRGAPPED=true
      - COMPLIANCE_MODE=sox
    volumes:
      - ./data:/data
      - ./configs:/configs
  
  glassdome-ui:
    image: glassdome/ui:enterprise-v1.0
  
  glassdome-research:
    image: glassdome/research:enterprise-v1.0
    volumes:
      - ./models:/models  # Offline LLM models
  
  postgres:
    image: postgres:15
    volumes:
      - ./db:/var/lib/postgresql/data
  
  redis:
    image: redis:7
  
  vault:
    image: vault:1.15
    # Secrets management
```

**Deployment:**
```bash
docker-compose -f docker-compose.enterprise.yml up -d
```

**Deployment time:** 15 minutes  
**Technical skill required:** Low-Medium  
**Best for:** Development, small teams, testing

---

## Air-Gapped Deployment (Critical)

### **Challenge:**
No internet connectivity = no `pip install`, `apt install`, `docker pull`, LLM API calls

### **Solution: Complete Offline Bundle**

```
glassdome-enterprise-offline-v1.0.tar.gz (50-100GB)
├── Container images (all)
│   ├── glassdome-api.tar
│   ├── glassdome-ui.tar
│   ├── glassdome-research.tar
│   ├── postgres.tar
│   ├── redis.tar
│   └── vault.tar
├── Python packages (all dependencies)
│   └── pypi-mirror/
│       ├── fastapi-0.104.1.whl
│       ├── uvicorn-0.24.0.whl
│       └── ... (500+ packages)
├── System packages (Ubuntu/RHEL)
│   └── apt-mirror/
│       ├── ansible_13.0.deb
│       ├── terraform_1.6.6.deb
│       └── ... (200+ packages)
├── AI Models (local LLMs)
│   ├── llama-3-70b-instruct.gguf (40GB)
│   ├── mistral-7b.gguf (4GB)
│   └── embeddings-model.bin (2GB)
├── Vulnerability Database
│   ├── nvd-cve-database.json (5GB)
│   ├── exploit-db-archive.tar
│   └── vulnerability-playbooks/ (200+ playbooks)
├── OS Templates
│   ├── ubuntu-22.04-template.qcow2
│   ├── ubuntu-20.04-template.qcow2
│   ├── debian-12-template.qcow2
│   └── windows-server-2022-template.qcow2 (optional)
└── Documentation
    ├── AIRGAPPED_INSTALL.md
    ├── SECURITY_HARDENING.md
    └── COMPLIANCE_GUIDE.md
```

### **Air-Gapped Installation Process:**

```bash
# Step 1: Transfer bundle to air-gapped network (physical media)
# Copy glassdome-enterprise-offline-v1.0.tar.gz via USB/DVD

# Step 2: Extract bundle
tar -xzf glassdome-enterprise-offline-v1.0.tar.gz
cd glassdome-enterprise-offline

# Step 3: Load container images
./scripts/load-images.sh

# Step 4: Setup local package repositories
./scripts/setup-apt-mirror.sh
./scripts/setup-pypi-mirror.sh

# Step 5: Deploy platform
./installer.sh --offline \
               --platform proxmox \
               --nodes pve01,pve02,pve03

# Step 6: Verify
glassdome verify --offline
```

**Result:** Fully functional platform with zero external dependencies ✅

---

## Enterprise Features (Required)

### **1. Role-Based Access Control (RBAC)**

```yaml
roles:
  - name: administrator
    permissions:
      - manage_users
      - manage_scenarios
      - manage_infrastructure
      - view_audit_logs
      - deploy_scenarios
  
  - name: instructor
    permissions:
      - create_scenarios
      - deploy_scenarios
      - view_student_progress
      - grade_labs
  
  - name: student
    permissions:
      - access_assigned_scenarios
      - submit_flags
      - view_own_progress
  
  - name: auditor
    permissions:
      - view_audit_logs
      - export_compliance_reports
      - view_all_activity
```

### **2. Audit Logging (Compliance)**

```python
# Every action logged with full context
{
  "timestamp": "2024-11-20T15:23:45Z",
  "user": "john.doe@company.com",
  "action": "deploy_scenario",
  "scenario": "enterprise_web_app",
  "source_ip": "10.0.1.50",
  "result": "success",
  "compliance_tags": ["sox", "pci-dss"],
  "vms_created": [
    {"name": "web-01", "ip": "10.0.2.10"},
    {"name": "db-01", "ip": "10.0.2.20"}
  ]
}
```

**Audit log retention:** 7 years (configurable)  
**Tamper-proof:** Cryptographic signatures  
**Export formats:** JSON, CSV, SIEM-compatible

### **3. SSO/SAML Integration**

```yaml
# Support enterprise authentication
authentication:
  mode: saml
  providers:
    - okta
    - azure_ad
    - ping_identity
    - active_directory
  
  # Or LDAP
  ldap:
    server: ldap://dc.company.com
    base_dn: "ou=users,dc=company,dc=com"
```

### **4. Compliance Reporting**

```bash
# Generate compliance reports
glassdome compliance report \
  --type sox \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --output sox-annual-report.pdf
```

**Supported standards:**
- SOC 2 Type II
- FedRAMP Moderate/High
- PCI-DSS 4.0
- GDPR
- HIPAA
- NIST 800-53
- ISO 27001

### **5. High Availability (HA)**

```
┌─────────────────────────────────────────────────┐
│           Load Balancer (HA Proxy)              │
└──────────────┬──────────────────────────────────┘
               │
       ┌───────┴───────┐
       │               │
┌──────▼──────┐ ┌─────▼───────┐
│   API-1     │ │   API-2     │
│ (Active)    │ │ (Standby)   │
└──────┬──────┘ └─────┬───────┘
       │               │
       └───────┬───────┘
               │
┌──────────────▼──────────────────────────────────┐
│   PostgreSQL Cluster (3 nodes)                  │
│   - Primary (write)                             │
│   - Replica 1 (read)                            │
│   - Replica 2 (read)                            │
└─────────────────────────────────────────────────┘
```

**SLA targets:**
- Uptime: 99.9% (3 nines)
- RTO: < 15 minutes
- RPO: < 5 minutes
- Automated failover

### **6. Secrets Management (Vault Integration)**

```bash
# All secrets in HashiCorp Vault
vault kv put glassdome/proxmox/api \
  user="apex@pve" \
  token="secret-token-here"

vault kv put glassdome/ai/openai \
  api_key="sk-..."

# Application fetches at runtime
# Never stored in plain text
```

### **7. Network Security**

```
┌─────────────────────────────────────────────┐
│       DMZ / Perimeter Network               │
│   ┌─────────────────────────────┐          │
│   │   Reverse Proxy / WAF       │          │
│   │   (nginx + ModSecurity)     │          │
│   └──────────┬──────────────────┘          │
└──────────────┼──────────────────────────────┘
               │ TLS 1.3 only
               │ Mutual TLS (mTLS) optional
┌──────────────▼──────────────────────────────┐
│       Internal Network (Zero-Trust)         │
│   ┌────────────────────────────┐           │
│   │   Glassdome Control Plane   │           │
│   │   - API Gateway             │           │
│   │   - Web UI                  │           │
│   │   - Service Mesh (Istio)    │           │
│   └────────────────────────────┘           │
│                                              │
│   ┌────────────────────────────┐           │
│   │   Cyber Range Network       │           │
│   │   (Isolated VLANs)          │           │
│   │   - Student VMs             │           │
│   │   - Vulnerable systems      │           │
│   └────────────────────────────┘           │
└──────────────────────────────────────────────┘
```

**Security controls:**
- TLS 1.3 everywhere (no TLS 1.2)
- Certificate management (auto-renewal)
- Network segmentation (VLANs)
- Firewall rules (default deny)
- IDS/IPS integration (optional)

---

## Packaging Strategy

### **Option 1: OVA/OVF Appliance** (VMware/Proxmox)

```
Glassdome-Enterprise-v1.0.ova (100GB)
├── Management VM
│   ├── Ubuntu 22.04 LTS (hardened)
│   ├── All services containerized
│   ├── Pre-loaded AI models
│   └── Vulnerability database
├── Network config
│   ├── eth0: Management (DHCP/Static)
│   ├── eth1: Cyber range network
│   └── eth2: Student access
└── First-boot wizard
    ├── Admin password setup
    ├── Network configuration
    ├── Compliance mode selection
    └── License activation
```

**Deployment:**
```bash
# Import OVA
qm importovf 9000 Glassdome-Enterprise-v1.0.ova local-lvm

# Start VM
qm start 9000

# Access web UI
https://glassdome-ip:8443/setup
```

---

### **Option 2: Kubernetes Helm Chart**

```bash
# Add Glassdome Helm repo (or use offline bundle)
helm repo add glassdome https://charts.glassdome.com
# OR for air-gapped:
helm repo add glassdome file:///mnt/usb/glassdome-charts

# Deploy
helm install glassdome-prod glassdome/glassdome-enterprise \
  --namespace glassdome \
  --create-namespace \
  --values values-production.yaml \
  --values values-airgapped.yaml \
  --values values-fedramp.yaml \
  --set license.key="GLASS-DOME-ENT-..." \
  --set airgapped.enabled=true \
  --set compliance.mode=fedramp-moderate \
  --set ha.enabled=true \
  --set ha.replicas=3
```

**Values file example:**
```yaml
# values-production.yaml
global:
  environment: production
  domain: glassdome.company.internal
  
airgapped:
  enabled: true
  localRegistry: registry.company.internal
  
compliance:
  mode: fedramp-moderate
  auditRetention: 7years
  
ha:
  enabled: true
  replicas: 3
  database:
    replicas: 3
    backup:
      enabled: true
      schedule: "0 2 * * *"

resources:
  api:
    cpu: 4000m
    memory: 8Gi
  research:
    cpu: 8000m
    memory: 32Gi
    gpu: true  # For local LLM

storage:
  class: enterprise-ssd
  size: 500Gi

security:
  tls:
    enabled: true
    certManager: true
  networkPolicy:
    enabled: true
  podSecurityPolicy: restricted
```

---

### **Option 3: Terraform + Ansible Bundle**

```
glassdome-enterprise-installer-v1.0.tar.gz
├── install.sh                    # One-command installer
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   └── modules/
│       ├── proxmox/
│       ├── vmware/
│       └── openstack/
├── ansible/
│   ├── site.yml
│   ├── roles/
│   │   ├── glassdome-api/
│   │   ├── glassdome-ui/
│   │   ├── glassdome-database/
│   │   └── glassdome-airgapped/
│   └── inventory/
│       ├── production.ini
│       └── airgapped.ini
├── offline-packages/
│   ├── containers/              # All Docker images
│   ├── apt/                     # APT packages
│   ├── pypi/                    # Python packages
│   └── models/                  # AI models
└── docs/
    ├── INSTALL.md
    ├── AIRGAPPED.md
    └── SECURITY.md
```

**Installation:**
```bash
# Extract bundle
tar -xzf glassdome-enterprise-installer-v1.0.tar.gz
cd glassdome-enterprise-installer

# Edit configuration
vim terraform/terraform.tfvars

# Deploy
./install.sh --platform proxmox \
             --airgapped \
             --compliance fedramp \
             --ha

# Outputs:
# ✓ 3 management VMs deployed (HA)
# ✓ PostgreSQL cluster (3 nodes)
# ✓ Redis cluster
# ✓ Load balancer configured
# ✓ TLS certificates generated
# ✓ Initial admin account created
# 
# 🎉 Glassdome Enterprise ready!
# 
# Access: https://glassdome.company.internal
# Admin: admin@company.internal
# Password: (generated - see /root/glassdome-credentials.txt)
```

---

## Licensing Model (Enterprise)

### **Per-Seat Licensing**
```
$500/year per concurrent user
- Minimum: 10 seats ($5,000/year)
- Volume discount: 100+ seats (25% off)
- Unlimited scenarios
- Unlimited VMs
- All features included
```

### **Site License**
```
$50,000/year per data center
- Unlimited users
- Unlimited scenarios
- Unlimited VMs
- Premium support (24/7)
- Dedicated success manager
```

### **Perpetual License**
```
$250,000 one-time
- Lifetime license
- 1 year support included
- Source code access (optional)
- Custom development (add-on)
```

---

## Support Tiers

### **Standard Support** (included)
- Email support (8x5, next business day)
- Documentation portal
- Community forum
- Quarterly updates

### **Premium Support** (+$25K/year)
- 24/7 phone/email support
- 4-hour response SLA
- Dedicated Slack channel
- Monthly updates
- Custom playbook development

### **Enterprise Support** (+$100K/year)
- 24/7 emergency hotline
- 1-hour response SLA
- On-site support (2 visits/year)
- Dedicated engineer
- Custom feature development
- Security advisory board access

---

## Compliance Documentation (Required)

**Included with enterprise license:**

1. **System Security Plan (SSP)** - FedRAMP template
2. **Security Assessment Report (SAR)** - Independent audit
3. **Continuous Monitoring Plan** - Ongoing compliance
4. **Incident Response Plan** - Security incidents
5. **Business Continuity Plan** - Disaster recovery
6. **Privacy Impact Assessment** - GDPR/CCPA
7. **Security Architecture Diagram** - Network topology
8. **Data Flow Diagrams** - Information flows
9. **Access Control Matrix** - RBAC documentation
10. **Vendor Assessment** - Third-party dependencies

**These documents save enterprises 6-12 months of compliance work!**

---

## Deployment Checklist

### **Pre-Deployment**
- [ ] Infrastructure sizing calculated
- [ ] Network topology designed
- [ ] Firewall rules approved
- [ ] SSL certificates acquired
- [ ] License key obtained
- [ ] Offline bundle downloaded (if air-gapped)
- [ ] Compliance requirements documented
- [ ] SSO/SAML configured
- [ ] Backup strategy defined
- [ ] Disaster recovery plan created

### **Deployment**
- [ ] Infrastructure provisioned
- [ ] Glassdome installed
- [ ] Database cluster configured
- [ ] HA tested (failover)
- [ ] TLS configured
- [ ] SSO integrated
- [ ] RBAC configured
- [ ] Audit logging enabled
- [ ] Monitoring configured
- [ ] Backup automated

### **Post-Deployment**
- [ ] Security hardening applied
- [ ] Penetration test completed
- [ ] User training conducted
- [ ] Documentation provided
- [ ] Compliance audit passed
- [ ] Go-live approval obtained

---

## Success Metrics

**For enterprise buyers:**
- Time to deploy new CVE training: 24 hours → **2 hours** (92% reduction)
- Infrastructure cost: $500K/year (SaaS) → **$100K/year** (self-hosted)
- Compliance documentation: 6 months → **Included** (instant)
- User training time: 2 weeks → **2 days** (90% reduction)
- Security team productivity: +40% (faster response to threats)

---

## Competitive Advantages (Enterprise)

| Feature | Traditional Cyber Range | Glassdome Enterprise |
|---------|-------------------------|----------------------|
| **Deployment** | Weeks (vendor setup) | Hours (self-service) |
| **Cost** | $500K-$2M/year | $50K-$250K/year |
| **On-Premise** | Limited or no support | Full support ✅ |
| **Air-Gapped** | Not supported | Fully supported ✅ |
| **CVE Speed** | 2-4 weeks | 2-4 hours ✅ |
| **Customization** | Vendor dependent | Full control ✅ |
| **Compliance** | Extra cost | Included ✅ |
| **Data Sovereignty** | Vendor's cloud | Your infrastructure ✅ |

---

## Next Steps

1. **Build offline bundle** (critical for Fortune 50)
2. **Create Helm chart** (most enterprises use K8s)
3. **Develop compliance documentation** (saves buyers months)
4. **Build HA architecture** (production requirement)
5. **Implement RBAC/SSO** (security requirement)
6. **Create installer scripts** (one-command deploy)
7. **Package local LLM** (air-gapped AI)
8. **Document security hardening** (compliance requirement)

**The platform must be 100% self-contained and deployable without internet access.** 🔒

---

*Glassdome Enterprise: Air-gapped, compliant, autonomous cyber range for Fortune 50*

