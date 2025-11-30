# Request Flow: Frontend → Backend → Agent/Orchestrator

> **Updated:** November 2025 - All API paths now use `/api/v1/` prefix

## Two Deployment Paths

### Path 1: **Simple Single VM** → Direct to Agent
### Path 2: **Complex Lab** → Orchestrator → Agents

---

## Path 1: Single VM (Direct to Agent)

**User Action:** Selects "Create Single VM" from dropdown

```
React Frontend (Dropdown)
  ↓
  User selects:
  - OS: Ubuntu 22.04
  - Cores: 2
  - Memory: 4GB
  - Disk: 20GB
  ↓
POST /api/v1/agents/ubuntu/create
  ↓
FastAPI Backend
  ↓
UbuntuInstallerAgent.run()
  ↓
Proxmox API
  ↓
VM Created ✅
  ↓
Return VM details to frontend
```

**Code:**
```jsx
// React: Simple VM request
const createSimpleVM = async () => {
  const response = await fetch('/api/v1/agents/ubuntu/create', {
    method: 'POST',
    body: JSON.stringify({
      name: 'my-ubuntu-vm',
      version: '22.04',
      cores: 2,
      memory: 4096,
      disk_size: 20
    })
  });
  const vm = await response.json();
  console.log('VM created:', vm.vm_id);
};
```

**When to use:**
- ✅ Single VM needed
- ✅ No users/packages required
- ✅ Quick deployment
- ✅ Testing
- ✅ Basic infrastructure

---

## Path 2: Complete Lab (Orchestrator → Agents)

**User Action:** Selects "Deploy Lab Template" from dropdown

```
React Frontend (Lab Designer)
  ↓
  User designs lab:
  - Drag Kali VM onto canvas
  - Drag Ubuntu VM onto canvas
  - Configure users, packages, network
  - Connect VMs
  ↓
POST /api/v1/canvas/deploy
  ↓
FastAPI Backend
  ↓
LabOrchestrator.deploy_lab()
  ↓
  ├─→ Creates networks
  ├─→ Calls KaliAgent for Kali VM
  ├─→ Calls UbuntuAgent for Ubuntu VM
  ├─→ Creates users (SSH)
  ├─→ Installs packages (SSH)
  └─→ Runs post-config (SSH)
  ↓
Complete Lab Ready ✅
  ↓
Return lab details to frontend
```

**Code:**
```jsx
// React: Lab deployment request
const deployLab = async (labDesign) => {
  const response = await fetch('/api/v1/canvas/deploy', {
    method: 'POST',
    body: JSON.stringify({
      lab_id: 'security_lab_001',
      vms: [
        {
          vm_id: 'kali',
          os_type: 'kali',
          resources: { cores: 4, memory: 8192, disk_size: 80 },
          users: [{ username: 'pentester', sudo: true }],
          packages: { system: ['nmap', 'metasploit'] }
        },
        {
          vm_id: 'target',
          os_type: 'ubuntu',
          resources: { cores: 2, memory: 4096, disk_size: 40 },
          users: [{ username: 'webadmin' }],
          packages: { system: ['apache2'] }
        }
      ]
    })
  });
  const lab = await response.json();
  console.log('Lab deployed:', lab.lab_id);
};
```

**When to use:**
- ✅ Multiple VMs needed
- ✅ User accounts required
- ✅ Packages to install
- ✅ Network isolation needed
- ✅ Dependencies between VMs
- ✅ Complete cyber range

---

## Frontend Dropdown Options

### Simple Dropdown (Quick Deploy)

```jsx
<select onChange={handleVMSelect}>
  <option value="">Select VM Type...</option>
  
  <optgroup label="Quick Deploy (Single VM)">
    <option value="ubuntu-22.04">Ubuntu 22.04 Server</option>
    <option value="ubuntu-20.04">Ubuntu 20.04 Server</option>
    <option value="kali-2024">Kali Linux 2024.1</option>
    <option value="debian-12">Debian 12</option>
    <option value="centos-9">CentOS Stream 9</option>
  </optgroup>
  
  <optgroup label="Lab Templates (Orchestrated)">
    <option value="lab-web-security">Web Security Lab</option>
    <option value="lab-network-defense">Network Defense Lab</option>
    <option value="lab-malware-analysis">Malware Analysis Lab</option>
    <option value="lab-ctf">CTF Environment</option>
  </optgroup>
</select>
```

### Advanced Dropdown (With Configuration)

```jsx
// Step 1: Select type
<select value={deployType} onChange={handleTypeChange}>
  <option value="single">Single VM (Quick)</option>
  <option value="lab">Complete Lab (Advanced)</option>
</select>

// If Single VM selected:
{deployType === 'single' && (
  <div>
    <select name="os">
      <option value="ubuntu">Ubuntu</option>
      <option value="kali">Kali</option>
      <option value="debian">Debian</option>
    </select>
    
    <input type="number" name="cores" placeholder="CPU Cores" />
    <input type="number" name="memory" placeholder="Memory (MB)" />
    <input type="number" name="disk" placeholder="Disk (GB)" />
    
    <button onClick={createSingleVM}>Deploy VM</button>
  </div>
)}

// If Lab selected:
{deployType === 'lab' && (
  <div>
    <select name="lab_template">
      <option value="custom">Custom Lab (Drag & Drop)</option>
      <option value="web_security">Web Security Lab</option>
      <option value="network_defense">Network Defense</option>
    </select>
    
    <button onClick={openLabDesigner}>Open Lab Designer</button>
  </div>
)}
```

---

## Backend API Endpoints

### Single VM Endpoints (Direct to Agent)

```python
# glassdome/api/ubuntu.py
@router.post("/api/v1/agents/ubuntu/create")
async def create_ubuntu_vm(request: CreateVMRequest):
    """
    Create a single Ubuntu VM
    Goes DIRECTLY to UbuntuInstallerAgent
    """
    agent = UbuntuInstallerAgent(proxmox_client)
    result = await agent.run({
        "element_type": "ubuntu_vm",
        "config": request.dict()
    })
    return result

# Similar for other OSes:
# POST /api/v1/agents/kali/create
# POST /api/v1/agents/debian/create
# POST /api/v1/agents/centos/create
```

### Lab Endpoint (Orchestrator)

```python
# glassdome/api/labs.py
@router.post("/api/v1/canvas/deploy")
async def deploy_lab(request: LabDeployRequest):
    """
    Deploy complete lab with multiple VMs
    Goes to Orchestrator, which calls agents
    """
    orchestrator = LabOrchestrator(proxmox_client)
    result = await orchestrator.deploy_lab(request.lab_spec)
    return result
```

---

## Decision Flow

```
Frontend User Action
    ↓
    Is it a single VM?
    ├─ YES → Call agent endpoint directly
    │         POST /api/v1/agents/{os}/create
    │         └─→ Agent creates VM
    │
    └─ NO → Is it a lab?
              └─ YES → Call orchestrator endpoint
                       POST /api/v1/canvas/deploy
                       └─→ Orchestrator calls multiple agents
                           └─→ Each agent creates one VM
                           └─→ Orchestrator does post-config
```

---

## React Component Example

```jsx
// SimpleVMCreator.jsx
import React, { useState } from 'react';

export default function SimpleVMCreator() {
  const [vmType, setVmType] = useState('');
  
  const handleQuickDeploy = async () => {
    // Direct to agent
    const response = await fetch(`/api/v1/agents/${vmType}/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: `${vmType}-vm-${Date.now()}`,
        version: 'latest',
        cores: 2,
        memory: 4096,
        disk_size: 20
      })
    });
    
    const result = await response.json();
    alert(`VM created: ${result.vm_id}`);
  };
  
  return (
    <div className="quick-deploy">
      <h3>Quick Deploy (Single VM)</h3>
      
      <select value={vmType} onChange={e => setVmType(e.target.value)}>
        <option value="">Choose OS...</option>
        <option value="ubuntu">Ubuntu 22.04</option>
        <option value="kali">Kali Linux</option>
        <option value="debian">Debian 12</option>
      </select>
      
      <button onClick={handleQuickDeploy}>Deploy Now</button>
    </div>
  );
}
```

```jsx
// LabDeployer.jsx
import React, { useState } from 'react';

export default function LabDeployer() {
  const [labTemplate, setLabTemplate] = useState('');
  
  const handleLabDeploy = async () => {
    // Send to orchestrator
    const labSpec = LAB_TEMPLATES[labTemplate]; // Pre-defined template
    
    const response = await fetch('/api/v1/canvas/deploy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lab_spec: labSpec })
    });
    
    const result = await response.json();
    alert(`Lab deployed: ${result.lab_id}`);
  };
  
  return (
    <div className="lab-deploy">
      <h3>Deploy Complete Lab</h3>
      
      <select value={labTemplate} onChange={e => setLabTemplate(e.target.value)}>
        <option value="">Choose Lab Template...</option>
        <option value="web_security">Web Security Lab</option>
        <option value="network_defense">Network Defense Lab</option>
        <option value="malware_analysis">Malware Analysis Lab</option>
      </select>
      
      <button onClick={handleLabDeploy}>Deploy Lab</button>
    </div>
  );
}
```

---

## Summary

| User Action | API Endpoint | Backend Handler | Who Creates VM |
|-------------|--------------|-----------------|----------------|
| **Single VM** | `POST /api/v1/agents/{os}/create` | Direct to Agent | **Agent alone** |
| **Complete Lab** | `POST /api/v1/canvas/deploy` | Orchestrator | **Orchestrator → Agent** |

### Single VM (Direct to Agent):
- ✅ Faster
- ✅ Simpler
- ✅ No extra config
- ❌ Just bare VM

### Complete Lab (Orchestrator):
- ✅ Full configuration
- ✅ Multiple VMs
- ✅ Users, packages, network
- ✅ Dependencies managed
- ⏱️ Takes longer

**Both paths end up calling agents for VM creation, but the orchestrator adds all the extra configuration on top!**

