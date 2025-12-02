/**
 * Dashboard page component
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

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
        const response = await fetch('/api/v1/registry/status')
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

// MXWest network probe hook
function useMXWestStatus() {
  const [status, setStatus] = useState(null)
  
  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/api/v1/probes/mxwest')
        if (response.ok) {
          setStatus(await response.json())
        }
      } catch (err) {
        console.error('MXWest probe error:', err)
      }
    }
    fetchStatus()
    const interval = setInterval(fetchStatus, 30000) // Check every 30s
    return () => clearInterval(interval)
  }, [])
  
  return status
}

function Dashboard({ healthStatus }) {
  const navigate = useNavigate()
  const [isDemoOpen, setIsDemoOpen] = useState(false)
  const registryStatus = useRegistryStatus()
  const mxwestStatus = useMXWestStatus()

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
          <div className="status-item">
            <span className="status-label">MXWest Link</span>
            <span className={`status-value ${mxwestStatus?.status === 'healthy' ? 'healthy' : 'error'}`}>
              {mxwestStatus?.status === 'healthy' 
                ? `✓ ${mxwestStatus?.mxwest?.latency_ms?.toFixed(0) || '?'}ms` 
                : mxwestStatus?.status === 'vpn_down' 
                  ? '⚠ VPN Down'
                  : '✗ Offline'}
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

        <div className="feature-card clickable updock-card" onClick={() => navigate('/features/updock')}>
          <div className="feature-icon">🚀</div>
          <h3>Updock Player Access</h3>
          <p>Browser-based RDP/SSH access to lab VMs via Guacamole gateway</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable whiteknight-card" onClick={() => navigate('/features/whiteknight')}>
          <div className="feature-icon">🛡️</div>
          <h3>WhiteKnight Validation</h3>
          <p>Automated security validation and compliance checking for labs</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable whitepawn-card" onClick={() => navigate('/features/whitepawn')}>
          <div className="feature-icon">♙</div>
          <h3>WhitePawn Monitoring</h3>
          <p>Continuous deployment monitoring with drift detection and alerting</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable overseer-card" onClick={() => navigate('/features/overseer')}>
          <div className="feature-icon">🧠</div>
          <h3>Overseer AI</h3>
          <p>Intelligent operator chat with context-aware deployment assistance</p>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable rbac-card active-feature" onClick={() => navigate('/features/rbac')}>
          <div className="feature-icon">🔐</div>
          <h3>Role-Based Access Control</h3>
          <p>Granular permissions with Admin, Architect, Engineer, and Observer roles</p>
          <span className="feature-status active">✓ Active</span>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable vault-card active-feature" onClick={() => navigate('/features/vault')}>
          <div className="feature-icon">🔒</div>
          <h3>HashiCorp Vault</h3>
          <p>Centralized secrets management for credentials, API keys, and tokens</p>
          <span className="feature-status active">✓ Active</span>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable api-docs-card active-feature" onClick={() => navigate('/features/api-docs')}>
          <div className="feature-icon">📖</div>
          <h3>Documented & Versioned API</h3>
          <p>Interactive OpenAPI documentation with full schema validation and versioned endpoints</p>
          <span className="feature-status active">✓ Active</span>
          <span className="feature-link">Learn more →</span>
        </div>

        <div className="feature-card clickable api-testing-card active-feature" onClick={() => navigate('/features/api-testing')}>
          <div className="feature-icon">🧪</div>
          <h3>API Test & Validation Pipeline</h3>
          <p>Comprehensive pytest suite with smoke tests, auth validation, and endpoint coverage</p>
          <span className="feature-status active">✓ Active</span>
          <span className="feature-link">Learn more →</span>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
