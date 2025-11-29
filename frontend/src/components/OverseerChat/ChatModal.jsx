/**
 * Overseer Chat Modal with Contextual Help
 * 
 * A slide-out modal chat interface for interacting with the Overseer AI.
 * Supports real-time WebSocket communication with streaming responses.
 * Includes integrated SomaFM radio player and page-specific help.
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { useLocation } from 'react-router-dom'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import ActionConfirm from './ActionConfirm'
import { getHelpForRoute, getHelpContextForOverseer } from '../../help-content'
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

export default function ChatModal({ isOpen, onClose, audioRef, radioState, setRadioState, onMusicStateChange }) {
  const location = useLocation()
  const [activeTab, setActiveTab] = useState('chat') // 'chat' | 'help'
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [streamingContent, setStreamingContent] = useState('')
  const [radioExpanded, setRadioExpanded] = useState(false) // Start collapsed
  
  // Get help content for current page
  const currentHelp = getHelpForRoute(location.pathname)
  const helpContext = getHelpContextForOverseer(location.pathname)
  
  // Internal audio state if not provided externally
  const internalAudioRef = useRef(null)
  const [internalRadioState, setInternalRadioState] = useState({
    isPlaying: false,
    volume: 0.7,
    currentStation: 'defcon'
  })
  
  // Use external or internal state
  const effectiveAudioRef = audioRef || internalAudioRef
  const effectiveRadioState = radioState || internalRadioState
  const effectiveSetRadioState = setRadioState || setInternalRadioState
  
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  
  // Radio controls
  const station = STATIONS[effectiveRadioState.currentStation]
  
  // Notify parent of music state changes
  useEffect(() => {
    if (onMusicStateChange) {
      onMusicStateChange(effectiveRadioState.isPlaying)
    }
  }, [effectiveRadioState.isPlaying, onMusicStateChange])
  
  const toggleRadioPlay = async () => {
    if (!effectiveAudioRef.current) return
    if (effectiveRadioState.isPlaying) {
      effectiveAudioRef.current.pause()
      effectiveSetRadioState(prev => ({ ...prev, isPlaying: false }))
    } else {
      try {
        await effectiveAudioRef.current.play()
        effectiveSetRadioState(prev => ({ ...prev, isPlaying: true }))
      } catch (err) {
        console.error('Playback failed:', err)
      }
    }
  }
  
  const changeStation = (stationId) => {
    const wasPlaying = effectiveRadioState.isPlaying
    if (effectiveAudioRef.current) effectiveAudioRef.current.pause()
    effectiveSetRadioState(prev => ({ ...prev, currentStation: stationId, isPlaying: false }))
    
    if (wasPlaying) {
      setTimeout(() => {
        if (effectiveAudioRef.current) {
          effectiveAudioRef.current.src = STATIONS[stationId].stream
          effectiveAudioRef.current.play()
            .then(() => effectiveSetRadioState(prev => ({ ...prev, isPlaying: true })))
            .catch(console.error)
        }
      }, 100)
    }
  }
  
  const setVolume = (vol) => {
    effectiveSetRadioState(prev => ({ ...prev, volume: vol }))
    if (effectiveAudioRef.current) {
      effectiveAudioRef.current.volume = vol
    }
  }

  // Initialize conversation and WebSocket
  useEffect(() => {
    if (!isOpen) return
    
    const initConversation = async () => {
      try {
        const response = await fetch(`${CHAT_API_BASE}/conversations`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        const data = await response.json()
        setConversationId(data.conversation_id)
      } catch (error) {
        console.error('Failed to create conversation:', error)
      }
    }

    initConversation()
  }, [isOpen])

  // WebSocket connection management
  useEffect(() => {
    if (!isOpen || !conversationId) return

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}/${conversationId}`)
      
      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
      }
      
      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      ws.onmessage = (event) => {
        handleWebSocketMessage(event.data)
      }
      
      wsRef.current = ws
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [isOpen, conversationId])

  // Heartbeat to keep connection alive
  useEffect(() => {
    if (!isOpen || !isConnected) return

    const heartbeat = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 30000)

    return () => clearInterval(heartbeat)
  }, [isOpen, isConnected])

  const handleWebSocketMessage = useCallback((data) => {
    try {
      const parsed = JSON.parse(data)
      
      switch (parsed.type) {
        case 'response':
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'assistant',
            content: parsed.content,
            timestamp: new Date().toISOString()
          }])
          setIsLoading(false)
          break
          
        case 'stream':
          setStreamingContent(prev => prev + parsed.content)
          break
          
        case 'stream_end':
          if (streamingContent) {
            setMessages(prev => [...prev, {
              id: `msg-${Date.now()}`,
              role: 'assistant',
              content: streamingContent,
              timestamp: new Date().toISOString()
            }])
            setStreamingContent('')
          }
          setIsLoading(false)
          break
          
        case 'action_required':
          setPendingAction(parsed.action)
          break
          
        case 'tool_result':
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'system',
            content: `Tool executed: ${parsed.tool}\nResult: ${JSON.stringify(parsed.result, null, 2)}`,
            timestamp: new Date().toISOString()
          }])
          break
          
        case 'error':
          setIsLoading(false)
          setMessages(prev => [...prev, {
            id: `msg-${Date.now()}`,
            role: 'system',
            content: `Error: ${parsed.error}`,
            timestamp: new Date().toISOString()
          }])
          break
          
        case 'pong':
          break
          
        default:
          console.log('Unknown message type:', parsed.type)
      }
    } catch (e) {
      console.error('Failed to parse message:', e)
    }
  }, [streamingContent])

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
    
    // Prepend page context to the message for Overseer
    const contextualMessage = `[User is on page: ${currentHelp.title}]\n\n${content}`
    
    // Send via WebSocket if connected
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      setIsLoading(true)
      wsRef.current.send(JSON.stringify({
        type: 'message',
        content: contextualMessage,
        context: helpContext, // Send help context as additional data
        stream: false
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
            body: JSON.stringify({ 
              message: contextualMessage, 
              context: helpContext,
              stream: false 
            })
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

  // Ask Overseer about a specific help topic
  const askAboutTopic = (topic) => {
    setActiveTab('chat')
    sendMessage(`Tell me more about: ${topic.title}`)
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
        
        {/* Tab Navigation */}
        <div className="chat-tabs">
          <button 
            className={`chat-tab ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            💬 Chat
          </button>
          <button 
            className={`chat-tab ${activeTab === 'help' ? 'active' : ''}`}
            onClick={() => setActiveTab('help')}
          >
            ❓ Help: {currentHelp.title}
          </button>
        </div>
        
        {/* Chat Tab */}
        {activeTab === 'chat' && (
          <>
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
                    : `Ask about ${currentHelp.title}...`
                }
              />
            </div>
          </>
        )}
        
        {/* Help Tab */}
        {activeTab === 'help' && (
          <div className="help-tab-content">
            <div className="help-page-header">
              <span className="help-page-role">{currentHelp.role.toUpperCase()}</span>
              <h2>{currentHelp.title}</h2>
              <p>{currentHelp.summary}</p>
            </div>
            
            <div className="help-topics">
              {currentHelp.topics.map((topic, idx) => (
                <div key={idx} className="help-topic">
                  <div className="help-topic-header">
                    <h3>{topic.title}</h3>
                    <button 
                      className="help-ask-btn"
                      onClick={() => askAboutTopic(topic)}
                      title="Ask Overseer about this"
                    >
                      💬 Ask
                    </button>
                  </div>
                  <div className="help-topic-content">
                    {topic.content.split('\n').map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            
            {currentHelp.quickActions.length > 0 && (
              <div className="help-quick-actions">
                <h4>Quick Actions</h4>
                {currentHelp.quickActions.map((action, idx) => (
                  <div key={idx} className="help-action">
                    <span className="help-action-label">{action.label}</span>
                    <span className="help-action-hint">{action.action}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
        
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
              {effectiveRadioState.isPlaying && (
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
                  className={`radio-play-btn ${effectiveRadioState.isPlaying ? 'playing' : ''}`}
                  onClick={toggleRadioPlay}
                  style={{ '--accent': station.color }}
                >
                  {effectiveRadioState.isPlaying ? '❚❚' : '▶'}
                </button>
                
                <div className="radio-volume">
                  <span>{effectiveRadioState.volume === 0 ? '🔇' : effectiveRadioState.volume < 0.5 ? '🔉' : '🔊'}</span>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={effectiveRadioState.volume}
                    onChange={(e) => setVolume(parseFloat(e.target.value))}
                    style={{ '--accent': station.color }}
                  />
                </div>
                
                {effectiveRadioState.isPlaying && (
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
                    className={`radio-station-btn ${effectiveRadioState.currentStation === id ? 'active' : ''}`}
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
      
      {/* Internal audio element when no external ref provided */}
      {!audioRef && (
        <audio 
          ref={internalAudioRef}
          src={STATIONS[effectiveRadioState.currentStation].stream}
          preload="none"
        />
      )}
    </div>
  )
}
