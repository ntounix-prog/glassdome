/**
 * Labcanvas page component
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useState, useCallback, useRef, useEffect } from 'react'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  Panel
} from 'reactflow'
import 'reactflow/dist/style.css'
import '../styles/LabCanvas.css'

const initialNodes = []
const initialEdges = []

const elementTypes = {
  vms: [
    { id: 'kali', name: 'Kali Linux', type: 'attack', icon: '⚔️', os: 'linux' },
    { id: 'parrot', name: 'Parrot Security', type: 'attack', icon: '🦜', os: 'linux' },
    { id: 'dvwa', name: 'DVWA', type: 'vulnerable', icon: '🎯', os: 'linux' },
    { id: 'metasploitable', name: 'Metasploitable', type: 'vulnerable', icon: '🎯', os: 'linux' },
    { id: 'ubuntu', name: 'Ubuntu Server', type: 'base', icon: '🖥️', os: 'linux' },
    { id: 'windows', name: 'Windows Server', type: 'base', icon: '🪟', os: 'windows' },
    { id: 'pfsense', name: 'pfSense Firewall', type: 'firewall', icon: '🛡️', os: 'bsd' },
    { id: 'guacamole', name: 'Guacamole Gateway', type: 'gateway', icon: '🥑', os: 'linux' },
  ],
  networks: [
    { id: 'lab-network', name: 'Lab Network', icon: '🔗', type: 'isolated' },
    { id: 'aws-vpc', name: 'AWS VPC', icon: '☁️', type: 'vpc', platform: 'aws' },
    { id: 'attack-subnet', name: 'Attack Subnet', icon: '⚔️', type: 'subnet', subnetType: 'attack' },
    { id: 'dmz-subnet', name: 'DMZ Subnet', icon: '🌐', type: 'subnet', subnetType: 'dmz' },
    { id: 'internal-subnet', name: 'Internal Subnet', icon: '🔒', type: 'subnet', subnetType: 'internal' },
  ],
  platforms: [
    { id: 'proxmox', name: 'Proxmox VE', icon: '🖥️', type: 'hypervisor' },
    { id: 'aws', name: 'AWS EC2', icon: '☁️', type: 'cloud' },
    { id: 'azure', name: 'Azure VM', icon: '🔷', type: 'cloud' },
  ]
}

// Generate a unique lab ID
const generateLabId = () => `lab-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`

function LabCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState(null)
  const [labName, setLabName] = useState('New Cyber Range Lab')
  const [labId, setLabId] = useState(() => generateLabId())
  const [platform, setPlatform] = useState('proxmox')
  const [isDeploying, setIsDeploying] = useState(false)
  const [savedLabs, setSavedLabs] = useState([])
  const [isLoadMenuOpen, setIsLoadMenuOpen] = useState(false)
  const [deploymentLogs, setDeploymentLogs] = useState([])
  const [showDeployPanel, setShowDeployPanel] = useState(false)
  const nodeIdCounter = useRef(1)
  const loadMenuTimeoutRef = useRef(null)
  const deployLogRef = useRef(null)

  // Add a log entry
  const addLog = (message, type = 'info') => {
    const entry = {
      id: Date.now(),
      time: new Date().toLocaleTimeString(),
      message,
      type // 'info', 'success', 'error', 'warning'
    }
    setDeploymentLogs(prev => [...prev, entry])
    // Auto-scroll to bottom
    setTimeout(() => {
      if (deployLogRef.current) {
        deployLogRef.current.scrollTop = deployLogRef.current.scrollHeight
      }
    }, 50)
  }

  const clearLogs = () => setDeploymentLogs([])

  // Fetch saved labs on mount
  useEffect(() => {
    fetchSavedLabs()
  }, [])

  const fetchSavedLabs = async () => {
    try {
      const response = await fetch('/api/v1/labs')
      if (response.ok) {
        const data = await response.json()
        setSavedLabs(data.labs || [])
      }
    } catch (error) {
      console.error('Error fetching labs:', error)
    }
  }

  const loadLab = async (lab) => {
    try {
      const response = await fetch(`/api/v1/labs/${lab.id}`)
      if (!response.ok) throw new Error('Failed to load lab')
      
      const labData = await response.json()
      
      // Set lab metadata
      setLabId(labData.id)
      setLabName(labData.name)
      
      // Reconstruct nodes with React elements
      if (labData.canvas_data?.nodes) {
        const reconstructedNodes = labData.canvas_data.nodes.map(n => ({
          ...n,
          data: {
            ...n.data,
            label: n.data.nodeType === 'network' ? (
              <div className="custom-node network-node">
                <div className="node-icon">🔗</div>
                <div className="node-label">Lab Network</div>
                <div className="node-details">
                  <span className="auto-assign">Auto-configured</span>
                </div>
              </div>
            ) : (
              <div className="custom-node vm-node">
                <div className="node-icon">{getElementIcon(n.data.elementId)}</div>
                <div className="node-label">{getElementName(n.data.elementId)}</div>
              </div>
            )
          },
          style: {
            background: n.data.nodeType === 'network' ? '#1a3a4a' : getNodeColor(n.data.elementType),
            border: n.data.nodeType === 'network' ? '2px solid #64c8ff' : '2px solid #222',
            borderRadius: n.data.nodeType === 'network' ? '12px' : '8px',
            padding: '10px',
            minWidth: n.data.nodeType === 'network' ? '180px' : '150px'
          }
        }))
        
        setNodes(reconstructedNodes)
        
        // Update node counter to avoid ID collisions
        const maxId = reconstructedNodes.reduce((max, n) => {
          const match = n.id.match(/node_(\d+)/)
          return match ? Math.max(max, parseInt(match[1])) : max
        }, 0)
        nodeIdCounter.current = maxId + 1
      }
      
      // Load edges
      if (labData.canvas_data?.edges) {
        setEdges(labData.canvas_data.edges.map(e => ({
          ...e,
          style: { stroke: '#64c8ff', strokeWidth: 2 },
          animated: true
        })))
      }
      
      setIsLoadMenuOpen(false)
      alert(`Loaded lab: ${labData.name}`)
    } catch (error) {
      console.error('Error loading lab:', error)
      alert('Failed to load lab: ' + error.message)
    }
  }

  const getElementIcon = (elementId) => {
    const allElements = [...elementTypes.vms, ...elementTypes.networks]
    return allElements.find(e => e.id === elementId)?.icon || '📦'
  }

  const getElementName = (elementId) => {
    const allElements = [...elementTypes.vms, ...elementTypes.networks]
    return allElements.find(e => e.id === elementId)?.name || elementId
  }

  const onConnect = useCallback(
    (params) => {
      const sourceNode = nodes.find(n => n.id === params.source)
      const targetNode = nodes.find(n => n.id === params.target)
      
      const networkNode = [sourceNode, targetNode].find(n => 
        n?.data?.nodeType === 'network'
      )
      const vmNode = [sourceNode, targetNode].find(n => 
        n?.data?.nodeType === 'vm'
      )
      
      if (networkNode && vmNode) {
        console.log(`Connecting VM ${vmNode.data.label} to network ${networkNode.data.networkConfig?.name}`)
      }
      
      setEdges((eds) => addEdge({
        ...params,
        style: { stroke: '#64c8ff', strokeWidth: 2 },
        animated: true
      }, eds))
    },
    [setEdges, nodes]
  )

  const addNode = (elementType, category) => {
    const isNetwork = category === 'network'
    const nodeId = `node_${nodeIdCounter.current++}`
    
    let networkConfig = null
    if (isNetwork) {
      networkConfig = {
        name: `lab-network-${nodeId}`,
        displayName: 'Lab Network',
        network_type: 'isolated',
        auto_assign: true
      }
    }

    const newNode = {
      id: nodeId,
      type: 'default',
      position: { 
        x: Math.random() * 400 + 100, 
        y: Math.random() * 300 + 100 
      },
      data: { 
        label: isNetwork ? (
          <div className="custom-node network-node">
            <div className="node-icon">🔗</div>
            <div className="node-label">Lab Network</div>
            <div className="node-details">
              <span className="auto-assign">Auto-configured</span>
            </div>
          </div>
        ) : (
          <div className="custom-node vm-node">
            <div className="node-icon">{elementType.icon}</div>
            <div className="node-label">{elementType.name}</div>
          </div>
        ),
        nodeType: isNetwork ? 'network' : 'vm',
        elementType: elementType.type,
        elementId: elementType.id,
        os: elementType.os,
        networkConfig: networkConfig
      },
      style: {
        background: isNetwork ? '#1a3a4a' : getNodeColor(elementType.type),
        border: isNetwork ? '2px solid #64c8ff' : '2px solid #222',
        borderRadius: isNetwork ? '12px' : '8px',
        padding: '10px',
        minWidth: isNetwork ? '180px' : '150px'
      }
    }
    setNodes((nds) => [...nds, newNode])
  }

  const getNodeColor = (type) => {
    const colors = {
      attack: '#ff6b6b',
      vulnerable: '#ffd93d',
      base: '#6bcf7f',
      firewall: '#ff9f43',
      gateway: '#9b59b6',
      vpc: '#3498db',
      subnet: '#2ecc71',
      hypervisor: '#e67e22',
      cloud: '#1abc9c',
      default: '#74b9ff'
    }
    return colors[type] || colors.default
  }

  const onNodeClick = (event, node) => {
    setSelectedNode(node)
  }

  const clearCanvas = () => {
    setNodes([])
    setEdges([])
    setSelectedNode(null)
    setLabId(generateLabId())
    setLabName('New Cyber Range Lab')
  }

  const saveLab = async () => {
    const labData = {
      id: labId,
      name: labName,
      canvas_data: {
        nodes: nodes.map(n => ({
          ...n,
          data: {
            ...n.data,
            lab_id: labId,
            label: undefined
          }
        })),
        edges
      }
    }

    try {
      const response = await fetch('/api/v1/labs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(labData)
      })
      const result = await response.json()
      
      const vmCount = nodes.filter(n => n.data.nodeType === 'vm').length
      const hasNetwork = nodes.some(n => n.data.nodeType === 'network')
      
      alert(`Lab saved!\n\nID: ${labId}\nName: ${labName}\nVMs: ${vmCount}\nNetwork: ${hasNetwork ? 'Yes (auto-configured on deploy)' : 'No'}`)
      
      // Refresh saved labs list
      fetchSavedLabs()
    } catch (error) {
      console.error('Error saving lab:', error)
      alert('Failed to save lab')
    }
  }

  const deployLab = async () => {
    if (nodes.length === 0) {
      addLog('❌ Cannot deploy: No elements on canvas', 'error')
      setShowDeployPanel(true)
      return
    }

    const platformNames = { proxmox: 'Proxmox', aws: 'AWS', azure: 'Azure' }
    const platformName = platformNames[platform] || platform
    const vmNodes = nodes.filter(n => n.data.nodeType === 'vm')
    const networkNodes = nodes.filter(n => n.data.nodeType === 'network')
    
    // Show deploy panel and start logging
    setShowDeployPanel(true)
    clearLogs()
    
    addLog(`🚀 Starting deployment of "${labName}"`, 'info')
    addLog(`📍 Target: ${platformName}`, 'info')
    addLog(`🖥️ VMs: ${vmNodes.length} | 🌐 Networks: ${networkNodes.length}`, 'info')
    
    setIsDeploying(true)
    
    try {
      addLog('📦 Preparing deployment package...', 'info')
      
      const deploymentData = {
        lab_id: labId,
        platform_id: platform,
        lab_data: { 
          nodes: nodes.map(n => ({
            id: n.id,
            type: n.data.nodeType,
            elementId: n.data.elementId,
            elementType: n.data.elementType,
            os: n.data.os,
            networkConfig: n.data.networkConfig,
            position: n.position
          })),
          edges: edges.map(e => ({
            source: e.source,
            target: e.target
          }))
        }
      }

      addLog('📤 Sending to deployment API...', 'info')
      
      const response = await fetch('/api/v1/deployments', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deploymentData)
      })
      
      const result = await response.json()
      
      if (!response.ok) {
        throw new Error(result.detail || result.message || `HTTP ${response.status}`)
      }
      
      if (result.success) {
        addLog(`✅ Deployment initiated!`, 'success')
        addLog(`🆔 Deployment ID: ${result.deployment_id}`, 'success')
        
        if (result.vms && result.vms.length > 0) {
          result.vms.forEach(vm => {
            addLog(`  ✓ ${vm.name} (VM ${vm.vm_id})`, 'success')
          })
        }
        
        addLog(`📊 Status: ${result.status}`, 'success')
        
        if (result.network) {
          addLog(`🌐 Network: VLAN ${result.network.vlan_id} (${result.network.cidr})`, 'success')
        }
      } else {
        addLog(`❌ Deployment failed: ${result.message}`, 'error')
        if (result.errors && result.errors.length > 0) {
          result.errors.forEach(err => {
            addLog(`  ⚠️ ${err}`, 'error')
          })
        }
      }
    } catch (error) {
      console.error('Error deploying lab:', error)
      addLog(`❌ Deployment error: ${error.message}`, 'error')
      addLog(`💡 Check browser console (F12) for details`, 'warning')
    } finally {
      setIsDeploying(false)
      addLog('─'.repeat(40), 'info')
    }
  }

  return (
    <div className="lab-canvas-container">
      <div className="sidebar">
        <div className="sidebar-header">
          <h3>Lab Elements</h3>
        </div>

        <div className="element-section">
          <h4>🖥️ Virtual Machines</h4>
          {elementTypes.vms.map((vm) => (
            <button
              key={vm.id}
              className="element-button"
              onClick={() => addNode(vm, 'vm')}
            >
              <span className="element-icon">{vm.icon}</span>
              {vm.name}
            </button>
          ))}
        </div>

        <div className="element-section">
          <h4>🌐 Networks (Proxmox)</h4>
          {elementTypes.networks.filter(n => !n.platform).map((network) => (
            <button
              key={network.id}
              className="element-button network-button"
              onClick={() => addNode(network, 'network')}
            >
              <span className="element-icon">{network.icon}</span>
              {network.name}
            </button>
          ))}
        </div>

        <div className="element-section">
          <h4>☁️ AWS Cloud</h4>
          {elementTypes.networks.filter(n => n.platform === 'aws' || n.type === 'subnet').map((network) => (
            <button
              key={network.id}
              className="element-button network-button aws-button"
              onClick={() => addNode(network, 'network')}
            >
              <span className="element-icon">{network.icon}</span>
              {network.name}
            </button>
          ))}
          <div className="element-hint">
            <small>🥑 Guacamole auto-deployed as gateway</small>
          </div>
        </div>

        <div className="sidebar-footer">
          <button className="btn-secondary" onClick={clearCanvas}>
            Clear Canvas
          </button>
        </div>
      </div>

      <div className="canvas-main">
        <div className="canvas-header">
          <input
            type="text"
            className="lab-name-input"
            value={labName}
            onChange={(e) => setLabName(e.target.value)}
            placeholder="Lab Name"
          />
          <div className="canvas-actions">
            <select 
              className="platform-select"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              <option value="proxmox">🖥️ Proxmox (On-Prem)</option>
              <option value="aws">☁️ AWS EC2</option>
              <option value="azure">🔷 Azure (Coming Soon)</option>
            </select>
            <button className="btn-secondary" onClick={saveLab}>
              💾 Save
            </button>
            
            {/* Load Dropdown */}
            <div 
              className="load-dropdown"
              onMouseEnter={() => {
                if (loadMenuTimeoutRef.current) clearTimeout(loadMenuTimeoutRef.current)
                setIsLoadMenuOpen(true)
              }}
              onMouseLeave={() => {
                loadMenuTimeoutRef.current = setTimeout(() => setIsLoadMenuOpen(false), 300)
              }}
            >
              <button 
                className="btn-secondary"
                onClick={() => setIsLoadMenuOpen(!isLoadMenuOpen)}
              >
                📂 Load ▼
              </button>
              {isLoadMenuOpen && (
                <div className="load-dropdown-menu">
                  {savedLabs.length === 0 ? (
                    <div className="load-dropdown-empty">No saved labs</div>
                  ) : (
                    savedLabs.map(lab => (
                      <button
                        key={lab.id}
                        className="load-dropdown-item"
                        onClick={() => loadLab(lab)}
                      >
                        <span className="load-lab-name">{lab.name}</span>
                        <span className="load-lab-meta">
                          {lab.node_count || 0} nodes
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>

            <button 
              className="btn-primary" 
              onClick={deployLab}
              disabled={isDeploying || nodes.length === 0}
            >
              {isDeploying ? '⏳ Deploying...' : '🚀 Deploy'}
            </button>
          </div>
        </div>

        <div className="canvas-area">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            fitView
          >
            <Controls />
            <MiniMap 
              nodeColor={(node) => {
                if (node.data?.nodeType === 'network') return '#64c8ff'
                return getNodeColor(node.data?.elementType)
              }}
            />
            <Background variant="dots" gap={12} size={1} />
            <Panel position="top-left">
              <div className="info-panel">
                <div className="info-item lab-id-display">
                  <span className="info-label">Lab ID:</span>
                  <span className="info-value mono">{labId.slice(0, 12)}...</span>
                </div>
                <div className="info-item">
                  <span className="info-label">VMs:</span>
                  <span className="info-value">{nodes.filter(n => n.data?.nodeType === 'vm').length}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Networks:</span>
                  <span className="info-value">{nodes.filter(n => n.data?.nodeType === 'network').length}</span>
                </div>
                <div className="info-item">
                  <span className="info-label">Connections:</span>
                  <span className="info-value">{edges.length}</span>
                </div>
              </div>
            </Panel>
          </ReactFlow>
        </div>
      </div>

      {/* Deployment Status Panel */}
      {showDeployPanel && (
        <div className="deploy-panel">
          <div className="deploy-panel-header">
            <h3>📋 Deployment Log</h3>
            <div className="deploy-panel-actions">
              <button 
                className="btn-small btn-secondary"
                onClick={clearLogs}
                title="Clear logs"
              >
                🗑️
              </button>
              <button 
                className="btn-small btn-secondary"
                onClick={() => setShowDeployPanel(false)}
                title="Close panel"
              >
                ✕
              </button>
            </div>
          </div>
          <div className="deploy-panel-content" ref={deployLogRef}>
            {deploymentLogs.length === 0 ? (
              <div className="deploy-empty">No deployment activity yet</div>
            ) : (
              deploymentLogs.map(log => (
                <div key={log.id} className={`deploy-log-entry ${log.type}`}>
                  <span className="log-time">{log.time}</span>
                  <span className="log-message">{log.message}</span>
                </div>
              ))
            )}
          </div>
          {isDeploying && (
            <div className="deploy-panel-footer">
              <div className="deploy-progress">
                <div className="progress-spinner"></div>
                <span>Deployment in progress...</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Toggle button when panel is hidden */}
      {!showDeployPanel && deploymentLogs.length > 0 && (
        <button 
          className="deploy-panel-toggle"
          onClick={() => setShowDeployPanel(true)}
          title="Show deployment log"
        >
          📋 {deploymentLogs.filter(l => l.type === 'error').length > 0 ? '⚠️' : ''}
        </button>
      )}
    </div>
  )
}

export default LabCanvas
