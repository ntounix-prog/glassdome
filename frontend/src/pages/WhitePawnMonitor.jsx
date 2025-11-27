import { useState, useEffect, useCallback } from 'react'
import NetworkMap from '../components/NetworkMap'
import '../styles/WhitePawnMonitor.css'

function WhitePawnMonitor() {
  const [status, setStatus] = useState(null)
  const [deployments, setDeployments] = useState([])
  const [alerts, setAlerts] = useState([])
  const [reconcilerStatus, setReconcilerStatus] = useState(null)
  const [selectedLab, setSelectedLab] = useState(null)
  const [connectivityMatrix, setConnectivityMatrix] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState('map') // 'map', 'matrix', 'alerts'

  const fetchData = useCallback(async () => {
    try {
      // Fetch all data in parallel
      const [statusRes, deploymentsRes, alertsRes, reconcilerRes] = await Promise.all([
        fetch('/api/whitepawn/status'),
        fetch('/api/whitepawn/deployments'),
        fetch('/api/whitepawn/alerts?limit=50'),
        fetch('/api/whitepawn/reconciler/status')
      ])

      const statusData = await statusRes.json()
      const deploymentsData = await deploymentsRes.json()
      const alertsData = await alertsRes.json()
      const reconcilerData = await reconcilerRes.json()

      setStatus(statusData)
      setDeployments(deploymentsData.deployments || [])
      setAlerts(alertsData.alerts || [])
      setReconcilerStatus(reconcilerData)
      setError(null)
      
      // Auto-select first deployment if none selected
      if (!selectedLab && deploymentsData.deployments?.length > 0) {
        setSelectedLab(deploymentsData.deployments[0].lab_id)
      }
    } catch (err) {
      setError('Failed to fetch WhitePawn data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [selectedLab])

  // Fetch data on mount and every 10 seconds
  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Fetch connectivity matrix when lab is selected
  useEffect(() => {
    if (selectedLab) {
      fetch(`/api/whitepawn/labs/${selectedLab}/matrix`)
        .then(res => res.json())
        .then(data => setConnectivityMatrix(data))
        .catch(err => console.error('Failed to fetch matrix:', err))
    }
  }, [selectedLab])

  const startOrchestrator = async () => {
    try {
      await fetch('/api/whitepawn/start', { method: 'POST' })
      fetchData()
    } catch (err) {
      console.error('Failed to start orchestrator:', err)
    }
  }

  const stopOrchestrator = async () => {
    try {
      await fetch('/api/whitepawn/stop', { method: 'POST' })
      fetchData()
    } catch (err) {
      console.error('Failed to stop orchestrator:', err)
    }
  }

  const startReconciler = async () => {
    try {
      await fetch('/api/whitepawn/reconciler/start', { method: 'POST' })
      fetchData()
    } catch (err) {
      console.error('Failed to start reconciler:', err)
    }
  }

  const acknowledgeAlert = async (alertId) => {
    try {
      await fetch(`/api/whitepawn/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user: 'admin' })
      })
      fetchData()
    } catch (err) {
      console.error('Failed to acknowledge alert:', err)
    }
  }

  const resolveAlert = async (alertId) => {
    try {
      await fetch(`/api/whitepawn/alerts/${alertId}/resolve`, { method: 'POST' })
      fetchData()
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    }
  }

  const getSeverityClass = (severity) => {
    return `severity-${severity}`
  }

  const getSelectedDeployment = () => {
    return deployments.find(d => d.lab_id === selectedLab)
  }

  const getTargetsFromMatrix = () => {
    if (!connectivityMatrix?.matrix) return []
    return Object.entries(connectivityMatrix.matrix).map(([ip, data]) => ({
      ip,
      name: data.name,
      status: data.reachable ? 'online' : 'offline',
      latency: data.latency_ms
    }))
  }

  if (loading) {
    return (
      <div className="whitepawn-container">
        <div className="loading">Loading WhitePawn status...</div>
      </div>
    )
  }

  return (
    <div className="whitepawn-container">
      <header className="whitepawn-header">
        <div className="header-left">
          <h1>♙ WhitePawn</h1>
          <span className="subtitle">Continuous Network Monitoring</span>
        </div>
        
        {/* Network Selector */}
        <div className="network-selector">
          <label>Monitoring:</label>
          <select 
            value={selectedLab || ''} 
            onChange={(e) => setSelectedLab(e.target.value)}
            disabled={deployments.length === 0}
          >
            {deployments.length === 0 ? (
              <option value="">No labs deployed</option>
            ) : (
              deployments.map(dep => (
                <option key={dep.lab_id} value={dep.lab_id}>
                  {dep.lab_name || dep.lab_id} 
                  {dep.status === 'active' ? ' ● Active' : ''}
                </option>
              ))
            )}
          </select>
        </div>
        
        <div className="header-right">
          <div className={`orchestrator-status ${status?.running ? 'running' : 'stopped'}`}>
            <span className="status-dot"></span>
            {status?.running ? 'Active' : 'Stopped'}
          </div>
          {status?.running ? (
            <button className="btn-stop" onClick={stopOrchestrator}>Stop</button>
          ) : (
            <button className="btn-start" onClick={startOrchestrator}>Start</button>
          )}
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      {/* Main Content Area */}
      <div className="whitepawn-main">
        {/* Left Sidebar - Stats */}
        <div className="stats-sidebar">
          <div className="stat-card">
            <span className="stat-value">{status?.total_deployments || 0}</span>
            <span className="stat-label">Deployments</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{status?.active_monitors || 0}</span>
            <span className="stat-label">Active</span>
          </div>
          <div className="stat-card warning">
            <span className="stat-value">{status?.unresolved_alerts || 0}</span>
            <span className="stat-label">Alerts</span>
          </div>
          
          {/* Reconciler Status */}
          <div className="reconciler-card">
            <div className="reconciler-header">
              <span>🔄 Reconciler</span>
              <span className={`status-dot ${reconcilerStatus?.running ? 'running' : 'stopped'}`}></span>
            </div>
            {reconcilerStatus?.running ? (
              <span className="reconciler-info">Every {reconcilerStatus?.interval_seconds}s</span>
            ) : (
              <button className="btn-mini" onClick={startReconciler}>Start</button>
            )}
            {reconcilerStatus?.drift_count > 0 && (
              <span className="drift-badge">⚠️ {reconcilerStatus.drift_count} drifts</span>
            )}
          </div>
          
          {/* Selected Lab Info */}
          {selectedLab && getSelectedDeployment() && (
            <div className="selected-lab-card">
              <h4>{getSelectedDeployment().lab_name || selectedLab}</h4>
              <div className="lab-stats">
                <span>Checks: {getSelectedDeployment().total_checks || 0}</span>
                <span>Alerts: {getSelectedDeployment().total_alerts || 0}</span>
                <span>Uptime: {(getSelectedDeployment().uptime_percent || 100).toFixed(1)}%</span>
              </div>
              {getSelectedDeployment().last_heartbeat && (
                <div className="heartbeat">
                  ♥ {new Date(getSelectedDeployment().last_heartbeat).toLocaleTimeString()}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Center - Network Map / Content */}
        <div className="content-area">
          {/* Tab Navigation */}
          <div className="tab-nav">
            <button 
              className={activeTab === 'map' ? 'active' : ''} 
              onClick={() => setActiveTab('map')}
            >
              🗺️ Network Map
            </button>
            <button 
              className={activeTab === 'matrix' ? 'active' : ''} 
              onClick={() => setActiveTab('matrix')}
            >
              🔗 Connectivity
            </button>
            <button 
              className={activeTab === 'alerts' ? 'active' : ''} 
              onClick={() => setActiveTab('alerts')}
            >
              🚨 Alerts {alerts.length > 0 && <span className="badge">{alerts.length}</span>}
            </button>
          </div>

          {/* Tab Content */}
          <div className="tab-content">
            {activeTab === 'map' && (
              <div className="map-container">
                <NetworkMap 
                  matrix={connectivityMatrix?.matrix}
                  targets={getTargetsFromMatrix()}
                  labId={selectedLab}
                />
              </div>
            )}

            {activeTab === 'matrix' && (
              <div className="matrix-tab">
                {connectivityMatrix?.matrix ? (
                  <>
                    <div className="matrix-grid">
                      {Object.entries(connectivityMatrix.matrix).map(([ip, data]) => (
                        <div key={ip} className={`matrix-cell ${data.reachable ? 'reachable' : 'unreachable'}`}>
                          <span className="cell-ip">{ip}</span>
                          <span className="cell-name">{data.name}</span>
                          <span className="cell-status">
                            {data.reachable ? (
                              <>✓ {data.latency_ms?.toFixed(1)}ms</>
                            ) : (
                              '✗ Unreachable'
                            )}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="matrix-summary">
                      {connectivityMatrix.reachable_pairs}/{connectivityMatrix.total_pairs} reachable
                      {connectivityMatrix.avg_latency_ms && (
                        <span> | Avg: {connectivityMatrix.avg_latency_ms.toFixed(1)}ms</span>
                      )}
                      {connectivityMatrix.max_latency_ms && (
                        <span> | Max: {connectivityMatrix.max_latency_ms.toFixed(1)}ms</span>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="no-data">
                    {selectedLab ? 'No connectivity data yet' : 'Select a lab to view connectivity'}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'alerts' && (
              <div className="alerts-tab">
                {alerts.length === 0 ? (
                  <div className="no-data success">
                    🎉 No unresolved alerts - All systems operational
                  </div>
                ) : (
                  <div className="alerts-list">
                    {alerts.map(alert => (
                      <div key={alert.id} className={`alert-card ${getSeverityClass(alert.severity)}`}>
                        <div className="alert-header">
                          <span className={`severity-badge ${alert.severity}`}>
                            {alert.severity.toUpperCase()}
                          </span>
                          <span className="alert-type">{alert.alert_type}</span>
                          <span className="alert-time">
                            {new Date(alert.created_at).toLocaleTimeString()}
                          </span>
                        </div>
                        <div className="alert-title">{alert.title}</div>
                        <div className="alert-message">{alert.message}</div>
                        {alert.target_ip && (
                          <div className="alert-target">
                            Target: {alert.target_ip} 
                            {alert.target_vm_name && ` (${alert.target_vm_name})`}
                          </div>
                        )}
                        {alert.latency_ms && (
                          <div className="alert-latency">Latency: {alert.latency_ms.toFixed(1)}ms</div>
                        )}
                        <div className="alert-actions">
                          {!alert.acknowledged && (
                            <button onClick={() => acknowledgeAlert(alert.id)}>Acknowledge</button>
                          )}
                          <button onClick={() => resolveAlert(alert.id)}>Resolve</button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default WhitePawnMonitor
