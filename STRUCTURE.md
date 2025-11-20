# Glassdome Project Structure

**Complete directory layout and organization.**

---

## Overview

Glassdome is organized into clear, logical categories to support development, deployment, and maintenance of an autonomous vulnerability research and emulation platform.

---

## Directory Tree

```
glassdome/
├── glassdome/              # Main Python package (core application code)
│   ├── agents/             # Autonomous agents
│   ├── ai/                 # AI/LLM integration (Research Agent)
│   ├── api/                # REST API routes
│   ├── core/               # Core utilities and configuration
│   ├── models/             # Data models
│   ├── orchestration/      # Multi-VM orchestration
│   ├── platforms/          # Cloud/hypervisor clients
│   ├── research/           # CVE research components
│   ├── services/           # Business logic services
│   ├── templates/          # Template engines
│   └── vulnerabilities/    # Vulnerability injection library
│
├── frontend/               # React web application
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Page components
│   │   ├── styles/         # CSS stylesheets
│   │   └── utils/          # Frontend utilities
│   └── public/             # Static assets
│
├── scripts/                # Utility scripts (organized by purpose)
│   ├── setup/              # Setup and configuration
│   ├── testing/            # Testing and validation
│   ├── deployment/         # Deployment automation
│   └── tools/              # General utilities
│
├── examples/               # Usage examples and demos
│   ├── simple/             # Simple examples
│   ├── advanced/           # Advanced use cases
│   └── tutorials/          # Step-by-step tutorials
│
├── tests/                  # Automated test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   ├── e2e/                # End-to-end tests
│   └── fixtures/           # Test fixtures
│
├── docs/                   # Documentation (SOURCE OF TRUTH)
│   ├── README.md           # Documentation index
│   ├── architecture/       # Architecture docs
│   ├── guides/             # User guides
│   ├── api/                # API documentation
│   └── development/        # Developer docs
│
├── configs/                # Configuration templates
│   ├── templates/          # Lab templates
│   ├── scenarios/          # Training scenarios
│   └── platforms/          # Platform configs
│
├── agent_context/          # AI assistant context
│   ├── JOURNAL_*.md        # Daily development journals
│   └── README.md           # Context explanation
│
├── .github/                # GitHub-specific files
│   └── workflows/          # CI/CD workflows
│
├── README.md               # Main project README
├── STRUCTURE.md            # This file
├── pyproject.toml          # Package configuration
├── setup.py                # Setup script
├── requirements.txt        # Python dependencies
├── Makefile                # Common commands
├── docker-compose.yml      # Docker orchestration
├── Dockerfile              # Docker image
├── env.example             # Environment variable template
└── .gitignore              # Git ignore patterns
```

---

## Package Structure (`glassdome/`)

The main Python package - all core application code.

### `/agents/` - Autonomous Agents

Agent framework and implementations:

```
agents/
├── __init__.py
├── base.py                 # Base agent classes
├── manager.py              # Agent coordination
├── ubuntu_installer.py     # Ubuntu VM agent
├── overseer.py             # Monitoring agent
├── reaper.py               # Vulnerability injection agent (Future)
├── research.py             # CVE research agent (Future)
├── os_installer_base.py    # Base OS installer
└── os_installer_factory.py # OS installer factory
```

### `/ai/` - AI/LLM Integration

LLM clients for autonomous research:

```
ai/
├── __init__.py
├── llm_client.py           # Unified LLM interface
├── prompts.py              # Prompt templates
└── structured_output.py    # Pydantic schemas for LLM responses
```

**Used by:** Research Agent for CVE analysis

### `/api/` - REST API Routes

FastAPI route handlers:

```
api/
├── __init__.py
├── ubuntu.py               # Ubuntu Agent endpoints
├── overseer.py             # Overseer Agent endpoints
├── labs.py                 # Lab management
├── research.py             # Research Agent endpoints (Future)
└── reaper.py               # Reaper Agent endpoints (Future)
```

### `/core/` - Core Utilities

Shared utilities and configuration:

```
core/
├── __init__.py
├── config.py               # Settings management
├── database.py             # Database connection
├── ssh_client.py           # SSH automation
└── logging.py              # Logging configuration (Future)
```

### `/models/` - Data Models

Pydantic models for API and database:

```
models/
├── __init__.py
├── lab.py                  # Lab configurations
├── deployment.py           # Deployment tracking
├── platform.py             # Platform connections
└── vulnerability.py        # Vulnerability data (Future)
```

### `/orchestration/` - Orchestration

Multi-VM deployment coordination:

```
orchestration/
├── __init__.py
├── engine.py               # Task orchestration engine
└── lab_orchestrator.py     # Lab deployment orchestrator
```

### `/platforms/` - Platform Clients

Cloud and hypervisor API clients:

```
platforms/
├── __init__.py
├── proxmox_client.py       # Proxmox VE API
├── proxmox_gateway.py      # Proxmox SSH operations
├── azure_client.py         # Azure SDK
└── aws_client.py           # AWS SDK
```

### `/research/` - CVE Research

Autonomous vulnerability research components:

```
research/
├── __init__.py
├── cve_analyzer.py         # CVE data analysis
├── exploit_finder.py       # PoC exploit search
├── procedure_generator.py  # Deployment procedure generation
└── schemas.py              # Research data models
```

**Used by:** Research Agent

### `/vulnerabilities/` - Vulnerability Library

Injectable vulnerability modules:

```
vulnerabilities/
├── __init__.py
├── base.py                 # Base vulnerability class
├── library.py              # Vulnerability registry
├── web/                    # Web vulnerabilities
│   ├── sql_injection.py
│   ├── xss.py
│   └── command_injection.py
├── network/                # Network misconfigurations
│   ├── smb_anonymous.py
│   └── weak_ssh.py
└── system/                 # System misconfigurations
    ├── weak_sudo.py
    └── suid_exploit.py
```

**Used by:** Reaper Agent

---

## Scripts (`scripts/`)

All utility scripts, organized by function.

### `/setup/` - Setup Scripts

One-time setup and configuration:
- `setup.sh` - Create virtual environment
- `setup_proxmox.py` - Configure Proxmox connection

### `/testing/` - Testing Scripts

Component testing and validation:
- `test_vm_creation.py` - Test VM deployment
- `monitor_infrastructure.py` - Test monitoring

### `/deployment/` - Deployment Scripts

Automation for deployment tasks:
- `create_template_auto.py` - Create Proxmox templates

### `/tools/` - Utility Tools

General-purpose utilities (future).

---

## Frontend (`frontend/`)

React web application:

```
frontend/
├── src/
│   ├── main.jsx            # App entry point
│   ├── App.jsx             # Main component
│   ├── components/         # Reusable components
│   │   ├── QuickDeploy.jsx
│   │   └── LabTemplates.jsx
│   ├── pages/              # Page components
│   │   ├── Dashboard.jsx
│   │   ├── LabCanvas.jsx
│   │   └── Deployments.jsx
│   ├── styles/             # Component styles
│   └── utils/              # Frontend utilities
├── public/                 # Static assets
├── index.html              # HTML template
├── package.json            # NPM dependencies
└── vite.config.js          # Vite configuration
```

---

## Tests (`tests/`)

Automated test suite:

```
tests/
├── unit/                   # Fast, isolated tests
│   ├── agents/
│   ├── platforms/
│   └── research/
├── integration/            # Component integration tests
│   ├── proxmox/
│   └── orchestration/
├── e2e/                    # End-to-end tests
│   └── deployment/
├── fixtures/               # Test data and mocks
└── conftest.py             # Pytest configuration
```

---

## Documentation (`docs/`)

**All documentation lives here** (source of truth):

```
docs/
├── README.md               # Documentation index
├── QUICKSTART.md
├── GETTING_STARTED.md
├── INSTALL.md
├── COMPLETE_ARCHITECTURE.md
├── RESEARCH_AGENT.md
├── REAPER_AGENT.md
├── API_KEYS.md
└── [30+ other docs]
```

---

## Configuration (`configs/`)

Templates and examples:

```
configs/
├── templates/              # Lab templates (YAML)
│   ├── web_security.yaml
│   └── network_defense.yaml
├── scenarios/              # Training scenarios
└── platforms/              # Platform-specific configs
```

---

## Examples (`examples/`)

Usage examples:

```
examples/
├── create_ubuntu_vm.py         # Simple VM creation
├── complex_lab_deployment.py   # Multi-VM lab
└── (future examples)
```

---

## Root Directory Files

Only essential files in root:

### Configuration Files
- `pyproject.toml` - Modern Python package config
- `setup.py` - Traditional setup script
- `requirements.txt` - Python dependencies
- `env.example` - Environment variable template
- `.gitignore` - Git ignore patterns

### Build/Deploy Files
- `Makefile` - Common commands
- `Dockerfile` - Docker image
- `docker-compose.yml` - Multi-container setup

### Documentation (Root)
- `README.md` - Main project README
- `STRUCTURE.md` - This file
- `QUICKSTART.md` → symlink to `docs/QUICKSTART.md`
- `GETTING_STARTED.md` → symlink to `docs/GETTING_STARTED.md`
- `INSTALL.md` → symlink to `docs/INSTALL.md`

### Utilities (Root)
- `activate.sh` - Quick venv activation

---

## Design Principles

### 1. Separation of Concerns
- **Code:** `/glassdome/` - core application
- **Scripts:** `/scripts/` - utilities
- **Tests:** `/tests/` - validation
- **Docs:** `/docs/` - documentation
- **Config:** `/configs/` - templates

### 2. Scalability
- Modular package structure
- Clear subdirectories by function
- Easy to add new components

### 3. Clarity
- Each directory has a clear purpose
- README in each major directory
- Logical grouping of related files

### 4. Maintainability
- Documentation lives in `/docs/`
- Scripts organized by purpose
- Tests mirror code structure

### 5. Professional
- Clean root directory
- Standard Python package layout
- Follows community best practices

---

## Navigation Guide

### "I want to..."

**...understand the system:**
→ `docs/COMPLETE_ARCHITECTURE.md`

**...add a new agent:**
→ `glassdome/agents/[your_agent].py`

**...add AI capabilities:**
→ `glassdome/ai/[component].py`

**...add a vulnerability module:**
→ `glassdome/vulnerabilities/[category]/[vuln].py`

**...add an API endpoint:**
→ `glassdome/api/[route].py`

**...write a setup script:**
→ `scripts/setup/[script].py`

**...write tests:**
→ `tests/[category]/test_[module].py`

**...create a lab template:**
→ `configs/templates/[template].yaml`

**...add documentation:**
→ `docs/[doc].md`

---

## Adding New Components

### New Agent
1. Create `glassdome/agents/[agent_name].py`
2. Inherit from `DeploymentAgent` base class
3. Create API routes in `glassdome/api/[agent_name].py`
4. Add tests in `tests/unit/agents/test_[agent_name].py`
5. Document in `docs/[AGENT_NAME]_AGENT.md`

### New Platform
1. Create `glassdome/platforms/[platform]_client.py`
2. Implement platform API interface
3. Add configuration in `env.example`
4. Add tests in `tests/integration/[platform]/`
5. Document in `docs/[PLATFORM]_SETUP.md`

### New Vulnerability
1. Create `glassdome/vulnerabilities/[category]/[vuln].py`
2. Inherit from `VulnerabilityBase`
3. Implement injection and validation methods
4. Add to vulnerability library registry
5. Document exploit steps and remediation

---

## File Naming Conventions

- **Python modules:** `snake_case.py`
- **Classes:** `PascalCase`
- **Functions/variables:** `snake_case`
- **Constants:** `UPPER_SNAKE_CASE`
- **Scripts:** `snake_case.py` or `kebab-case.sh`
- **Docs:** `UPPER_SNAKE_CASE.md` (for major docs) or `lowercase.md`
- **Config templates:** `lowercase_descriptive.yaml`

---

## Import Patterns

```python
# From anywhere, import from glassdome package
from glassdome.agents import UbuntuInstallerAgent
from glassdome.platforms import ProxmoxClient
from glassdome.orchestration import LabOrchestrator
from glassdome.ai import LLMClient
from glassdome.vulnerabilities import SQLInjectionBasic
```

---

## Summary

**Organized for:**
- ✅ **Clarity** - Each directory has a clear purpose
- ✅ **Scalability** - Easy to add new components
- ✅ **Maintainability** - Logical organization
- ✅ **Professionalism** - Clean, standard structure
- ✅ **Collaboration** - Easy for teams to navigate

**Next:** Build components within this structure!

---

*Last Updated: November 20, 2024*  
*Structure Version: 2.0*  
*This is a living document - update as structure evolves*

