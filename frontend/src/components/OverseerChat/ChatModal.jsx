/**
 * Overseer Chat Modal
 * 
 * A slide-out modal chat interface for interacting with the Overseer AI.
 * Supports real-time WebSocket communication with streaming responses.
 * Includes integrated SomaFM radio player at the bottom.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import ActionConfirm from './ActionConfirm'
import './ChatModal.css'

const CHAT_API_BASE = '/api/chat'
const WS_URL = `ws://${window.location.host}/api/chat/ws`

// SomaFM stations
const STATIONS = {
  defcon: { name: 'DEF CON', stream: 'https://ice1.somafm.com/defcon-128-mp3', icon: '💀', color: '#00ff41' },
  deepspaceone: { name: 'Deep Space', stream: 'https://ice1.somafm.com/deepspaceone-128-mp3', icon: '🚀', color: '#8b5cf6' },
  darkzone: { name: 'Dark Zone', stream: 'https://ice1.somafm.com/darkzone-128-mp3', icon: '🌑', color: '#ef4444' },
  dronezone: { name: 'Drone Zone', stream: 'https://ice1.somafm.com/dronezone-128-mp3', icon: '🎧', color: '#06b6d4' },
  spacestation: { name: 'Space Station', stream: 'https://ice1.somafm.com/spacestation-128-mp3', icon: '🛸', color: '#f59e0b' },
  cliqhop: { name: 'cliqhop', stream: 'https://ice1.somafm.com/cliqhop-128-mp3', icon: '🎹', color: '#ec4899' },
}

export default function ChatModal({ isOpen, onClose, audioRef, radioState, setRadioState }) {
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [streamingContent, setStreamingContent] = useState('')
  const [radioExpanded, setRadioExpanded] = useState(true)
  
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  
  // Radio controls
  const station = STATIONS[radioState.currentStation]
  
  const toggleRadioPlay = async () => {
    if (!audioRef.current) return
    if (radioState.isPlaying) {
      audioRef.current.pause()
      setRadioState(prev => ({ ...prev, isPlaying: false }))
    } else {
      try {
        await audioRef.current.play()
        setRadioState(prev => ({ ...prev, isPlaying: true }))
      } catch (err) {
        console.error('Playback failed:', err)
      }
    }
  }
  
  const changeStation = (stationId) => {
    const wasPlaying = radioState.isPlaying
    if (audioRef.current) audioRef.current.pause()
    setRadioState(prev => ({ ...prev, currentStation: stationId, isPlaying: false }))
    
    if (wasPlaying) {
      setTimeout(() => {
        if (audioRef.current) {
          audioRef.current.src = STATIONS[stationId].stream
          audioRef.current.play()
            .then(() => setRadioState(prev => ({ ...prev, isPlaying: true })))
            .catch(console.error)
        }
      }, 100)
    }
  }
  
  const setVolume = (vol) => {
    setRadioState(prev => ({ ...prev, volume: vol }))
    if (audioRef.current) audioRef.current.volume = vol
  }

  // Initialize conversation and WebSocket on open
  useEffect(() => {
    if (isOpen && !conversationId) {
      initializeConversation()
    }
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [isOpen])

  // Connect/disconnect WebSocket when conversation changes
  useEffect(() => {
    if (conversationId && isOpen) {
      connectWebSocket()
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [conversationId, isOpen])

  const initializeConversation = async () => {
    try {
      const response = await fetch(`${CHAT_API_BASE}/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      setConversationId(data.conversation_id)
      
      // Add welcome message
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: "Hello! I'm Overseer, your operations assistant. I can help you deploy labs, create Reaper missions, or check system status. What would you like to do?",
        timestamp: new Date().toISOString()
      }])
    } catch (error) {
      console.error('Failed to initialize conversation:', error)
      setMessages([{
        id: 'error',
        role: 'system',
        content: 'Failed to connect to Overseer. Please try again.',
        timestamp: new Date().toISOString()
      }])
    }
  }

  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return
    }

    const ws = new WebSocket(`${WS_URL}/${conversationId}`)
    
    ws.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
    }
    
    ws.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
      
      // Attempt reconnection after 3 seconds
      if (isOpen) {
        reconnectTimeoutRef.current = setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }
    }
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      handleWebSocketMessage(data)
    }
    
    wsRef.current = ws
  }, [conversationId, isOpen])

  const handleWebSocketMessage = (data) => {
    switch (data.type) {
      case 'connected':
        // Already handled welcome message
        break
        
      case 'start':
        // Start of streaming response
        setIsLoading(true)
        setStreamingContent('')
        break
        
      case 'chunk':
        // Streaming chunk
        setStreamingContent(prev => prev + data.content)
        break
        
      case 'complete':
        // Response complete
        setIsLoading(false)
        if (streamingContent || data.response) {
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: data.response || streamingContent,
            timestamp: new Date().toISOString()
          }])
        }
        setStreamingContent('')
        break
        
      case 'action':
        // Pending action needs confirmation
        setPendingAction(data.action)
        break
        
      case 'action_result':
        // Action was processed
        setPendingAction(null)
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString(),
          actionResult: data.result
        }])
        break
        
      case 'error':
        setIsLoading(false)
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          role: 'system',
          content: `Error: ${data.error}`,
          timestamp: new Date().toISOString()
        }])
        break
        
      case 'pong':
        // Heartbeat response
        break
        
      default:
        console.log('Unknown message type:', data.type)
    }
  }

  const sendMessage = async (content) => {
    if (!content.trim() || isLoading) return
    
    // Add user message to UI
    const userMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: content,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    
    // Send via WebSocket if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setIsLoading(true)
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: content,
        stream: false  // Use non-streaming to support tool calls
      }))
    } else {
      // Fallback to REST API
      try {
        setIsLoading(true)
        const response = await fetch(
          `${CHAT_API_BASE}/conversations/${conversationId}/messages`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: content, stream: false })
          }
        )
        const data = await response.json()
        
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: data.response,
          timestamp: new Date().toISOString()
        }])
        
        if (data.pending_action) {
          setPendingAction(data.pending_action)
        }
      } catch (error) {
        console.error('Failed to send message:', error)
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          role: 'system',
          content: 'Failed to send message. Please try again.',
          timestamp: new Date().toISOString()
        }])
      } finally {
        setIsLoading(false)
      }
    }
  }

  const handleActionConfirm = (approved) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'confirm',
        approved: approved
      }))
    }
    setPendingAction(null)
  }

  const handleClose = () => {
    if (wsRef.current) {
      wsRef.current.close()
    }
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="chat-modal-overlay" onClick={handleClose}>
      <div className="chat-modal" onClick={e => e.stopPropagation()}>
        <div className="chat-header">
          <div className="chat-header-left">
            <div className="chat-avatar">🧠</div>
            <div className="chat-title">
              <h3>Overseer</h3>
              <span className={`chat-status ${isConnected ? 'connected' : 'disconnected'}`}>
                {isConnected ? 'Connected' : 'Reconnecting...'}
              </span>
            </div>
          </div>
          <button className="chat-close-btn" onClick={handleClose}>
            ✕
          </button>
        </div>
        
        <div className="chat-body">
          <MessageList 
            messages={messages} 
            streamingContent={streamingContent}
            isLoading={isLoading}
          />
          
          {pendingAction && (
            <ActionConfirm 
              action={pendingAction}
              onConfirm={() => handleActionConfirm(true)}
              onReject={() => handleActionConfirm(false)}
            />
          )}
        </div>
        
        <div className="chat-footer">
          <MessageInput 
            onSend={sendMessage}
            disabled={isLoading || !!pendingAction}
            placeholder={
              pendingAction 
                ? "Please confirm or reject the action above..." 
                : "Ask Overseer anything..."
            }
          />
        </div>
        
        {/* Integrated Radio Player */}
        <div className={`radio-section ${radioExpanded ? 'expanded' : 'collapsed'}`}>
          <div 
            className="radio-section-header"
            onClick={() => setRadioExpanded(!radioExpanded)}
            style={{ borderColor: station.color }}
          >
            <div className="radio-section-title">
              <span className="radio-station-icon" style={{ textShadow: `0 0 10px ${station.color}` }}>
                {station.icon}
              </span>
              <span className="radio-station-name">{station.name}</span>
              {radioState.isPlaying && (
                <span className="radio-playing-badge" style={{ background: station.color }}>▶</span>
              )}
            </div>
            <div className="radio-section-controls">
              <span className="radio-toggle-hint">{radioExpanded ? '▼' : '▲'}</span>
            </div>
          </div>
          
          {radioExpanded && (
            <div className="radio-section-body">
              <div className="radio-player-row">
                <button 
                  className={`radio-play-btn ${radioState.isPlaying ? 'playing' : ''}`}
                  onClick={toggleRadioPlay}
                  style={{ '--accent': station.color }}
                >
                  {radioState.isPlaying ? '❚❚' : '▶'}
                </button>
                
                <div className="radio-volume">
                  <span>{radioState.volume === 0 ? '🔇' : radioState.volume < 0.5 ? '🔉' : '🔊'}</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={radioState.volume}
                    onChange={(e) => setVolume(parseFloat(e.target.value))}
                    style={{ '--accent': station.color }}
                  />
                </div>
                
                {radioState.isPlaying && (
                  <div className="radio-visualizer-mini">
                    {[...Array(5)].map((_, i) => (
                      <div key={i} className="bar" style={{ '--accent': station.color, animationDelay: `${i * 0.1}s` }} />
                    ))}
                  </div>
                )}
              </div>
              
              <div className="radio-stations-row">
                {Object.entries(STATIONS).map(([id, s]) => (
                  <button
                    key={id}
                    className={`radio-station-btn ${radioState.currentStation === id ? 'active' : ''}`}
                    onClick={() => changeStation(id)}
                    title={s.name}
                    style={{ '--color': s.color }}
                  >
                    {s.icon}
                  </button>
                ))}
                <a href="https://somafm.com" target="_blank" rel="noopener noreferrer" className="somafm-link">
                  SomaFM
                </a>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

