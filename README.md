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
git clone https://github.com/ntounix-prog/glassdome.git
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

```
glassdome/                     # Main Python package (renamed from backend)
├── __init__.py               # Package exports - import from anywhere!
├── cli.py                    # Command-line interface
├── server.py                 # Server entry point
├── main.py                   # FastAPI application
├── agents/                   # Autonomous agent framework
│   ├── base.py              # Base agent classes
│   └── manager.py           # Agent coordination
├── orchestration/           # Deployment orchestration
│   └── engine.py           # Orchestration engine
├── platforms/              # Platform integrations
│   ├── proxmox_client.py  # Proxmox API
│   ├── azure_client.py    # Azure API  
│   └── aws_client.py      # AWS API
├── models/                 # Database models
│   ├── lab.py             # Lab configurations
│   ├── deployment.py      # Deployment tracking
│   └── platform.py        # Platform configs
└── core/                  # Core configuration
    ├── config.py          # Settings
    └── database.py        # Database setup

frontend/                   # React application
├── src/
│   ├── pages/
│   │   ├── Dashboard.jsx   # Main dashboard
│   │   ├── LabCanvas.jsx   # Drag-and-drop designer
│   │   └── Deployments.jsx # Monitoring
│   └── styles/            # Component styles

pyproject.toml             # Package configuration
setup.py                   # Setup script
INSTALL.md                # Installation guide
```

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

**All documentation is in the [`docs/`](docs/) directory:**

### 🚀 Getting Started
- **[QUICKSTART.md](docs/QUICKSTART.md)** - 5-minute quick start
- **[GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Complete setup walkthrough
- **[INSTALL.md](docs/INSTALL.md)** - Package installation guide

### 📖 Guides
- **[SETUP.md](docs/SETUP.md)** - Detailed setup instructions
- **[PACKAGE_GUIDE.md](docs/PACKAGE_GUIDE.md)** - How to use as a Python package
- **[AGENT_QUICKSTART.md](docs/AGENT_QUICKSTART.md)** - Ubuntu Agent quick start

### 🏗️ Architecture
- **[COMPLETE_ARCHITECTURE.md](docs/COMPLETE_ARCHITECTURE.md)** - Full system architecture
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design overview
- **[AGENT_ARCHITECTURE.md](docs/AGENT_ARCHITECTURE.md)** - Agent design patterns

### 🤖 Agents
- **[RESEARCH_AGENT.md](docs/RESEARCH_AGENT.md)** - AI-powered CVE research
- **[REAPER_AGENT.md](docs/REAPER_AGENT.md)** - Vulnerability injection
- **[UBUNTU_AGENT.md](docs/UBUNTU_AGENT.md)** - Ubuntu VM deployment
- **[SSH_AGENT_CAPABILITIES.md](docs/SSH_AGENT_CAPABILITIES.md)** - SSH automation

### 🔧 Configuration
- **[API_KEYS.md](docs/API_KEYS.md)** - API keys and LLM configuration
- **[GET_CREDENTIALS.md](docs/GET_CREDENTIALS.md)** - How to get Proxmox credentials
- **[PROXMOX_SETUP.md](docs/PROXMOX_SETUP.md)** - Proxmox template setup

### 📊 Project Info
- **[PROJECT_VISION.md](docs/PROJECT_VISION.md)** - Vision and roadmap
- **[PROJECT_STATUS.md](docs/PROJECT_STATUS.md)** - Current status
- **[PROJECT_SUMMARY.md](docs/PROJECT_SUMMARY.md)** - Project overview
- **[VP_PRESENTATION_ROADMAP.md](docs/VP_PRESENTATION_ROADMAP.md)** - Roadmap to demo

### 🔬 Development
- **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** - Build details
- **[RESTRUCTURE_SUMMARY.md](docs/RESTRUCTURE_SUMMARY.md)** - Package restructuring
- **[PROGRESS_JOURNAL.md](docs/PROGRESS_JOURNAL.md)** - Development journal
- **[SESSION_SUMMARY.md](docs/SESSION_SUMMARY.md)** - Latest session notes

### 📋 Additional
- **[API.md](docs/API.md)** - API documentation
- **[ORCHESTRATOR_GUIDE.md](docs/ORCHESTRATOR_GUIDE.md)** - Lab orchestration
- **[REQUEST_FLOW.md](docs/REQUEST_FLOW.md)** - Request flow diagrams
- **[FEATURES_TODO.md](docs/FEATURES_TODO.md)** - Planned features
- **[GIT_SETUP.md](docs/GIT_SETUP.md)** - Git configuration

**📁 All docs live in `/docs/` - that's the source of truth!**

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

- **Repository:** https://github.com/ntounix-prog/glassdome
- **Issues:** https://github.com/ntounix-prog/glassdome/issues
- **Documentation:** https://github.com/ntounix-prog/glassdome/docs

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
