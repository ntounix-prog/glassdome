import { useState, useCallback, useRef } from 'react'
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
    { id: 'kali', name: 'Kali Linux', type: 'attack', icon: '⚔️' },
    { id: 'dvwa', name: 'DVWA', type: 'vulnerable', icon: '🎯' },
    { id: 'metasploitable', name: 'Metasploitable', type: 'vulnerable', icon: '🎯' },
    { id: 'ubuntu', name: 'Ubuntu Server', type: 'base', icon: '🖥️' },
    { id: 'windows', name: 'Windows Server', type: 'base', icon: '🪟' },
  ],
  networks: [
    { id: 'isolated', name: 'Isolated Network', icon: '🔒' },
    { id: 'nat', name: 'NAT Network', icon: '🌐' },
  ]
}

function LabCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)
  const [selectedElement, setSelectedElement] = useState(null)
  const [labName, setLabName] = useState('New Cyber Range Lab')
  const [platform, setPlatform] = useState('2') // Default to AWS
  const [isDeploying, setIsDeploying] = useState(false)
  const nodeIdCounter = useRef(1)

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  )

  const addNode = (elementType) => {
    const newNode = {
      id: `node_${nodeIdCounter.current++}`,
      type: 'default',
      position: { 
        x: Math.random() * 400 + 100, 
        y: Math.random() * 300 + 100 
      },
      data: { 
        label: (
          <div className="custom-node">
            <div className="node-icon">{elementType.icon}</div>
            <div className="node-label">{elementType.name}</div>
          </div>
        ),
        elementType: elementType.type,
        elementId: elementType.id
      },
      style: {
        background: getNodeColor(elementType.type),
        border: '2px solid #222',
        borderRadius: '8px',
        padding: '10px',
        minWidth: '150px'
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

  const clearCanvas = () => {
    setNodes([])
    setEdges([])
  }

  const saveLab = async () => {
    const labData = {
      name: labName,
      canvas_data: {
        nodes,
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

    const platformName = platform === '2' ? 'AWS' : 'Proxmox'
    const confirmed = window.confirm(
      `Deploy "${labName}" to ${platformName}? This will create ${nodes.length} resources.`
    )
    
    if (confirmed) {
      setIsDeploying(true)
      try {
        const response = await fetch('/api/deployments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lab_id: 'current',
            platform_id: platform,
            lab_data: { nodes, edges }
          })
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
              onClick={() => addNode(vm)}
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
              className="element-button"
              onClick={() => addNode(network)}
            >
              <span className="element-icon">{network.icon}</span>
              {network.name}
            </button>
          ))}
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
              <option value="2">☁️ AWS</option>
              <option value="1">🖥️ Proxmox</option>
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
            fitView
          >
            <Controls />
            <MiniMap />
            <Background variant="dots" gap={12} size={1} />
            <Panel position="top-left">
              <div className="info-panel">
                <div className="info-item">
                  <span className="info-label">Elements:</span>
                  <span className="info-value">{nodes.length}</span>
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

