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
    { id: 'dvwa', name: 'DVWA', type: 'vulnerable', icon: '🎯', os: 'linux' },
    { id: 'metasploitable', name: 'Metasploitable', type: 'vulnerable', icon: '🎯', os: 'linux' },
    { id: 'ubuntu', name: 'Ubuntu Server', type: 'base', icon: '🖥️', os: 'linux' },
    { id: 'windows', name: 'Windows Server', type: 'base', icon: '🪟', os: 'windows' },
  ],
  networks: [
    { id: 'isolated', name: 'Isolated Network', icon: '🔒', type: 'isolated' },
    { id: 'nat', name: 'NAT Network', icon: '🌐', type: 'nat' },
    { id: 'bridged', name: 'Bridged Network', icon: '🔗', type: 'bridged' },
  ]
}

// Default network configurations
const DEFAULT_NETWORK_CONFIGS = {
  isolated: { cidr: '192.168.100.0/24', vlan_id: 100, gateway: '192.168.100.1' },
  nat: { cidr: '10.0.1.0/24', vlan_id: 10, gateway: '10.0.1.1' },
  bridged: { cidr: '192.168.1.0/24', vlan_id: null, gateway: '192.168.1.1' },
}

function LabCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedNode, setSelectedNode] = useState(null)
  const [labName, setLabName] = useState('New Cyber Range Lab')
  const [platform, setPlatform] = useState('1') // Default to Proxmox
  const [isDeploying, setIsDeploying] = useState(false)
  const [networkDefinitions, setNetworkDefinitions] = useState({})
  const [showNetworkConfig, setShowNetworkConfig] = useState(false)
  const [editingNetwork, setEditingNetwork] = useState(null)
  const nodeIdCounter = useRef(1)

  // Fetch existing networks on mount
  useEffect(() => {
    fetchNetworks()
  }, [])

  const fetchNetworks = async () => {
    try {
      const response = await fetch('/api/networks')
      const data = await response.json()
      // Build a map of network definitions
      const netMap = {}
      data.networks.forEach(net => {
        netMap[net.name] = net
      })
      setNetworkDefinitions(netMap)
    } catch (error) {
      console.error('Failed to fetch networks:', error)
    }
  }

  const onConnect = useCallback(
    (params) => {
      // When connecting a VM to a network, track the connection
      const sourceNode = nodes.find(n => n.id === params.source)
      const targetNode = nodes.find(n => n.id === params.target)
      
      // Determine which is the network and which is the VM
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
    
    // For networks, create a config object
    let networkConfig = null
    if (isNetwork) {
      const defaults = DEFAULT_NETWORK_CONFIGS[elementType.id] || DEFAULT_NETWORK_CONFIGS.isolated
      networkConfig = {
        name: `${elementType.id}-${nodeId}`,
        displayName: elementType.name,
        cidr: defaults.cidr,
        vlan_id: defaults.vlan_id,
        gateway: defaults.gateway,
        network_type: elementType.type || 'isolated',
        dhcp_enabled: false
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
            <div className="node-icon">{elementType.icon}</div>
            <div className="node-label">{elementType.name}</div>
            {networkConfig && (
              <div className="node-details">
                <span className="cidr">{networkConfig.cidr}</span>
                {networkConfig.vlan_id && <span className="vlan">VLAN {networkConfig.vlan_id}</span>}
              </div>
            )}
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
      default: '#74b9ff'
    }
    return colors[type] || colors.default
  }

  const onNodeClick = (event, node) => {
    setSelectedNode(node)
    if (node.data.nodeType === 'network') {
      setEditingNetwork(node.data.networkConfig)
      setShowNetworkConfig(true)
    }
  }

  const updateNetworkConfig = (field, value) => {
    if (!editingNetwork) return
    
    const updated = { ...editingNetwork, [field]: value }
    setEditingNetwork(updated)
    
    // Update the node
    setNodes(nds => nds.map(n => {
      if (n.id === selectedNode.id) {
        return {
          ...n,
          data: {
            ...n.data,
            networkConfig: updated,
            label: (
              <div className="custom-node network-node">
                <div className="node-icon">🔒</div>
                <div className="node-label">{updated.displayName}</div>
                <div className="node-details">
                  <span className="cidr">{updated.cidr}</span>
                  {updated.vlan_id && <span className="vlan">VLAN {updated.vlan_id}</span>}
                </div>
              </div>
            )
          }
        }
      }
      return n
    }))
  }

  const clearCanvas = () => {
    setNodes([])
    setEdges([])
    setSelectedNode(null)
    setShowNetworkConfig(false)
  }

  const saveLab = async () => {
    // First, save network definitions to the backend
    const networks = nodes.filter(n => n.data.nodeType === 'network')
    
    for (const netNode of networks) {
      const config = netNode.data.networkConfig
      try {
        await fetch('/api/networks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: config.name,
            cidr: config.cidr,
            vlan_id: config.vlan_id,
            gateway: config.gateway,
            network_type: config.network_type,
            dhcp_enabled: config.dhcp_enabled,
            lab_id: labName
          })
        })
      } catch (error) {
        console.error('Failed to save network:', error)
      }
    }

    const labData = {
      name: labName,
      canvas_data: {
        nodes: nodes.map(n => ({
          ...n,
          data: {
            ...n.data,
            label: undefined // Don't save React components
          }
        })),
        edges
      }
    }

    try {
      const response = await fetch('/api/labs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(labData)
      })
      const result = await response.json()
      alert(`Lab saved successfully! ID: ${result.lab_id}`)
    } catch (error) {
      console.error('Error saving lab:', error)
      alert('Failed to save lab')
    }
  }

  const deployLab = async () => {
    if (nodes.length === 0) {
      alert('Please add some elements to the lab before deploying')
      return
    }

    const platformName = platform === '1' ? 'Proxmox' : 'AWS'
    const vmNodes = nodes.filter(n => n.data.nodeType === 'vm')
    const networkNodes = nodes.filter(n => n.data.nodeType === 'network')
    
    const confirmed = window.confirm(
      `Deploy "${labName}" to ${platformName}?\n\n` +
      `VMs: ${vmNodes.length}\n` +
      `Networks: ${networkNodes.length}\n` +
      `Connections: ${edges.length}`
    )
    
    if (confirmed) {
      setIsDeploying(true)
      try {
        // Build deployment data with network info
        const deploymentData = {
          lab_id: 'current',
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

        const response = await fetch('/api/deployments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(deploymentData)
        })
        const result = await response.json()
        if (result.success) {
          alert(`✅ Deployment initiated!\n\nID: ${result.deployment_id}\nVMs: ${result.vms?.length || 0}\nStatus: ${result.status}`)
        } else {
          alert(`❌ Deployment failed: ${result.message}\n\nErrors: ${result.errors?.join(', ') || 'Unknown error'}`)
        }
      } catch (error) {
        console.error('Error deploying lab:', error)
        alert('Failed to deploy lab: ' + error.message)
      } finally {
        setIsDeploying(false)
      }
    }
  }

  // Get connected networks for a VM
  const getVMNetworks = (vmNodeId) => {
    const connected = edges.filter(e => e.source === vmNodeId || e.target === vmNodeId)
    return connected.map(e => {
      const networkId = e.source === vmNodeId ? e.target : e.source
      const networkNode = nodes.find(n => n.id === networkId)
      return networkNode?.data?.networkConfig
    }).filter(Boolean)
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
          <h4>🌐 Networks</h4>
          {elementTypes.networks.map((network) => (
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

        {/* Network Config Panel */}
        {showNetworkConfig && editingNetwork && (
          <div className="element-section network-config-section">
            <h4>🔧 Network Config</h4>
            <div className="config-form">
              <label>
                Name
                <input 
                  type="text" 
                  value={editingNetwork.displayName}
                  onChange={(e) => updateNetworkConfig('displayName', e.target.value)}
                />
              </label>
              <label>
                CIDR
                <input 
                  type="text" 
                  value={editingNetwork.cidr}
                  onChange={(e) => updateNetworkConfig('cidr', e.target.value)}
                  placeholder="192.168.100.0/24"
                />
              </label>
              <label>
                VLAN ID
                <input 
                  type="number" 
                  value={editingNetwork.vlan_id || ''}
                  onChange={(e) => updateNetworkConfig('vlan_id', e.target.value ? parseInt(e.target.value) : null)}
                  placeholder="100"
                />
              </label>
              <label>
                Gateway
                <input 
                  type="text" 
                  value={editingNetwork.gateway}
                  onChange={(e) => updateNetworkConfig('gateway', e.target.value)}
                  placeholder="192.168.100.1"
                />
              </label>
              <label className="checkbox-label">
                <input 
                  type="checkbox" 
                  checked={editingNetwork.dhcp_enabled}
                  onChange={(e) => updateNetworkConfig('dhcp_enabled', e.target.checked)}
                />
                Enable DHCP
              </label>
              <button 
                className="btn-secondary"
                onClick={() => setShowNetworkConfig(false)}
              >
                Done
              </button>
            </div>
          </div>
        )}

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
              <option value="1">🖥️ Proxmox</option>
              <option value="2">☁️ AWS</option>
            </select>
            <button className="btn-secondary" onClick={saveLab}>
              💾 Save Lab
            </button>
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
    </div>
  )
}

export default LabCanvas
