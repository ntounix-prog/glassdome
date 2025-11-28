/**
 * Chattoggle component
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

/**
 * ChatToggle Component
 * 
 * Floating DRAGGABLE button to toggle the Overseer chat modal.
 * Can be moved anywhere on screen to avoid overlapping other UI elements.
 */

import { useState, useRef, useEffect } from 'react'
import './ChatToggle.css'

export default function ChatToggle({ onClick, hasUnread, isPlaying }) {
  // Load saved position from localStorage or use default
  const getInitialPosition = () => {
    const saved = localStorage.getItem('overseer-button-position')
    if (saved) {
      try {
        return JSON.parse(saved)
      } catch {
        return null
      }
    }
    return null
  }

  const [position, setPosition] = useState(getInitialPosition)
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const buttonRef = useRef(null)

  // Save position to localStorage when it changes
  useEffect(() => {
    if (position) {
      localStorage.setItem('overseer-button-position', JSON.stringify(position))
    }
  }, [position])

  const handleMouseDown = (e) => {
    // Only start drag on left mouse button
    if (e.button !== 0) return
    
    setIsDragging(true)
    setDragStart({
      x: e.clientX - (position?.x || 0),
      y: e.clientY - (position?.y || 0)
    })
    e.preventDefault()
  }

  const handleMouseMove = (e) => {
    if (!isDragging) return

    const newX = e.clientX - dragStart.x
    const newY = e.clientY - dragStart.y

    // Keep button within viewport bounds
    const buttonWidth = buttonRef.current?.offsetWidth || 120
    const buttonHeight = buttonRef.current?.offsetHeight || 50
    
    const boundedX = Math.max(-window.innerWidth + buttonWidth + 20, 
                              Math.min(0, newX))
    const boundedY = Math.max(-window.innerHeight + buttonHeight + 20, 
                              Math.min(0, newY))

    setPosition({ x: boundedX, y: boundedY })
  }

  const handleMouseUp = (e) => {
    if (isDragging) {
      setIsDragging(false)
      // If barely moved, treat as click
      const moved = Math.abs(e.clientX - dragStart.x - (position?.x || 0)) > 5 ||
                    Math.abs(e.clientY - dragStart.y - (position?.y || 0)) > 5
      if (!moved) {
        onClick()
      }
    }
  }

  // Add global mouse listeners when dragging
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
      return () => {
        window.removeEventListener('mousemove', handleMouseMove)
        window.removeEventListener('mouseup', handleMouseUp)
      }
    }
  }, [isDragging, dragStart])

  const handleClick = (e) => {
    // Only trigger click if not dragging
    if (!isDragging) {
      onClick()
    }
  }

  const handleDoubleClick = () => {
    // Double-click resets to default position
    setPosition(null)
    localStorage.removeItem('overseer-button-position')
  }

  const style = position ? {
    right: `${-position.x}px`,
    bottom: `${-position.y}px`,
  } : {}

  return (
    <button 
      ref={buttonRef}
      className={`chat-toggle ${hasUnread ? 'has-unread' : ''} ${isDragging ? 'dragging' : ''} ${isPlaying ? 'radio-playing' : ''}`}
      onMouseDown={handleMouseDown}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      title="Chat with Overseer (drag to move, double-click to reset)"
      style={style}
    >
      <span className="chat-toggle-drag-hint">⋮⋮</span>
      <span className="chat-toggle-icon">🧠</span>
      <span className="chat-toggle-label">Overseer</span>
      {isPlaying && <span className="radio-playing-indicator">🎵</span>}
      {hasUnread && <span className="unread-indicator" />}
    </button>
  )
}
