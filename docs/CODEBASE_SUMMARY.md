# Glassdome Codebase Summary

**Date:** November 22, 2024  
**Purpose:** High-level overview for development team handoff

---

## 🎯 Project Overview

**Glassdome** is an autonomous, AI-powered deployment system for cybersecurity lab environments. It uses intelligent agents to deploy complex cyber range scenarios across multiple platforms (Proxmox, ESXi, AWS, Azure) in minutes.

### Key Differentiator

Not just VM deployment - it's a complete cyber range platform with:
- **Research Agent** - AI-powered CVE research and lab generation
- **Reaper Agent** - Automated vulnerability injection
- **Multi-platform orchestration** - Deploy across Proxmox, AWS, Azure, ESXi
- **Visual lab designer** - Drag-and-drop interface (in development)

---

## 📊 Current Status

**Completion:** ~60-70%

### ✅ Completed

- **Multi-platform deployment** - Proxmox, ESXi, AWS, Azure
- **Agent framework** - Base agent system with OS-specific agents
- **Template-based deployment** - Fast, reliable VM creation
- **Windows deployment** - Server 2022 and Windows 11 support
- **Mailcow integration** - Email operations
- **Platform abstraction** - Clean interface for all platforms
- **Configuration management** - Pydantic-based settings
- **SSH automation** - Remote command execution
- **IP pool management** - Static IP allocation

### 🚧 In Progress

- **Multi-VM orchestration** - Dependency management
- **React frontend** - Visual lab designer (25% complete)
- **Scenario YAML parser** - Lab definition parsing
- **Network orchestration** - VLAN management

### 📋 Planned

- **Research Agent** - AI-powered CVE research
- **Reaper Agent** - Vulnerability injection
- **Dashboard** - Real-time monitoring
- **Authentication** - JWT/RBAC

---

## 🏗️ Architecture

### Core Components

```
┌─────────────────────────────────┐
│   React Frontend (Port 5174)    │
└──────────────┬──────────────────┘
               │ REST API
┌──────────────▼──────────────────┐
│   FastAPI Backend (Port 8001)   │
│   • API Endpoints               │
│   • Orchestration Layer         │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│      Agent Framework            │
│   • UbuntuInstallerAgent        │
│   • WindowsInstallerAgent       │
│   • MailcowAgent                │
└──────────────┬──────────────────┘
               │
┌──────────────▼──────────────────┐
│   Platform Abstraction Layer    │
│   • ProxmoxClient               │
│   • AWSClient                   │
│   • AzureClient                 │
│   • ESXiClient                  │
└─────────────────────────────────┘
```

### Design Patterns

1. **Agent-Based Architecture** - Autonomous components for specific tasks
2. **Platform Abstraction** - Unified interface across platforms
3. **Template-First** - Pre-built templates for fast deployment
4. **Configuration via Pydantic** - Type-safe settings management

---

## 📁 Directory Structure

```
glassdome/
├── glassdome/              # Main Python package
│   ├── agents/             # Autonomous agents
│   ├── platforms/          # Platform clients
│   ├── core/               # Configuration, SSH, utilities
│   ├── api/                # REST API routes
│   ├── models/             # Data models
│   ├── orchestration/      # Multi-VM coordination
│   └── integrations/       # External integrations
│
├── frontend/               # React web application
├── scripts/                # Utility scripts
├── docs/                   # Documentation (source of truth)
├── tests/                  # Test suite
├── configs/                # Configuration templates
└── examples/               # Usage examples
```

**See [STRUCTURE.md](STRUCTURE.md) for complete details.**

---

## 🔧 Technology Stack

### Backend
- **Python 3.11+** - Core language
- **FastAPI** - Async API framework
- **SQLAlchemy** - ORM
- **Pydantic** - Settings and validation
- **Paramiko** - SSH operations
- **Proxmoxer** - Proxmox API
- **Boto3** - AWS SDK
- **Azure SDK** - Azure management

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **React Flow** - Network topology (planned)

### Infrastructure
- **PostgreSQL** - Database (planned)
- **Redis** - Task queue (planned)
- **Celery** - Async tasks (planned)

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/ntounix-prog/glassdome.git
cd glassdome
pip install -e ".[dev]"
```

### Configuration

```bash
cp env.example .env
# Edit .env with your credentials
```

### Run

```bash
# Backend
glassdome serve

# Frontend
cd frontend && npm run dev
```

**See [QUICKSTART.md](QUICKSTART.md) for detailed setup.**

---

## 📚 Documentation

### Essential Reading

1. **[DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)** - Start here
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
3. **[STRUCTURE.md](STRUCTURE.md)** - Project organization
4. **[TECHNICAL_ASSESSMENT.md](TECHNICAL_ASSESSMENT.md)** - Technical status

### Platform Guides

- **[PLATFORM_SETUP.md](PLATFORM_SETUP.md)** - Platform configuration
- **[WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md)** - Windows deployment
- **[MAILCOW_INTEGRATION.md](MAILCOW_INTEGRATION.md)** - Email integration

### Development

- **[API.md](API.md)** - REST API documentation
- **[AGENTS.md](AGENTS.md)** - Agent framework
- **[PACKAGE_GUIDE.md](PACKAGE_GUIDE.md)** - Python package usage

**Complete index:** [docs/README.md](README.md)

---

## 🎓 Key Concepts

### Agents

Autonomous components that handle specific tasks:
- **UbuntuInstallerAgent** - Deploys Ubuntu VMs
- **WindowsInstallerAgent** - Deploys Windows VMs
- **MailcowAgent** - Manages email operations
- **OverseerAgent** - Monitors infrastructure

### Platform Clients

Abstract interface to hypervisors/cloud:
- **ProxmoxClient** - Proxmox VE API
- **AWSClient** - AWS EC2
- **AzureClient** - Azure VMs
- **ESXiClient** - VMware ESXi

### Templates

Pre-built VM images for fast deployment:
- **Ubuntu 22.04** - Template ID 9000
- **Windows Server 2022** - Template ID 9100
- **Windows 11** - Template ID 9101

---

## 🔍 Code Quality

### Standards

- **Formatting:** Black (line length 100)
- **Type hints:** Required for all functions
- **Docstrings:** Google style
- **Testing:** Pytest with coverage

### Current Coverage

- **Unit tests:** Partial
- **Integration tests:** Partial
- **E2E tests:** Minimal

---

## 🐛 Known Issues

See [ISSUES_TO_CREATE.md](ISSUES_TO_CREATE.md) for complete list.

### High Priority

- Multi-VM orchestration not implemented
- React frontend is skeleton only
- Network orchestration (VLANs) not implemented
- Scenario YAML parser not implemented

### Medium Priority

- Windows deployment on ESXi needs testing
- Guest agent installation needs automation
- Template creation needs full automation

---

## 🎯 Development Priorities

### Phase 1: Core Functionality (Current)

- ✅ Multi-platform deployment
- ✅ Agent framework
- ✅ Template-based deployment
- 🚧 Multi-VM orchestration
- 🚧 Network orchestration

### Phase 2: Frontend & UX

- 🚧 React dashboard
- 🚧 Visual lab designer
- 📋 Real-time monitoring
- 📋 Scenario library

### Phase 3: AI & Automation

- 📋 Research Agent
- 📋 Reaper Agent
- 📋 Autonomous troubleshooting
- 📋 Self-healing deployments

---

## 🤝 Contributing

### Development Workflow

1. Create feature branch
2. Write tests first
3. Implement feature
4. Submit pull request

### Code Standards

- Follow existing patterns
- Add type hints
- Write docstrings
- Update documentation

**See [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md) for details.**

---

## 📞 Support

### Resources

- **Documentation:** `docs/` directory
- **Examples:** `examples/` directory
- **Session Logs:** `docs/session_logs/` for development history

### Common Issues

**"Template not found"**
- Ensure template ID is set in `.env`
- Verify template exists on platform

**"Authentication failed"**
- Check credentials in `.env`
- Verify API tokens are valid

---

## 📈 Project Metrics

- **Lines of Code:** ~15,000+ (estimated)
- **Python Files:** ~100+
- **Test Coverage:** ~30% (estimated)
- **Documentation:** Comprehensive
- **Platforms Supported:** 4 (Proxmox, ESXi, AWS, Azure)
- **OS Support:** Ubuntu 22.04, Windows Server 2022, Windows 11

---

## 🎉 Achievements

- ✅ Multi-platform deployment working
- ✅ Clean platform abstraction
- ✅ Template-based deployment
- ✅ Windows deployment automation
- ✅ Comprehensive documentation
- ✅ Professional code structure

---

## 🚀 Next Steps for Team

1. **Review documentation** - Start with [DEVELOPER_ONBOARDING.md](DEVELOPER_ONBOARDING.md)
2. **Set up environment** - Follow [QUICKSTART.md](QUICKSTART.md)
3. **Study architecture** - Read [ARCHITECTURE.md](ARCHITECTURE.md)
4. **Explore codebase** - Start with agents and platforms
5. **Pick a task** - See [ISSUES_TO_CREATE.md](ISSUES_TO_CREATE.md)

---

*Last Updated: November 22, 2024*  
*Prepared for development team handoff*

