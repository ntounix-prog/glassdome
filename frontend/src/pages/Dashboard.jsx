import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import DemoShowcase from '../components/DemoShowcase'
import '../styles/Dashboard.css'

function Dashboard({ healthStatus }) {
  const navigate = useNavigate()
  const [isDemoOpen, setIsDemoOpen] = useState(false)

  const platforms = [
    { id: 'proxmox', name: 'Proxmox', icon: '🖥️', path: '/platform/proxmox' },
    { id: 'esxi', name: 'ESXi', icon: '🏢', path: '/platform/esxi' },
    { id: 'aws', name: 'AWS', icon: '☁️', path: '/platform/aws' },
    { id: 'azure', name: 'Azure', icon: '🌐', path: '/platform/azure' },
  ]

  return (
    <div className="dashboard">
      {/* Demo Button - Only on Dashboard */}
      <button 
        className="demo-button"
        onClick={() => setIsDemoOpen(true)}
      >
        ▶ Demo
      </button>

      {/* Demo Showcase */}
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

      <div className="features-grid">
        <div className="feature-card">
          <div className="feature-icon">🤖</div>
          <h3>Autonomous Agents</h3>
          <p>AI-powered deployment agents handle complex orchestration automatically</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🎨</div>
          <h3>Drag & Drop Design</h3>
          <p>Visual lab designer with intuitive drag-and-drop interface</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">☁️</div>
          <h3>Multi-Platform</h3>
          <p>Deploy to Proxmox, Azure, AWS, or hybrid environments</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">⚡</div>
          <h3>Rapid Deployment</h3>
          <p>Go from design to deployed lab in minutes, not hours</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">🔄</div>
          <h3>Orchestration</h3>
          <p>Complex dependency management and parallel execution</p>
        </div>

        <div className="feature-card">
          <div className="feature-icon">📊</div>
          <h3>Real-time Monitoring</h3>
          <p>Track deployment progress and resource health in real-time</p>
        </div>
      </div>

      <div className="platforms-section">
        <h2>Platforms</h2>
        <p className="platforms-subtitle">Click a platform to view status and manage VMs</p>
        <div className="platform-badges">
          {platforms.map((platform) => (
            <Link 
              key={platform.id} 
              to={platform.path} 
              className="platform-badge clickable"
            >
              <span className="badge-icon">{platform.icon}</span>
              <span>{platform.name}</span>
              <span className="badge-arrow">→</span>
            </Link>
          ))}
        </div>
      </div>

      {/* Tools Section */}
      <div className="tools-section">
        <h2>Tools</h2>
        <div className="tools-grid">
          <Link to="/reaper" className="tool-card reaper">
            <span className="tool-icon">💀</span>
            <div className="tool-info">
              <h3>REAPER</h3>
              <p>Vulnerability Injection System</p>
            </div>
            <span className="tool-arrow">→</span>
          </Link>
          <Link to="/creator" className="tool-card creator">
            <span className="tool-icon">🎨</span>
            <div className="tool-info">
              <h3>Lab Creator</h3>
              <p>Design & Deploy Labs</p>
            </div>
            <span className="tool-arrow">→</span>
          </Link>
        </div>
      </div>

      <div className="status-section">
        <h3>System Status</h3>
        <div className="status-grid">
          <div className="status-item">
            <span className="status-label">Backend API</span>
            <span className={`status-value ${healthStatus ? 'healthy' : 'error'}`}>
              {healthStatus ? 'Operational' : 'Down'}
            </span>
          </div>
          <div className="status-item">
            <span className="status-label">Agent Manager</span>
            <span className="status-value healthy">Ready</span>
          </div>
          <div className="status-item">
            <span className="status-label">Orchestration Engine</span>
            <span className="status-value healthy">Ready</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard

