# Glassdome Documentation

**Complete documentation index for the Glassdome cyber range deployment framework.**

---

## 🚀 Getting Started

### Quick Start Guides

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start guide
- **[PLATFORM_SETUP.md](PLATFORM_SETUP.md)** - Platform configuration (Proxmox, ESXi, AWS, Azure)
- **[API_KEYS.md](API_KEYS.md)** - API keys and authentication setup

---

## 📖 Core Documentation

### Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design philosophy
- **[STRUCTURE.md](STRUCTURE.md)** - Complete project structure and organization
- **[TECHNICAL_ASSESSMENT.md](TECHNICAL_ASSESSMENT.md)** - Technical evaluation and status

### Incident Management

- **[INCIDENTS.md](INCIDENTS.md)** - Incident log and tracking
- **[ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md](ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md)** - INC-001: Email delivery failure (WireGuard MTU)

### Agents

- **[AGENTS.md](AGENTS.md)** - Agent framework overview
- **[OVERSEER_ENTITY.md](OVERSEER_ENTITY.md)** - Overseer agent documentation

### Platform Integration

- **[PLATFORM_SETUP.md](PLATFORM_SETUP.md)** - Platform configuration guides
- **[WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md)** - Windows deployment guide (consolidated)
- **[WINDOWS_TEMPLATE_GUIDE.md](WINDOWS_TEMPLATE_GUIDE.md)** - Windows template creation

### Integrations

- **[MAILCOW_INTEGRATION.md](MAILCOW_INTEGRATION.md)** - Mailcow email integration (consolidated)
- **[IAC_INTEGRATION.md](IAC_INTEGRATION.md)** - Infrastructure as Code integration

---

## 🔧 Development

### API & Services

- **[API.md](API.md)** - REST API documentation
- **[REQUEST_FLOW.md](REQUEST_FLOW.md)** - Request flow diagrams
- **[OPERATIONAL_AUTOMATION.md](OPERATIONAL_AUTOMATION.md)** - Operational automation

### Development Guides

- **[PACKAGE_GUIDE.md](PACKAGE_GUIDE.md)** - Using Glassdome as a Python package
- **[GIT_SETUP.md](GIT_SETUP.md)** - Git configuration and workflow
- **[BUILD_PLAN.md](BUILD_PLAN.md)** - Build and deployment plan

---

## 📊 Project Status

- **[PROJECT_STATUS.md](PROJECT_STATUS.md)** - Current project status
- **[CURRENT_STATE.md](CURRENT_STATE.md)** - Infrastructure state
- **[VP_PRESENTATION_ROADMAP.md](VP_PRESENTATION_ROADMAP.md)** - Roadmap and milestones
- **[ISSUES_TO_CREATE.md](ISSUES_TO_CREATE.md)** - Known issues and TODOs

---

## 🏢 Enterprise & Deployment

- **[ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md)** - Enterprise deployment guide
- **[COMMUNICATIONS_ARCHITECTURE.md](COMMUNICATIONS_ARCHITECTURE.md)** - Communication patterns
- **[RAG_USAGE.md](RAG_USAGE.md)** - RAG (Retrieval Augmented Generation) usage
- **[RAG_TEST_PLAN.md](RAG_TEST_PLAN.md)** - RAG testing plan

---

## 📝 Session Logs

Development session logs and lessons learned:

- **[session_logs/SESSION_SUMMARY.md](session_logs/SESSION_SUMMARY.md)** - Session summaries
- **[session_logs/CRITICAL_LESSONS_2024-11-20.md](session_logs/CRITICAL_LESSONS_2024-11-20.md)** - Critical lessons
- **[session_logs/CRITICAL_LESSONS_2024-11-21.md](session_logs/CRITICAL_LESSONS_2024-11-21.md)** - Critical lessons
- **[session_logs/SESSION_2024-11-22_MAILCOW_INTEGRATION.md](session_logs/SESSION_2024-11-22_MAILCOW_INTEGRATION.md)** - Mailcow integration session

**Full session logs:** See `docs/session_logs/` directory

---

## 📚 Archive

Historical and superseded documentation:

- **[`_archive/`](_archive/)** - Archived documentation
  - Old architecture docs
  - Superseded guides
  - Historical implementation notes

---

## 🎯 Documentation Principles

1. **Single Source of Truth:** All documentation lives in `docs/`
2. **Consolidation:** Related docs are merged into comprehensive guides
3. **Clarity:** Clear structure and navigation
4. **Maintenance:** Regular updates and cleanup

---

## 📖 Documentation Structure

```
docs/
├── README.md (this file)
├── Getting Started/
│   ├── QUICKSTART.md
│   └── PLATFORM_SETUP.md
├── Architecture/
│   ├── ARCHITECTURE.md
│   └── STRUCTURE.md
├── Guides/
│   ├── WINDOWS_DEPLOYMENT.md
│   ├── MAILCOW_INTEGRATION.md
│   └── ...
├── Development/
│   ├── API.md
│   └── PACKAGE_GUIDE.md
├── Status/
│   ├── PROJECT_STATUS.md
│   └── CURRENT_STATE.md
└── session_logs/
    └── ...
```

---

## 🔍 Finding Documentation

### By Topic

**Windows Deployment:**
- [WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md) - Main guide
- [WINDOWS_TEMPLATE_GUIDE.md](WINDOWS_TEMPLATE_GUIDE.md) - Template creation
- [WINDOWS_CLOUDBASE_INIT_DEPLOYMENT.md](WINDOWS_CLOUDBASE_INIT_DEPLOYMENT.md) - Cloud-init setup

**Mailcow Integration:**
- [MAILCOW_INTEGRATION.md](MAILCOW_INTEGRATION.md) - Main guide
- [MAILCOW_API_DIAGNOSTICS.md](MAILCOW_API_DIAGNOSTICS.md) - Troubleshooting
- [MAILCOW_BEARER_TOKEN_UPDATE.md](MAILCOW_BEARER_TOKEN_UPDATE.md) - Auth details

**Incident Resolution:**
- [INCIDENTS.md](INCIDENTS.md) - Incident log (INC-001: Email delivery failure)
- [ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md](ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md) - Full RCA for INC-001
- [ROME_WIREGUARD_FIX.md](ROME_WIREGUARD_FIX.md) - WireGuard service recovery
- [MAIL_TLS_MTU_ISSUE.md](MAIL_TLS_MTU_ISSUE.md) - MTU fragmentation analysis
- [EMAIL_NETWORK_ISSUE_DIAGNOSIS.md](EMAIL_NETWORK_ISSUE_DIAGNOSIS.md) - Network connectivity diagnosis
- [ROME_DUAL_ISP_CONFIG.md](ROME_DUAL_ISP_CONFIG.md) - Dual ISP configuration notes

**Platform Setup:**
- [PLATFORM_SETUP.md](PLATFORM_SETUP.md) - All platforms
- [API_KEYS.md](API_KEYS.md) - Authentication

### By Audience

**New Developers:**
1. Start with [QUICKSTART.md](QUICKSTART.md)
2. Read [ARCHITECTURE.md](ARCHITECTURE.md)
3. Review [STRUCTURE.md](STRUCTURE.md)
4. Check [PACKAGE_GUIDE.md](PACKAGE_GUIDE.md)

**DevOps Engineers:**
1. [PLATFORM_SETUP.md](PLATFORM_SETUP.md)
2. [ENTERPRISE_DEPLOYMENT.md](ENTERPRISE_DEPLOYMENT.md)
3. [OPERATIONAL_AUTOMATION.md](OPERATIONAL_AUTOMATION.md)

**Security Engineers:**
1. [WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md)
2. [AGENTS.md](AGENTS.md)
3. [TECHNICAL_ASSESSMENT.md](TECHNICAL_ASSESSMENT.md)

---

## 📝 Contributing to Documentation

1. **Add new docs** to `docs/` directory
2. **Update this index** when adding major docs
3. **Consolidate** related documentation
4. **Archive** superseded docs to `docs/_archive/`

---

*Last Updated: November 22, 2024*  
*Documentation Version: 2.0*

