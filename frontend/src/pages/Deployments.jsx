import { useState, useEffect } from 'react'
import '../styles/Deployments.css'

function Deployments() {
  const [deployments, setDeployments] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDeployments()
  }, [])

  const fetchDeployments = async () => {
    try {
      const response = await fetch('/api/deployments')
      const data = await response.json()
      setDeployments(data.deployments || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching deployments:', error)
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: '#ffd93d',
      in_progress: '#74b9ff',
      completed: '#6bcf7f',
      failed: '#ff6b6b',
    }
    return colors[status] || '#888'
  }

  return (
    <div className="deployments-page">
      <div className="page-header">
        <h1>Deployments</h1>
        <p>Monitor and manage your active deployments</p>
      </div>

      {loading ? (
        <div className="loading">Loading deployments...</div>
      ) : deployments.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🚀</div>
          <h2>No Active Deployments</h2>
          <p>Create and deploy a lab to see it here</p>
        </div>
      ) : (
        <div className="deployments-grid">
          {deployments.map((deployment) => (
            <div key={deployment.id} className="deployment-card">
              <div className="deployment-header">
                <h3>{deployment.name}</h3>
                <span
                  className="status-badge"
                  style={{ background: getStatusColor(deployment.status) }}
                >
                  {deployment.status}
                </span>
              </div>

              <div className="deployment-info">
                <div className="info-row">
                  <span className="label">Platform:</span>
                  <span className="value">{deployment.platform || 'Proxmox'}</span>
                </div>
                <div className="info-row">
                  <span className="label">Resources:</span>
                  <span className="value">{deployment.resource_count || 0}</span>
                </div>
                <div className="info-row">
                  <span className="label">Progress:</span>
                  <span className="value">{deployment.progress || 0}%</span>
                </div>
              </div>

              <div className="progress-bar">
                <div
                  className="progress-fill"
                  style={{ width: `${deployment.progress || 0}%` }}
                />
              </div>

              <div className="deployment-actions">
                <button className="btn-small btn-secondary">View Details</button>
                <button className="btn-small btn-danger">Stop</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Deployments

