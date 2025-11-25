/**
 * ChatToggle Component
 * 
 * Floating button to toggle the Overseer chat modal.
 */

import './ChatToggle.css'

export default function ChatToggle({ onClick, hasUnread }) {
  return (
    <button 
      className={`chat-toggle ${hasUnread ? 'has-unread' : ''}`}
      onClick={onClick}
      title="Chat with Overseer"
    >
      <span className="chat-toggle-icon">🧠</span>
      <span className="chat-toggle-label">Overseer</span>
      {hasUnread && <span className="unread-indicator" />}
    </button>
  )
}

