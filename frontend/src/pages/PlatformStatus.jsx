/**
 * Platformstatus page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

/**
 * Platform Status Page
 * Displays VMs and status for a specific platform
 * 
 * For Proxmox: Uses Registry API for fast updates (1-10s polling)
 * For others: Uses platform API directly
 */
import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import '../styles/PlatformStatus.css'

// Platform-specific icons and colors
// Cloud platforms are on-demand only (no auto-polling to save costs)
const PLATFORM_CONFIG = {
  proxmox: {
    icon: '🖥️',
    name: 'Proxmox VE',
    color: '#e57000',
    description: 'On-premise virtualization platform',
    onDemand: false,
    pollInterval: 5000  // 5s - uses Registry
  },
  esxi: {
    icon: '🏢',
    name: 'VMware ESXi',
    color: '#717074',
    description: 'Enterprise virtualization',
    onDemand: false,
    pollInterval: 30000  // 30s
  },
  aws: {
    icon: '☁️',
    name: 'Amazon Web Services',
    color: '#ff9900',
    description: 'AWS EC2 instances (on-demand)',
    onDemand: true,  // No auto-polling - costs money
    pollInterval: null
  },
  azure: {
    icon: '🌐',
    name: 'Microsoft Azure',
    color: '#0078d4',
    description: 'Azure Virtual Machines (on-demand)',
    onDemand: true,  // No auto-polling - costs money
    pollInterval: null
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
  const [selectedServer, setSelectedServer] = useState('all') // 'all' or instance_id like '01', '02'

  const config = PLATFORM_CONFIG[platform] || PLATFORM_CONFIG.proxmox

  // Use Registry for Proxmox (fast), platform API for others
  const fetchStatus = useCallback(async () => {
    try {
      setLoading(prev => prev === true ? true : false) // Don't flash loading on refresh
      
      if (platform === 'proxmox') {
        // Use Registry API for fast updates
        const response = await fetch('/api/registry/resources?platform=proxmox')
        const data = await response.json()
        
        if (!response.ok) {
          throw new Error('Failed to fetch from registry')
        }
        
        // Transform Registry data to match expected format
        const vms = (data.resources || []).map(r => ({
          vmid: parseInt(r.platform_id),
          name: r.name,
          status: r.state,
          node: `${r.config?.node || 'pve'} (${r.platform_instance})`,
          cpu: 0, // Registry doesn't track real-time CPU
          memory: r.config?.maxmem,
          disk: r.config?.maxdisk,
          uptime: r.config?.uptime,
          template: r.resource_type === 'template',
          ip_address: r.config?.ip_address,
        }))
        
        // Get unique nodes from VMs
        const nodeSet = new Map()
        vms.forEach(vm => {
          const nodeMatch = vm.node?.match(/^(\w+)\s*\((\d+)\)/)
          if (nodeMatch) {
            const [, nodeName, instanceId] = nodeMatch
            if (!nodeSet.has(instanceId)) {
              nodeSet.set(instanceId, {
                node: nodeName,
                instance_id: instanceId,
                status: 'online',
                host: `192.168.215.${instanceId === '01' ? '78' : '77'}`,
              })
            }
          }
        })
        
        // Calculate summary
        const running = vms.filter(v => v.status === 'running').length
        const stopped = vms.filter(v => v.status === 'stopped').length
        const templates = vms.filter(v => v.template).length
        
        setStatus({
          connected: true,
          vms,
          nodes: Array.from(nodeSet.values()),
          summary: {
            total: vms.length,
            running,
            stopped,
            templates,
            instances: Array.from(nodeSet.entries()).map(([id, node]) => ({
              instance_id: id,
              vms: vms.filter(v => v.node?.includes(`(${id})`)).length,
            })),
          },
        })
        setError(null)
      } else {
        // Use platform API for non-Proxmox
        let url
        if (platform === 'aws') {
          url = '/api/platforms/aws/all-regions'
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
      }
    } catch (err) {
      console.error('Error fetching platform status:', err)
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [platform, instanceId])

  useEffect(() => {
    fetchStatus()
    
    // Cloud platforms (AWS, Azure) are on-demand only - no auto-polling to save costs
    // Proxmox uses Registry (fast) - poll every 5 seconds
    // Others (ESXi) use platform API - poll every 30 seconds
    const pollInterval = config.pollInterval
    if (pollInterval && !config.onDemand) {
      const interval = setInterval(fetchStatus, pollInterval)
      return () => clearInterval(interval)
    }
  }, [platform, instanceId, fetchStatus, config.pollInterval, config.onDemand])

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

  // Filter VMs by server, status, and search
  const filteredVMs = status?.vms?.filter(vm => {
    // Filter by selected server (for Proxmox)
    if (platform === 'proxmox' && selectedServer !== 'all') {
      // node format is "pve01 (01)" - extract instance ID
      const match = vm.node?.match(/\((\d+)\)/)
      const vmInstance = match ? match[1] : null
      if (vmInstance !== selectedServer) return false
    }
    
    // Filter by status
    if (filter === 'running' && vm.status !== 'running' && vm.status !== 'poweredOn') return false
    if (filter === 'stopped' && vm.status !== 'stopped' && vm.status !== 'poweredOff') return false
    if (filter === 'templates' && !vm.template) return false
    
    // Filter by search
    if (search && !vm.name.toLowerCase().includes(search.toLowerCase())) return false
    
    return true
  }) || []
  
  // Get selected server info for display
  const selectedServerInfo = selectedServer !== 'all' 
    ? status?.nodes?.find(n => n.instance_id === selectedServer) 
    : null

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

          {/* Proxmox Servers Section - clickable cards to filter VMs */}
          {status.nodes && status.nodes.length > 0 && (
            <div className="nodes-section">
              <h3>Proxmox Servers <span className="select-hint">(click to filter)</span></h3>
              <div className="nodes-grid">
                {/* "All Servers" option */}
                <div 
                  className={`node-card selectable ${selectedServer === 'all' ? 'selected' : ''}`}
                  onClick={() => setSelectedServer('all')}
                >
                  <div className="node-name">📊 All Servers</div>
                  <div className="node-status">View combined</div>
                  <div className="node-stat vm-count">{status.summary?.total || 0} VMs total</div>
                </div>
                
                {status.nodes.map((node, idx) => {
                  // Find matching instance info for VM count
                  const instanceInfo = status.summary?.instances?.find(
                    i => i.instance_id === node.instance_id
                  )
                  const isSelected = selectedServer === node.instance_id
                  return (
                    <div 
                      key={idx} 
                      className={`node-card selectable ${node.status || 'online'} ${isSelected ? 'selected' : ''}`}
                      onClick={() => setSelectedServer(node.instance_id)}
                    >
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
            
            {config.onDemand && (
              <span className="on-demand-note">
                💰 On-demand only (no auto-refresh to save cloud costs)
              </span>
            )}
          </div>

          {/* VM Table with server header */}
          <div className="vm-table-container">
            {platform === 'proxmox' && (
              <div className="vm-table-header">
                {selectedServer === 'all' ? (
                  <h3>📊 All Virtual Machines</h3>
                ) : (
                  <h3>
                    🖥️ {selectedServerInfo?.node || `Server ${selectedServer}`}
                    {selectedServerInfo?.host && (
                      <span className="server-host"> ({selectedServerInfo.host})</span>
                    )}
                  </h3>
                )}
                <span className="vm-count-badge">{filteredVMs.length} VMs</span>
              </div>
            )}
            
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
                  {platform === 'proxmox' && selectedServer === 'all' && <th>Server</th>}
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredVMs.length === 0 ? (
                  <tr>
                    <td colSpan={platform === 'proxmox' && selectedServer === 'all' ? 9 : 8} className="no-vms">
                      {loading ? 'Loading...' : 'No VMs found on this server'}
                    </td>
                  </tr>
                ) : (
                  filteredVMs.map((vm) => (
                    <tr key={`${vm.vmid}-${vm.node}`} className={vm.template ? 'template-row' : ''}>
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
                      {platform === 'proxmox' && selectedServer === 'all' && (
                        <td className="server-cell">{vm.node?.split(' ')[0]}</td>
                      )}
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

