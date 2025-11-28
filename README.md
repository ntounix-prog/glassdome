# Glassdome 🔮

**Agentic Cyber Range Deployment Framework**

Glassdome is an autonomous, AI-powered deployment system for cybersecurity lab environments. Using intelligent agents and a visual drag-and-drop interface, deploy complex cyber range scenarios to Proxmox, Azure, or AWS in minutes.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Key Features

- **🤖 Autonomous Agents** - AI-powered agents handle complex deployments automatically
- **🎨 Drag & Drop Designer** - Visual canvas for designing cyber range labs
- **☁️ Multi-Platform** - Deploy to Proxmox, Azure, or AWS seamlessly
- **🔄 Smart Orchestration** - Dependency management and parallel execution
- **📊 Real-time Monitoring** - Track deployment progress and resource health
- **📚 Template Library** - Reusable lab configurations for common scenarios
- **📦 Python Package** - Install anywhere, use everywhere

## 🚀 Quick Start

### Installation as a Package

```bash
# Clone the repository
git clone https://github.com/ntounix/glassdome.git
cd glassdome

# Install as a Python package (editable mode)
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Start the Server

```bash
# Using CLI command (port 8001 to avoid conflicts)
glassdome serve

# Or with custom port
glassdome serve --port 9000 --host 0.0.0.0

# Or traditional way
cd glassdome
uvicorn main:app --reload --port 8001
```

### Start the Frontend

```bash
cd frontend
npm install
npm run dev  # Runs on port 5174
```

### Access Your Application

- 🌐 **Frontend:** http://localhost:5174
- ⚡ **Backend API:** http://localhost:8001
- 📖 **API Docs:** http://localhost:8001/docs

### Docker (Alternative)

```bash
docker-compose up --build
```

## 📦 Use as a Python Package

After installation, use Glassdome from anywhere:

```python
# Import from anywhere on your system
from glassdome import ProxmoxClient, AzureClient, AWSClient
from glassdome import agent_manager, OrchestrationEngine
from glassdome.models import Lab, Deployment

# Use in your own projects
client = ProxmoxClient(host="...", user="...", password="...")

# Create orchestration
engine = OrchestrationEngine()
engine.add_task("vm1", {"type": "create_vm", "config": {...}})

# Deploy programmatically
result = await engine.run(executor_func=deploy_task)
```

## 🛠️ CLI Commands

```bash
# System management
glassdome init              # Initialize Glassdome
glassdome status            # Check system status
glassdome serve             # Start API server

# Platform testing
glassdome test-platform --platform proxmox

# Agent management
glassdome agent list        # List all agents
glassdome agent start       # Start agent manager

# Lab management
glassdome lab list          # List all labs
glassdome lab create --name "My Lab"

# Deployment management
glassdome deploy list       # List deployments
glassdome deploy create --lab-id lab_123 --platform proxmox
glassdome deploy destroy deployment_id
```

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│     React Frontend (5174)           │
│  • Dashboard  • Lab Designer        │
└──────────────┬──────────────────────┘
               │ REST API
┌──────────────▼──────────────────────┐
│   FastAPI Backend (8001)            │
│  • Lab Management  • Agents         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Agentic Orchestration Layer       │
│  • Agent Manager  • Orchestration   │
└───┬──────────────────────┬──────────┘
    │                      │
┌───▼────┐  ┌────────┐  ┌─▼──────┐
│Proxmox │  │ Azure  │  │  AWS   │
└────────┘  └────────┘  └────────┘
```

## 🎨 Project Structure

**See [STRUCTURE.md](STRUCTURE.md) for complete directory layout.**

### Quick Overview

```
glassdome/
├── glassdome/              # Main Python package
│   ├── agents/             # Autonomous agents
│   ├── ai/                 # AI/LLM integration (Research Agent)
│   ├── api/                # REST API routes
│   ├── core/               # Core utilities
│   ├── models/             # Data models
│   ├── orchestration/      # Multi-VM coordination
│   ├── platforms/          # Cloud/hypervisor clients
│   ├── research/           # CVE research components
│   └── vulnerabilities/    # Vulnerability injection library
│
├── frontend/               # React web application
├── scripts/                # Organized utility scripts
│   ├── setup/              # Setup scripts
│   ├── testing/            # Test scripts
│   └── deployment/         # Deployment automation
├── examples/               # Usage examples
├── tests/                  # Automated test suite
├── docs/                   # Documentation (source of truth)
└── configs/                # Lab templates and scenarios
```

**For detailed structure:** See [STRUCTURE.md](STRUCTURE.md)

## 🛠️ Tech Stack

### Backend (Python Package)
- **Python 3.11+** - Core language
- **FastAPI** - Async API framework
- **SQLAlchemy** - ORM
- **Celery + Redis** - Task queue
- **LangChain** - AI agent framework
- **Click** - CLI framework

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **React Flow** - Drag-and-drop canvas
- **Zustand** - State management

### Platform Integrations
- **Proxmoxer** - Proxmox VE API
- **Boto3** - AWS SDK
- **Azure SDK** - Azure management

## ⚙️ Configuration

Create `.env` from `env.example`:

```bash
cp env.example .env
```

Configure your platforms:

```env
# Ports (changed to avoid conflicts with other projects)
BACKEND_PORT=8001
VITE_PORT=5174

# Proxmox
PROXMOX_HOST=your-proxmox-host
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your-password

# Azure
AZURE_SUBSCRIPTION_ID=...
AZURE_TENANT_ID=...

# AWS
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

## 📚 Documentation

**📖 [Complete Documentation Index](docs/README.md)**

All documentation is organized in the [`docs/`](docs/) directory. See the [documentation index](docs/README.md) for a complete guide.

### Quick Links

- **[Developer Onboarding](docs/DEVELOPER_ONBOARDING.md)** - Start here if you're new
- **[Quick Start](docs/QUICKSTART.md)** - Get running in 5 minutes
- **[Architecture](docs/ARCHITECTURE.md)** - System design overview
- **[Platform Setup](docs/PLATFORM_SETUP.md)** - Configure Proxmox, AWS, Azure, ESXi
- **[Windows Deployment](docs/WINDOWS_DEPLOYMENT.md)** - Windows VM deployment guide
- **[Mailcow Integration](docs/MAILCOW_INTEGRATION.md)** - Email integration guide

**📁 All documentation lives in `/docs/` - that's the source of truth!**

## 🔧 Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black glassdome/

# Type checking
mypy glassdome/

# Start with auto-reload
glassdome serve --reload
```

## 🎯 Use Cases

- 🎯 **Red Team Labs** - Attack/defense scenarios
- 🔒 **Security Training** - Hands-on learning
- 🐛 **Vulnerability Testing** - Isolated environments
- 🏆 **CTF Events** - Rapid deployment
- 🔬 **Research Labs** - Reproducible research
- 📜 **Certification Prep** - OSCP, CEH, CISSP

## 🔗 Integration with Other Projects

Since Glassdome is now a package with configurable ports, it won't conflict with your other server projects:

```python
# In your other project (running on port 8000)
from glassdome import ProxmoxClient, agent_manager

# Use Glassdome functionality
client = ProxmoxClient(...)
result = await client.create_vm(...)
```

## 📊 Port Configuration

**Default Ports (Changed to Avoid Conflicts):**
- Backend API: **8001** (was 8000)
- Frontend Dev: **5174** (was 5173)

Configure in `.env` or via CLI:
```bash
glassdome serve --port 9000
```

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines.

## 📄 License

MIT License - see LICENSE file

## 🔗 Links

- **Repository:** https://github.com/ntounix/glassdome
- **Issues:** https://github.com/ntounix/glassdome/issues
- **Documentation:** https://github.com/ntounix/glassdome/docs

## 🎉 What's New

### v0.1.0 - Package Structure
- ✅ **Python Package** - Install and import from anywhere
- ✅ **CLI Commands** - `glassdome` command-line interface
- ✅ **Configurable Ports** - Avoid conflicts with other projects (8001, 5174)
- ✅ **No Location Restrictions** - Use Glassdome functions across your codebase
- ✅ **Professional Structure** - `pyproject.toml`, proper package exports

---

**Built with ❤️ for autonomous cybersecurity lab deployment**

**Start your first deployment:**
```bash
pip install -e .
glassdome serve
# Visit http://localhost:5174
```

🚀 **Deploy cyber ranges autonomously!**
