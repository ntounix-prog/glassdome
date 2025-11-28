/**
 * Labmonitor page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

/**
 * Lab Monitor Page
 * 
 * Real-time monitoring of lab resources using the central Registry.
 * Shows:
 * - All labs with their VMs and health status
 * - Real-time event stream
 * - Drift detection and auto-fix
 * - Resource state and IP addresses
 */

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  useRegistryStatus, 
  useLabs, 
  useLabSnapshot, 
  useResources,
  useDrift,
  useRegistryEvents,
  useReconcile 
} from '../hooks/useRegistry'
import '../styles/LabMonitor.css'

// Format bytes to human readable
function formatBytes(bytes) {
  if (!bytes) return '-'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// Format uptime
function formatUptime(seconds) {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)
  
  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

// State icon/color mapping
const STATE_CONFIG = {
  running: { icon: '🟢', color: '#22c55e', label: 'Running' },
  stopped: { icon: '🔴', color: '#ef4444', label: 'Stopped' },
  paused: { icon: '🟡', color: '#eab308', label: 'Paused' },
  unknown: { icon: '⚪', color: '#6b7280', label: 'Unknown' },
  error: { icon: '🔴', color: '#dc2626', label: 'Error' },
}

// Drift type labels
const DRIFT_LABELS = {
  state: 'State Mismatch',
  name: 'Name Mismatch',
  config: 'Config Drift',
  missing: 'Missing Resource',
  extra: 'Unexpected Resource',
  network: 'Network Mismatch',
  ip: 'IP Mismatch',
}

function LabCard({ lab, selected, onClick }) {
  const healthColor = lab.healthy ? '#22c55e' : '#ef4444'
  
  return (
    <div 
      className={`lab-card ${selected ? 'selected' : ''}`}
      onClick={onClick}
      style={{ borderLeftColor: healthColor }}
    >
      <div className="lab-card-header">
        <h3>{lab.name || lab.lab_id}</h3>
        <span className={`health-badge ${lab.healthy ? 'healthy' : 'unhealthy'}`}>
          {lab.healthy ? '✓ Healthy' : '⚠ Drift'}
        </span>
      </div>
      <div className="lab-card-stats">
        <div className="stat">
          <span className="stat-value">{lab.running_vms}/{lab.total_vms}</span>
          <span className="stat-label">VMs Running</span>
        </div>
        {lab.drift_count > 0 && (
          <div className="stat warning">
            <span className="stat-value">{lab.drift_count}</span>
            <span className="stat-label">Drifts</span>
          </div>
        )}
      </div>
    </div>
  )
}

function VMRow({ vm }) {
  const stateConfig = STATE_CONFIG[vm.state] || STATE_CONFIG.unknown
  
  return (
    <tr className={`vm-row ${vm.state}`}>
      <td className="vm-id">{vm.platform_id}</td>
      <td className="vm-name">
        {vm.config?.role === 'gateway' && <span className="role-badge gateway">GW</span>}
        {vm.name}
      </td>
      <td>
        <span className="state-badge" style={{ color: stateConfig.color }}>
          {stateConfig.icon} {stateConfig.label}
        </span>
      </td>
      <td className="vm-ip">
        {vm.config?.ip_address || '-'}
      </td>
      <td>{vm.config?.node || '-'}</td>
      <td>{formatUptime(vm.config?.uptime)}</td>
      <td>{formatBytes(vm.config?.maxmem)}</td>
    </tr>
  )
}

function DriftAlert({ drift, onResolve }) {
  const label = DRIFT_LABELS[drift.drift_type] || drift.drift_type
  
  return (
    <div className={`drift-alert severity-${drift.severity}`}>
      <div className="drift-header">
        <span className="drift-type">{label}</span>
        {drift.auto_fix && <span className="auto-fix-badge">Auto-fix</span>}
      </div>
      <div className="drift-detail">
        <span className="expected">Expected: {drift.expected}</span>
        <span className="actual">Actual: {drift.actual}</span>
      </div>
      {!drift.auto_fix && (
        <button className="resolve-btn" onClick={() => onResolve(drift.resource_id)}>
          Resolve
        </button>
      )}
    </div>
  )
}

function EventItem({ event }) {
  const time = new Date(event.timestamp).toLocaleTimeString()
  
  const eventIcons = {
    created: '➕',
    updated: '🔄',
    deleted: '🗑️',
    state_changed: '⚡',
    drift_detected: '⚠️',
    drift_resolved: '✅',
    reconcile_start: '🔧',
    reconcile_complete: '✓',
    reconcile_failed: '❌',
    agent_heartbeat: '💓',
  }
  
  return (
    <div className={`event-item ${event.event_type}`}>
      <span className="event-icon">{eventIcons[event.event_type] || '•'}</span>
      <span className="event-type">{event.event_type}</span>
      <span className="event-resource">{event.resource_id?.split(':').pop()}</span>
      <span className="event-time">{time}</span>
    </div>
  )
}

export default function LabMonitor() {
  const navigate = useNavigate()
  const [selectedLabId, setSelectedLabId] = useState(null)
  const [showEvents, setShowEvents] = useState(false)
  
  // Registry data
  const { status, loading: statusLoading, error: statusError } = useRegistryStatus()
  const { labs, loading: labsLoading } = useLabs()
  const { snapshot, loading: snapshotLoading } = useLabSnapshot(selectedLabId)
  const { resources } = useResources({ labId: selectedLabId })
  const { drifts, resolveDrift } = useDrift(selectedLabId)
  const { events, connected } = useRegistryEvents(selectedLabId)
  const { reconcileLab, loading: reconciling } = useReconcile()

  // Auto-select first lab
  if (!selectedLabId && labs.length > 0) {
    setSelectedLabId(labs[0].lab_id)
  }

  const handleReconcile = async () => {
    if (!selectedLabId) return
    try {
      await reconcileLab(selectedLabId)
    } catch (err) {
      console.error('Reconcile failed:', err)
    }
  }

  if (statusError) {
    return (
      <div className="lab-monitor error-state">
        <div className="error-banner">
          <span>⚠️ Registry not available: {statusError}</span>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="lab-monitor">
      {/* Header */}
      <header className="monitor-header">
        <div className="header-left">
          <button className="back-btn" onClick={() => navigate('/')}>← Back</button>
          <h1>🔬 Lab Monitor</h1>
          <span className="subtitle">Real-time Lab State</span>
        </div>
        
        <div className="header-center">
          <div className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {connected ? 'Live' : 'Connecting...'}
          </div>
        </div>
        
        <div className="header-right">
          <button 
            className="events-toggle"
            onClick={() => setShowEvents(!showEvents)}
          >
            📡 Events {events.length > 0 && <span className="badge">{events.length}</span>}
          </button>
        </div>
      </header>

      {/* Registry Stats Bar */}
      <div className="stats-bar">
        <div className="stat-item">
          <span className="stat-value">{status?.total_resources || 0}</span>
          <span className="stat-label">Resources</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{status?.lab_count || 0}</span>
          <span className="stat-label">Labs</span>
        </div>
        <div className="stat-item">
          <span className="stat-value">{status?.agents || 0}</span>
          <span className="stat-label">Agents</span>
        </div>
        <div className={`stat-item ${status?.active_drifts > 0 ? 'warning' : ''}`}>
          <span className="stat-value">{status?.active_drifts || 0}</span>
          <span className="stat-label">Drifts</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="monitor-content">
        {/* Left Sidebar - Lab List */}
        <aside className="labs-sidebar">
          <h2>Labs</h2>
          {labsLoading ? (
            <div className="loading">Loading labs...</div>
          ) : labs.length === 0 ? (
            <div className="empty-state">
              <p>No labs deployed</p>
              <button onClick={() => navigate('/lab')}>Create Lab</button>
            </div>
          ) : (
            <div className="labs-list">
              {labs.map(lab => (
                <LabCard
                  key={lab.lab_id}
                  lab={lab}
                  selected={selectedLabId === lab.lab_id}
                  onClick={() => setSelectedLabId(lab.lab_id)}
                />
              ))}
            </div>
          )}
        </aside>

        {/* Main Area - Selected Lab Detail */}
        <main className="lab-detail">
          {!selectedLabId ? (
            <div className="no-selection">
              <p>Select a lab to view details</p>
            </div>
          ) : snapshotLoading ? (
            <div className="loading">Loading lab snapshot...</div>
          ) : !snapshot ? (
            <div className="no-data">Lab not found in registry</div>
          ) : (
            <>
              {/* Lab Header */}
              <div className="lab-header">
                <div className="lab-title">
                  <h2>{snapshot.name || selectedLabId}</h2>
                  <span className={`health-indicator ${snapshot.healthy ? 'healthy' : 'unhealthy'}`}>
                    {snapshot.healthy ? '✓ All Systems Operational' : '⚠ Drift Detected'}
                  </span>
                </div>
                <div className="lab-actions">
                  <button 
                    className="reconcile-btn"
                    onClick={handleReconcile}
                    disabled={reconciling}
                  >
                    {reconciling ? '🔄 Reconciling...' : '🔧 Reconcile'}
                  </button>
                </div>
              </div>

              {/* Drift Alerts */}
              {drifts.length > 0 && (
                <div className="drift-section">
                  <h3>⚠️ Active Drifts</h3>
                  <div className="drift-list">
                    {drifts.map((drift, idx) => (
                      <DriftAlert 
                        key={idx} 
                        drift={drift} 
                        onResolve={resolveDrift}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* VM Table */}
              <div className="vms-section">
                <h3>Virtual Machines ({snapshot.total_vms})</h3>
                <table className="vm-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Name</th>
                      <th>State</th>
                      <th>IP Address</th>
                      <th>Node</th>
                      <th>Uptime</th>
                      <th>Memory</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.vms?.length === 0 ? (
                      <tr>
                        <td colSpan="7" className="no-vms">No VMs in this lab</td>
                      </tr>
                    ) : (
                      snapshot.vms?.map(vm => (
                        <VMRow key={vm.id} vm={vm} />
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Network Info */}
              {snapshot.networks?.length > 0 && (
                <div className="networks-section">
                  <h3>Networks</h3>
                  <div className="networks-grid">
                    {snapshot.networks.map(net => (
                      <div key={net.id} className="network-card">
                        <span className="network-name">{net.name}</span>
                        <span className="network-vlan">VLAN {net.config?.vlan_id || '?'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </main>

        {/* Right Sidebar - Events (togglable) */}
        {showEvents && (
          <aside className="events-sidebar">
            <div className="events-header">
              <h3>Live Events</h3>
              <button className="close-btn" onClick={() => setShowEvents(false)}>×</button>
            </div>
            <div className="events-list">
              {events.length === 0 ? (
                <div className="no-events">No recent events</div>
              ) : (
                events.slice(0, 50).map((event, idx) => (
                  <EventItem key={idx} event={event} />
                ))
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  )
}

