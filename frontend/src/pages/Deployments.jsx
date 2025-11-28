/**
 * Deployments page component
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import '../styles/Deployments.css'

function Deployments() {
  const [missions, setMissions] = useState([])
  const [labs, setLabs] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('all') // 'all', 'labs', 'missions'
  const navigate = useNavigate()

  const fetchData = useCallback(async () => {
    try {
      // Fetch both missions and labs in parallel
      const [missionsRes, labsRes] = await Promise.all([
        fetch('/api/reaper/missions').catch(() => ({ json: () => ({ missions: [] }) })),
        fetch('/api/registry/labs').catch(() => ({ json: () => ({ labs: [] }) })),
      ])
      
      const missionsData = await missionsRes.json()
      const labsData = await labsRes.json()
      
      // Handle both array and { missions: [] } formats
      const missionsList = missionsData.missions || missionsData || []
      // Filter to only show missions that have VMs deployed
      const deploymentsWithVMs = missionsList.filter(m => m.vm_created_id || m.status !== 'pending')
      setMissions(deploymentsWithVMs)
      setLabs(labsData.labs || [])
      setLoading(false)
    } catch (error) {
      console.error('Error fetching deployments:', error)
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    // Poll for updates every 5 seconds
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [fetchData])

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

  // Get filtered items based on active tab
  const getDisplayItems = () => {
    if (activeTab === 'labs') return { labs, missions: [] }
    if (activeTab === 'missions') return { labs: [], missions }
    return { labs, missions }
  }
  
  const { labs: displayLabs, missions: displayMissions } = getDisplayItems()
  const totalCount = labs.length + missions.length

  return (
    <div className="deployments-page">
      <div className="page-header">
        <div className="header-left">
          <h1>🚀 Deployments</h1>
          <p>Labs and Reaper missions</p>
        </div>
        <div className="header-actions">
          <button 
            className="btn-secondary"
            onClick={() => navigate('/lab')}
          >
            + New Lab
          </button>
          <button 
            className="btn-primary"
            onClick={() => navigate('/reaper')}
          >
            + New Mission
          </button>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="filter-tabs">
        <button 
          className={activeTab === 'all' ? 'active' : ''} 
          onClick={() => setActiveTab('all')}
        >
          All ({totalCount})
        </button>
        <button 
          className={activeTab === 'labs' ? 'active' : ''} 
          onClick={() => setActiveTab('labs')}
        >
          🧪 Labs ({labs.length})
        </button>
        <button 
          className={activeTab === 'missions' ? 'active' : ''} 
          onClick={() => setActiveTab('missions')}
        >
          💉 Missions ({missions.length})
        </button>
      </div>

      {loading ? (
        <div className="loading">Loading deployments...</div>
      ) : totalCount === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">🚀</div>
          <h2>No Active Deployments</h2>
          <p>Create a lab or Reaper mission to get started</p>
          <div className="empty-actions">
            <button className="btn-secondary" onClick={() => navigate('/lab')}>
              Design a Lab
            </button>
            <button className="btn-primary" onClick={() => navigate('/reaper')}>
              Create a Mission
            </button>
          </div>
        </div>
      ) : (
        <div className="deployments-grid">
          {/* Labs Section */}
          {displayLabs.map((lab) => (
            <div key={lab.lab_id} className="deployment-card lab-card">
              <div className="deployment-header">
                <span className="type-badge lab">🧪 LAB</span>
                <h3>{lab.lab_id}</h3>
                <span className={`status-badge status-${lab.status}`}>
                  {lab.status}
                </span>
              </div>

              <div className="deployment-info">
                <div className="info-row">
                  <span className="label">VMs:</span>
                  <span className="value">{lab.vm_count || 0}</span>
                </div>
                {lab.network && (
                  <div className="info-row">
                    <span className="label">Network:</span>
                    <span className="value">{lab.network}</span>
                  </div>
                )}
              </div>

              <div className="deployment-actions">
                <button 
                  className="btn-small btn-secondary"
                  onClick={() => navigate('/monitor')}
                >
                  View in Monitor
                </button>
              </div>
            </div>
          ))}

          {/* Missions Section */}
          {displayMissions.map((mission) => (
            <div key={mission.id} className="deployment-card mission-card">
              <div className="deployment-header">
                <span className="type-badge mission">💉 MISSION</span>
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
