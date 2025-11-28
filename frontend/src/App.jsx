/**
 * App module
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

import { useState, useEffect, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import LabCanvas from './pages/LabCanvas'
import Deployments from './pages/Deployments'
import PlatformStatus from './pages/PlatformStatus'
import ReaperDesign from './pages/ReaperDesign'
import WhiteKnightDesign from './pages/WhiteKnightDesign'
import WhitePawnMonitor from './pages/WhitePawnMonitor'
import LabMonitor from './pages/LabMonitor'
import FeatureDetail from './pages/FeatureDetail'
// Player Portal
import PlayerPortal from './pages/player/PlayerPortal'
import PlayerLobby from './pages/player/PlayerLobby'
import PlayerSession from './pages/player/PlayerSession'
import { ChatModal, ChatToggle } from './components/OverseerChat'
import './App.css'

// SomaFM default station
const DEFAULT_STATION = 'defcon'
const STATIONS = {
  defcon: { stream: 'https://ice1.somafm.com/defcon-128-mp3', icon: '💀' },
}

// Dropdown Menu Component
function NavDropdown({ label, items, defaultPath }) {
  const [isOpen, setIsOpen] = useState(false)
  const navigate = useNavigate()
  const closeTimeoutRef = useRef(null)

  const handleMouseEnter = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current)
    }
    setIsOpen(true)
  }

  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setIsOpen(false)
    }, 300) // 300ms delay before closing
  }

  return (
    <div 
      className="nav-dropdown"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <button 
        className="nav-dropdown-trigger"
        onClick={() => navigate(defaultPath)}
      >
        {label}
        <span className="dropdown-arrow">▼</span>
      </button>
      {isOpen && (
        <div className="nav-dropdown-menu">
          {items.map((item) => (
            <Link 
              key={item.path} 
              to={item.path} 
              className="nav-dropdown-item"
              onClick={() => setIsOpen(false)}
            >
              <span className="dropdown-icon">{item.icon}</span>
              <span>{item.name}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

// Navigation Component (needs to be inside Router)
function Navigation({ healthStatus, loading, radioState }) {
  const monitorItems = [
    { name: 'Lab Monitor', icon: '🔬', path: '/monitor' },
    { name: 'WhitePawn', icon: '♟️', path: '/whitepawn' },
    { name: 'Proxmox', icon: '🖥️', path: '/platform/proxmox' },
    { name: 'ESXi', icon: '🏢', path: '/platform/esxi' },
    { name: 'AWS', icon: '☁️', path: '/platform/aws' },
    { name: 'Azure', icon: '🌐', path: '/platform/azure' },
  ]

  const designItems = [
    { name: 'Lab Designer', icon: '🎨', path: '/lab' },
    { name: 'Reaper', icon: '💀', path: '/reaper' },
    { name: 'WhiteKnight', icon: '🛡️', path: '/whiteknight' },
  ]

  return (
    <nav className="navbar">
      <div className="nav-brand">
        <Link to="/" className="brand-link">
          <h1>🔮 Glassdome</h1>
        </Link>
        <p className="tagline">Cyber Range Deployment Framework</p>
      </div>
      <div className="nav-links">
        <Link to="/">Dashboard</Link>
        <NavDropdown label="Design" items={designItems} defaultPath="/lab" />
        <NavDropdown label="Monitor" items={monitorItems} defaultPath="/monitor" />
        <Link to="/deployments">Deployments</Link>
      </div>
      <div className="nav-status">
        {radioState.isPlaying && (
          <span className="radio-indicator">🎵</span>
        )}
        {loading ? (
          <span className="status-indicator status-loading">Checking...</span>
        ) : healthStatus ? (
          <span className="status-indicator status-healthy">✓ Connected</span>
        ) : (
          <span className="status-indicator status-error">✗ Disconnected</span>
        )}
      </div>
    </nav>
  )
}

function App() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(false)
  
  // Shared radio state - persists across modal open/close
  const [radioState, setRadioState] = useState({
    isPlaying: false,
    currentStation: DEFAULT_STATION,
    volume: 0.7
  })
  const audioRef = useRef(null)

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

  // Keep audio volume in sync
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = radioState.volume
    }
  }, [radioState.volume])

  return (
    <Router>
      <div className="App">
        {/* Persistent audio element - never unmounts */}
        <audio 
          ref={audioRef}
          src={STATIONS[radioState.currentStation]?.stream || STATIONS.defcon.stream}
          preload="none"
          onPlay={() => setRadioState(prev => ({ ...prev, isPlaying: true }))}
          onPause={() => setRadioState(prev => ({ ...prev, isPlaying: false }))}
          onEnded={() => setRadioState(prev => ({ ...prev, isPlaying: false }))}
        />
        
        <Navigation healthStatus={healthStatus} loading={loading} radioState={radioState} />

        <Routes>
          {/* Admin Routes */}
          <Route path="/" element={<Dashboard healthStatus={healthStatus} />} />
          <Route path="/lab" element={<LabCanvas />} />
          <Route path="/lab/:labId" element={<LabCanvas />} />
          <Route path="/deployments" element={<Deployments />} />
          <Route path="/platform/:platform" element={<PlatformStatus />} />
          <Route path="/platform/:platform/:instanceId" element={<PlatformStatus />} />
          <Route path="/reaper" element={<ReaperDesign />} />
          <Route path="/whiteknight" element={<WhiteKnightDesign />} />
          <Route path="/whitepawn" element={<WhitePawnMonitor />} />
          <Route path="/monitor" element={<LabMonitor />} />
          <Route path="/features/:featureId" element={<FeatureDetail />} />
          
          {/* Player Portal Routes */}
          <Route path="/player" element={<PlayerPortal />} />
          <Route path="/player/:labId" element={<PlayerLobby />} />
          <Route path="/player/:labId/:vmName" element={<PlayerSession />} />
        </Routes>

        {/* Overseer Chat with integrated Radio */}
        <ChatToggle 
          onClick={() => setIsChatOpen(true)} 
          hasUnread={false}
          isPlaying={radioState.isPlaying}
        />
        <ChatModal 
          isOpen={isChatOpen} 
          onClose={() => setIsChatOpen(false)}
          audioRef={audioRef}
          radioState={radioState}
          setRadioState={setRadioState}
        />
      </div>
    </Router>
  )
}

export default App
