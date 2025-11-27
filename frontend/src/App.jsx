import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import LabCanvas from './pages/LabCanvas'
import Deployments from './pages/Deployments'
import PlatformStatus from './pages/PlatformStatus'
import ReaperDesign from './pages/ReaperDesign'
import WhiteKnightDesign from './pages/WhiteKnightDesign'
import WhitePawnMonitor from './pages/WhitePawnMonitor'
import { ChatModal, ChatToggle } from './components/OverseerChat'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(false)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setHealthStatus(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('API Error:', err)
        setLoading(false)
      })
  }, [])

  return (
    <Router>
      <div className="App">

        <nav className="navbar">
          <div className="nav-brand">
            <h1>🔮 Glassdome</h1>
            <p className="tagline">Cyber Range Deployment Framework</p>
          </div>
          <div className="nav-links">
            <Link to="/">Dashboard</Link>
            <Link to="/lab">Lab Designer</Link>
            <Link to="/deployments">Deployments</Link>
          </div>
          <div className="nav-status">
            {loading ? (
              <span className="status-indicator status-loading">Checking...</span>
            ) : healthStatus ? (
              <span className="status-indicator status-healthy">✓ Connected</span>
            ) : (
              <span className="status-indicator status-error">✗ Disconnected</span>
            )}
          </div>
        </nav>

        <Routes>
          <Route path="/" element={<Dashboard healthStatus={healthStatus} />} />
          <Route path="/lab" element={<LabCanvas />} />
          <Route path="/lab/:labId" element={<LabCanvas />} />
          <Route path="/deployments" element={<Deployments />} />
          <Route path="/platform/:platform" element={<PlatformStatus />} />
          <Route path="/platform/:platform/:instanceId" element={<PlatformStatus />} />
          <Route path="/reaper" element={<ReaperDesign />} />
          <Route path="/whiteknight" element={<WhiteKnightDesign />} />
          <Route path="/whitepawn" element={<WhitePawnMonitor />} />
        </Routes>

        {/* Overseer Chat Interface */}
        <ChatToggle 
          onClick={() => setIsChatOpen(true)} 
          hasUnread={false}
        />
        <ChatModal 
          isOpen={isChatOpen} 
          onClose={() => setIsChatOpen(false)} 
        />
      </div>
    </Router>
  )
}

export default App
