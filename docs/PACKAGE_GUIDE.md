# Glassdome Package Guide

## 🎉 What Changed

Glassdome is now a **proper Python package** with **no location restrictions** and **configurable ports**.

### Key Changes

1. **Directory renamed:** `backend/` → `glassdome/`
2. **Package structure:** Full Python package with `pyproject.toml`
3. **New ports:** Backend 8001 (was 8000), Frontend 5174 (was 5173)
4. **CLI commands:** `glassdome` command available system-wide
5. **Import anywhere:** `from glassdome import ...` works everywhere

---

## 📦 Installation

### Install in Development Mode (Recommended)

```bash
cd /home/nomad/glassdome
pip install -e .
```

This allows you to:
- ✅ Import `glassdome` from anywhere on your system
- ✅ Make changes and see them immediately
- ✅ Use in any Python project
- ✅ Run CLI commands system-wide

### Verify Installation

```bash
# Check package is installed
pip show glassdome

# Check CLI is available
glassdome --version

# Test import
python -c "import glassdome; print(glassdome.__version__)"
```

---

## 🚀 Quick Start

### Option 1: Using CLI (Recommended)

```bash
# Start the server
glassdome serve

# Or with custom port
glassdome serve --port 9000

# With auto-reload for development
glassdome serve --reload
```

### Option 2: Traditional Way

```bash
cd /home/nomad/glassdome
python -m uvicorn glassdome.main:app --reload --port 8001
```

### Start Frontend

```bash
cd /home/nomad/glassdome/frontend
npm install
npm run dev  # Runs on port 5174
```

### Access

- Frontend: http://localhost:5174
- Backend: http://localhost:8001
- API Docs: http://localhost:8001/docs

---

## 📚 Using as a Package

### Import Anywhere

```python
# In ANY Python file, ANYWHERE on your system:
from glassdome import ProxmoxClient, AzureClient, AWSClient
from glassdome import agent_manager, OrchestrationEngine
from glassdome.models import Lab, Deployment, DeploymentStatus

# Use immediately
client = ProxmoxClient(host="...", user="...", password="...")
vms = await client.list_vms("node1")
```

### In Your Own Projects

```python
# In /home/nomad/other_project/my_script.py
from glassdome import ProxmoxClient, agent_manager

def deploy_my_lab():
    # Use Glassdome functionality
    client = ProxmoxClient(...)
    result = client.create_vm(...)
    return result
```

### In Jupyter Notebooks

```python
# In any Jupyter notebook
import glassdome
from glassdome.platforms import ProxmoxClient

# Access all Glassdome features
client = ProxmoxClient(...)
```

---

## 🔧 CLI Commands

### Server Management

```bash
glassdome serve                     # Start API server (port 8001)
glassdome serve --port 9000         # Custom port
glassdome serve --reload            # Auto-reload on changes
```

### System Management

```bash
glassdome init                      # Initialize Glassdome
glassdome status                    # System status
glassdome test-platform --platform proxmox
```

### Agent Management

```bash
glassdome agent list                # List all agents
glassdome agent start               # Start agent manager
```

### Lab Management

```bash
glassdome lab list                  # List all labs
glassdome lab create --name "My Lab"
```

### Deployment Management

```bash
glassdome deploy list               # List deployments
glassdome deploy create --lab-id lab_123 --platform proxmox
glassdome deploy destroy deploy_123
```

---

## 🔌 Port Configuration

### Default Ports (Changed)

| Service | Old Port | New Port | Reason |
|---------|----------|----------|--------|
| Backend | 8000 | **8001** | Avoid conflicts |
| Frontend | 5173 | **5174** | Avoid conflicts |

### Configure Ports

**Via Environment (.env):**
```bash
BACKEND_PORT=8001
VITE_PORT=5174
```

**Via CLI:**
```bash
glassdome serve --port 9000
```

**Via Code:**
```python
from glassdome.core.config import settings
settings.backend_port = 9000
```

---

## 🏗️ Package Structure

```
glassdome/                          # Main package (importable)
├── __init__.py                    # Package exports
├── cli.py                         # CLI commands
├── server.py                      # Server entry point
├── main.py                        # FastAPI app
├── agents/                        # Agent framework
├── orchestration/                 # Orchestration engine
├── platforms/                     # Platform clients
├── models/                        # Database models
└── core/                          # Configuration

pyproject.toml                     # Package config
setup.py                           # Setup script
```

---

## 🎯 Use Cases

### Use Case 1: Standalone Server

```bash
# Just run as a server
glassdome serve
```

### Use Case 2: Import in Other Projects

```python
# Use Glassdome in your existing projects
from glassdome import ProxmoxClient

# Your project continues as normal
# But now has access to all Glassdome functionality
```

### Use Case 3: Custom Scripts

```python
#!/usr/bin/env python3
from glassdome import OrchestrationEngine, agent_manager

# Create custom deployment scripts
engine = OrchestrationEngine()
# ... your custom logic
```

### Use Case 4: Jupyter Analysis

```python
# Analyze deployment data in notebooks
from glassdome.models import Deployment
import pandas as pd

deployments = Deployment.query.all()
df = pd.DataFrame([d.__dict__ for d in deployments])
df.plot()
```

---

## 🔄 Integration with Other Projects

Since Glassdome uses different ports and is a package:

### Scenario: Multiple Projects on Same Server

```
Port 8000 → Your other project (403press, etc.)
Port 8001 → Glassdome API
Port 5174 → Glassdome Frontend
```

### In Your Other Project's Code

```python
# In /home/nomad/403press/my_app.py
from glassdome import ProxmoxClient

# Use Glassdome to deploy test environments
def create_test_env():
    client = ProxmoxClient(...)
    vm = client.create_vm(...)
    return vm
```

---

## 🧪 Development Workflow

### 1. Install in Editable Mode

```bash
cd /home/nomad/glassdome
pip install -e ".[dev]"
```

### 2. Make Changes

Edit any file in `glassdome/`

### 3. Changes Are Immediate

```python
# No reinstall needed!
from glassdome import MyChangedFunction
```

### 4. Run Tests

```bash
pytest
```

---

## 📝 Import Examples

### Basic Import

```python
import glassdome
print(glassdome.__version__)  # 0.1.0
```

### Specific Imports

```python
from glassdome import ProxmoxClient, AzureClient, AWSClient
from glassdome.agents import BaseAgent, DeploymentAgent
from glassdome.orchestration import OrchestrationEngine
from glassdome.models import Lab, Deployment
```

### All Exports

```python
from glassdome import *  # Not recommended, but works

# Gives you:
# - ProxmoxClient, AzureClient, AWSClient
# - agent_manager, OrchestrationEngine
# - BaseAgent, DeploymentAgent, etc.
# - Lab, Deployment, Platform models
# - settings
```

---

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Ports
BACKEND_PORT=8001
VITE_PORT=5174

# Database
DATABASE_URL=postgresql+asyncpg://...

# Proxmox
PROXMOX_HOST=your-host
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=secret

# Azure
AZURE_SUBSCRIPTION_ID=...

# AWS
AWS_ACCESS_KEY_ID=...
```

### In Code

```python
from glassdome.core.config import settings

# Access settings
print(settings.backend_port)      # 8001
print(settings.proxmox_host)       # your-host
print(settings.database_url)       # postgresql://...
```

---

## 🚨 Troubleshooting

### Import Error

```bash
# If you get: ModuleNotFoundError: No module named 'glassdome'
pip install -e /home/nomad/glassdome
```

### Port Already in Use

```bash
# Find process
lsof -i :8001

# Use different port
glassdome serve --port 9000
```

### CLI Not Found

```bash
# Reinstall with entry points
pip install -e .

# Or use directly
python -m glassdome.cli serve
```

---

## 📊 Comparison

### Before (Project)

```
backend/main.py                    # Must run from project dir
cd /home/nomad/glassdome          # Location restricted
python backend/main.py            # Manual execution
```

### After (Package)

```python
from glassdome import ...          # Import from anywhere
glassdome serve                   # CLI command
pip install -e .                  # Standard installation
```

---

## 🎓 Advanced Usage

### Custom Agents

```python
from glassdome.agents.base import DeploymentAgent

class MyCustomAgent(DeploymentAgent):
    async def _deploy_element(self, element_type, config):
        # Your custom logic
        return {"success": True, "resource_id": "..."}

# Register
from glassdome import agent_manager
agent_manager.register_agent(MyCustomAgent("custom_1", client))
```

### Custom Orchestration

```python
from glassdome import OrchestrationEngine

engine = OrchestrationEngine()

# Add complex task graph
engine.add_task("network", {...})
engine.add_task("vm1", {...}, dependencies=["network"])
engine.add_task("vm2", {...}, dependencies=["network"])
engine.add_task("configure", {...}, dependencies=["vm1", "vm2"])

# Execute
result = await engine.run(executor_func)
```

---

## ✅ Benefits

- ✅ **No Location Restrictions** - Use anywhere
- ✅ **Clean Imports** - `from glassdome import ...`
- ✅ **CLI Commands** - `glassdome serve`
- ✅ **Port Flexibility** - Coexist with other projects
- ✅ **Professional Structure** - Standard Python package
- ✅ **Easy Distribution** - `pip install`
- ✅ **Type Hints** - Full IDE support
- ✅ **Documentation** - Auto-generated from code

---

## 🎉 Summary

Glassdome is now:
1. **A proper Python package** - Install and import anywhere
2. **Port-flexible** - Uses 8001/5174 to avoid conflicts
3. **CLI-enabled** - `glassdome` commands
4. **Location-agnostic** - Functions work across codebase
5. **Integration-ready** - Use in other projects

**Install once, use everywhere!**

```bash
pip install -e /home/nomad/glassdome
glassdome serve
# Happy deploying! 🚀
```

