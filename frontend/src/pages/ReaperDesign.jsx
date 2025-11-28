/**
 * Reaper Design Page
 * 
 * Main interface for managing exploit library and running injection missions.
 * Architects define exploits here, then Overseer can trigger missions.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  const [showLogs, setShowLogs] = useState(false);

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

      {/* Log Viewer Toggle Button */}
      <button 
        className="show-logs-btn"
        onClick={() => setShowLogs(!showLogs)}
      >
        {showLogs ? '📜 Hide Logs' : '📜 Show Logs'}
      </button>

      {/* Log Viewer Panel */}
      <AnimatePresence>
        {showLogs && (
          <LogViewer isOpen={showLogs} onClose={() => setShowLogs(false)} />
        )}
      </AnimatePresence>
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
  const [showAddModal, setShowAddModal] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const fileInputRef = useRef(null);
  
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

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      // Handle both formats: {exploits: [...]} or direct array
      const exploitsArray = data.exploits || (Array.isArray(data) ? data : [data]);
      
      const res = await fetch(`${API_BASE}/api/reaper/exploits/import`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          exploits: exploitsArray,
          overwrite: false
        })
      });
      
      const result = await res.json();
      setImportResult(result);
      
      if (result.imported > 0 || result.updated > 0) {
        onRefresh();
      }
    } catch (err) {
      setImportResult({ errors: [`Failed to parse JSON: ${err.message}`] });
    }
    
    // Reset file input
    e.target.value = '';
  };

  const downloadTemplate = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/reaper/exploits/template`);
      const template = await res.json();
      
      const blob = new Blob([JSON.stringify(template, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'exploit_template.json';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download template:', err);
    }
  };

  const exportExploits = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/reaper/exploits/export`);
      const data = await res.json();
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `exploits_backup_${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to export exploits:', err);
    }
  };

  return (
    <motion.div 
      className="library-container"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
    >
      {/* Import Result Banner */}
      {importResult && (
        <div className={`import-result ${importResult.errors?.length > 0 ? 'has-errors' : 'success'}`}>
          <div className="import-stats">
            {importResult.imported > 0 && <span>✅ {importResult.imported} imported</span>}
            {importResult.updated > 0 && <span>🔄 {importResult.updated} updated</span>}
            {importResult.errors?.length > 0 && (
              <span className="errors">⚠️ {importResult.errors.length} errors</span>
            )}
          </div>
          {importResult.errors?.length > 0 && (
            <ul className="error-list">
              {importResult.errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          )}
          <button onClick={() => setImportResult(null)}>×</button>
        </div>
      )}

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
          <button className="btn-secondary" onClick={downloadTemplate} title="Download example JSON template">
            📄 Template
          </button>
          <button className="btn-secondary" onClick={exportExploits} title="Export all exploits">
            📤 Export
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleFileUpload}
            style={{ display: 'none' }}
          />
          <button className="btn-primary" onClick={() => fileInputRef.current?.click()}>
            📥 Import JSON
          </button>
          <button className="btn-primary" onClick={() => setShowAddModal(true)}>
            ➕ Add Exploit
          </button>
        </div>
      </div>
      
      {/* Add Exploit Modal */}
      {showAddModal && (
        <AddExploitModal 
          onClose={() => setShowAddModal(false)}
          onCreated={() => {
            setShowAddModal(false);
            onRefresh();
          }}
        />
      )}

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
    template_id: 9000,  // Ubuntu 22.04 template
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
// Add Exploit Modal
// ============================================================================

function AddExploitModal({ onClose, onCreated }) {
  const [formData, setFormData] = useState({
    name: '',
    display_name: '',
    description: '',
    cve_id: '',
    exploit_type: 'custom',
    severity: 'medium',
    target_os: 'linux',
    target_services: [],
    install_script: '',
    ansible_playbook: '',
    ansible_vars: {},
    exploitation_steps: '',
    remediation_steps: '',
    tags: []
  });
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('basic'); // basic, script, ansible

  const handleSubmit = async () => {
    if (!formData.name || !formData.display_name) {
      setError('Name and Display Name are required');
      return;
    }

    setCreating(true);
    setError(null);

    try {
      // Clean up empty arrays/objects
      const payload = {
        ...formData,
        target_services: formData.target_services.length > 0 ? formData.target_services : null,
        tags: formData.tags.length > 0 ? formData.tags : null,
        install_script: formData.install_script || null,
        ansible_playbook: formData.ansible_playbook || null,
        ansible_vars: Object.keys(formData.ansible_vars).length > 0 ? formData.ansible_vars : null,
      };

      const res = await fetch(`${API_BASE}/api/reaper/exploits`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create exploit');
      }

      onCreated();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleTagInput = (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
      e.preventDefault();
      const newTag = e.target.value.trim().toLowerCase();
      if (!formData.tags.includes(newTag)) {
        setFormData({ ...formData, tags: [...formData.tags, newTag] });
      }
      e.target.value = '';
    }
  };

  const handleServiceInput = (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) {
      e.preventDefault();
      const newService = e.target.value.trim().toLowerCase();
      if (!formData.target_services.includes(newService)) {
        setFormData({ ...formData, target_services: [...formData.target_services, newService] });
      }
      e.target.value = '';
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <motion.div 
        className="modal-content add-exploit-modal"
        onClick={e => e.stopPropagation()}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
      >
        <button className="modal-close" onClick={onClose}>×</button>
        
        <h2>➕ Add New Exploit</h2>
        
        {error && <div className="modal-error">{error}</div>}

        {/* Tab Navigation */}
        <div className="modal-tabs">
          <button 
            className={activeTab === 'basic' ? 'active' : ''} 
            onClick={() => setActiveTab('basic')}
          >
            📋 Basic Info
          </button>
          <button 
            className={activeTab === 'script' ? 'active' : ''} 
            onClick={() => setActiveTab('script')}
          >
            📜 Script
          </button>
          <button 
            className={activeTab === 'ansible' ? 'active' : ''} 
            onClick={() => setActiveTab('ansible')}
          >
            🅰️ Ansible
          </button>
        </div>

        <div className="modal-body">
          {/* Basic Info Tab */}
          {activeTab === 'basic' && (
            <div className="form-section">
              <div className="form-row">
                <label>
                  Name (unique identifier)*
                  <input 
                    type="text" 
                    value={formData.name}
                    onChange={e => setFormData({ ...formData, name: e.target.value.toLowerCase().replace(/\s+/g, '-') })}
                    placeholder="my-custom-exploit"
                  />
                </label>
                <label>
                  Display Name*
                  <input 
                    type="text" 
                    value={formData.display_name}
                    onChange={e => setFormData({ ...formData, display_name: e.target.value })}
                    placeholder="My Custom Exploit"
                  />
                </label>
              </div>

              <label>
                Description
                <textarea 
                  value={formData.description}
                  onChange={e => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Describe what this exploit does..."
                  rows={3}
                />
              </label>

              <div className="form-row">
                <label>
                  CVE ID
                  <input 
                    type="text" 
                    value={formData.cve_id}
                    onChange={e => setFormData({ ...formData, cve_id: e.target.value })}
                    placeholder="CVE-2024-XXXXX"
                  />
                </label>
                <label>
                  Type
                  <select value={formData.exploit_type} onChange={e => setFormData({ ...formData, exploit_type: e.target.value })}>
                    <option value="web">Web</option>
                    <option value="network">Network</option>
                    <option value="privesc">Privilege Escalation</option>
                    <option value="credential">Credential</option>
                    <option value="misconfig">Misconfiguration</option>
                    <option value="ad">Active Directory</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
                <label>
                  Severity
                  <select value={formData.severity} onChange={e => setFormData({ ...formData, severity: e.target.value })}>
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
                    <option value="info">Info</option>
                  </select>
                </label>
                <label>
                  Target OS
                  <select value={formData.target_os} onChange={e => setFormData({ ...formData, target_os: e.target.value })}>
                    <option value="linux">Linux</option>
                    <option value="windows">Windows</option>
                    <option value="macos">macOS</option>
                    <option value="any">Any</option>
                  </select>
                </label>
              </div>

              <label>
                Target Services (press Enter to add)
                <input type="text" onKeyDown={handleServiceInput} placeholder="apache, mysql, ssh..." />
                <div className="tag-list">
                  {formData.target_services.map(s => (
                    <span key={s} className="tag" onClick={() => setFormData({ ...formData, target_services: formData.target_services.filter(t => t !== s) })}>
                      {s} ×
                    </span>
                  ))}
                </div>
              </label>

              <label>
                Tags (press Enter to add)
                <input type="text" onKeyDown={handleTagInput} placeholder="owasp, training, ctf..." />
                <div className="tag-list">
                  {formData.tags.map(t => (
                    <span key={t} className="tag" onClick={() => setFormData({ ...formData, tags: formData.tags.filter(tag => tag !== t) })}>
                      {t} ×
                    </span>
                  ))}
                </div>
              </label>
            </div>
          )}

          {/* Script Tab */}
          {activeTab === 'script' && (
            <div className="form-section">
              <p className="tab-description">
                Use bash/PowerShell scripts for simple vulnerability injection.
                These run directly on the target VM via SSH/WinRM.
              </p>
              
              <label>
                Install Script (bash for Linux, PowerShell for Windows)
                <textarea 
                  value={formData.install_script}
                  onChange={e => setFormData({ ...formData, install_script: e.target.value })}
                  placeholder={`#!/bin/bash
# Create vulnerable user
useradd -m vulnuser
echo 'vulnuser:password123' | chpasswd
echo 'Vulnerable user created'`}
                  rows={12}
                  className="code-input"
                />
              </label>

              <label>
                Exploitation Steps (for training documentation)
                <textarea 
                  value={formData.exploitation_steps}
                  onChange={e => setFormData({ ...formData, exploitation_steps: e.target.value })}
                  placeholder="1. Connect via SSH&#10;2. Use weak credentials&#10;3. ..."
                  rows={4}
                />
              </label>

              <label>
                Remediation Steps
                <textarea 
                  value={formData.remediation_steps}
                  onChange={e => setFormData({ ...formData, remediation_steps: e.target.value })}
                  placeholder="1. Remove vulnerable user&#10;2. Enforce strong passwords&#10;3. ..."
                  rows={4}
                />
              </label>
            </div>
          )}

          {/* Ansible Tab */}
          {activeTab === 'ansible' && (
            <div className="form-section">
              <p className="tab-description">
                Reference Ansible playbooks for complex scenarios. 
                Playbooks should be in <code>glassdome/vulnerabilities/playbooks/</code>
              </p>
              
              <label>
                Ansible Playbook Path
                <input 
                  type="text" 
                  value={formData.ansible_playbook}
                  onChange={e => setFormData({ ...formData, ansible_playbook: e.target.value })}
                  placeholder="web/inject_sqli.yml"
                />
                <small>Relative to glassdome/vulnerabilities/playbooks/</small>
              </label>

              <label>
                Ansible Variables (JSON)
                <textarea 
                  value={JSON.stringify(formData.ansible_vars, null, 2)}
                  onChange={e => {
                    try {
                      setFormData({ ...formData, ansible_vars: JSON.parse(e.target.value) });
                    } catch {}
                  }}
                  placeholder={`{
  "mysql_password": "vulnerable123",
  "security_level": "low"
}`}
                  rows={6}
                  className="code-input"
                />
              </label>

              <div className="info-box">
                <strong>💡 Tip:</strong> Your engineers can create custom Ansible playbooks 
                and reference them here. Standard Ansible playbook format is fully supported.
                <br/><br/>
                <strong>Available playbooks:</strong>
                <ul>
                  <li><code>web/inject_sqli.yml</code> - DVWA SQL injection</li>
                  <li><code>web/inject_xss.yml</code> - XSS vulnerabilities</li>
                  <li><code>system/weak_ssh.yml</code> - Weak SSH credentials</li>
                  <li><code>system/weak_sudo.yml</code> - Sudo misconfigurations</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button 
            className="btn-primary" 
            onClick={handleSubmit}
            disabled={creating}
          >
            {creating ? 'Creating...' : 'Create Exploit'}
          </button>
        </div>
      </motion.div>
    </div>
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


// ============================================================================
// Log Viewer Component
// ============================================================================

function LogViewer({ isOpen, onClose }) {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const logsEndRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      // Fetch initial logs
      fetch(`${API_BASE}/api/reaper/logs?lines=50`)
        .then(res => res.json())
        .then(data => {
          if (data.logs) {
            setLogs(data.logs);
          }
        })
        .catch(err => console.error('Failed to fetch logs:', err));

      // Connect WebSocket for live updates
      const wsUrl = API_BASE.replace('http', 'ws') + '/api/reaper/logs/stream';
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => setConnected(true);
      wsRef.current.onclose = () => setConnected(false);
      wsRef.current.onerror = () => setConnected(false);
      wsRef.current.onmessage = (event) => {
        const newLines = event.data.split('\n').filter(l => l.trim());
        setLogs(prev => [...prev.slice(-200), ...newLines]); // Keep last 200 lines
      };
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isOpen]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  if (!isOpen) return null;

  const getLineClass = (line) => {
    if (line.includes('[ERROR]') || line.includes('ERROR')) return 'error';
    if (line.includes('[WARNING]') || line.includes('WARNING')) return 'warning';
    if (line.includes('✓') || line.includes('success')) return 'success';
    if (line.includes('[MISSION')) return 'mission';
    return '';
  };

  return (
    <motion.div 
      className="log-viewer"
      initial={{ y: '100%' }}
      animate={{ y: 0 }}
      exit={{ y: '100%' }}
      transition={{ type: 'spring', damping: 25 }}
    >
      <div className="log-header">
        <span className="log-title">
          📜 Reaper Logs
          <span className={`connection-status ${connected ? 'connected' : ''}`}>
            {connected ? '● Live' : '○ Disconnected'}
          </span>
        </span>
        <div className="log-actions">
          <button onClick={() => setLogs([])}>Clear</button>
          <button onClick={onClose}>✕</button>
        </div>
      </div>
      <div className="log-content">
        {logs.length === 0 ? (
          <div className="log-empty">No logs yet. Run a mission to see activity.</div>
        ) : (
          logs.map((line, i) => (
            <div key={i} className={`log-line ${getLineClass(line)}`}>
              {line}
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </motion.div>
  );
}

