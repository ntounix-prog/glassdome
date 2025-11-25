/**
 * Overseer Chat Modal
 * 
 * A slide-out modal chat interface for interacting with the Overseer AI.
 * Supports real-time WebSocket communication with streaming responses.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import ActionConfirm from './ActionConfirm'
import './ChatModal.css'

const CHAT_API_BASE = '/api/chat'
const WS_URL = `ws://${window.location.host}/api/chat/ws`

export default function ChatModal({ isOpen, onClose }) {
  const [messages, setMessages] = useState([])
  const [conversationId, setConversationId] = useState(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [pendingAction, setPendingAction] = useState(null)
  const [streamingContent, setStreamingContent] = useState('')
  
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)

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
      </div>
    </div>
  )
}

