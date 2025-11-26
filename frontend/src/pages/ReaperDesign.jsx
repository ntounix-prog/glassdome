/**
 * Reaper Design Page
 * 
 * Main interface for managing exploit library and running injection missions.
 * Architects define exploits here, then Overseer can trigger missions.
 */

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import '../styles/ReaperDesign.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8011';

// ============================================================================
// Main Component
// ============================================================================

export default function ReaperDesign() {
  const [activeTab, setActiveTab] = useState('library');
  const [exploits, setExploits] = useState([]);
  const [missions, setMissions] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedExploit, setSelectedExploit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [typeFilter, setTypeFilter] = useState('');
  const [severityFilter, setSeverityFilter] = useState('');

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchMissions, 5000); // Poll missions
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      await Promise.all([fetchExploits(), fetchMissions(), fetchStats()]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const fetchExploits = async () => {
    let url = `${API_BASE}/api/reaper/exploits?enabled_only=false`;
    if (typeFilter) url += `&exploit_type=${typeFilter}`;
    if (severityFilter) url += `&severity=${severityFilter}`;
    
    const res = await fetch(url);
    const data = await res.json();
    setExploits(data.exploits || []);
  };

  const fetchMissions = async () => {
    const res = await fetch(`${API_BASE}/api/reaper/missions`);
    const data = await res.json();
    setMissions(data.missions || []);
  };

  const fetchStats = async () => {
    const res = await fetch(`${API_BASE}/api/reaper/stats`);
    const data = await res.json();
    setStats(data);
  };

  const seedExploits = async () => {
    try {
      await fetch(`${API_BASE}/api/reaper/exploits/seed`, { method: 'POST' });
      await fetchExploits();
      await fetchStats();
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchExploits();
  }, [typeFilter, severityFilter]);

  return (
    <div className="reaper-container">
      {/* Header */}
      <div className="reaper-header">
        <div className="reaper-title">
          <span className="reaper-icon">💀</span>
          <h1>REAPER</h1>
          <span className="reaper-subtitle">Vulnerability Injection System</span>
        </div>
        
        {stats && (
          <div className="reaper-stats">
            <div className="stat-item">
              <span className="stat-value">{stats.exploits?.total || 0}</span>
              <span className="stat-label">Exploits</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.exploits?.verified || 0}</span>
              <span className="stat-label">Verified</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">{stats.missions?.total || 0}</span>
              <span className="stat-label">Missions</span>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="reaper-tabs">
        <button 
          className={`tab ${activeTab === 'library' ? 'active' : ''}`}
          onClick={() => setActiveTab('library')}
        >
          📚 Exploit Library
        </button>
        <button 
          className={`tab ${activeTab === 'mission' ? 'active' : ''}`}
          onClick={() => setActiveTab('mission')}
        >
          🎯 Mission Builder
        </button>
        <button 
          className={`tab ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => setActiveTab('active')}
        >
          ⚡ Active Missions
        </button>
        <button 
          className={`tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 History
        </button>
      </div>

      {/* Content */}
      <div className="reaper-content">
        {error && (
          <div className="error-banner">
            {error}
            <button onClick={() => setError(null)}>×</button>
          </div>
        )}

        <AnimatePresence mode="wait">
          {activeTab === 'library' && (
            <ExploitLibrary 
              key="library"
              exploits={exploits}
              onSelect={setSelectedExploit}
              selectedExploit={selectedExploit}
              onSeed={seedExploits}
              onRefresh={fetchExploits}
              typeFilter={typeFilter}
              setTypeFilter={setTypeFilter}
              severityFilter={severityFilter}
              setSeverityFilter={setSeverityFilter}
              loading={loading}
            />
          )}
          
          {activeTab === 'mission' && (
            <MissionBuilder 
              key="mission"
              exploits={exploits}
              onMissionCreated={() => {
                fetchMissions();
                setActiveTab('active');
              }}
            />
          )}
          
          {activeTab === 'active' && (
            <ActiveMissions 
              key="active"
              missions={missions.filter(m => 
                ['pending', 'starting', 'deploying_vm', 'injecting', 'verifying'].includes(m.status)
              )}
              onRefresh={fetchMissions}
            />
          )}
          
          {activeTab === 'history' && (
            <MissionHistory 
              key="history"
              missions={missions.filter(m => 
                ['completed', 'failed', 'cancelled'].includes(m.status)
              )}
            />
          )}
        </AnimatePresence>
      </div>

      {/* Exploit Detail Modal */}
      {selectedExploit && (
        <ExploitDetailModal 
          exploit={selectedExploit}
          onClose={() => setSelectedExploit(null)}
        />
      )}
    </div>
  );
}


// ============================================================================
// Exploit Library Component
// ============================================================================

function ExploitLibrary({ 
  exploits, onSelect, selectedExploit, onSeed, onRefresh,
  typeFilter, setTypeFilter, severityFilter, setSeverityFilter, loading 
}) {
  const exploitTypes = ['web', 'network', 'privesc', 'credential', 'misconfig', 'malware', 'ad', 'custom'];
  const severities = ['critical', 'high', 'medium', 'low', 'info'];

  const getSeverityColor = (severity) => {
    const colors = {
      critical: '#ff2d55',
      high: '#ff6b35',
      medium: '#ffcc00',
      low: '#34c759',
      info: '#5ac8fa'
    };
    return colors[severity] || '#8e8e93';
  };

  const getTypeIcon = (type) => {
    const icons = {
      web: '🌐',
      network: '🔌',
      privesc: '⬆️',
      credential: '🔑',
      misconfig: '⚙️',
      malware: '🦠',
      ad: '🏢',
      custom: '🔧'
    };
    return icons[type] || '❓';
  };

  return (
    <motion.div 
      className="library-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      {/* Toolbar */}
      <div className="library-toolbar">
        <div className="filters">
          <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
            <option value="">All Types</option>
            {exploitTypes.map(t => (
              <option key={t} value={t}>{t.toUpperCase()}</option>
            ))}
          </select>
          
          <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)}>
            <option value="">All Severities</option>
            {severities.map(s => (
              <option key={s} value={s}>{s.toUpperCase()}</option>
            ))}
          </select>
        </div>
        
        <div className="actions">
          <button className="btn-secondary" onClick={onRefresh}>
            🔄 Refresh
          </button>
          <button className="btn-secondary" onClick={onSeed}>
            🌱 Seed Defaults
          </button>
          <button className="btn-primary">
            ➕ Add Exploit
          </button>
        </div>
      </div>

      {/* Exploit Grid */}
      {loading ? (
        <div className="loading">Loading exploits...</div>
      ) : exploits.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">📦</span>
          <h3>No Exploits Found</h3>
          <p>Click "Seed Defaults" to add starter exploits, or create your own.</p>
        </div>
      ) : (
        <div className="exploit-grid">
          {exploits.map(exploit => (
            <motion.div 
              key={exploit.id}
              className={`exploit-card ${selectedExploit?.id === exploit.id ? 'selected' : ''}`}
              onClick={() => onSelect(exploit)}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="exploit-header">
                <span className="exploit-type-icon">{getTypeIcon(exploit.exploit_type)}</span>
                <span 
                  className="exploit-severity"
                  style={{ backgroundColor: getSeverityColor(exploit.severity) }}
                >
                  {exploit.severity.toUpperCase()}
                </span>
              </div>
              
              <h3 className="exploit-name">{exploit.display_name}</h3>
              
              {exploit.cve_id && (
                <span className="exploit-cve">{exploit.cve_id}</span>
              )}
              
              <p className="exploit-desc">
                {exploit.description?.substring(0, 100)}
                {exploit.description?.length > 100 ? '...' : ''}
              </p>
              
              <div className="exploit-meta">
                <span className="exploit-os">🖥️ {exploit.target_os}</span>
                {exploit.verified && <span className="exploit-verified">✓ Verified</span>}
              </div>
              
              {exploit.tags && (
                <div className="exploit-tags">
                  {exploit.tags.slice(0, 3).map(tag => (
                    <span key={tag} className="tag">{tag}</span>
                  ))}
                </div>
              )}
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}


// ============================================================================
// Mission Builder Component
// ============================================================================

function MissionBuilder({ exploits, onMissionCreated }) {
  const [step, setStep] = useState(1);
  const [missionName, setMissionName] = useState('');
  const [platform, setPlatform] = useState('proxmox');
  const [targetType, setTargetType] = useState('new'); // 'new' or 'existing'
  const [targetVmId, setTargetVmId] = useState('');
  const [selectedExploits, setSelectedExploits] = useState([]);
  const [vmConfig, setVmConfig] = useState({
    name: 'reaper-target',
    os_type: 'ubuntu',
    cores: 2,
    memory: 2048
  });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const toggleExploit = (exploit) => {
    setSelectedExploits(prev => {
      const exists = prev.find(e => e.id === exploit.id);
      if (exists) {
        return prev.filter(e => e.id !== exploit.id);
      } else {
        return [...prev, exploit];
      }
    });
  };

  const createMission = async () => {
    if (!missionName || selectedExploits.length === 0) {
      setError('Please provide a name and select at least one exploit');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      const payload = {
        name: missionName,
        platform: platform,
        exploit_ids: selectedExploits.map(e => e.id),
        target_vm_id: targetType === 'existing' ? targetVmId : null,
        target_vm_config: targetType === 'new' ? vmConfig : null,
      };

      const res = await fetch(`${API_BASE}/api/reaper/missions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Failed to create mission');
      
      const mission = await res.json();
      
      // Start the mission
      await fetch(`${API_BASE}/api/reaper/missions/${mission.mission_id}/start`, {
        method: 'POST'
      });

      onMissionCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <motion.div 
      className="mission-builder"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      {/* Progress */}
      <div className="builder-progress">
        <div className={`progress-step ${step >= 1 ? 'active' : ''}`}>
          <span className="step-num">1</span>
          <span className="step-label">Configure</span>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${step >= 2 ? 'active' : ''}`}>
          <span className="step-num">2</span>
          <span className="step-label">Select Exploits</span>
        </div>
        <div className="progress-line" />
        <div className={`progress-step ${step >= 3 ? 'active' : ''}`}>
          <span className="step-num">3</span>
          <span className="step-label">Launch</span>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      {/* Step 1: Configure */}
      {step === 1 && (
        <div className="builder-step">
          <h2>Mission Configuration</h2>
          
          <div className="form-group">
            <label>Mission Name</label>
            <input 
              type="text"
              value={missionName}
              onChange={(e) => setMissionName(e.target.value)}
              placeholder="e.g., Web Security Test Lab"
            />
          </div>

          <div className="form-group">
            <label>Platform</label>
            <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
              <option value="proxmox">Proxmox</option>
              <option value="aws">AWS</option>
              <option value="esxi">ESXi</option>
              <option value="azure">Azure</option>
            </select>
          </div>

          <div className="form-group">
            <label>Target</label>
            <div className="radio-group">
              <label>
                <input 
                  type="radio" 
                  checked={targetType === 'new'}
                  onChange={() => setTargetType('new')}
                />
                Deploy New VM
              </label>
              <label>
                <input 
                  type="radio" 
                  checked={targetType === 'existing'}
                  onChange={() => setTargetType('existing')}
                />
                Use Existing VM
              </label>
            </div>
          </div>

          {targetType === 'existing' && (
            <div className="form-group">
              <label>VM ID</label>
              <input 
                type="text"
                value={targetVmId}
                onChange={(e) => setTargetVmId(e.target.value)}
                placeholder="e.g., 105 or i-0123456789abcdef"
              />
            </div>
          )}

          {targetType === 'new' && (
            <div className="vm-config">
              <div className="form-group">
                <label>VM Name</label>
                <input 
                  type="text"
                  value={vmConfig.name}
                  onChange={(e) => setVmConfig({...vmConfig, name: e.target.value})}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>CPU Cores</label>
                  <input 
                    type="number"
                    value={vmConfig.cores}
                    onChange={(e) => setVmConfig({...vmConfig, cores: parseInt(e.target.value)})}
                    min="1"
                    max="8"
                  />
                </div>
                <div className="form-group">
                  <label>Memory (MB)</label>
                  <input 
                    type="number"
                    value={vmConfig.memory}
                    onChange={(e) => setVmConfig({...vmConfig, memory: parseInt(e.target.value)})}
                    min="512"
                    step="512"
                  />
                </div>
              </div>
            </div>
          )}

          <button className="btn-primary btn-large" onClick={() => setStep(2)}>
            Continue →
          </button>
        </div>
      )}

      {/* Step 2: Select Exploits */}
      {step === 2 && (
        <div className="builder-step">
          <h2>Select Exploits to Inject</h2>
          <p className="step-hint">
            Selected: {selectedExploits.length} exploit{selectedExploits.length !== 1 ? 's' : ''}
          </p>

          <div className="exploit-selector">
            {exploits.filter(e => e.enabled).map(exploit => (
              <div 
                key={exploit.id}
                className={`exploit-select-item ${selectedExploits.find(e => e.id === exploit.id) ? 'selected' : ''}`}
                onClick={() => toggleExploit(exploit)}
              >
                <div className="select-checkbox">
                  {selectedExploits.find(e => e.id === exploit.id) ? '✓' : ''}
                </div>
                <div className="select-info">
                  <span className="select-name">{exploit.display_name}</span>
                  <span className="select-meta">
                    {exploit.exploit_type} • {exploit.severity} • {exploit.target_os}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="builder-buttons">
            <button className="btn-secondary" onClick={() => setStep(1)}>
              ← Back
            </button>
            <button 
              className="btn-primary btn-large" 
              onClick={() => setStep(3)}
              disabled={selectedExploits.length === 0}
            >
              Continue →
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Launch */}
      {step === 3 && (
        <div className="builder-step">
          <h2>Review & Launch</h2>
          
          <div className="mission-summary">
            <div className="summary-item">
              <span className="summary-label">Mission</span>
              <span className="summary-value">{missionName}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Platform</span>
              <span className="summary-value">{platform.toUpperCase()}</span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Target</span>
              <span className="summary-value">
                {targetType === 'new' ? `New VM: ${vmConfig.name}` : `Existing: ${targetVmId}`}
              </span>
            </div>
            <div className="summary-item">
              <span className="summary-label">Exploits</span>
              <span className="summary-value">{selectedExploits.length} selected</span>
            </div>
          </div>

          <div className="selected-exploits-list">
            {selectedExploits.map(e => (
              <div key={e.id} className="selected-exploit-tag">
                {e.display_name}
              </div>
            ))}
          </div>

          <div className="builder-buttons">
            <button className="btn-secondary" onClick={() => setStep(2)}>
              ← Back
            </button>
            <button 
              className="btn-danger btn-large"
              onClick={createMission}
              disabled={creating}
            >
              {creating ? '⏳ Launching...' : '🚀 Launch Mission'}
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}


// ============================================================================
// Active Missions Component
// ============================================================================

function ActiveMissions({ missions, onRefresh }) {
  const getStatusIcon = (status) => {
    const icons = {
      pending: '⏳',
      starting: '🔄',
      deploying_vm: '🖥️',
      injecting: '💉',
      verifying: '🔍',
      completed: '✅',
      failed: '❌',
      cancelled: '🚫'
    };
    return icons[status] || '❓';
  };

  return (
    <motion.div 
      className="active-missions"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <div className="missions-header">
        <h2>Active Missions</h2>
        <button className="btn-secondary" onClick={onRefresh}>🔄 Refresh</button>
      </div>

      {missions.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">🎯</span>
          <h3>No Active Missions</h3>
          <p>Create a new mission from the Mission Builder tab.</p>
        </div>
      ) : (
        <div className="missions-list">
          {missions.map(mission => (
            <div key={mission.mission_id} className="mission-card">
              <div className="mission-card-header">
                <span className="mission-status-icon">{getStatusIcon(mission.status)}</span>
                <h3>{mission.name}</h3>
                <span className="mission-platform">{mission.platform}</span>
              </div>
              
              <div className="mission-progress">
                <div 
                  className="progress-bar"
                  style={{ width: `${mission.progress}%` }}
                />
              </div>
              
              <div className="mission-info">
                <span className="mission-step">{mission.current_step || 'Initializing...'}</span>
                <span className="mission-progress-text">{mission.progress}%</span>
              </div>
              
              {mission.vm_ip_address && (
                <div className="mission-vm-info">
                  <span>VM IP: {mission.vm_ip_address}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}


// ============================================================================
// Mission History Component
// ============================================================================

function MissionHistory({ missions }) {
  return (
    <motion.div 
      className="mission-history"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      <h2>Mission History</h2>
      
      {missions.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon">📜</span>
          <h3>No Mission History</h3>
          <p>Completed missions will appear here.</p>
        </div>
      ) : (
        <table className="history-table">
          <thead>
            <tr>
              <th>Status</th>
              <th>Name</th>
              <th>Platform</th>
              <th>Exploits</th>
              <th>Created</th>
              <th>Completed</th>
            </tr>
          </thead>
          <tbody>
            {missions.map(mission => (
              <tr key={mission.mission_id} className={`status-${mission.status}`}>
                <td>
                  <span className={`status-badge ${mission.status}`}>
                    {mission.status}
                  </span>
                </td>
                <td>{mission.name}</td>
                <td>{mission.platform}</td>
                <td>{mission.exploit_ids?.length || 0}</td>
                <td>{new Date(mission.created_at).toLocaleDateString()}</td>
                <td>
                  {mission.completed_at 
                    ? new Date(mission.completed_at).toLocaleDateString()
                    : '-'
                  }
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </motion.div>
  );
}


// ============================================================================
// Exploit Detail Modal
// ============================================================================

function ExploitDetailModal({ exploit, onClose }) {
  const [fullExploit, setFullExploit] = useState(null);
  
  useEffect(() => {
    fetch(`${API_BASE}/api/reaper/exploits/${exploit.id}`)
      .then(res => res.json())
      .then(data => setFullExploit(data));
  }, [exploit.id]);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <motion.div 
        className="modal-content exploit-detail"
        onClick={e => e.stopPropagation()}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
      >
        <button className="modal-close" onClick={onClose}>×</button>
        
        <div className="exploit-detail-header">
          <h2>{exploit.display_name}</h2>
          {exploit.cve_id && <span className="cve-badge">{exploit.cve_id}</span>}
        </div>

        <div className="exploit-detail-meta">
          <span className={`severity-badge ${exploit.severity}`}>
            {exploit.severity.toUpperCase()}
          </span>
          <span className="type-badge">{exploit.exploit_type}</span>
          <span className="os-badge">{exploit.target_os}</span>
          {exploit.cvss_score && (
            <span className="cvss-badge">CVSS: {exploit.cvss_score}</span>
          )}
        </div>

        <p className="exploit-detail-desc">{exploit.description}</p>

        {exploit.target_services?.length > 0 && (
          <div className="detail-section">
            <h3>Target Services</h3>
            <div className="service-tags">
              {exploit.target_services.map(s => (
                <span key={s} className="service-tag">{s}</span>
              ))}
            </div>
          </div>
        )}

        {exploit.exploitation_steps && (
          <div className="detail-section">
            <h3>Exploitation Steps</h3>
            <pre className="code-block">{exploit.exploitation_steps}</pre>
          </div>
        )}

        {exploit.remediation_steps && (
          <div className="detail-section">
            <h3>Remediation</h3>
            <pre className="code-block">{exploit.remediation_steps}</pre>
          </div>
        )}

        {fullExploit?.install_script && (
          <div className="detail-section">
            <h3>Install Script</h3>
            <pre className="code-block">{fullExploit.install_script}</pre>
          </div>
        )}
      </motion.div>
    </div>
  );
}

