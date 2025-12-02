# Glassdome Market Positioning & Technical Enablement Guide

**Prepared for:** Leah Salzman (leah.salzman@wwt.com)  
**Date:** December 1, 2025  
**Version:** 1.0  
**Classification:** Internal - WWT Sales Enablement

---

## Executive Summary

Glassdome is an **Agentic Cyber Range Deployment Framework** that differentiates from traditional cyber range vendors through its AI-driven automation, multi-platform support, and infrastructure-as-code approach. This document provides market positioning, competitive analysis, integration requirements, and sales enablement guidance.

**Key Value Proposition:** Glassdome deploys complete cybersecurity training environments in minutes, not days, with AI-powered vulnerability injection and real-time monitoring—across any infrastructure (on-prem, cloud, or hybrid).

---

## 1. Market Landscape

### 1.1 Market Size & Growth

| Metric | Value |
|--------|-------|
| **Market Size (2024)** | $1.2 billion |
| **CAGR (2024-2030)** | 22-25% |
| **Projected Size (2030)** | $4.5-5 billion |
| **Primary Drivers** | Skills gap, regulatory compliance, rising threats |

### 1.2 Major Competitors

| Vendor | Headquarters | Key Differentiator | Pricing Model |
|--------|-------------|-------------------|---------------|
| **Cloud Range** | Nashville, TN | OT/ICS focus, NATO partnerships | Enterprise subscription |
| **Cyberbit** | Israel | Real-time threat emulation | Enterprise licensing |
| **RangeForce** | Norfolk, VA | Gamification, skill assessment | Per-user subscription |
| **IBM Security Range** | Cambridge, MA | IBM ecosystem integration | Enterprise licensing |
| **CybExer** | Estonia | NATO-recognized, government focus | Enterprise licensing |
| **Aries Security** | Colorado | Physical + virtual hybrid | Custom deployment |

### 1.3 Market Pain Points (Opportunity Areas)

1. **Slow Deployment**: Traditional ranges take weeks to configure
2. **Limited Customization**: Pre-built scenarios don't match customer environments
3. **High Cost**: $100K-$500K+ annual licensing for enterprise solutions
4. **Vendor Lock-in**: Proprietary platforms limit flexibility
5. **No Air-Gap Support**: Most solutions require cloud connectivity
6. **Skills Gap**: Customers need training on the range platform itself

---

## 2. Glassdome Competitive Differentiation

### 2.1 Technical Differentiators

| Feature | Glassdome | Traditional Vendors |
|---------|-----------|---------------------|
| **Deployment Speed** | Minutes (API-driven) | Days to weeks |
| **Platform Support** | Proxmox, ESXi, AWS, Azure, GCP | Usually 1-2 platforms |
| **AI Integration** | Overseer AI (Claude/GPT), Research Agent | Limited or none |
| **Infrastructure-as-Code** | Full API, Ansible, Terraform-ready | GUI-only configuration |
| **Air-Gap Capable** | Yes (on-prem with local LLM) | Rarely |
| **Open Architecture** | REST API, WebSocket, extensible | Proprietary, closed |
| **Vulnerability Injection** | Reaper (automated, parallel) | Manual or limited |
| **Cost Model** | Open-source core + WWT services | $100K+ licensing |

### 2.2 Unique Capabilities

#### 🤖 Agentic Architecture
- **Overseer AI**: Natural language lab deployment ("Deploy a web security lab with SQL injection vulnerabilities")
- **Reaper System**: Parallel vulnerability injection across multiple VMs
- **WhitePawn**: Continuous network connectivity monitoring
- **WhiteKnight**: Defensive monitoring and validation

#### 🎨 Canvas-Based Visual Design
- Drag-and-drop lab topology design
- Real-time deployment status
- Network visualization with React Flow

#### 🔄 Multi-Platform Orchestration
```
┌─────────────────────────────────────────────────────────────┐
│                    Glassdome Orchestrator                    │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│ Proxmox  │  ESXi    │   AWS    │  Azure   │  Future (GCP)  │
│ Client   │ Client   │ Client   │ Client   │                │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
```

#### 🔐 Enterprise Security
- HashiCorp Vault integration for secrets management
- JWT authentication with RBAC
- Audit logging for compliance
- Air-gapped deployment support

### 2.3 Framework Alignment

| Framework | Glassdome Support |
|-----------|-------------------|
| **MITRE ATT&CK** | Scenarios mapped to TTPs |
| **NICE Framework** | KSA alignment for skill assessment |
| **NIST CSF** | Training scenarios for each function |
| **SOC 2** | Audit logging, access controls |
| **FedRAMP** | Air-gap deployment option |

---

## 3. Technical Architecture

### 3.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    React Dashboard (Frontend)               │
│  Home │ Lab Canvas │ Deployments │ Reaper │ WhiteKnight    │
└────────────────────────┬────────────────────────────────────┘
                         │ REST API / WebSocket
┌────────────────────────┴────────────────────────────────────┐
│                     FastAPI Backend (Python)                │
│  ┌──────────────┬──────────────┬────────────────────────┐  │
│  │ API Routers  │ Orchestrator │ Overseer AI            │  │
│  │ (labs,reaper)│ (Celery)     │ (Claude/GPT)           │  │
│  └──────────────┴──────────────┴────────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────┴───────────────────────────────────┐
│              Distributed Task Queue (Celery + Redis)         │
│  orchestrator@worker .... 8 threads (deploy/config)         │
│  reaper-1@worker ........ 4 threads (inject/exploit)        │
│  whiteknight-1@worker ... 4 threads (validate/test)         │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.12) |
| **Database** | PostgreSQL (async via asyncpg) |
| **Cache/Queue** | Redis |
| **Task Queue** | Celery |
| **Frontend** | React 18 + TypeScript + Vite |
| **Secrets** | HashiCorp Vault |
| **Auth** | JWT tokens with RBAC |
| **AI** | OpenAI GPT-4, Anthropic Claude, Local LLM |

### 3.3 Reaper Vulnerability Injection System

```
┌─────────────────────────────────────────────────────────────┐
│                    Overseer Entity                          │
│  (Creates and monitors Reaper missions)                     │
└────────────┬────────────────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────────────────┐
│                    Mission Engine                           │
│  - Event-driven controller                                  │
│  - Parallel task execution                                  │
│  - Failure handling (host locking)                          │
└─────┬───────────────────────────────────────┬───────────────┘
      │                                       │
┌─────▼─────────────────┐         ┌───────────▼──────────────┐
│    Task Queue         │         │      Event Bus           │
│  (Redis/In-memory)    │         │  (Result distribution)   │
└─────┬─────────────────┘         └───────────▲──────────────┘
      │                                       │
┌─────▼─────────────────────────────────────┬─┘
│         Reaper Agents (Workers)           │
│  - Linux Agent (SSH + Ansible)            │
│  - Windows Agent (WinRM + Ansible)        │
│  - Mac Agent (SSH + Ansible)              │
└───────────────────────────────────────────┘
```

**Vulnerability Playbooks Available:**
- Web: SQL Injection (DVWA), XSS
- System: Weak sudo, Weak SSH credentials
- Network: Open ports, Weak firewall

---

## 4. WWT Platform Integration (Guacamole)

### 4.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    WWT Platform Frontend                    │
│  (Existing customer portal)                                 │
└────────────────────────┬────────────────────────────────────┘
                         │ iFrame / SSO
┌────────────────────────▼────────────────────────────────────┐
│                 Apache Guacamole Gateway                    │
│  - Browser-based VM access (RDP, VNC, SSH)                  │
│  - LDAP/SAML/OAuth authentication                           │
│  - Session recording and audit                              │
└────────────────────────┬────────────────────────────────────┘
                         │ RDP/VNC/SSH
┌────────────────────────▼────────────────────────────────────┐
│                    Glassdome Backend                        │
│  - Lab provisioning API                                     │
│  - VM management                                            │
│  - Reaper vulnerability injection                           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Customer Infrastructure                         │
│  Proxmox │ ESXi │ AWS │ Azure │ On-Prem                     │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Level of Effort (LOE) Estimate

| Phase | Tasks | Duration | Resources |
|-------|-------|----------|-----------|
| **Phase 1: Core Integration** | Guacamole deployment, SSO integration, API connectivity | 4-6 weeks | 2 engineers |
| **Phase 2: UI Integration** | WWT portal embedding, branding, user workflows | 3-4 weeks | 1 engineer + 1 designer |
| **Phase 3: Production Hardening** | Security audit, performance testing, documentation | 2-3 weeks | 2 engineers |
| **Phase 4: Pilot Deployment** | Customer pilot, feedback integration, refinement | 4-6 weeks | 1 engineer + 1 PM |

**Total Estimated LOE:** 13-19 weeks (3-5 months)

### 4.3 Integration Requirements

#### Technical Requirements
- [ ] Apache Guacamole 1.5+ deployment
- [ ] LDAP/Active Directory integration
- [ ] SSL/TLS certificates
- [ ] Load balancer for Guacamole cluster
- [ ] Database (MySQL/PostgreSQL) for Guacamole
- [ ] Network connectivity to Glassdome backend

#### Security Requirements
- [ ] SSO integration (SAML 2.0 or OAuth 2.0)
- [ ] MFA enforcement
- [ ] Session timeout policies
- [ ] Audit logging to SIEM
- [ ] Network segmentation

#### Operational Requirements
- [ ] Monitoring and alerting
- [ ] Backup and recovery procedures
- [ ] Capacity planning documentation
- [ ] Runbook for common operations

---

## 5. Sales & Field Technical Enablement Plan

### 5.1 Target Customer Segments

| Segment | Use Case | Key Value Proposition |
|---------|----------|----------------------|
| **Enterprise SOC Teams** | Incident response training | Realistic threat simulation, MITRE ATT&CK alignment |
| **Government/Defense** | Compliance training, red team exercises | Air-gap support, FedRAMP-ready |
| **Education** | Cybersecurity curriculum labs | Cost-effective, scalable, self-service |
| **MSSPs** | Customer training, certification prep | Multi-tenant, white-label capable |
| **Critical Infrastructure** | OT/ICS security training | Hybrid IT/OT scenarios |

### 5.2 Competitive Positioning Matrix

| Scenario | Glassdome Advantage | Competitor Weakness |
|----------|--------------------|--------------------|
| **Multi-cloud customer** | Native AWS, Azure, GCP support | Most vendors single-platform |
| **Air-gapped environment** | Full on-prem with local LLM | Cloud-dependent |
| **Rapid deployment need** | Minutes via API | Days/weeks for traditional |
| **Custom scenarios** | AI-generated, Ansible-based | Pre-built only |
| **Budget-conscious** | Open-source core | $100K+ licensing |
| **Integration-heavy** | REST API, Terraform, Ansible | Proprietary, closed |

### 5.3 Discovery Questions

**For Enterprise Customers:**
1. How long does it currently take to deploy a training environment?
2. What platforms do you use for virtualization? (VMware, Proxmox, cloud?)
3. Do you have air-gapped or compliance requirements?
4. How do you currently track training effectiveness and skill gaps?
5. What's your annual budget for cybersecurity training tools?

**For Government/Defense:**
1. What compliance frameworks must you adhere to? (FedRAMP, NIST, CMMC?)
2. Do you need on-premises deployment with no cloud connectivity?
3. How do you currently conduct red team/blue team exercises?
4. What's your timeline for procurement and deployment?

### 5.4 Demo Scenarios

| Demo | Duration | Key Features Shown |
|------|----------|-------------------|
| **Quick Start** | 15 min | Canvas deployment, single VM, Overseer AI chat |
| **Enterprise** | 45 min | Multi-VM lab, Reaper injection, WhitePawn monitoring |
| **Technical Deep Dive** | 90 min | API integration, Ansible playbooks, custom scenarios |

### 5.5 Objection Handling

| Objection | Response |
|-----------|----------|
| "We already have Cyberbit/RangeForce" | "Glassdome complements existing tools with multi-platform support and AI automation. We can deploy to your existing infrastructure." |
| "Open-source means no support" | "WWT provides enterprise support, SLAs, and professional services. The open core ensures no vendor lock-in." |
| "We need FedRAMP compliance" | "Glassdome supports full air-gapped deployment with local LLM. We can work with your compliance team on certification." |
| "Too technical for our team" | "The Overseer AI allows natural language deployment. Your team can say 'Deploy a web security lab' and it happens." |

### 5.6 Pricing Strategy (Suggested)

| Tier | Description | Price Range |
|------|-------------|-------------|
| **Community** | Open-source, self-supported | Free |
| **Professional** | WWT support, updates, basic training | $25K-50K/year |
| **Enterprise** | Full support, custom scenarios, integration | $75K-150K/year |
| **Managed Service** | WWT-hosted, fully managed | $150K-300K/year |

*Note: Pricing significantly below competitors ($100K-500K) while offering more capabilities.*

---

## 6. Field Engineer & Sales Enablement Program

### 6.1 Enablement Program Overview

**Program Duration:** 6 weeks (phased rollout)  
**Target Audience:** Field Engineers, Solutions Architects, Account Executives  
**Delivery Method:** Hybrid (self-paced + instructor-led)

### 6.2 Training Tracks

#### Track A: Sales Enablement (Account Executives)
**Duration:** 1 week (8 hours total)

| Module | Duration | Content |
|--------|----------|---------|
| **Module 1: Market Overview** | 2 hours | Cyber range market, competitor landscape, buyer personas |
| **Module 2: Glassdome Value Prop** | 2 hours | Key differentiators, ROI messaging, use cases |
| **Module 3: Discovery & Qualification** | 2 hours | Discovery questions, qualification criteria, red flags |
| **Module 4: Demo & Objection Handling** | 2 hours | Live demo walkthrough, common objections, closing techniques |

**Certification:** Sales Certification Quiz (80% pass rate)

#### Track B: Technical Enablement (Field Engineers)
**Duration:** 3 weeks (40 hours total)

| Week | Focus | Hands-On Labs |
|------|-------|---------------|
| **Week 1: Platform Fundamentals** | Architecture, API, deployment models | Deploy Glassdome on Proxmox |
| **Week 2: Advanced Features** | Reaper, Overseer AI, multi-platform | Create custom vulnerability scenario |
| **Week 3: Integration & Support** | Guacamole, SSO, troubleshooting | Full customer deployment simulation |

**Certification:** Technical Certification Exam + Lab Practical

#### Track C: Solutions Architecture (Pre-Sales Engineers)
**Duration:** 2 weeks (20 hours total)

| Module | Duration | Content |
|--------|----------|---------|
| **Module 1: Architecture Deep Dive** | 4 hours | System design, scalability, HA patterns |
| **Module 2: Integration Patterns** | 4 hours | SIEM, SOAR, IdP integration, API customization |
| **Module 3: Sizing & Scoping** | 4 hours | Capacity planning, LOE estimation, SOW templates |
| **Module 4: Customer Workshops** | 8 hours | Whiteboard sessions, technical discovery, POC design |

**Certification:** Architecture Review Board Presentation

### 6.3 Enablement Resources

#### Self-Service Resources
| Resource | Location | Purpose |
|----------|----------|---------|
| **Product Datasheet** | SharePoint/Sales | 2-page overview for customers |
| **Technical Whitepaper** | SharePoint/Engineering | Deep-dive architecture document |
| **Demo Environment** | demo.glassdome.wwt.com | Always-on demo instance |
| **Battle Cards** | Salesforce | Competitor comparison quick reference |
| **ROI Calculator** | Excel/Web Tool | Customer-facing value calculator |
| **Video Library** | WWT University | On-demand training recordings |

#### Customer-Facing Materials
| Material | Audience | Use Case |
|----------|----------|----------|
| **Executive Overview Deck** | C-Suite, VPs | Initial introduction meeting |
| **Technical Architecture Deck** | Security Architects | Deep-dive technical sessions |
| **Case Studies** | All | Proof points and references |
| **POC Proposal Template** | Technical Buyers | Structured pilot engagement |
| **Implementation Guide** | IT Teams | Post-sale deployment reference |

### 6.4 Certification Levels

| Level | Requirements | Badge |
|-------|--------------|-------|
| **Glassdome Aware** | Complete Sales Track A | 🟢 Green |
| **Glassdome Certified** | Complete Technical Track B | 🔵 Blue |
| **Glassdome Expert** | Complete Track B + C + 3 customer deployments | 🟣 Purple |
| **Glassdome Master** | Expert + contribute to product development | ⭐ Gold |

### 6.5 Enablement Timeline

```
Week 1-2: Sales Enablement (Track A)
├── Day 1-2: Market & Value Prop (all AEs)
├── Day 3-4: Discovery & Demo Training
└── Day 5: Certification Quiz

Week 3-5: Technical Enablement (Track B)
├── Week 3: Platform Fundamentals (all FEs)
├── Week 4: Advanced Features
└── Week 5: Integration & Support

Week 6: Solutions Architecture (Track C)
├── Day 1-2: Architecture Deep Dive
├── Day 3-4: Integration & Sizing
└── Day 5: Certification Presentation

Ongoing: Monthly Office Hours + Quarterly Updates
```

### 6.6 Success Metrics for Enablement

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Certification Rate** | 90% of target audience | LMS completion tracking |
| **Time to First Demo** | < 2 weeks post-training | CRM activity tracking |
| **Demo-to-POC Conversion** | > 40% | Sales pipeline analysis |
| **POC-to-Close Rate** | > 60% | Deal tracking |
| **Customer Satisfaction** | > 4.5/5 | Post-engagement surveys |

### 6.7 Ongoing Enablement

#### Monthly Activities
- **Office Hours:** 1-hour Q&A with product team (1st Thursday)
- **Win/Loss Reviews:** Analysis of recent deals (3rd Thursday)
- **Feature Updates:** New capability walkthroughs (as released)

#### Quarterly Activities
- **Roadmap Review:** Product direction and upcoming features
- **Competitive Update:** Market changes and new entrants
- **Skills Assessment:** Identify training gaps and refreshers

#### Annual Activities
- **Glassdome Summit:** 2-day in-person training event
- **Certification Renewal:** Re-certification for all levels
- **Customer Advisory Board:** Feedback integration session

---

## 7. Implementation Roadmap

### 7.1 Phase 1: Foundation (Weeks 1-4)
- [ ] Deploy Guacamole gateway
- [ ] Configure SSO integration
- [ ] Establish API connectivity to Glassdome
- [ ] Basic UI integration

### 6.2 Phase 2: Feature Integration (Weeks 5-8)
- [ ] Lab provisioning workflow
- [ ] Reaper vulnerability injection UI
- [ ] Monitoring dashboard
- [ ] User management

### 6.3 Phase 3: Production (Weeks 9-12)
- [ ] Security hardening
- [ ] Performance optimization
- [ ] Documentation and training
- [ ] Pilot customer deployment

### 6.4 Phase 4: Scale (Weeks 13-16)
- [ ] Multi-tenant support
- [ ] Advanced scenarios library
- [ ] Customer feedback integration
- [ ] GA release

---

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Deployment Time** | < 5 minutes for standard lab | API timing logs |
| **Customer Satisfaction** | > 4.5/5 rating | Post-training surveys |
| **Platform Uptime** | 99.9% | Monitoring systems |
| **Training Effectiveness** | 30% improvement in incident response | Pre/post assessments |
| **Cost Savings** | 50% vs. traditional vendors | Customer ROI analysis |

---

## 8. Appendix

### 8.1 API Reference

```bash
# Deploy a lab
POST /api/v1/labs/deploy
{
  "name": "web-security-training",
  "scenario": "web-app-pentest",
  "platform": "proxmox",
  "vms": [
    {"type": "ubuntu", "role": "attacker"},
    {"type": "dvwa", "role": "target"}
  ]
}

# Check deployment status
GET /api/v1/labs/{lab_id}/status

# Inject vulnerabilities
POST /api/v1/reaper/missions
{
  "lab_id": "lab-001",
  "vulnerabilities": ["sql-injection", "xss"]
}
```

### 8.2 Contact Information

- **Technical Questions:** brett.turner@wwt.com
- **Sales Inquiries:** leah.salzman@wwt.com
- **Support:** zachery.turpen@wwt.com

---

*Document generated by Glassdome Overseer AI - December 1, 2024*

