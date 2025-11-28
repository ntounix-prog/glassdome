/**
 * Guacamoleviewer component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

import { useEffect, useRef, useState } from 'react';
import Guacamole from 'guacamole-common-js';
import './GuacamoleViewer.css';

const GUACAMOLE_URL = 'http://192.168.3.8:8080/guacamole';

export default function GuacamoleViewer({ connectionId, onDisconnect }) {
  const displayRef = useRef(null);
  const [client, setClient] = useState(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const [authToken, setAuthToken] = useState(null);

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
          setError('Failed to authenticate with Guacamole');
        }
      } catch (err) {
        setError(`Auth error: ${err.message}`);
      }
    };
    getToken();
  }, []);

  // Connect to Guacamole when we have a token
  useEffect(() => {
    if (!authToken || !connectionId || !displayRef.current) return;

    // Build WebSocket tunnel URL
    const wsUrl = `ws://192.168.3.8:8080/guacamole/websocket-tunnel?token=${authToken}`;
    
    const tunnel = new Guacamole.WebSocketTunnel(wsUrl);
    const guacClient = new Guacamole.Client(tunnel);

    // Handle errors
    guacClient.onerror = (error) => {
      console.error('Guacamole error:', error);
      setError(`Connection error: ${error.message || 'Unknown error'}`);
    };

    // Handle state changes
    guacClient.onstatechange = (state) => {
      switch (state) {
        case Guacamole.Client.State.IDLE:
          console.log('Guacamole: IDLE');
          break;
        case Guacamole.Client.State.CONNECTING:
          console.log('Guacamole: CONNECTING');
          break;
        case Guacamole.Client.State.WAITING:
          console.log('Guacamole: WAITING');
          break;
        case Guacamole.Client.State.CONNECTED:
          console.log('Guacamole: CONNECTED');
          setConnected(true);
          break;
        case Guacamole.Client.State.DISCONNECTING:
          console.log('Guacamole: DISCONNECTING');
          break;
        case Guacamole.Client.State.DISCONNECTED:
          console.log('Guacamole: DISCONNECTED');
          setConnected(false);
          onDisconnect?.();
          break;
      }
    };

    // Get display element and add to DOM
    const display = guacClient.getDisplay().getElement();
    displayRef.current.appendChild(display);

    // Make display fill container
    display.style.width = '100%';
    display.style.height = '100%';

    // Connect
    guacClient.connect(`id=${connectionId}&GUAC_DATA_SOURCE=postgresql&GUAC_TYPE=c&GUAC_WIDTH=1920&GUAC_HEIGHT=1080&GUAC_DPI=96`);
    setClient(guacClient);

    // Mouse handling
    const mouse = new Guacamole.Mouse(display);
    mouse.onEach(['mousedown', 'mouseup', 'mousemove'], (e) => {
      guacClient.sendMouseState(e.state);
    });

    // Keyboard handling
    const keyboard = new Guacamole.Keyboard(document);
    keyboard.onkeydown = (keysym) => {
      guacClient.sendKeyEvent(1, keysym);
    };
    keyboard.onkeyup = (keysym) => {
      guacClient.sendKeyEvent(0, keysym);
    };

    // Cleanup
    return () => {
      keyboard.onkeydown = null;
      keyboard.onkeyup = null;
      guacClient.disconnect();
      if (displayRef.current) {
        displayRef.current.innerHTML = '';
      }
    };
  }, [authToken, connectionId, onDisconnect]);

  // Handle resize
  useEffect(() => {
    if (!client || !connected) return;

    const handleResize = () => {
      const display = client.getDisplay();
      if (displayRef.current) {
        const width = displayRef.current.clientWidth;
        const height = displayRef.current.clientHeight;
        client.sendSize(width, height);
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [client, connected]);

  if (error) {
    return (
      <div className="guac-error">
        <div className="error-icon">⚠️</div>
        <h3>Connection Error</h3>
        <p>{error}</p>
        <button onClick={() => window.location.reload()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="guacamole-viewer">
      {!connected && (
        <div className="guac-connecting">
          <div className="spinner"></div>
          <p>Connecting to remote desktop...</p>
        </div>
      )}
      <div 
        ref={displayRef} 
        className={`guac-display ${connected ? 'connected' : ''}`}
        tabIndex={0}
      />
    </div>
  );
}

