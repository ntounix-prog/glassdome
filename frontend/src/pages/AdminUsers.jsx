/**
 * Admin User Management Page
 * 
 * CRUD interface for managing Glassdome users.
 * Admin only (level 100).
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import '../styles/AdminUsers.css'

const ROLES = [
  { value: 'admin', label: 'Admin', level: 100, color: '#ff6b6b', icon: '👑' },
  { value: 'architect', label: 'Architect', level: 75, color: '#ffd93d', icon: '🏗️' },
  { value: 'engineer', label: 'Engineer', level: 50, color: '#6bcf7f', icon: '⚙️' },
  { value: 'observer', label: 'Observer', level: 25, color: '#74b9ff', icon: '👁️' },
]

export default function AdminUsers() {
  const { getAuthHeaders, user: currentUser } = useAuth()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
    role: 'observer'
  })

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/v1/auth/users', {
        headers: getAuthHeaders()
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch users')
      }
      
      const data = await response.json()
      setUsers(data.users || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [getAuthHeaders])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      const response = await fetch('/api/v1/auth/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(formData)
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to create user')
      }
      
      setShowCreateModal(false)
      setFormData({ email: '', username: '', password: '', full_name: '', role: 'observer' })
      fetchUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleUpdate = async (e) => {
    e.preventDefault()
    try {
      const updateData = {
        email: formData.email,
        username: formData.username,
        full_name: formData.full_name,
        role: formData.role,
        is_active: formData.is_active
      }
      
      const response = await fetch(`/api/v1/auth/users/${editingUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(updateData)
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to update user')
      }
      
      setEditingUser(null)
      setFormData({ email: '', username: '', password: '', full_name: '', role: 'observer' })
      fetchUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeactivate = async (userId) => {
    if (!confirm('Are you sure you want to deactivate this user?')) return
    
    try {
      const response = await fetch(`/api/v1/auth/users/${userId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to deactivate user')
      }
      
      fetchUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  const openEditModal = (user) => {
    setEditingUser(user)
    setFormData({
      email: user.email,
      username: user.username,
      full_name: user.full_name || '',
      role: user.role,
      is_active: user.is_active
    })
  }

  const getRoleInfo = (role) => ROLES.find(r => r.value === role) || ROLES[3]

  if (loading && users.length === 0) {
    return (
      <div className="admin-users-container">
        <div className="loading">Loading users...</div>
      </div>
    )
  }

  return (
    <div className="admin-users-container">
      <header className="admin-header">
        <div className="header-left">
          <h1>👥 User Management</h1>
          <span className="subtitle">Manage Glassdome users and permissions</span>
        </div>
        <button className="btn-create" onClick={() => setShowCreateModal(true)}>
          ➕ Create User
        </button>
      </header>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="users-table-container">
        <table className="users-table">
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Level</th>
              <th>Status</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => {
              const roleInfo = getRoleInfo(user.role)
              return (
                <tr key={user.id} className={!user.is_active ? 'inactive' : ''}>
                  <td className="user-cell">
                    <span className="user-icon">{roleInfo.icon}</span>
                    <div className="user-info">
                      <span className="username">{user.username}</span>
                      {user.full_name && (
                        <span className="fullname">{user.full_name}</span>
                      )}
                    </div>
                  </td>
                  <td>{user.email}</td>
                  <td>
                    <span 
                      className="role-badge"
                      style={{ background: roleInfo.color }}
                    >
                      {roleInfo.label}
                    </span>
                  </td>
                  <td className="level-cell">{user.level}</td>
                  <td>
                    <span className={`status-badge ${user.is_active ? 'active' : 'inactive'}`}>
                      {user.is_active ? '✓ Active' : '✗ Inactive'}
                    </span>
                  </td>
                  <td className="date-cell">
                    {user.last_login 
                      ? new Date(user.last_login).toLocaleDateString()
                      : 'Never'}
                  </td>
                  <td className="actions-cell">
                    <button 
                      className="btn-edit"
                      onClick={() => openEditModal(user)}
                      title="Edit user"
                    >
                      ✏️
                    </button>
                    {user.id !== currentUser?.id && (
                      <button 
                        className="btn-delete"
                        onClick={() => handleDeactivate(user.id)}
                        title="Deactivate user"
                      >
                        🗑️
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Create User Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={() => setShowCreateModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>➕ Create New User</h2>
              <button className="modal-close" onClick={() => setShowCreateModal(false)}>×</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={e => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={e => setFormData({...formData, username: e.target.value})}
                  required
                  minLength={3}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={e => setFormData({...formData, password: e.target.value})}
                  required
                  minLength={8}
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={e => setFormData({...formData, full_name: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={formData.role}
                  onChange={e => setFormData({...formData, role: e.target.value})}
                >
                  {ROLES.map(role => (
                    <option key={role.value} value={role.value}>
                      {role.icon} {role.label} (Level {role.level})
                    </option>
                  ))}
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  Create User
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit User Modal */}
      {editingUser && (
        <div className="modal-overlay" onClick={() => setEditingUser(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>✏️ Edit User: {editingUser.username}</h2>
              <button className="modal-close" onClick={() => setEditingUser(null)}>×</button>
            </div>
            <form onSubmit={handleUpdate}>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={e => setFormData({...formData, email: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={e => setFormData({...formData, username: e.target.value})}
                  required
                />
              </div>
              <div className="form-group">
                <label>Full Name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={e => setFormData({...formData, full_name: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Role</label>
                <select
                  value={formData.role}
                  onChange={e => setFormData({...formData, role: e.target.value})}
                >
                  {ROLES.map(role => (
                    <option key={role.value} value={role.value}>
                      {role.icon} {role.label} (Level {role.level})
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={e => setFormData({...formData, is_active: e.target.checked})}
                  />
                  Active Account
                </label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => setEditingUser(null)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

