/**
 * PlayerSession - VM desktop viewer using Guacamole
 * 
 * This component embeds the Guacamole remote desktop client.
 * For now, it uses an iframe to the Guacamole web UI.
 * Future: Use guacamole-common-js for native integration.
 */

import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ChatModal from '../../components/OverseerChat/ChatModal';
import ChatToggle from '../../components/OverseerChat/ChatToggle';
import LabTimer from './components/LabTimer';
import '../../styles/player/PlayerSession.css';

// Updock (Guacamole) server
const UPDOCK_URL = 'http://192.168.3.8:8080/guacamole';

export default function PlayerSession() {
  const { labId, vmName } = useParams();
  const navigate = useNavigate();
  const iframeRef = useRef(null);
  
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMusicPlaying, setIsMusicPlaying] = useState(false);
  const [showToolbar, setShowToolbar] = useState(true);
  const [vmInfo, setVmInfo] = useState(null);

  useEffect(() => {
    // Fetch VM info
    fetchVmInfo();
    
    // Auto-hide toolbar after 3 seconds of inactivity
    let hideTimer;
    const handleMouseMove = () => {
      setShowToolbar(true);
      clearTimeout(hideTimer);
      hideTimer = setTimeout(() => {
        if (isFullscreen) setShowToolbar(false);
      }, 3000);
    };
    
    window.addEventListener('mousemove', handleMouseMove);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      clearTimeout(hideTimer);
    };
  }, [labId, vmName, isFullscreen]);

  const fetchVmInfo = async () => {
    try {
      // Try to get VM details
      const response = await fetch(`/api/deployments/${labId}`);
      if (response.ok) {
        const data = await response.json();
        const vm = data.vms?.find(v => v.name === vmName);
        setVmInfo(vm || { name: vmName, os: 'unknown' });
      } else {
        setVmInfo({ name: vmName, os: detectOS(vmName) });
      }
      setIsConnected(true);
    } catch (err) {
      setVmInfo({ name: vmName, os: detectOS(vmName) });
      setIsConnected(true);
    }
  };

  const detectOS = (name) => {
    if (name.includes('kali')) return 'kali';
    if (name.includes('ubuntu')) return 'ubuntu';
    if (name.includes('windows') || name.includes('win')) return 'windows';
    return 'linux';
  };

  const getOSIcon = (os) => {
    switch (os) {
      case 'kali': return '🐉';
      case 'ubuntu': return '🐧';
      case 'windows': return '🪟';
      default: return '🖥️';
    }
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const handleBack = () => {
    navigate(`/player/${labId}`);
  };

  const sendCtrlAltDel = () => {
    // This would require guacamole-common-js integration
    // For now, just show a message
    alert('Ctrl+Alt+Del sent (requires native Guacamole integration)');
  };

  const handleClipboard = () => {
    // Clipboard sync would require guacamole-common-js
    alert('Clipboard sync (requires native Guacamole integration)');
  };

  // Build Guacamole connection URL
  // Format: /guacamole/#/client/{connectionId}
  // For now, we'll link to the main Guacamole page
  const guacamoleUrl = `${UPDOCK_URL}/#/`;

  return (
    <div className={`player-session ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Toolbar */}
      <div className={`session-toolbar ${showToolbar ? 'visible' : 'hidden'}`}>
        <div className="toolbar-left">
          <button className="toolbar-button back-button" onClick={handleBack}>
            ← Back
          </button>
          <div className="vm-info">
            <span className="vm-icon">{getOSIcon(vmInfo?.os)}</span>
            <span className="vm-name">{vmName}</span>
            <span className={`connection-status ${isConnected ? 'connected' : ''}`}>
              {isConnected ? '● Connected' : '○ Connecting...'}
            </span>
          </div>
        </div>
        
        <div className="toolbar-center">
          <LabTimer compact />
        </div>
        
        <div className="toolbar-right">
          <button 
            className="toolbar-button" 
            onClick={handleClipboard}
            title="Clipboard"
          >
            📋
          </button>
          <button 
            className="toolbar-button" 
            onClick={sendCtrlAltDel}
            title="Send Ctrl+Alt+Del"
          >
            ⌨️
          </button>
          <button 
            className="toolbar-button" 
            onClick={toggleFullscreen}
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? '⊙' : '⛶'}
          </button>
          <button 
            className="toolbar-button chat-button" 
            onClick={() => setIsChatOpen(true)}
            title="AI Assistant"
          >
            💬
          </button>
        </div>
      </div>

      {/* Desktop Viewer */}
      <div className="desktop-container">
        {connectionError ? (
          <div className="connection-error">
            <span className="error-icon">⚠️</span>
            <h2>Connection Failed</h2>
            <p>{connectionError}</p>
            <button onClick={fetchVmInfo}>Retry</button>
          </div>
        ) : (
          <>
            {/* Placeholder until Guacamole connection is configured */}
            <div className="desktop-placeholder">
              <div className="placeholder-content">
                <div className="placeholder-icon">{getOSIcon(vmInfo?.os)}</div>
                <h2>{vmName}</h2>
                <p>Remote Desktop Session</p>
                
                <div className="connection-options">
                  <a 
                    href={guacamoleUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="connect-button"
                  >
                    🔗 Open in Updock (Guacamole)
                  </a>
                  
                  <div className="manual-info">
                    <p className="info-label">Or connect manually:</p>
                    <div className="info-grid">
                      <span className="label">Guacamole:</span>
                      <code>{UPDOCK_URL}</code>
                      <span className="label">Login:</span>
                      <code>guacadmin / guacadmin</code>
                    </div>
                  </div>
                </div>
                
                <p className="integration-note">
                  💡 Full embedded desktop coming soon with guacamole-common-js
                </p>
              </div>
            </div>
            
            {/* Future: Native Guacamole viewer 
            <iframe 
              ref={iframeRef}
              src={guacamoleUrl}
              className="guacamole-frame"
              title={`${vmName} Desktop`}
              allowFullScreen
            />
            */}
          </>
        )}
      </div>

      {/* Floating Chat - minimized in session view */}
      {!isChatOpen && (
        <button 
          className="floating-chat-button"
          onClick={() => setIsChatOpen(true)}
        >
          💬
          {isMusicPlaying && <span className="music-indicator">🎵</span>}
        </button>
      )}
      
      <ChatModal 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)}
        onMusicStateChange={setIsMusicPlaying}
      />
    </div>
  );
}

