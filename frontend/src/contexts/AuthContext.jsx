/**
 * Authentication Context
 * 
 * Provides authentication state and methods throughout the app.
 * Handles JWT token storage, login/logout, and user info.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

// API base URL
const API_BASE = ''

// Token storage keys
const TOKEN_KEY = 'glassdome_token'
const USER_KEY = 'glassdome_user'

/**
 * Auth Provider Component
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Initialize from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY)
    const storedUser = localStorage.getItem(USER_KEY)
    
    if (storedToken && storedUser) {
      try {
        setToken(storedToken)
        setUser(JSON.parse(storedUser))
        // Verify token is still valid
        verifyToken(storedToken)
      } catch (e) {
        // Invalid stored data, clear it
        logout()
      }
    }
    setLoading(false)
  }, [])

  /**
   * Verify token is still valid by fetching user info
   */
  const verifyToken = async (authToken) => {
    try {
      const response = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
      
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
        localStorage.setItem(USER_KEY, JSON.stringify(userData))
      } else {
        // Token invalid, logout
        logout()
      }
    } catch (e) {
      console.error('Token verification failed:', e)
      // Don't logout on network errors, token might still be valid
    }
  }

  /**
   * Login with username and password
   */
  const login = async (username, password) => {
    setError(null)
    setLoading(true)
    
    try {
      // Get token
      const tokenResponse = await fetch(`${API_BASE}/api/auth/login/user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
      })
      
      if (!tokenResponse.ok) {
        let errorMessage = 'Login failed'
        try {
          const errorData = await tokenResponse.json()
          errorMessage = errorData.detail || errorMessage
        } catch (e) {
          // Response body was empty or not JSON
          errorMessage = `Login failed (${tokenResponse.status})`
        }
        throw new Error(errorMessage)
      }
      
      const tokenData = await tokenResponse.json()
      const authToken = tokenData.access_token
      
      // Store token
      setToken(authToken)
      localStorage.setItem(TOKEN_KEY, authToken)
      
      // Get user info
      const userResponse = await fetch(`${API_BASE}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${authToken}`
        }
      })
      
      if (userResponse.ok) {
        const userData = await userResponse.json()
        setUser(userData)
        localStorage.setItem(USER_KEY, JSON.stringify(userData))
      }
      
      return { success: true }
    } catch (e) {
      setError(e.message)
      return { success: false, error: e.message }
    } finally {
      setLoading(false)
    }
  }

  /**
   * Register a new user
   */
  const register = async (email, username, password, fullName = null) => {
    setError(null)
    setLoading(true)
    
    try {
      const response = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` })
        },
        body: JSON.stringify({
          email,
          username,
          password,
          full_name: fullName
        })
      })
      
      if (!response.ok) {
        let errorMessage = 'Registration failed'
        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorMessage
        } catch (e) {
          // Response body was empty or not JSON
          errorMessage = `Registration failed (${response.status})`
        }
        throw new Error(errorMessage)
      }
      
      const userData = await response.json()
      
      // Auto-login after registration
      return await login(username, password)
    } catch (e) {
      setError(e.message)
      return { success: false, error: e.message }
    } finally {
      setLoading(false)
    }
  }

  /**
   * Logout - clear token and user data
   */
  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setError(null)
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }, [])

  /**
   * Get auth headers for API calls
   */
  const getAuthHeaders = useCallback(() => {
    if (!token) return {}
    return {
      'Authorization': `Bearer ${token}`
    }
  }, [token])

  /**
   * Check if user has a specific permission
   */
  const hasPermission = useCallback((permission) => {
    if (!user) return false
    if (user.is_superuser) return true
    if (user.permissions?.includes('*')) return true
    return user.permissions?.includes(permission) || false
  }, [user])

  /**
   * Check if user meets minimum level
   */
  const hasLevel = useCallback((minLevel) => {
    if (!user) return false
    if (user.is_superuser) return true
    return user.level >= minLevel
  }, [user])

  /**
   * Role check helpers
   */
  const isAdmin = hasLevel(100)
  const isArchitect = hasLevel(75)
  const isEngineer = hasLevel(50)
  const isObserver = hasLevel(25)

  const value = {
    // State
    user,
    token,
    loading,
    error,
    isAuthenticated: !!user && !!token,
    
    // Actions
    login,
    register,
    logout,
    
    // Helpers
    getAuthHeaders,
    hasPermission,
    hasLevel,
    
    // Role shortcuts
    isAdmin,
    isArchitect,
    isEngineer,
    isObserver,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Hook to access auth context
 */
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext

