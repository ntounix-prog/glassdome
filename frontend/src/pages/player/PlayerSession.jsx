/**
 * PlayerSession - VM desktop viewer using Guacamole
 * 
 * This component embeds the Guacamole remote desktop client using guacamole-common-js.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Guacamole from 'guacamole-common-js';
import ChatModal from '../../components/OverseerChat/ChatModal';
import LabTimer from './components/LabTimer';
import '../../styles/player/PlayerSession.css';

// Updock (Guacamole) server - use relative URL for proxy, or direct for fallback
const UPDOCK_HOST = '192.168.3.8:8080';
const GUACAMOLE_URL = '/guacamole'; // Proxied through Vite
const GUACAMOLE_DIRECT_URL = `http://${UPDOCK_HOST}/guacamole`; // Direct access fallback

// Connection map - patterns to guacamole connection ID
// In production, this would be fetched from an API
const CONNECTION_MAP = {
  // SSH connections
  'kali-ssh': '5',
  'ubuntu-ssh': '6',
  // RDP connections
  'kali-rdp': '7',
  'ubuntu-rdp': '8',
};

// Extract VM type from name (e.g., "brettlab-kali-00" -> "kali")
const extractVmType = (vmName) => {
  const lowerName = vmName.toLowerCase();
  if (lowerName.includes('kali')) return 'kali';
  if (lowerName.includes('ubuntu')) return 'ubuntu';
  if (lowerName.includes('windows')) return 'windows';
  return 'unknown';
};

export default function PlayerSession() {
  const { labId, vmName } = useParams();
  const navigate = useNavigate();
  const displayRef = useRef(null);
  const clientRef = useRef(null);
  const keyboardRef = useRef(null);
  
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [connectionState, setConnectionState] = useState('connecting');
  const [connectionError, setConnectionError] = useState('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMusicPlaying, setIsMusicPlaying] = useState(false);
  const [showToolbar, setShowToolbar] = useState(true);
  const [authToken, setAuthToken] = useState(null);
  const [connectionMode, setConnectionMode] = useState('rdp'); // 'ssh' or 'rdp'
  const [scale, setScale] = useState(1);

  // Get auth token on mount
  useEffect(() => {
    const getToken = async () => {
      try {
        const response = await fetch(`${GUACAMOLE_URL}/api/tokens`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: 'username=guacadmin&password=guacadmin',
        });
        const data = await response.json();
        if (data.authToken) {
          setAuthToken(data.authToken);
        } else {
          setConnectionError('Failed to authenticate with Guacamole');
          setConnectionState('error');
        }
      } catch (err) {
        setConnectionError(`Auth error: ${err.message}`);
        setConnectionState('error');
      }
    };
    getToken();
  }, []);

  // Get connection ID based on VM name and mode
  const getConnectionId = useCallback(() => {
    const vmType = extractVmType(vmName);
    const key = `${vmType}-${connectionMode}`;
    console.log(`Looking up connection: vmName=${vmName}, vmType=${vmType}, mode=${connectionMode}, key=${key}`);
    return CONNECTION_MAP[key];
  }, [vmName, connectionMode]);

  // Connect to Guacamole
  useEffect(() => {
    if (!authToken || !displayRef.current) return;

    const connectionId = getConnectionId();
    if (!connectionId) {
      setConnectionError(`No connection found for ${vmName}. Please use Guacamole directly.`);
      setConnectionState('error');
      return;
    }

    // Clean up previous connection
    if (clientRef.current) {
      clientRef.current.disconnect();
    }
    if (displayRef.current) {
      displayRef.current.innerHTML = '';
    }

    setConnectionState('connecting');

    // Create WebSocket tunnel - use current host for proxy
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/guacamole/websocket-tunnel`;
    const tunnel = new Guacamole.WebSocketTunnel(wsUrl);
    const client = new Guacamole.Client(tunnel);
    clientRef.current = client;

    // Error handler
    tunnel.onerror = (status) => {
      console.error('Tunnel error:', status);
      setConnectionError(`Tunnel error: ${status.message || 'Connection failed'}`);
      setConnectionState('error');
    };

    client.onerror = (status) => {
      console.error('Client error:', status);
      setConnectionError(`Client error: ${status.message || 'Unknown error'}`);
      setConnectionState('error');
    };

    // State change handler
    client.onstatechange = (state) => {
      switch (state) {
        case Guacamole.Client.State.IDLE:
          setConnectionState('idle');
          break;
        case Guacamole.Client.State.CONNECTING:
          setConnectionState('connecting');
          break;
        case Guacamole.Client.State.WAITING:
          setConnectionState('waiting');
          break;
        case Guacamole.Client.State.CONNECTED:
          setConnectionState('connected');
          break;
        case Guacamole.Client.State.DISCONNECTING:
          setConnectionState('disconnecting');
          break;
        case Guacamole.Client.State.DISCONNECTED:
          setConnectionState('disconnected');
          break;
        default:
          break;
      }
    };

    // Get display and add to DOM
    const display = client.getDisplay();
    const displayElement = display.getElement();
    displayRef.current.appendChild(displayElement);

    // Handle display scaling
    const updateScale = () => {
      if (!displayRef.current) return;
      const containerWidth = displayRef.current.clientWidth;
      const containerHeight = displayRef.current.clientHeight;
      const displayWidth = display.getWidth();
      const displayHeight = display.getHeight();
      
      if (displayWidth && displayHeight) {
        const scaleX = containerWidth / displayWidth;
        const scaleY = containerHeight / displayHeight;
        const newScale = Math.min(scaleX, scaleY, 1);
        display.scale(newScale);
        setScale(newScale);
      }
    };

    display.onresize = updateScale;
    window.addEventListener('resize', updateScale);

    // Mouse handling
    const mouse = new Guacamole.Mouse(displayElement);
    mouse.onEach(['mousedown', 'mouseup', 'mousemove'], (e) => {
      if (connectionState === 'connected') {
        client.sendMouseState(e.state);
      }
    });

    // Keyboard handling
    const keyboard = new Guacamole.Keyboard(displayElement);
    keyboardRef.current = keyboard;
    
    keyboard.onkeydown = (keysym) => {
      client.sendKeyEvent(1, keysym);
      return true; // Prevent default
    };
    
    keyboard.onkeyup = (keysym) => {
      client.sendKeyEvent(0, keysym);
      return true;
    };

    // Build connection parameters
    const params = new URLSearchParams({
      token: authToken,
      'GUAC_DATA_SOURCE': 'postgresql',
      'GUAC_ID': connectionId,
      'GUAC_TYPE': 'c',
      'GUAC_WIDTH': window.innerWidth.toString(),
      'GUAC_HEIGHT': window.innerHeight.toString(),
      'GUAC_DPI': '96',
    });

    // Connect
    try {
      client.connect(params.toString());
    } catch (err) {
      console.error('Connect error:', err);
      setConnectionError(`Connect error: ${err.message}`);
      setConnectionState('error');
    }

    // Cleanup
    return () => {
      window.removeEventListener('resize', updateScale);
      if (keyboard) {
        keyboard.onkeydown = null;
        keyboard.onkeyup = null;
      }
      if (client) {
        client.disconnect();
      }
    };
  }, [authToken, getConnectionId, vmName]);

  // Auto-hide toolbar in fullscreen
  useEffect(() => {
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
  }, [isFullscreen]);

  const getOSIcon = () => {
    if (vmName.includes('kali')) return '🐉';
    if (vmName.includes('ubuntu')) return '🐧';
    if (vmName.includes('windows') || vmName.includes('win')) return '🪟';
    return '🖥️';
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
    if (clientRef.current) {
      clientRef.current.disconnect();
    }
    navigate(`/player/${labId}`);
  };

  const sendCtrlAltDel = () => {
    if (clientRef.current && connectionState === 'connected') {
      // Send Ctrl+Alt+Del key sequence
      const ctrl = 0xFFE3;
      const alt = 0xFFE9;
      const del = 0xFFFF;
      
      clientRef.current.sendKeyEvent(1, ctrl);
      clientRef.current.sendKeyEvent(1, alt);
      clientRef.current.sendKeyEvent(1, del);
      clientRef.current.sendKeyEvent(0, del);
      clientRef.current.sendKeyEvent(0, alt);
      clientRef.current.sendKeyEvent(0, ctrl);
    }
  };

  const toggleConnectionMode = () => {
    const newMode = connectionMode === 'rdp' ? 'ssh' : 'rdp';
    setConnectionMode(newMode);
    // Will trigger reconnection via useEffect
  };

  const focusDisplay = () => {
    if (displayRef.current) {
      displayRef.current.focus();
    }
  };

  const getStatusText = () => {
    switch (connectionState) {
      case 'connecting': return 'Connecting...';
      case 'waiting': return 'Waiting for server...';
      case 'connected': return 'Connected';
      case 'disconnecting': return 'Disconnecting...';
      case 'disconnected': return 'Disconnected';
      case 'error': return 'Error';
      default: return 'Idle';
    }
  };

  return (
    <div className={`player-session ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Toolbar */}
      <div className={`session-toolbar ${showToolbar ? 'visible' : 'hidden'}`}>
        <div className="toolbar-left">
          <button className="toolbar-button back-button" onClick={handleBack}>
            ← Back
          </button>
          <div className="vm-info">
            <span className="vm-icon">{getOSIcon()}</span>
            <span className="vm-name">{vmName}</span>
            <span className={`connection-status ${connectionState}`}>
              ● {getStatusText()}
            </span>
          </div>
        </div>
        
        <div className="toolbar-center">
          <LabTimer compact />
        </div>
        
        <div className="toolbar-right">
          <button 
            className={`toolbar-button mode-toggle ${connectionMode}`}
            onClick={toggleConnectionMode}
            title={`Switch to ${connectionMode === 'rdp' ? 'SSH' : 'RDP'}`}
          >
            {connectionMode === 'rdp' ? '🖥️ RDP' : '⌨️ SSH'}
          </button>
          <button 
            className="toolbar-button" 
            onClick={sendCtrlAltDel}
            title="Send Ctrl+Alt+Del"
            disabled={connectionState !== 'connected'}
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
      <div className="desktop-container" onClick={focusDisplay}>
        {connectionState === 'error' || connectionState === 'connecting' ? (
          <div className="connection-fallback">
            <div className="fallback-icon">{getOSIcon()}</div>
            <h2>{vmName}</h2>
            <p className="fallback-subtitle">Remote Desktop Session</p>
            
            {connectionState === 'error' && (
              <p className="error-message">⚠️ {connectionError}</p>
            )}
            
            <div className="fallback-actions">
              <a 
                href={GUACAMOLE_DIRECT_URL} 
                target="_blank" 
                rel="noopener noreferrer"
                className="open-desktop-btn"
              >
                🖥️ Open Desktop in Guacamole
              </a>
              
              <p className="fallback-hint">
                Login: <code>guacadmin</code> / <code>guacadmin</code>
              </p>
              <p className="fallback-hint">
                Select: <code>🖥️ brettlab-{vmName.includes('kali') ? 'kali' : 'ubuntu'}-rdp</code>
              </p>
            </div>
          </div>
        ) : (
          <>
            {connectionState === 'connecting' && (
              <div className="connection-overlay">
                <div className="spinner"></div>
                <p>Connecting to {vmName}...</p>
                <p className="sub">Mode: {connectionMode.toUpperCase()}</p>
              </div>
            )}
            <div 
              ref={displayRef} 
              className={`guac-display ${connectionState === 'connected' ? 'active' : ''}`}
              tabIndex={0}
            />
          </>
        )}
      </div>

      {/* Floating Chat */}
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
