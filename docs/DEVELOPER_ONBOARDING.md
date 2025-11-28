# Developer Onboarding Guide

**Welcome to Glassdome!** This guide will help you get up to speed quickly.

---

## 🎯 What is Glassdome?

Glassdome is an **autonomous, AI-powered deployment system** for cybersecurity lab environments. It uses intelligent agents to deploy complex cyber range scenarios to Proxmox, Azure, AWS, or ESXi in minutes.

**Key Differentiator:** Not just VM deployment - it's a complete cyber range platform with:
- AI-powered vulnerability research (Research Agent)
- Automated vulnerability injection (Reaper Agent)
- Multi-platform orchestration
- Visual drag-and-drop lab designer

---

## 🚀 Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/ntounix/glassdome.git
cd glassdome

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install package
pip install -e ".[dev]"
```

### 2. Configure Environment

```bash
# Copy environment template
cp env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required Configuration:**
- At least one platform (Proxmox, AWS, Azure, or ESXi)
- API keys for cloud providers
- SSH credentials for hypervisors

### 3. Verify Installation

```bash
# Check system status
glassdome status

# Test platform connection
glassdome test-platform --platform proxmox
```

---

## 📁 Project Structure

```
glassdome/
├── glassdome/          # Main Python package
│   ├── agents/         # Autonomous agents
│   ├── platforms/      # Platform clients (Proxmox, AWS, Azure, ESXi)
│   ├── core/           # Configuration, SSH, utilities
│   ├── api/            # REST API routes
│   └── ...
├── frontend/           # React web application
├── scripts/            # Utility scripts
├── docs/               # Documentation (source of truth)
└── tests/              # Test suite
```

**See [STRUCTURE.md](STRUCTURE.md) for complete details.**

---

## 🏗️ Architecture Overview

### Core Concepts

1. **Agents** - Autonomous components that handle specific tasks
   - `UbuntuInstallerAgent` - Deploys Ubuntu VMs
   - `WindowsInstallerAgent` - Deploys Windows VMs
   - `MailcowAgent` - Manages email operations
   - `OverseerAgent` - Monitors infrastructure

2. **Platform Clients** - Abstract interface to hypervisors/cloud
   - `ProxmoxClient` - Proxmox VE API
   - `AWSClient` - AWS EC2
   - `AzureClient` - Azure VMs
   - `ESXiClient` - VMware ESXi

3. **Orchestration** - Multi-VM coordination
   - Dependency management
   - Parallel execution
   - State tracking

### Request Flow

```
User/API Request
    ↓
Agent (OS-specific logic)
    ↓
PlatformClient (infrastructure API)
    ↓
Hypervisor/Cloud Provider
```

**See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture.**

---

## 💻 Development Workflow

### Running the Application

```bash
# Start backend API server
glassdome serve
# or
uvicorn glassdome.main:app --reload --port 8001

# Start frontend (in separate terminal)
cd frontend
npm install
npm run dev  # Runs on port 5174
```

### Code Organization

**Adding a New Agent:**
1. Create `glassdome/agents/your_agent.py`
2. Inherit from `BaseAgent` or `DeploymentAgent`
3. Implement required methods
4. Add API routes in `glassdome/api/`
5. Write tests in `tests/unit/agents/`

**Adding a New Platform:**
1. Create `glassdome/platforms/your_platform_client.py`
2. Implement `PlatformClient` interface
3. Add configuration to `env.example`
4. Write tests in `tests/integration/`

### Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/unit/agents/test_ubuntu_agent.py

# With coverage
pytest --cov=glassdome --cov-report=html
```

### Code Quality

```bash
# Format code
black glassdome/

# Type checking
mypy glassdome/

# Linting
flake8 glassdome/
```

---

## 📚 Essential Documentation

### Must-Read for New Developers

1. **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
2. **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design
3. **[STRUCTURE.md](STRUCTURE.md)** - Project organization
4. **[PACKAGE_GUIDE.md](PACKAGE_GUIDE.md)** - Using as Python package

### Platform-Specific

- **[PLATFORM_SETUP.md](PLATFORM_SETUP.md)** - Platform configuration
- **[WINDOWS_DEPLOYMENT.md](WINDOWS_DEPLOYMENT.md)** - Windows deployment
- **[MAILCOW_INTEGRATION.md](MAILCOW_INTEGRATION.md)** - Email integration

### Development

- **[API.md](API.md)** - REST API documentation
- **[AGENTS.md](AGENTS.md)** - Agent framework
- **[REQUEST_FLOW.md](REQUEST_FLOW.md)** - Request flow diagrams

---

## 🔧 Common Tasks

### Deploy a Ubuntu VM

```python
from glassdome.agents import UbuntuInstallerAgent
from glassdome.platforms import ProxmoxClient

proxmox = ProxmoxClient(...)
agent = UbuntuInstallerAgent(platform_client=proxmox)

config = {
    "name": "test-vm",
    "template_id": 9000,  # Ubuntu 22.04 template
    "memory_mb": 2048,
    "cpu_cores": 2,
    "disk_size_gb": 20,
    "static_ip": "192.168.3.100"
}

result = await agent.execute(config)
```

### Deploy a Windows VM

```python
from glassdome.agents import WindowsInstallerAgent

agent = WindowsInstallerAgent(platform_client=proxmox)

config = {
    "name": "windows-server",
    "windows_version": "server2022",
    "template_id": 9100,
    "memory_mb": 16384,  # 16GB
    "cpu_cores": 8,      # 8 vCPU
    "disk_size_gb": 80   # 80GB
}

result = await agent.execute(config)
```

### Use Platform Client Directly

```python
from glassdome.platforms import ProxmoxClient

client = ProxmoxClient(
    host="192.168.3.2",
    user="root@pam",
    password="your-password"
)

# Create VM
result = await client.create_vm({
    "name": "my-vm",
    "template_id": 9000,
    "memory_mb": 2048,
    "cpu_cores": 2
})
```

---

## 🐛 Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Platform Connection

```bash
# Test Proxmox
glassdome test-platform --platform proxmox

# Test AWS
glassdome test-platform --platform aws
```

### View Logs

```bash
# Backend logs
tail -f logs/glassdome.log

# Agent logs
tail -f logs/agents.log
```

---

## 📝 Code Standards

### Python Style

- **Format:** Black (line length 100)
- **Type hints:** Required for all functions
- **Docstrings:** Google style
- **Naming:** snake_case for functions/variables, PascalCase for classes

### Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit
3. Push and create pull request
4. Code review and merge

**See [GIT_SETUP.md](GIT_SETUP.md) for Git configuration.**

---

## 🎓 Learning Path

### Week 1: Basics
- [ ] Read [QUICKSTART.md](QUICKSTART.md)
- [ ] Set up development environment
- [ ] Deploy a test VM
- [ ] Read [ARCHITECTURE.md](ARCHITECTURE.md)

### Week 2: Deep Dive
- [ ] Study agent framework ([AGENTS.md](AGENTS.md))
- [ ] Understand platform abstraction
- [ ] Review platform clients code
- [ ] Read [STRUCTURE.md](STRUCTURE.md)

### Week 3: Contribution
- [ ] Pick a small issue/feature
- [ ] Write tests first
- [ ] Implement feature
- [ ] Submit pull request

---

## 🤝 Getting Help

### Resources

- **Documentation:** All docs in `docs/` directory
- **Code Examples:** See `examples/` directory
- **Session Logs:** See `docs/session_logs/` for development history

### Common Issues

**"Template not found"**
- Ensure template ID is set in `.env`
- Verify template exists on platform

**"Authentication failed"**
- Check credentials in `.env`
- Verify API tokens are valid

**"VM creation failed"**
- Check platform logs
- Verify resource availability
- Check network configuration

---

## 🎯 Project Goals

Glassdome aims to be:

1. **Autonomous** - AI-powered agents handle complex tasks
2. **Platform-Agnostic** - Works across Proxmox, AWS, Azure, ESXi
3. **Air-Gappable** - Can run in isolated environments
4. **Enterprise-Ready** - Scalable, secure, maintainable

**See [PROJECT_STATUS.md](PROJECT_STATUS.md) for current status.**

---

## 📞 Next Steps

1. **Set up your environment** (see Quick Start above)
2. **Read core documentation** (Architecture, Structure)
3. **Deploy a test VM** to verify setup
4. **Explore the codebase** starting with agents and platforms
5. **Pick a task** from [ISSUES_TO_CREATE.md](ISSUES_TO_CREATE.md)

---

**Welcome to the team! 🚀**

*Last Updated: November 22, 2024*

