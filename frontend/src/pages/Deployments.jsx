import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/Deployments.css'

function Deployments() {
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchMissions()
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchMissions, 5000)
    return () => clearInterval(interval)
  }, [])

  const fetchMissions = async () => {
    try {
      const response = await fetch('/api/reaper/missions')
      const data = await response.json()
      // Handle both array and { missions: [] } formats
      const missionsList = data.missions || data || []
      // Filter to only show missions that have VMs deployed
      const deploymentsWithVMs = missionsList.filter(m => m.vm_created_id || m.status !== 'pending')
      setMissions(deploymentsWithVMs)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching missions:', error)
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    const colors = {
      pending: '#ffd93d',
      deploying: '#74b9ff',
      injecting: '#a29bfe',
      verifying: '#81ecec',
      completed: '#6bcf7f',
      failed: '#ff6b6b',
    }
    return colors[status] || '#888'
  }

  const getStatusIcon = (status) => {
    const icons = {
      pending: '⏳',
      deploying: '🚀',
      injecting: '💉',
      verifying: '🔍',
      completed: '✅',
      failed: '❌',
    }
    return icons[status] || '❓'
  }

  const handleViewDetails = (mission) => {
    navigate('/reaper', { state: { selectedMission: mission.mission_id } })
  }

  const handleStopMission = async (missionId) => {
    // TODO: Implement mission stop
    console.log('Stop mission:', missionId)
  }

  const handleDestroyVM = async (mission) => {
    if (!mission.vm_created_id) return
    
    if (!confirm(`Destroy VM ${mission.vm_created_id} (${mission.vm_ip_address})?\n\nThis will permanently delete the VM from Proxmox. This cannot be undone.`)) return
    
    try {
      const response = await fetch(`/api/reaper/missions/${mission.mission_id}/destroy`, {
        method: 'DELETE',
      })
      const data = await response.json()
      
      if (data.success) {
        alert(`✅ VM ${mission.vm_created_id} destroyed successfully`)
        fetchMissions() // Refresh the list
      } else {
        alert(`❌ Failed to destroy VM: ${data.error || data.message}`)
      }
    } catch (error) {
      console.error('Error destroying VM:', error)
      alert(`❌ Error: ${error.message}`)
    }
  }

  return (
    <div className="deployments-page">
      <div className="page-header">
        <h1>🚀 Deployments</h1>
        <p>Monitor Reaper missions and deployed VMs</p>
        <button 
          className="btn-primary"
          onClick={() => navigate('/reaper')}
        >
          + New Mission
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading deployments...</div>
      ) : missions.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🚀</div>
          <h2>No Active Deployments</h2>
          <p>Create a Reaper mission to deploy vulnerable VMs</p>
          <button 
            className="btn-primary"
            onClick={() => navigate('/reaper')}
          >
            Go to Reaper
          </button>
        </div>
      ) : (
        <div className="deployments-grid">
          {missions.map((mission) => (
            <div key={mission.id} className="deployment-card">
              <div className="deployment-header">
                <h3>{mission.name || `Mission ${mission.mission_id?.slice(0, 8)}`}</h3>
                <span
                  className="status-badge"
                  style={{ background: getStatusColor(mission.status) }}
                >
                  {getStatusIcon(mission.status)} {mission.status}
                </span>
              </div>

              <div className="deployment-info">
                <div className="info-row">
                  <span className="label">Platform:</span>
                  <span className="value">{mission.platform || 'proxmox'}</span>
                </div>
                {mission.vm_created_id && (
                  <div className="info-row">
                    <span className="label">VM ID:</span>
                    <span className="value vm-id">{mission.vm_created_id}</span>
                  </div>
                )}
                {mission.vm_ip_address && (
                  <div className="info-row">
                    <span className="label">IP Address:</span>
                    <span className="value ip-address">{mission.vm_ip_address}</span>
                  </div>
                )}
                <div className="info-row">
                  <span className="label">Progress:</span>
                  <span className="value">{mission.progress || 0}%</span>
                </div>
                {mission.current_step && (
                  <div className="info-row">
                    <span className="label">Current Step:</span>
                    <span className="value step">{mission.current_step}</span>
                  </div>
                )}
              </div>

              <div className="deployment-progress">
                <div
                  className="deployment-progress-fill"
                  style={{ 
                    width: `${mission.progress || 0}%`,
                    background: getStatusColor(mission.status)
                  }}
                />
              </div>

              {mission.error_message && (
                <div className="error-message">
                  ⚠️ {mission.error_message}
                </div>
              )}

              <div className="deployment-actions">
                <button 
                  className="btn-small btn-secondary"
                  onClick={() => handleViewDetails(mission)}
                >
                  View in Reaper
                </button>
                {mission.vm_created_id && mission.status === 'completed' && (
                  <button 
                    className="btn-small btn-danger"
                    onClick={() => handleDestroyVM(mission)}
                  >
                    Destroy VM
                  </button>
                )}
              </div>

              <div className="deployment-meta">
                <span className="timestamp">
                  Created: {new Date(mission.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Deployments
