# Glassdome Installation Guide

## Installation as a Python Package

Glassdome is now a proper Python package that can be installed system-wide or in any environment.

### Option 1: Install in Development Mode (Editable)

This allows you to modify the code and have changes reflected immediately:

```bash
cd /home/nomad/glassdome
pip install -e .
```

### Option 2: Install with Development Dependencies

```bash
pip install -e ".[dev]"
```

### Option 3: Install from Source

```bash
cd /home/nomad/glassdome
pip install .
```

### Option 4: Install from GitHub

```bash
pip install git+https://github.com/ntounix/glassdome.git
```

## Using Glassdome as a Package

After installation, you can import Glassdome from anywhere:

### Python Code

```python
# Import the entire package
import glassdome

# Or import specific components
from glassdome import ProxmoxClient, AzureClient, AWSClient
from glassdome import agent_manager, OrchestrationEngine
from glassdome.models import Lab, Deployment

# Use anywhere in your code
client = ProxmoxClient(host="...", user="...", password="...")
labs = Lab.query.all()
```

### Command Line Interface

After installation, you get CLI commands:

```bash
# Start the server (default port 8001)
glassdome serve

# Or with custom port
glassdome serve --port 9000 --host 0.0.0.0

# Initialize the system
glassdome init

# Check status
glassdome status

# Test platform connectivity
glassdome test-platform --platform proxmox

# Manage agents
glassdome agent list
glassdome agent start

# Manage labs
glassdome lab list
glassdome lab create --name "My Lab"

# Manage deployments
glassdome deploy list
glassdome deploy create --lab-id lab_123 --platform proxmox
```

## Port Configuration

By default, Glassdome uses:
- **Backend API:** Port 8001 (changed from 8000 to avoid conflicts)
- **Frontend:** Port 5174 (changed from 5173 to avoid conflicts)

You can change these in `.env`:

```bash
BACKEND_PORT=8001
VITE_PORT=5174
```

Or pass as command arguments:

```bash
glassdome serve --port 9000
```

## Using Glassdome in Your Own Projects

### Example 1: Deploy a Lab Programmatically

```python
from glassdome import ProxmoxClient, OrchestrationEngine, agent_manager

# Initialize platform
proxmox = ProxmoxClient(
    host="proxmox.local",
    user="root@pam",
    password="secret"
)

# Create orchestration
engine = OrchestrationEngine()

# Add tasks
engine.add_task("vm1", {
    "type": "create_vm",
    "config": {"name": "kali-linux", "memory": 4096}
})

engine.add_task("vm2", {
    "type": "create_vm", 
    "config": {"name": "dvwa", "memory": 2048}
}, dependencies=["vm1"])

# Execute
async def deploy():
    result = await engine.run(executor_func=deploy_task)
    print(f"Deployment: {result['completed']}/{result['total_tasks']} successful")

import asyncio
asyncio.run(deploy())
```

### Example 2: Monitor Deployments

```python
from glassdome.models import Deployment, DeploymentStatus

# Query active deployments
active = Deployment.query.filter_by(status=DeploymentStatus.IN_PROGRESS).all()

for deployment in active:
    print(f"{deployment.name}: {deployment.progress_percentage}%")
```

### Example 3: Create Custom Agents

```python
from glassdome.agents.base import DeploymentAgent

class CustomDeploymentAgent(DeploymentAgent):
    async def _deploy_element(self, element_type, config):
        # Your custom deployment logic
        return {"success": True, "resource_id": "custom_123"}

# Register with agent manager
from glassdome import agent_manager

custom_agent = CustomDeploymentAgent("custom_1", my_platform_client)
agent_manager.register_agent(custom_agent)
```

## No Installation Restrictions

The package structure means:
- ✅ Import from anywhere on your system
- ✅ No need to be in the project directory
- ✅ Use in Jupyter notebooks
- ✅ Integrate with other Python projects
- ✅ Deploy to production as a package
- ✅ Version and distribute via pip

## Virtual Environment (Optional but Recommended)

```bash
# Create virtual environment
python3 -m venv ~/.venvs/glassdome

# Activate
source ~/.venvs/glassdome/bin/activate

# Install
pip install -e /home/nomad/glassdome
```

## Uninstallation

```bash
pip uninstall glassdome
```

## Development Workflow

When developing:

1. Install in editable mode: `pip install -e .`
2. Make changes to code
3. Changes are immediately available system-wide
4. No need to reinstall

## Docker (Alternative)

If you prefer containers:

```bash
docker-compose up --build
```

Backend will be on port 8001, frontend on 5174.

## Integration with Other Server Projects

Since ports are now configurable and Glassdome is a package:

```bash
# Your other project on port 8000
# Glassdome on port 8001

# In your other project's code:
from glassdome import ProxmoxClient

# Use Glassdome functionality in your project
client = ProxmoxClient(...)
```

## Verification

After installation:

```bash
# Check installation
pip show glassdome

# Check CLI
glassdome --version

# Test imports
python -c "import glassdome; print(glassdome.__version__)"
```

## Next Steps

1. Configure `.env` with your credentials
2. Run `glassdome init` to initialize
3. Start server: `glassdome serve`
4. Or use programmatically in your own code

