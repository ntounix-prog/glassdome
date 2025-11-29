/**
 * Login Page
 * 
 * Authentication entry point for Glassdome.
 * Supports both login and first-user registration.
 */

import React, { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import '../styles/Login.css'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login, register, isAuthenticated, error: authError, loading } = useAuth()
  
  const [mode, setMode] = useState('login') // 'login' or 'register'
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: ''
  })
  const [error, setError] = useState('')
  const [isFirstUser, setIsFirstUser] = useState(false)

  // Check if this is first user setup
  useEffect(() => {
    checkFirstUser()
  }, [])

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from?.pathname || '/'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, location])

  const checkFirstUser = async () => {
    try {
      // Try to get roles (this will fail if no users exist)
      const response = await fetch('/api/auth/roles')
      if (response.ok) {
        // API works, check if we need to show register
        setIsFirstUser(false)
      }
    } catch (e) {
      // Assume first user if API fails
      setIsFirstUser(true)
      setMode('register')
    }
  }

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    })
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    // Validate fields aren't empty
    if (!formData.username || !formData.password) {
      setError('Please enter both username and password')
      return
    }

    if (mode === 'register') {
      // Validate registration
      if (formData.password !== formData.confirmPassword) {
        setError('Passwords do not match')
        return
      }
      if (formData.password.length < 8) {
        setError('Password must be at least 8 characters')
        return
      }
      if (!formData.email.includes('@')) {
        setError('Invalid email address')
        return
      }

      const result = await register(
        formData.email,
        formData.username,
        formData.password,
        formData.fullName || null
      )
      
      if (!result.success) {
        setError(result.error)
      }
    } else {
      // Login
      const result = await login(formData.username, formData.password)
      
      if (!result.success) {
        setError(result.error)
      }
    }
  }

  return (
    <div className="login-container">
      <div className="login-background">
        <div className="grid-lines"></div>
      </div>
      
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">🔮</div>
          <h1>Glassdome</h1>
          <p className="login-subtitle">
            {isFirstUser 
              ? 'Create Admin Account'
              : mode === 'login' 
                ? 'Cyber Range Platform' 
                : 'Create Account'}
          </p>
        </div>

        {error && (
          <div className="login-error">
            <span className="error-icon">⚠️</span>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="login-form">
          {mode === 'register' && (
            <>
              <div className="form-group">
                <label htmlFor="email">Email</label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  placeholder="admin@company.com"
                  required
                  autoComplete="email"
                />
              </div>
              
              <div className="form-group">
                <label htmlFor="fullName">Full Name (optional)</label>
                <input
                  type="text"
                  id="fullName"
                  name="fullName"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="John Doe"
                  autoComplete="name"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="username">
              {mode === 'login' ? 'Username or Email' : 'Username'}
            </label>
            <input
              type="text"
              id="username"
              name="username"
              value={formData.username}
              onChange={handleChange}
              placeholder={mode === 'login' ? 'admin' : 'Choose a username'}
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              id="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="••••••••"
              required
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            />
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label htmlFor="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••"
                required
                autoComplete="new-password"
              />
            </div>
          )}

          <button 
            type="submit" 
            className="login-button"
            disabled={loading}
          >
            {loading ? (
              <span className="loading-spinner">⏳</span>
            ) : mode === 'login' ? (
              <>🔓 Sign In</>
            ) : (
              <>✨ Create Account</>
            )}
          </button>
        </form>

        {!isFirstUser && (
          <div className="login-footer">
            {mode === 'login' ? (
              <p>
                Don't have an account?{' '}
                <button 
                  type="button"
                  className="link-button"
                  onClick={() => setMode('register')}
                >
                  Register
                </button>
              </p>
            ) : (
              <p>
                Already have an account?{' '}
                <button 
                  type="button"
                  className="link-button"
                  onClick={() => setMode('login')}
                >
                  Sign In
                </button>
              </p>
            )}
          </div>
        )}

        {isFirstUser && (
          <div className="first-user-notice">
            <span className="notice-icon">👑</span>
            <p>You're the first user! Your account will be created as <strong>Admin</strong>.</p>
          </div>
        )}
      </div>
    </div>
  )
}

