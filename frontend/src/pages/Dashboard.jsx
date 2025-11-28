import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import DemoShowcase from '../components/DemoShowcase'
import '../styles/Dashboard.css'

// Registry status hook
function useRegistryStatus() {
  const [status, setStatus] = useState(null)
  
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/registry/status')
        if (response.ok) {
          setStatus(await response.json())
        }
      } catch (err) {
        console.error('Registry status error:', err)
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000)
    return () => clearInterval(interval)
  }, [])
  
  return status
}

function Dashboard({ healthStatus }) {
  const navigate = useNavigate()
  const [isDemoOpen, setIsDemoOpen] = useState(false)
  const registryStatus = useRegistryStatus()

  return (
    <div className="dashboard">
      {/* Demo Button */}
      <button 
        className="demo-button"
        onClick={() => setIsDemoOpen(true)}
      >
        ▶ Demo
      </button>

      <DemoShowcase 
        isOpen={isDemoOpen} 
        onClose={() => setIsDemoOpen(false)} 
      />

      <div className="hero-section">
        <h1>Agentic Cyber Range Deployment</h1>
        <p className="hero-subtitle">
          Deploy complex cybersecurity lab environments with autonomous agents
        </p>
        <button className="btn-primary" onClick={() => navigate('/lab')}>
          Create New Lab
        </button>
      </div>

      <div className="status-section">
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">Backend API</span>
            <span className={`status-value ${healthStatus ? 'healthy' : 'error'}`}>
              {healthStatus ? '✓ Operational' : '✗ Down'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Lab Registry</span>
            <span className={`status-value ${registryStatus?.connected ? 'healthy' : 'error'}`}>
              {registryStatus?.connected ? `✓ ${registryStatus.total_resources} Resources` : '✗ Offline'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Agents</span>
            <span className={`status-value ${registryStatus?.agents > 0 ? 'healthy' : 'warning'}`}>
              {registryStatus?.agents || 0} Active
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Drifts</span>
            <span className={`status-value ${registryStatus?.active_drifts > 0 ? 'warning' : 'healthy'}`}>
              {registryStatus?.active_drifts || 0}
            </span>
          </div>
        </div>
      </div>

      <div className="features-grid">
        <div className="feature-card clickable" onClick={() => navigate('/features/agents')}>
          <div className="feature-icon">🤖</div>
          <h3>Autonomous Agents</h3>
          <p>AI-powered deployment agents handle complex orchestration automatically</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable" onClick={() => navigate('/features/designer')}>
          <div className="feature-icon">🎨</div>
          <h3>Drag & Drop Design</h3>
          <p>Visual lab designer with intuitive drag-and-drop interface</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable" onClick={() => navigate('/features/platforms')}>
          <div className="feature-icon">☁️</div>
          <h3>Multi-Platform</h3>
          <p>Deploy to Proxmox, Azure, AWS, or hybrid environments</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable" onClick={() => navigate('/features/deployment')}>
          <div className="feature-icon">⚡</div>
          <h3>Rapid Deployment</h3>
          <p>Go from design to deployed lab in minutes, not hours</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable" onClick={() => navigate('/features/orchestration')}>
          <div className="feature-icon">🔄</div>
          <h3>Orchestration</h3>
          <p>Complex dependency management and parallel execution</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable" onClick={() => navigate('/features/monitoring')}>
          <div className="feature-icon">📊</div>
          <h3>Real-time Monitoring</h3>
          <p>Track deployment progress and resource health in real-time</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable reaper-card" onClick={() => navigate('/features/reaper')}>
          <div className="feature-icon">☠️</div>
          <h3>Reaper Engine</h3>
          <p>Configure in place - deploy anywhere, same lab state every time</p>
          <span className="feature-link">Learn more →</span>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
