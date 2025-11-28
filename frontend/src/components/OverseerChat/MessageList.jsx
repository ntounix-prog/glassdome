/**
 * Messagelist component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

/**
 * MessageList Component
 * 
 * Displays the chat message history with auto-scroll.
 */

import { useEffect, useRef } from 'react'
import './MessageList.css'

export default function MessageList({ messages, streamingContent, isLoading }) {
  const messagesEndRef = useRef(null)
  const containerRef = useRef(null)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, streamingContent])

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const formatContent = (content) => {
    // Simple markdown-like formatting
    // Code blocks
    content = content.replace(/```(\w*)\n?([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
    // Inline code
    content = content.replace(/`([^`]+)`/g, '<code>$1</code>')
    // Bold
    content = content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Line breaks
    content = content.replace(/\n/g, '<br/>')
    
    return content
  }

  return (
    <div className="message-list" ref={containerRef}>
      {messages.map((message) => (
        <div
          key={message.id}
          className={`message message-${message.role}`}
        >
          <div className="message-avatar">
            {message.role === 'user' ? '👤' : message.role === 'assistant' ? '🧠' : '⚠️'}
          </div>
          <div className="message-content">
            <div 
              className="message-text"
              dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
            />
            {message.actionResult && (
              <div className="message-action-result">
                <div className="action-result-header">
                  {message.actionResult.success ? '✅ Action Completed' : '❌ Action Failed'}
                </div>
                {message.actionResult.message && (
                  <div className="action-result-message">{message.actionResult.message}</div>
                )}
              </div>
            )}
            <div className="message-timestamp">
              {formatTimestamp(message.timestamp)}
            </div>
          </div>
        </div>
      ))}
      
      {/* Streaming message */}
      {(isLoading || streamingContent) && (
        <div className="message message-assistant">
          <div className="message-avatar">🧠</div>
          <div className="message-content">
            <div 
              className="message-text"
              dangerouslySetInnerHTML={{ 
                __html: streamingContent 
                  ? formatContent(streamingContent) 
                  : '<span class="typing-indicator">●●●</span>' 
              }}
            />
          </div>
        </div>
      )}
      
      <div ref={messagesEndRef} />
    </div>
  )
}

