# Agent Architecture - Design Decision

## The Question

Should we have:
1. **Specialized Agents** - One agent per OS type (Ubuntu, Kali, Windows)
2. **One "Overlord" Agent** - Single agent that handles all OS types

## The Answer: Hybrid Architecture ⭐

We use a **hybrid approach** that combines the best of both:

```
Base OS Installer Agent (abstract base class)
    ↓ Inherits
├── Ubuntu Installer Agent (specialized)
├── Kali Installer Agent (specialized)
├── Windows Installer Agent (specialized)
└── ... more OS agents

OS Installer Factory (router/factory)
    ↓ Creates
Appropriate Agent for OS Type
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         API Request (any OS type)               │
└────────────────┬────────────────────────────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│      OS Installer Factory (Router)              │
│  • Determines OS type                           │
│  • Selects appropriate agent                    │
│  • Caches agents                                │
└────────────────┬────────────────────────────────┘
                 │
        ┌────────┼────────┐
        ↓        ↓        ↓
   ┌────────┬────────┬─────────┐
   │ Ubuntu │  Kali  │ Windows │  Specialized Agents
   │ Agent  │ Agent  │ Agent   │  (inherit from base)
   └────────┴────────┴─────────┘
        │        │        │
        └────────┴────────┘
               ↓
   ┌───────────────────────┐
   │ OSInstallerAgent      │  Base Class
   │ (Common Logic)        │  • Template cloning
   │                       │  • IP detection
   │                       │  • Resource config
   │                       │  • Error handling
   └───────────────────────┘
               ↓
        Platform Client
    (Proxmox, Azure, AWS)
```

---

## Why This Is Better

### ✅ **Best of Both Worlds**

| Feature | Specialized Only | Overlord Only | **Hybrid** |
|---------|-----------------|---------------|------------|
| Code reuse | ❌ Poor | ✅ Good | ✅ **Excellent** |
| Maintainability | ✅ Good | ❌ Poor | ✅ **Excellent** |
| Single Responsibility | ✅ Yes | ❌ No | ✅ **Yes** |
| Easy to extend | ⚠️ OK | ❌ Hard | ✅ **Easy** |
| Testing | ✅ Easy | ❌ Hard | ✅ **Easy** |
| Error isolation | ✅ Good | ❌ Poor | ✅ **Good** |
| Single entry point | ❌ No | ✅ Yes | ✅ **Yes** |

---

## Code Example

### Base Class (Shared Logic)

```python
class OSInstallerAgent(DeploymentAgent):
    """Base class with common logic"""
    
    async def _deploy_element(self, element_type, config):
        """Common deployment flow"""
        # 1. Validate
        # 2. Clone from template OR create from ISO
        # 3. Configure resources
        # 4. Start VM
        # 5. Wait for IP
        # 6. Return details
        
    @abstractmethod
    async def prepare_os_config(self, version, config):
        """OS-specific config - implemented by subclass"""
        pass
```

### Specialized Agent (Ubuntu)

```python
class UbuntuInstallerAgent(OSInstallerAgent):
    """Ubuntu-specific logic"""
    
    OS_VERSIONS = {
        "22.04": {...},
        "24.04": {...}
    }
    
    async def prepare_os_config(self, version, config):
        """Ubuntu-specific configuration"""
        return {
            "template_id": self.OS_VERSIONS[version]["template_id"],
            "iso": self.OS_VERSIONS[version]["iso"],
            # Ubuntu-specific settings
        }
```

### Factory (Router)

```python
class OSInstallerFactory:
    """Routes to appropriate agent"""
    
    _agent_registry = {
        "ubuntu": UbuntuInstallerAgent,
        "kali": KaliInstallerAgent,
        "windows": WindowsInstallerAgent,
    }
    
    @classmethod
    def get_agent(cls, os_type, platform_client):
        """Get the right agent for OS type"""
        agent_class = cls._agent_registry[os_type]
        return agent_class(f"{os_type}_1", platform_client)
```

---

## Usage Patterns

### Pattern 1: Direct Agent Use

```python
# For specialized control
from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent

agent = UbuntuInstallerAgent("ubuntu_1", proxmox_client)
result = await agent.run(task)
```

### Pattern 2: Factory Use

```python
# For flexibility
from glassdome.agents.os_installer_factory import OSInstallerFactory

agent = OSInstallerFactory.get_agent("ubuntu", proxmox_client)
result = await agent.run(task)
```

### Pattern 3: API Use (Hidden Implementation)

```bash
# User doesn't care about architecture
POST /api/vm/create
{
  "os_type": "ubuntu",  # Factory handles routing
  "version": "22.04",
  ...
}
```

---

## Benefits

### 1. **Code Reuse** 📦
- Common logic in base class
- No duplication
- Shared template cloning, IP detection, etc.

### 2. **Single Responsibility** 🎯
- Each agent handles ONE OS type
- Easy to understand
- Clear boundaries

### 3. **Easy to Extend** 🔧
```python
# Adding new OS is simple:

class DebianInstallerAgent(OSInstallerAgent):
    OS_VERSIONS = {...}
    
    async def prepare_os_config(self, version, config):
        # Debian-specific logic
        pass

# Register it
OSInstallerFactory.register_os_agent("debian", DebianInstallerAgent)
```

### 4. **Error Isolation** 🛡️
- Kali agent bug doesn't affect Ubuntu
- Each agent can fail independently
- Easier debugging

### 5. **Flexible APIs** 🔌
```python
# Can expose both:
POST /api/ubuntu/create    # Specific endpoint
POST /api/vm/create        # Generic endpoint with os_type parameter
```

### 6. **Testing** ✅
```python
# Test each agent independently
def test_ubuntu_agent():
    agent = UbuntuInstallerAgent(...)
    # Test Ubuntu-specific behavior

def test_kali_agent():
    agent = KaliInstallerAgent(...)
    # Test Kali-specific behavior

# Test factory
def test_factory_routing():
    agent = OSInstallerFactory.get_agent("ubuntu", ...)
    assert isinstance(agent, UbuntuInstallerAgent)
```

---

## When to Use Each Pattern

### Use Direct Agent When:
- ✅ You know the specific OS type
- ✅ You want OS-specific methods
- ✅ You're building OS-specific features

```python
ubuntu_agent = UbuntuInstallerAgent(...)
ubuntu_agent.create_template(...)  # Ubuntu-specific method
```

### Use Factory When:
- ✅ OS type comes from user input
- ✅ Building generic VM creation API
- ✅ Want flexibility to add OS types later

```python
os_type = request.json["os_type"]
agent = OSInstallerFactory.get_agent(os_type, client)
```

---

## Comparison to Alternatives

### ❌ **Pure Specialized (No Base Class)**

```python
class UbuntuAgent:
    async def clone_from_template(...):  # Duplicated
        # Template logic
    
class KaliAgent:
    async def clone_from_template(...):  # Duplicated
        # Same template logic again!
```

**Problem:** Lots of code duplication

### ❌ **Pure Overlord (One Big Agent)**

```python
class OSInstallerAgent:
    async def deploy(self, os_type, config):
        if os_type == "ubuntu":
            # Ubuntu logic
        elif os_type == "kali":
            # Kali logic
        elif os_type == "windows":
            # Windows logic
        # ... hundreds of lines ...
```

**Problems:**
- God object anti-pattern
- Hard to maintain
- Hard to test
- Violates Single Responsibility
- One bug affects all OS types

### ✅ **Our Hybrid Approach**

```python
# Base class: Common logic
class OSInstallerAgent(DeploymentAgent):
    async def _clone_from_template(...):  # Shared
        # Common template logic
    
    @abstractmethod
    async def prepare_os_config(...):
        # OS-specific, implemented by subclass
        pass

# Specialized: OS-specific logic
class UbuntuInstallerAgent(OSInstallerAgent):
    async def prepare_os_config(...):
        # Only Ubuntu-specific stuff here
        
class KaliInstallerAgent(OSInstallerAgent):
    async def prepare_os_config(...):
        # Only Kali-specific stuff here

# Factory: Routing
OSInstallerFactory.get_agent(os_type, client)
```

**Benefits:**
- ✅ Shared code in base
- ✅ Specialized where needed
- ✅ Easy to maintain
- ✅ Easy to test
- ✅ Easy to extend
- ✅ Single entry point option

---

## File Organization

```
glassdome/agents/
├── base.py                      # DeploymentAgent base
├── os_installer_base.py         # OSInstallerAgent (common OS logic)
├── os_installer_factory.py      # Factory/Router
├── ubuntu_installer.py          # Ubuntu-specific
├── kali_installer.py            # Kali-specific (future)
├── windows_installer.py         # Windows-specific (future)
└── manager.py                   # Agent Manager
```

---

## Conclusion

**Use the hybrid architecture:**
- ✅ Base class for common logic
- ✅ Specialized agents for OS-specific logic  
- ✅ Factory for routing and flexibility

**This gives you:**
- Single Responsibility Principle
- Don't Repeat Yourself (DRY)
- Open/Closed Principle (open for extension)
- Easy testing
- Clear architecture
- Best of both worlds!

---

**Recommendation: Keep specialized agents but add base class and factory for shared logic and flexibility.** ⭐

