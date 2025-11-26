/**
 * Platform Status Page
 * Displays VMs and status for a specific platform
 */
import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import '../styles/PlatformStatus.css'

// Platform-specific icons and colors
const PLATFORM_CONFIG = {
  proxmox: {
    icon: '🖥️',
    name: 'Proxmox VE',
    color: '#e57000',
    description: 'On-premise virtualization platform'
  },
  esxi: {
    icon: '🏢',
    name: 'VMware ESXi',
    color: '#717074',
    description: 'Enterprise virtualization'
  },
  aws: {
    icon: '☁️',
    name: 'Amazon Web Services',
    color: '#ff9900',
    description: 'AWS EC2 instances'
  },
  azure: {
    icon: '🌐',
    name: 'Microsoft Azure',
    color: '#0078d4',
    description: 'Azure Virtual Machines'
  }
}

function formatBytes(bytes) {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatUptime(seconds) {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

export default function PlatformStatus() {
  const { platform, instanceId } = useParams()
  const navigate = useNavigate()
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [actionLoading, setActionLoading] = useState(null)

  const config = PLATFORM_CONFIG[platform] || PLATFORM_CONFIG.proxmox

  useEffect(() => {
    fetchStatus()
    // Refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [platform, instanceId])

  const fetchStatus = async () => {
    try {
      setLoading(true)
      // For AWS, use all-regions endpoint to get both Virginia and Oregon
      // For Proxmox, use all-instances endpoint to get all clusters (pve01, pve02, etc.)
      let url
      if (platform === 'aws') {
        url = '/api/platforms/aws/all-regions'
      } else if (platform === 'proxmox') {
        url = '/api/platforms/proxmox/all-instances'
      } else if (instanceId) {
        url = `/api/platforms/${platform}/${instanceId}/vms`
      } else {
        url = `/api/platforms/${platform}`
      }
      
      const response = await fetch(url)
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch platform status')
      }
      
      setStatus(data)
      setError(null)
    } catch (err) {
      console.error('Error fetching platform status:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleVMAction = async (vmid, action, vmNode = null) => {
    setActionLoading(vmid)
    try {
      // Extract instance ID from node if available (format: "pve01 (01)")
      let targetInstance = instanceId || '01'
      if (vmNode && vmNode.includes('(')) {
        const match = vmNode.match(/\((\d+)\)/)
        if (match) {
          targetInstance = match[1]
        }
      }
      
      const url = `/api/platforms/${platform}/${targetInstance}/vms/${vmid}/${action}`
      const response = await fetch(url, { method: 'POST' })
      const data = await response.json()
      
      if (!response.ok) {
        throw new Error(data.detail || `Failed to ${action} VM`)
      }
      
      // Refresh status after action
      setTimeout(fetchStatus, 2000)
    } catch (err) {
      console.error(`Error ${action}ing VM:`, err)
      alert(`Failed to ${action} VM: ${err.message}`)
    } finally {
      setActionLoading(null)
    }
  }

  // Filter VMs
  const filteredVMs = status?.vms?.filter(vm => {
    // Filter by status
    if (filter === 'running' && vm.status !== 'running' && vm.status !== 'poweredOn') return false
    if (filter === 'stopped' && vm.status !== 'stopped' && vm.status !== 'poweredOff') return false
    if (filter === 'templates' && !vm.template) return false
    
    // Filter by search
    if (search && !vm.name.toLowerCase().includes(search.toLowerCase())) return false
    
    return true
  }) || []

  return (
    <div className="platform-status-page">
      <div className="platform-header" style={{ borderColor: config.color }}>
        <button className="back-button" onClick={() => navigate('/')}>
          ← Back
        </button>
        
        <div className="platform-title">
          <span className="platform-icon">{config.icon}</span>
          <div>
            <h1>{config.name}</h1>
            <p>{config.description}</p>
          </div>
        </div>
        
        <div className="connection-status">
          {loading ? (
            <span className="status-badge loading">Connecting...</span>
          ) : status?.connected ? (
            <span className="status-badge connected">Connected</span>
          ) : (
            <span className="status-badge disconnected">Disconnected</span>
          )}
        </div>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={fetchStatus}>Retry</button>
        </div>
      )}

      {status && status.connected && (
        <>
          {/* Summary Cards */}
          <div className="summary-cards">
            <div className="summary-card total">
              <div className="card-value">{status.summary?.total || 0}</div>
              <div className="card-label">Total VMs</div>
            </div>
            <div className="summary-card running">
              <div className="card-value">{status.summary?.running || 0}</div>
              <div className="card-label">Running</div>
            </div>
            <div className="summary-card stopped">
              <div className="card-value">{status.summary?.stopped || 0}</div>
              <div className="card-label">Stopped</div>
            </div>
            {status.summary?.templates > 0 && (
              <div className="summary-card templates">
                <div className="card-value">{status.summary?.templates || 0}</div>
                <div className="card-label">Templates</div>
              </div>
            )}
          </div>

          {/* Proxmox Servers Section - combines instance info with node stats */}
          {status.nodes && status.nodes.length > 0 && (
            <div className="nodes-section">
              <h3>Proxmox Servers</h3>
              <div className="nodes-grid">
                {status.nodes.map((node, idx) => {
                  // Find matching instance info for VM count
                  const instanceInfo = status.summary?.instances?.find(
                    i => i.instance_id === node.instance_id
                  )
                  return (
                    <div key={idx} className={`node-card ${node.status || 'online'}`}>
                      <div className="node-name">{node.node || node.name}</div>
                      {node.host && (
                        <div className="node-host">{node.host}</div>
                      )}
                      <div className="node-status">
                        {node.status === 'online' ? '🟢' : '🔴'} {node.status || 'online'}
                      </div>
                      {node.cpu !== undefined && (
                        <div className="node-stat">CPU: {(node.cpu * 100).toFixed(1)}%</div>
                      )}
                      {node.mem && node.maxmem && (
                        <div className="node-stat">
                          RAM: {formatBytes(node.mem)} / {formatBytes(node.maxmem)}
                        </div>
                      )}
                      {instanceInfo && (
                        <div className="node-stat vm-count">{instanceInfo.vms} VMs</div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="vm-filters">
            <div className="filter-group">
              <button 
                className={filter === 'all' ? 'active' : ''} 
                onClick={() => setFilter('all')}
              >
                All
              </button>
              <button 
                className={filter === 'running' ? 'active' : ''} 
                onClick={() => setFilter('running')}
              >
                Running
              </button>
              <button 
                className={filter === 'stopped' ? 'active' : ''} 
                onClick={() => setFilter('stopped')}
              >
                Stopped
              </button>
              <button 
                className={filter === 'templates' ? 'active' : ''} 
                onClick={() => setFilter('templates')}
              >
                Templates
              </button>
            </div>
            
            <input
              type="text"
              placeholder="Search VMs..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="search-input"
            />
            
            <button className="refresh-btn" onClick={fetchStatus} disabled={loading}>
              🔄 Refresh
            </button>
          </div>

          {/* VM Table */}
          <div className="vm-table-container">
            <table className="vm-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Status</th>
                  <th>CPU</th>
                  <th>Memory</th>
                  <th>Disk</th>
                  <th>Uptime</th>
                  {platform === 'proxmox' && <th>Node</th>}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredVMs.length === 0 ? (
                  <tr>
                    <td colSpan={platform === 'proxmox' ? 9 : 8} className="no-vms">
                      {loading ? 'Loading...' : 'No VMs found'}
                    </td>
                  </tr>
                ) : (
                  filteredVMs.map((vm) => (
                    <tr key={vm.vmid} className={vm.template ? 'template-row' : ''}>
                      <td className="vm-id">{vm.vmid}</td>
                      <td className="vm-name">
                        {vm.template && <span className="template-badge">📋</span>}
                        {vm.name}
                      </td>
                      <td>
                        <span className={`status-pill ${vm.status}`}>
                          {vm.status === 'running' || vm.status === 'poweredOn' ? '🟢' : '🔴'} 
                          {vm.status}
                        </span>
                      </td>
                      <td>{vm.cpu ? `${(vm.cpu * 100).toFixed(1)}%` : '-'}</td>
                      <td>
                        {vm.memory_used && vm.memory 
                          ? `${formatBytes(vm.memory_used)} / ${formatBytes(vm.memory)}`
                          : vm.memory ? formatBytes(vm.memory) : '-'
                        }
                      </td>
                      <td>{vm.disk ? formatBytes(vm.disk) : '-'}</td>
                      <td>{formatUptime(vm.uptime)}</td>
                      {platform === 'proxmox' && <td>{vm.node}</td>}
                      <td className="vm-actions">
                        {!vm.template && (
                          <>
                            {(vm.status === 'running' || vm.status === 'poweredOn') ? (
                              <button 
                                className="action-btn stop"
                                onClick={() => handleVMAction(vm.vmid, 'stop', vm.node)}
                                disabled={actionLoading === vm.vmid}
                              >
                                {actionLoading === vm.vmid ? '...' : '⏹️ Stop'}
                              </button>
                            ) : (
                              <button 
                                className="action-btn start"
                                onClick={() => handleVMAction(vm.vmid, 'start', vm.node)}
                                disabled={actionLoading === vm.vmid}
                              >
                                {actionLoading === vm.vmid ? '...' : '▶️ Start'}
                              </button>
                            )}
                          </>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {status && !status.connected && !loading && (
        <div className="not-connected">
          <div className="not-connected-icon">🔌</div>
          <h2>Platform Not Connected</h2>
          <p>{status.message}</p>
          <p className="help-text">
            Check your configuration in the .env file and ensure the platform is accessible.
          </p>
        </div>
      )}
    </div>
  )
}

