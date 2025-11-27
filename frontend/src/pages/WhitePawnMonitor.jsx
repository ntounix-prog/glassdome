import { useState, useEffect, useCallback } from 'react'
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
    } catch (err) {
      setError('Failed to fetch WhitePawn data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }, [])

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

  const getStatusClass = (status) => {
    return `status-${status}`
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

      <div className="whitepawn-grid">
        {/* Status Overview */}
        <div className="panel status-panel">
          <h2>📊 Status Overview</h2>
          <div className="stats-grid">
            <div className="stat">
              <span className="stat-value">{status?.total_deployments || 0}</span>
              <span className="stat-label">Total Deployments</span>
            </div>
            <div className="stat">
              <span className="stat-value">{status?.active_monitors || 0}</span>
              <span className="stat-label">Active Monitors</span>
            </div>
            <div className="stat">
              <span className="stat-value warning">{status?.unresolved_alerts || 0}</span>
              <span className="stat-label">Unresolved Alerts</span>
            </div>
            <div className="stat">
              <span className="stat-value">{reconcilerStatus?.total_checks || 0}</span>
              <span className="stat-label">Reconciler Checks</span>
            </div>
          </div>
        </div>

        {/* Reconciler Status */}
        <div className="panel reconciler-panel">
          <h2>🔄 State Reconciler</h2>
          <div className="reconciler-info">
            <div className={`reconciler-status ${reconcilerStatus?.running ? 'running' : 'stopped'}`}>
              <span className="status-dot"></span>
              {reconcilerStatus?.running ? 'Running' : 'Stopped'}
              {reconcilerStatus?.running && (
                <span className="interval">every {reconcilerStatus?.interval_seconds}s</span>
              )}
            </div>
            {reconcilerStatus?.last_run && (
              <div className="last-run">
                Last run: {new Date(reconcilerStatus.last_run).toLocaleTimeString()}
              </div>
            )}
            {reconcilerStatus?.drift_count > 0 && (
              <div className="drift-warning">
                ⚠️ {reconcilerStatus.drift_count} state drifts detected
              </div>
            )}
            {!reconcilerStatus?.running && (
              <button className="btn-start" onClick={startReconciler}>Start Reconciler</button>
            )}
          </div>
        </div>

        {/* Active Deployments */}
        <div className="panel deployments-panel">
          <h2>🛡️ Active Deployments</h2>
          <div className="deployments-list">
            {deployments.length === 0 ? (
              <div className="no-data">No WhitePawn deployments yet</div>
            ) : (
              deployments.map(dep => (
                <div 
                  key={dep.id} 
                  className={`deployment-card ${getStatusClass(dep.status)} ${selectedLab === dep.lab_id ? 'selected' : ''}`}
                  onClick={() => setSelectedLab(dep.lab_id)}
                >
                  <div className="deployment-header">
                    <span className="lab-name">{dep.lab_name || dep.lab_id}</span>
                    <span className={`status-badge ${dep.status}`}>{dep.status}</span>
                  </div>
                  <div className="deployment-stats">
                    <span>Checks: {dep.total_checks || 0}</span>
                    <span>Alerts: {dep.total_alerts || 0}</span>
                    <span>Uptime: {(dep.uptime_percent || 100).toFixed(1)}%</span>
                  </div>
                  {dep.last_heartbeat && (
                    <div className="heartbeat">
                      ♥ {new Date(dep.last_heartbeat).toLocaleTimeString()}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Connectivity Matrix */}
        <div className="panel matrix-panel">
          <h2>🔗 Connectivity Matrix</h2>
          {selectedLab ? (
            connectivityMatrix?.matrix ? (
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
                <div className="matrix-summary">
                  {connectivityMatrix.reachable_pairs}/{connectivityMatrix.total_pairs} reachable
                  {connectivityMatrix.avg_latency_ms && (
                    <span> | Avg: {connectivityMatrix.avg_latency_ms.toFixed(1)}ms</span>
                  )}
                </div>
              </div>
            ) : (
              <div className="no-data">No connectivity data for this lab yet</div>
            )
          ) : (
            <div className="no-data">Select a deployment to view connectivity</div>
          )}
        </div>

        {/* Alerts */}
        <div className="panel alerts-panel">
          <h2>🚨 Network Alerts</h2>
          <div className="alerts-list">
            {alerts.length === 0 ? (
              <div className="no-data">No unresolved alerts 🎉</div>
            ) : (
              alerts.map(alert => (
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
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default WhitePawnMonitor

