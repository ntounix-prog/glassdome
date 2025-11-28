/**
 * User Menu Component
 * 
 * Dropdown showing current user info and logout option.
 */

import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

const roleColors = {
  admin: '#ff6b6b',
  architect: '#ffd93d', 
  engineer: '#6bcf7f',
  observer: '#74b9ff'
}

const roleIcons = {
  admin: '👑',
  architect: '🏗️',
  engineer: '⚙️',
  observer: '👁️'
}

export default function UserMenu() {
  const { user, logout, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef(null)

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  if (!isAuthenticated) {
    return (
      <button 
        className="user-login-btn"
        onClick={() => navigate('/login')}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"/>
          <polyline points="10 17 15 12 10 7"/>
          <line x1="15" y1="12" x2="3" y2="12"/>
        </svg>
        Sign In
      </button>
    )
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
    setIsOpen(false)
  }

  return (
    <div className="user-menu" ref={menuRef}>
      <button 
        className="user-menu-trigger"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="user-avatar">
          {roleIcons[user?.role] || '👤'}
        </span>
        <span className="user-name">{user?.username}</span>
        <span 
          className="user-role-badge"
          style={{ background: roleColors[user?.role] || '#666' }}
        >
          {user?.role}
        </span>
      </button>

      {isOpen && (
        <div className="user-menu-dropdown">
          <div className="user-menu-header">
            <span className="user-menu-avatar">
              {roleIcons[user?.role] || '👤'}
            </span>
            <div className="user-menu-info">
              <span className="user-menu-name">{user?.full_name || user?.username}</span>
              <span className="user-menu-email">{user?.email}</span>
            </div>
          </div>
          
          <div className="user-menu-divider"></div>
          
          <div className="user-menu-stats">
            <div className="stat-item">
              <span className="stat-label">Role</span>
              <span 
                className="stat-value"
                style={{ color: roleColors[user?.role] }}
              >
                {user?.role}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Level</span>
              <span className="stat-value">{user?.level}</span>
            </div>
          </div>
          
          <div className="user-menu-divider"></div>
          
          <button className="user-menu-item" onClick={handleLogout}>
            <span>🚪</span> Logout
          </button>
        </div>
      )}

      <style>{`
        .user-login-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: transparent;
          border: 1px solid rgba(100, 200, 255, 0.4);
          color: #64c8ff;
          padding: 0.5rem 1rem;
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.85rem;
          font-weight: 500;
          letter-spacing: 0.5px;
          white-space: nowrap;
          position: relative;
          overflow: hidden;
          animation: loginPulse 2s ease-in-out infinite;
          box-shadow: 0 0 15px rgba(100, 200, 255, 0.2),
                      inset 0 0 15px rgba(100, 200, 255, 0.05);
          transition: all 0.3s ease;
        }
        
        @keyframes loginPulse {
          0%, 100% {
            box-shadow: 0 0 15px rgba(100, 200, 255, 0.2),
                        inset 0 0 15px rgba(100, 200, 255, 0.05);
            border-color: rgba(100, 200, 255, 0.4);
          }
          50% {
            box-shadow: 0 0 25px rgba(100, 200, 255, 0.4),
                        inset 0 0 20px rgba(100, 200, 255, 0.1);
            border-color: rgba(100, 200, 255, 0.7);
          }
        }
        
        .user-login-btn:hover {
          background: rgba(100, 200, 255, 0.1);
          border-color: #64c8ff;
          transform: scale(1.05);
          animation: none;
          box-shadow: 0 0 30px rgba(100, 200, 255, 0.5),
                      inset 0 0 20px rgba(100, 200, 255, 0.15);
        }
        
        .user-login-btn svg {
          flex-shrink: 0;
          filter: drop-shadow(0 0 3px rgba(100, 200, 255, 0.8));
        }
        
        .user-menu {
          position: relative;
        }
        
        .user-menu-trigger {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          background: rgba(30, 30, 40, 0.8);
          border: 1px solid rgba(100, 200, 255, 0.2);
          padding: 0.4rem 0.75rem;
          border-radius: 8px;
          cursor: pointer;
          color: #fff;
          transition: all 0.2s;
        }
        
        .user-menu-trigger:hover {
          border-color: rgba(100, 200, 255, 0.4);
          background: rgba(40, 40, 50, 0.9);
        }
        
        .user-avatar {
          font-size: 1.2rem;
        }
        
        .user-name {
          font-size: 0.85rem;
          max-width: 100px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        
        .user-role-badge {
          font-size: 0.65rem;
          padding: 0.15rem 0.4rem;
          border-radius: 4px;
          text-transform: uppercase;
          font-weight: 600;
          color: #000;
        }
        
        .user-menu-dropdown {
          position: absolute;
          top: calc(100% + 8px);
          right: 0;
          width: 240px;
          background: rgba(25, 25, 35, 0.98);
          border: 1px solid rgba(100, 200, 255, 0.2);
          border-radius: 12px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
          z-index: 1000;
          overflow: hidden;
        }
        
        .user-menu-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem;
          background: rgba(100, 200, 255, 0.05);
        }
        
        .user-menu-avatar {
          font-size: 2rem;
        }
        
        .user-menu-info {
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }
        
        .user-menu-name {
          font-weight: 600;
          color: #fff;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .user-menu-email {
          font-size: 0.75rem;
          color: #888;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .user-menu-divider {
          height: 1px;
          background: rgba(100, 200, 255, 0.1);
        }
        
        .user-menu-stats {
          display: flex;
          justify-content: space-around;
          padding: 0.75rem;
        }
        
        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 0.25rem;
        }
        
        .stat-label {
          font-size: 0.7rem;
          color: #666;
          text-transform: uppercase;
        }
        
        .stat-value {
          font-size: 0.9rem;
          font-weight: 600;
          color: #fff;
        }
        
        .user-menu-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          width: 100%;
          padding: 0.75rem 1rem;
          background: none;
          border: none;
          color: #ccc;
          cursor: pointer;
          text-align: left;
          transition: background 0.2s;
        }
        
        .user-menu-item:hover {
          background: rgba(100, 200, 255, 0.1);
          color: #fff;
        }
      `}</style>
    </div>
  )
}

