/**
 * Whiteknightdesign page component
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useState, useEffect } from 'react'
import '../styles/WhiteKnightDesign.css'

// Fetch deployed missions for target selection
const useDeployedMissions = () => {
  const [missions, setMissions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMissions = async () => {
      try {
        const response = await fetch('/api/v1/reaper/missions')
        if (response.ok) {
          const data = await response.json()
          // Show ALL missions that have a VM IP - the VM may still be running
          // even if the mission is marked completed
          const deployedMissions = (data.missions || []).filter(
            m => m.vm_ip_address  // Any mission with a VM IP is testable
          )
          setMissions(deployedMissions)
        }
      } catch (error) {
        console.error('Failed to fetch missions:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchMissions()
    // Refresh every 10 seconds
    const interval = setInterval(fetchMissions, 10000)
    return () => clearInterval(interval)
  }, [])

  return { missions, loading }
}

// Validation History Component
function ValidationHistory() {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedMission, setSelectedMission] = useState(null)
  const [missionValidations, setMissionValidations] = useState([])

  useEffect(() => {
    fetchHistory()
  }, [])

  const fetchHistory = async () => {
    try {
      const response = await fetch('/api/v1/reaper/history?days=14')
      if (response.ok) {
        const data = await response.json()
        // Only show missions with validations
        const withValidations = data.history.filter(m => m.validation_count > 0)
        setHistory(withValidations)
      }
    } catch (error) {
      console.error('Failed to fetch history:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchMissionValidations = async (missionId) => {
    try {
      const response = await fetch(`/api/v1/reaper/missions/${missionId}/validations`)
      if (response.ok) {
        const data = await response.json()
        setMissionValidations(data.validations)
        setSelectedMission(missionId)
      }
    } catch (error) {
      console.error('Failed to fetch validations:', error)
    }
  }

  if (loading) {
    return <div className="history-loading">Loading history...</div>
  }

  return (
    <div className="history-view">
      <div className="history-header">
        <h2>Validation History</h2>
        <p>Last 14 days • {history.length} missions with validations</p>
      </div>

      {history.length === 0 ? (
        <div className="history-empty">
          <span className="empty-icon">📭</span>
          <p>No validation history yet</p>
          <p className="empty-hint">Run validations from the Test Runner tab</p>
        </div>
      ) : (
        <div className="history-content">
          <div className="history-missions">
            {history.map(mission => (
              <div 
                key={mission.mission_id} 
                className={`history-mission-card ${selectedMission === mission.mission_id ? 'selected' : ''}`}
                onClick={() => fetchMissionValidations(mission.mission_id)}
              >
                <div className="mission-header">
                  <span className="mission-name">{mission.name}</span>
                  <span className="mission-date">
                    {new Date(mission.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="mission-target">
                  <span className="target-ip">{mission.vm_ip_address}</span>
                </div>
                <div className="mission-stats">
                  <span className="stat success">✓ {mission.validation_summary?.success || 0}</span>
                  <span className="stat failed">✗ {mission.validation_summary?.failed || 0}</span>
                  <span className="stat total">{mission.validation_count} tests</span>
                </div>
              </div>
            ))}
          </div>

          {selectedMission && missionValidations.length > 0 && (
            <div className="history-details">
              <h3>Validation Results</h3>
              <div className="validation-list">
                {missionValidations.map((v, idx) => (
                  <div key={idx} className={`validation-item ${v.status}`}>
                    <div className="validation-header">
                      <span className="validation-test">{v.test_name}</span>
                      <span className={`validation-status ${v.status}`}>
                        {v.status === 'success' ? '✓ FOUND' : v.status === 'failed' ? '✗ NOT FOUND' : '⚠ ERROR'}
                      </span>
                    </div>
                    <p className="validation-message">{v.message}</p>
                    {v.evidence && (
                      <pre className="validation-evidence">{v.evidence}</pre>
                    )}
                    <div className="validation-meta">
                      <span>{new Date(v.validated_at).toLocaleString()}</span>
                      {v.duration_ms && <span>{v.duration_ms}ms</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Tool categories and their items
const TOOL_CATEGORIES = {
  'SSH & Remote Access': [
    { name: 'sshpass', description: 'Non-interactive SSH password auth', status: 'ready' },
    { name: 'ssh', description: 'OpenSSH client', status: 'ready' },
    { name: 'hydra', description: 'Brute-force login cracker', status: 'ready' },
  ],
  'Network Analysis': [
    { name: 'nmap', description: 'Port scanner & service detection', status: 'ready' },
    { name: 'netcat', description: 'Network utility', status: 'ready' },
    { name: 'smbclient', description: 'SMB/CIFS client', status: 'ready' },
    { name: 'snmpwalk', description: 'SNMP enumeration', status: 'ready' },
  ],
  'Database Clients': [
    { name: 'mysql', description: 'MySQL client', status: 'ready' },
    { name: 'psql', description: 'PostgreSQL client', status: 'ready' },
    { name: 'redis-cli', description: 'Redis client', status: 'ready' },
  ],
  'Web Testing': [
    { name: 'curl', description: 'HTTP client', status: 'ready' },
    { name: 'wget', description: 'HTTP downloader', status: 'ready' },
  ],
  'Python Libraries': [
    { name: 'paramiko', description: 'SSH2 protocol library', status: 'ready' },
    { name: 'python-nmap', description: 'Nmap automation', status: 'ready' },
    { name: 'impacket', description: 'Network protocol toolkit', status: 'ready' },
  ],
}

// Validation abilities
const VALIDATION_ABILITIES = {
  'Connectivity': [
    { id: 'connectivity', name: 'Connectivity Check', description: 'Verify target is reachable (run first!)', tool: 'ping', severity: 'info' },
    { id: 'port_scan', name: 'Port Scan', description: 'Discover open ports', tool: 'nmap', severity: 'info' },
  ],
  'Credential Testing': [
    { id: 'ssh_creds', name: 'SSH Weak Creds', description: 'Test common weak passwords (vulnuser:password123)', tool: 'sshpass', severity: 'high' },
    { id: 'ftp_creds', name: 'FTP Login', description: 'Test FTP credentials', tool: 'hydra', severity: 'high' },
    { id: 'mysql_creds', name: 'MySQL Login', description: 'Test MySQL access', tool: 'mysql', severity: 'high' },
    { id: 'smb_creds', name: 'SMB Login', description: 'Test SMB shares', tool: 'smbclient', severity: 'high' },
    { id: 'postgres_creds', name: 'PostgreSQL Login', description: 'Test PostgreSQL access', tool: 'psql', severity: 'high' },
    { id: 'redis_creds', name: 'Redis Auth', description: 'Test Redis access', tool: 'redis-cli', severity: 'medium' },
  ],
  'Network Services': [
    { id: 'smb_anon', name: 'SMB Anonymous', description: 'Test anonymous SMB access', tool: 'smbclient', severity: 'high' },
    { id: 'snmp_public', name: 'SNMP Public', description: 'Test SNMP community strings', tool: 'snmpwalk', severity: 'medium' },
    { id: 'redis_open', name: 'Redis Open', description: 'Test unauthenticated Redis', tool: 'redis-cli', severity: 'critical' },
  ],
  'Web Vulnerabilities': [
    { id: 'http_methods', name: 'HTTP Methods', description: 'Check allowed methods', tool: 'curl', severity: 'low' },
    { id: 'dir_listing', name: 'Directory Listing', description: 'Check for exposed directories', tool: 'curl', severity: 'medium' },
    { id: 'security_headers', name: 'Security Headers', description: 'Check missing headers', tool: 'curl', severity: 'low' },
  ],
  'Privilege Escalation': [
    { id: 'sudo_nopass', name: 'Sudo NOPASSWD', description: 'Check sudo without password', tool: 'ssh', severity: 'critical' },
    { id: 'suid_binaries', name: 'SUID Binaries', description: 'Find SUID executables', tool: 'ssh', severity: 'high' },
    { id: 'docker_group', name: 'Docker Group', description: 'Check docker group membership', tool: 'ssh', severity: 'critical' },
  ],
}

function WhiteKnightDesign() {
  const [activeTab, setActiveTab] = useState('tools')
  const [containerStatus, setContainerStatus] = useState('unknown')
  const [testResults, setTestResults] = useState([])
  const [isRunning, setIsRunning] = useState(false)
  const [selectedTests, setSelectedTests] = useState([])
  const [selectedMission, setSelectedMission] = useState(null)
  const { missions, loading: missionsLoading } = useDeployedMissions()
  
  // Target config derived from selected mission
  const targetConfig = selectedMission ? {
    ip: selectedMission.vm_ip_address,
    username: 'ubuntu',  // Default from mission VM
    password: 'ubuntu',
    port: 22,
    mission_id: selectedMission.mission_id
  } : null

  // Check container status
  useEffect(() => {
    checkContainerStatus()
    const interval = setInterval(checkContainerStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const checkContainerStatus = async () => {
    try {
      const response = await fetch('/api/v1/whiteknight/status')
      if (response.ok) {
        const data = await response.json()
        setContainerStatus(data.status)
      } else {
        setContainerStatus('offline')
      }
    } catch (error) {
      setContainerStatus('offline')
    }
  }

  const toggleTest = (testId) => {
    setSelectedTests(prev => 
      prev.includes(testId) 
        ? prev.filter(id => id !== testId)
        : [...prev, testId]
    )
  }

  const selectAllInCategory = (category) => {
    const categoryTests = VALIDATION_ABILITIES[category].map(t => t.id)
    const allSelected = categoryTests.every(id => selectedTests.includes(id))
    
    if (allSelected) {
      setSelectedTests(prev => prev.filter(id => !categoryTests.includes(id)))
    } else {
      setSelectedTests(prev => [...new Set([...prev, ...categoryTests])])
    }
  }

  const runValidation = async () => {
    if (!selectedMission || selectedTests.length === 0) {
      alert('Please select a deployed mission and at least one test')
      return
    }

    setIsRunning(true)
    setTestResults([])

    try {
      const response = await fetch('/api/v1/whiteknight/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mission_id: selectedMission.mission_id,
          target_ip: selectedMission.vm_ip_address,
          username: 'ubuntu',
          password: 'ubuntu',
          port: 22,
          tests: selectedTests
        })
      })

      const data = await response.json()
      if (data.error) {
        setTestResults([{ test: 'error', status: 'failed', message: data.error }])
      } else {
        setTestResults(data.results || [])
      }
    } catch (error) {
      console.error('Validation error:', error)
      setTestResults([{ test: 'error', status: 'failed', message: error.message }])
    } finally {
      setIsRunning(false)
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return '#ff3366'
      case 'high': return '#ff6b35'
      case 'medium': return '#ffc107'
      case 'low': return '#28a745'
      default: return '#6c757d'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'ready': return '✓'
      case 'missing': return '✗'
      case 'loading': return '◐'
      default: return '?'
    }
  }

  return (
    <div className="whiteknight-container">
      <header className="whiteknight-header">
        <div className="header-title">
          <span className="header-icon">🛡️</span>
          <div>
            <h1>WHITE KNIGHT</h1>
            <p>Automated Vulnerability Validation Engine</p>
          </div>
        </div>
        <div className="container-status">
          <span className={`status-badge ${containerStatus}`}>
            {containerStatus === 'running' ? '● Container Online' : 
             containerStatus === 'offline' ? '○ Container Offline' : 
             '◐ Checking...'}
          </span>
        </div>
      </header>

      <nav className="whiteknight-tabs">
        <button 
          className={activeTab === 'tools' ? 'active' : ''} 
          onClick={() => setActiveTab('tools')}
        >
          🔧 Tools Inventory
        </button>
        <button 
          className={activeTab === 'abilities' ? 'active' : ''} 
          onClick={() => setActiveTab('abilities')}
        >
          ⚡ Validation Abilities
        </button>
        <button 
          className={activeTab === 'runner' ? 'active' : ''} 
          onClick={() => setActiveTab('runner')}
        >
          🎯 Test Runner
        </button>
        <button 
          className={activeTab === 'history' ? 'active' : ''} 
          onClick={() => setActiveTab('history')}
        >
          📜 History
        </button>
      </nav>

      <main className="whiteknight-content">
        {/* Tools Inventory Tab */}
        {activeTab === 'tools' && (
          <div className="tools-inventory">
            <div className="inventory-header">
              <h2>Available Tools</h2>
              <p>Security tools installed in the WhiteKnight container</p>
            </div>
            <div className="tools-categories">
              {Object.entries(TOOL_CATEGORIES).map(([category, tools]) => (
                <div key={category} className="tool-category">
                  <h3>{category}</h3>
                  <div className="tools-list">
                    {tools.map(tool => (
                      <div key={tool.name} className="tool-item">
                        <span className={`tool-status ${tool.status}`}>
                          {getStatusIcon(tool.status)}
                        </span>
                        <div className="tool-details">
                          <span className="tool-name">{tool.name}</span>
                          <span className="tool-desc">{tool.description}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Validation Abilities Tab */}
        {activeTab === 'abilities' && (
          <div className="abilities-view">
            <div className="abilities-header">
              <h2>Validation Capabilities</h2>
              <p>Tests WhiteKnight can perform to validate vulnerabilities</p>
            </div>
            <div className="abilities-grid">
              {Object.entries(VALIDATION_ABILITIES).map(([category, abilities]) => (
                <div key={category} className="ability-category">
                  <div className="category-header">
                    <h3>{category}</h3>
                    <span className="ability-count">{abilities.length} tests</span>
                  </div>
                  <div className="abilities-list">
                    {abilities.map(ability => (
                      <div key={ability.id} className="ability-card">
                        <div className="ability-header">
                          <span className="ability-name">{ability.name}</span>
                          <span 
                            className="severity-badge"
                            style={{ backgroundColor: getSeverityColor(ability.severity) }}
                          >
                            {ability.severity}
                          </span>
                        </div>
                        <p className="ability-desc">{ability.description}</p>
                        <span className="ability-tool">Tool: {ability.tool}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Test Runner Tab */}
        {activeTab === 'runner' && (
          <div className="test-runner">
            <div className="runner-config">
              <h2>🎯 Select Target VM</h2>
              <p className="security-notice">
                <span className="security-icon">🔒</span>
                WhiteKnight can ONLY target VMs with injected exploits from Reaper
              </p>
              <div className="config-form">
                <div className="form-group">
                  <label>Target Mission</label>
                  {missionsLoading ? (
                    <div className="loading-missions">Loading deployed missions...</div>
                  ) : missions.length === 0 ? (
                    <div className="no-missions">
                      <span className="empty-icon">📭</span>
                      <p>No deployed missions available</p>
                      <p className="hint">Deploy a mission from Reaper first</p>
                    </div>
                  ) : (
                    <select 
                      className="mission-select"
                      value={selectedMission?.mission_id || ''}
                      onChange={(e) => {
                        const mission = missions.find(m => m.mission_id === e.target.value)
                        setSelectedMission(mission || null)
                      }}
                    >
                      <option value="">-- Select a Target VM --</option>
                      {missions.map(mission => (
                        <option key={mission.mission_id} value={mission.mission_id}>
                          {mission.name} → {mission.vm_ip_address} ({mission.status === 'completed' ? '✓ ready' : mission.status})
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                
                {selectedMission && (
                  <div className="selected-mission-info">
                    <div className="mission-detail">
                      <span className="label">Mission:</span>
                      <span className="value">{selectedMission.name}</span>
                    </div>
                    <div className="mission-detail">
                      <span className="label">Target IP:</span>
                      <span className="value ip">{selectedMission.vm_ip_address}</span>
                    </div>
                    <div className="mission-detail">
                      <span className="label">VM ID:</span>
                      <span className="value">{selectedMission.vm_created_id || 'N/A'}</span>
                    </div>
                    <div className="mission-detail">
                      <span className="label">Status:</span>
                      <span className={`value status-${selectedMission.status}`}>
                        {selectedMission.status}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="test-selection">
              <h2>Select Tests</h2>
              <div className="test-categories">
                {Object.entries(VALIDATION_ABILITIES).map(([category, tests]) => (
                  <div key={category} className="test-category">
                    <div className="category-toggle">
                      <input 
                        type="checkbox"
                        checked={tests.every(t => selectedTests.includes(t.id))}
                        onChange={() => selectAllInCategory(category)}
                      />
                      <span>{category}</span>
                    </div>
                    <div className="test-options">
                      {tests.map(test => (
                        <label key={test.id} className="test-option">
                          <input 
                            type="checkbox"
                            checked={selectedTests.includes(test.id)}
                            onChange={() => toggleTest(test.id)}
                          />
                          <span className="test-name">{test.name}</span>
                          <span 
                            className="mini-severity"
                            style={{ backgroundColor: getSeverityColor(test.severity) }}
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="runner-actions">
              <button 
                className="run-button"
                onClick={runValidation}
                disabled={isRunning || containerStatus !== 'running' || !selectedMission}
              >
                {isRunning ? '◐ Running...' : '▶ Run Validation'}
              </button>
              <span className="selected-count">
                {selectedTests.length} test{selectedTests.length !== 1 ? 's' : ''} selected
                {!selectedMission && ' • Select a mission first'}
              </span>
            </div>

            {testResults.length > 0 && (
              <div className="results-panel">
                <h2>Results</h2>
                <div className="results-list">
                  {testResults.map((result, idx) => (
                    <div key={idx} className={`result-item ${result.status}`}>
                      <span className="result-icon">
                        {result.status === 'success' ? '✓' : 
                         result.status === 'failed' ? '✗' : '?'}
                      </span>
                      <div className="result-details">
                        <span className="result-test">{result.test}</span>
                        <span className="result-message">{result.message}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <ValidationHistory />
        )}
      </main>
    </div>
  )
}

export default WhiteKnightDesign

