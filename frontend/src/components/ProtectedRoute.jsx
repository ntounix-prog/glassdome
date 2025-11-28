/**
 * Protected Route Component
 * 
 * Wraps routes that require authentication.
 * Redirects to login if not authenticated.
 */

import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

/**
 * Protect a route - requires authentication
 * 
 * @param {object} props
 * @param {React.ReactNode} props.children - The protected content
 * @param {number} props.minLevel - Minimum user level required (default: 0)
 * @param {string} props.role - Required role (admin, architect, engineer, observer)
 * @param {string} props.permission - Required permission string
 */
export default function ProtectedRoute({ 
  children, 
  minLevel = 0, 
  role = null,
  permission = null 
}) {
  const { isAuthenticated, user, hasLevel, hasPermission, loading } = useAuth()
  const location = useLocation()

  // Show nothing while checking auth
  if (loading) {
    return (
      <div className="auth-loading">
        <div className="loading-spinner">⏳</div>
        <p>Verifying authentication...</p>
      </div>
    )
  }

  // Not authenticated - redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // Check role requirement
  if (role) {
    const roleLevel = {
      admin: 100,
      architect: 75,
      engineer: 50,
      observer: 25
    }[role] || 0
    
    if (!hasLevel(roleLevel)) {
      return (
        <div className="access-denied">
          <h2>🚫 Access Denied</h2>
          <p>You need <strong>{role}</strong> privileges to access this page.</p>
          <p>Your role: <strong>{user?.role}</strong></p>
        </div>
      )
    }
  }

  // Check level requirement
  if (minLevel > 0 && !hasLevel(minLevel)) {
    return (
      <div className="access-denied">
        <h2>🚫 Access Denied</h2>
        <p>This page requires level {minLevel}+.</p>
        <p>Your level: <strong>{user?.level}</strong></p>
      </div>
    )
  }

  // Check permission requirement
  if (permission && !hasPermission(permission)) {
    return (
      <div className="access-denied">
        <h2>🚫 Access Denied</h2>
        <p>Missing permission: <code>{permission}</code></p>
      </div>
    )
  }

  // All checks passed
  return children
}

/**
 * Access Denied styles (inline for simplicity)
 */
const styles = `
.auth-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
  color: #888;
}

.auth-loading .loading-spinner {
  font-size: 3rem;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.access-denied {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 50vh;
  text-align: center;
  color: #888;
}

.access-denied h2 {
  color: #ff6b6b;
  margin-bottom: 1rem;
}

.access-denied code {
  background: rgba(100, 200, 255, 0.1);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
}
`

// Inject styles
if (typeof document !== 'undefined') {
  const styleSheet = document.createElement('style')
  styleSheet.textContent = styles
  document.head.appendChild(styleSheet)
}

