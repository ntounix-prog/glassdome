/**
 * App module
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useState, useEffect, useRef } from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import UserMenu from './components/UserMenu'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import LabCanvas from './pages/LabCanvas'
import Deployments from './pages/Deployments'
import PlatformStatus from './pages/PlatformStatus'
import ReaperDesign from './pages/ReaperDesign'
import WhiteKnightDesign from './pages/WhiteKnightDesign'
import WhitePawnMonitor from './pages/WhitePawnMonitor'
import LabMonitor from './pages/LabMonitor'
import FeatureDetail from './pages/FeatureDetail'
import AdminUsers from './pages/AdminUsers'
import AdminSecrets from './pages/AdminSecrets'
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
    }, 300)
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

// Navigation Component (needs to be inside Router and AuthProvider)
function Navigation({ healthStatus, loading, radioState }) {
  const { isAuthenticated, hasLevel } = useAuth()
  
  const monitorItems = [
    { name: 'Lab Monitor', icon: '🔬', path: '/monitor' },
    { name: 'WhitePawn', icon: '♟️', path: '/whitepawn' },
    { name: 'Proxmox', icon: '🖥️', path: '/platform/proxmox' },
    { name: 'ESXi', icon: '🏢', path: '/platform/esxi' },
    { name: 'AWS', icon: '☁️', path: '/platform/aws' },
    { name: 'Azure', icon: '🌐', path: '/platform/azure' },
  ]

  // Filter design items based on user level
  const designItems = [
    { name: 'Lab Designer', icon: '🎨', path: '/lab', minLevel: 50 },
    { name: 'Reaper', icon: '💀', path: '/reaper', minLevel: 50 },
    { name: 'WhiteKnight', icon: '🛡️', path: '/whiteknight', minLevel: 50 },
  ].filter(item => !item.minLevel || hasLevel(item.minLevel))

  // Admin items (level 100 only)
  const adminItems = [
    { name: 'User Management', icon: '👥', path: '/admin/users' },
    { name: 'Secrets', icon: '🔐', path: '/admin/secrets' },
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
        {isAuthenticated && designItems.length > 0 && (
          <NavDropdown label="Design" items={designItems} defaultPath="/lab" />
        )}
        {isAuthenticated && (
          <NavDropdown label="Monitor" items={monitorItems} defaultPath="/monitor" />
        )}
        {isAuthenticated && (
          <Link to="/deployments">Deployments</Link>
        )}
        {isAuthenticated && hasLevel(100) && (
          <NavDropdown label="Admin" items={adminItems} defaultPath="/admin/users" />
        )}
        <Link to="/player">Player Portal</Link>
      </div>
      <div className="nav-status">
        {radioState.isPlaying && (
          <span className="radio-indicator">🎵</span>
        )}
        {loading ? (
          <span style={{
            padding: '8px 16px',
            borderRadius: '20px',
            fontSize: '14px',
            fontWeight: '600',
            whiteSpace: 'nowrap',
            background: 'rgba(116, 185, 255, 0.2)',
            color: '#74b9ff',
          }}>Checking...</span>
        ) : healthStatus ? (
          <span style={{
            padding: '8px 16px',
            borderRadius: '20px',
            fontSize: '14px',
            fontWeight: '600',
            whiteSpace: 'nowrap',
            background: 'rgba(107, 207, 127, 0.25)',
            color: '#6bcf7f',
            border: '1px solid rgba(107, 207, 127, 0.4)',
            boxShadow: '0 0 10px rgba(107, 207, 127, 0.3)',
          }}>✓ Connected</span>
        ) : (
          <span style={{
            padding: '8px 16px',
            borderRadius: '20px',
            fontSize: '14px',
            fontWeight: '600',
            whiteSpace: 'nowrap',
            background: 'rgba(255, 107, 107, 0.2)',
            color: '#ff6b6b',
          }}>✗ Disconnected</span>
        )}
        <UserMenu />
      </div>
    </nav>
  )
}

// Main App Content (inside AuthProvider)
function AppContent() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isChatOpen, setIsChatOpen] = useState(false)
  const { isAuthenticated } = useAuth()
  
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
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Dashboard healthStatus={healthStatus} />} />
        <Route path="/features/:featureId" element={<FeatureDetail />} />
        
        {/* Player Portal (public) */}
        <Route path="/player" element={<PlayerPortal />} />
        <Route path="/player/:labId" element={<PlayerLobby />} />
        <Route path="/player/:labId/:vmName" element={<PlayerSession />} />
        
        {/* Protected Routes - Engineer+ */}
        <Route path="/lab" element={
          <ProtectedRoute minLevel={50}>
            <LabCanvas />
          </ProtectedRoute>
        } />
        <Route path="/lab/:labId" element={
          <ProtectedRoute minLevel={50}>
            <LabCanvas />
          </ProtectedRoute>
        } />
        <Route path="/deployments" element={
          <ProtectedRoute minLevel={25}>
            <Deployments />
          </ProtectedRoute>
        } />
        <Route path="/platform/:platform" element={
          <ProtectedRoute minLevel={25}>
            <PlatformStatus />
          </ProtectedRoute>
        } />
        <Route path="/platform/:platform/:instanceId" element={
          <ProtectedRoute minLevel={25}>
            <PlatformStatus />
          </ProtectedRoute>
        } />
        <Route path="/reaper" element={
          <ProtectedRoute minLevel={50}>
            <ReaperDesign />
          </ProtectedRoute>
        } />
        <Route path="/whiteknight" element={
          <ProtectedRoute minLevel={50}>
            <WhiteKnightDesign />
          </ProtectedRoute>
        } />
        <Route path="/whitepawn" element={
          <ProtectedRoute minLevel={25}>
            <WhitePawnMonitor />
          </ProtectedRoute>
        } />
        <Route path="/monitor" element={
          <ProtectedRoute minLevel={25}>
            <LabMonitor />
          </ProtectedRoute>
        } />
        
        {/* Admin Routes (level 100 only) */}
        <Route path="/admin/users" element={
          <ProtectedRoute minLevel={100}>
            <AdminUsers />
          </ProtectedRoute>
        } />
        <Route path="/admin/secrets" element={
          <ProtectedRoute minLevel={100}>
            <AdminSecrets />
          </ProtectedRoute>
        } />
      </Routes>

      {/* Overseer Chat with integrated Radio - only for authenticated users */}
      {isAuthenticated && (
        <>
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
        </>
      )}
    </div>
  )
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </Router>
  )
}

export default App
