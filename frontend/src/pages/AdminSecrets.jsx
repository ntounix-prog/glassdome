/**
 * Admin Secrets Management Page
 * 
 * UI for managing secrets stored in Glassdome's secrets backend.
 * Admin only (level 100).
 */

import React, { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import '../styles/AdminSecrets.css'

// Common secrets that Glassdome uses
const COMMON_SECRETS = [
  { key: 'jwt_secret_key', label: 'JWT Secret Key', description: 'Secret key for signing JWT tokens', sensitive: true },
  { key: 'proxmox_password', label: 'Proxmox Password', description: 'Password for Proxmox API access', sensitive: true },
  { key: 'aws_access_key_id', label: 'AWS Access Key ID', description: 'AWS API access key', sensitive: false },
  { key: 'aws_secret_access_key', label: 'AWS Secret Key', description: 'AWS API secret key', sensitive: true },
  { key: 'azure_client_secret', label: 'Azure Client Secret', description: 'Azure service principal secret', sensitive: true },
  { key: 'esxi_password', label: 'ESXi Password', description: 'VMware ESXi password', sensitive: true },
  { key: 'vault_token', label: 'Vault Token', description: 'HashiCorp Vault access token', sensitive: true },
  { key: 'database_password', label: 'Database Password', description: 'PostgreSQL database password', sensitive: true },
  { key: 'redis_password', label: 'Redis Password', description: 'Redis server password', sensitive: true },
  { key: 'guacamole_password', label: 'Guacamole Password', description: 'Apache Guacamole admin password', sensitive: true },
]

export default function AdminSecrets() {
  const { getAuthHeaders } = useAuth()
  const [secrets, setSecrets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [editingSecret, setEditingSecret] = useState(null)
  const [showValue, setShowValue] = useState({})
  const [formData, setFormData] = useState({ key: '', value: '' })

  const fetchSecrets = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/secrets', {
        headers: getAuthHeaders()
      })
      
      if (!response.ok) {
        throw new Error('Failed to fetch secrets')
      }
      
      const data = await response.json()
      setSecrets(data.secrets || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [getAuthHeaders])

  useEffect(() => {
    fetchSecrets()
  }, [fetchSecrets])

  const handleAddSecret = async (e) => {
    e.preventDefault()
    try {
      const response = await fetch('/api/secrets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...getAuthHeaders()
        },
        body: JSON.stringify(formData)
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to add secret')
      }
      
      setShowAddModal(false)
      setFormData({ key: '', value: '' })
      fetchSecrets()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleDeleteSecret = async (key) => {
    if (!confirm(`Delete secret "${key}"? This cannot be undone.`)) return
    
    try {
      const response = await fetch(`/api/secrets/${encodeURIComponent(key)}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
      
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to delete secret')
      }
      
      fetchSecrets()
    } catch (err) {
      setError(err.message)
    }
  }

  const toggleShowValue = (key) => {
    setShowValue(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const getSecretInfo = (key) => {
    return COMMON_SECRETS.find(s => s.key === key)
  }

  if (loading && secrets.length === 0) {
    return (
      <div className="admin-secrets-container">
        <div className="loading">Loading secrets...</div>
      </div>
    )
  }

  return (
    <div className="admin-secrets-container">
      <header className="admin-header">
        <div className="header-left">
          <h1>🔐 Secrets Management</h1>
          <span className="subtitle">Manage platform credentials and API keys</span>
        </div>
        <button className="btn-create" onClick={() => setShowAddModal(true)}>
          ➕ Add Secret
        </button>
      </header>

      {error && (
        <div className="error-banner">
          ⚠️ {error}
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      <div className="secrets-info">
        <div className="info-card">
          <h3>💡 How Secrets Work</h3>
          <ul>
            <li>Secrets are stored securely using OS keyring or encrypted file</li>
            <li>HashiCorp Vault integration available for enterprise deployments</li>
            <li>Use CLI for initial setup: <code>glassdome secrets set &lt;key&gt;</code></li>
            <li>Secrets never leave the server - values are masked in UI</li>
          </ul>
        </div>
      </div>

      <div className="secrets-grid">
        {/* Common/Expected Secrets */}
        <section className="secrets-section">
          <h2>Platform Credentials</h2>
          <div className="secrets-list">
            {COMMON_SECRETS.map(secretInfo => {
              const isSet = secrets.includes(secretInfo.key)
              return (
                <div key={secretInfo.key} className={`secret-card ${isSet ? 'set' : 'unset'}`}>
                  <div className="secret-header">
                    <div className="secret-name">
                      <span className={`status-dot ${isSet ? 'set' : 'unset'}`} />
                      {secretInfo.label}
                    </div>
                    <div className="secret-actions">
                      {isSet ? (
                        <>
                          <button 
                            className="btn-action"
                            onClick={() => {
                              setEditingSecret(secretInfo.key)
                              setFormData({ key: secretInfo.key, value: '' })
                            }}
                            title="Update"
                          >
                            ✏️
                          </button>
                          <button 
                            className="btn-action delete"
                            onClick={() => handleDeleteSecret(secretInfo.key)}
                            title="Delete"
                          >
                            🗑️
                          </button>
                        </>
                      ) : (
                        <button 
                          className="btn-set"
                          onClick={() => {
                            setFormData({ key: secretInfo.key, value: '' })
                            setShowAddModal(true)
                          }}
                        >
                          Set Value
                        </button>
                      )}
                    </div>
                  </div>
                  <div className="secret-key">
                    <code>{secretInfo.key}</code>
                  </div>
                  <div className="secret-description">
                    {secretInfo.description}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* Custom Secrets */}
        {secrets.filter(s => !COMMON_SECRETS.find(c => c.key === s)).length > 0 && (
          <section className="secrets-section">
            <h2>Custom Secrets</h2>
            <div className="secrets-list">
              {secrets
                .filter(s => !COMMON_SECRETS.find(c => c.key === s))
                .map(key => (
                  <div key={key} className="secret-card set">
                    <div className="secret-header">
                      <div className="secret-name">
                        <span className="status-dot set" />
                        {key}
                      </div>
                      <div className="secret-actions">
                        <button 
                          className="btn-action"
                          onClick={() => {
                            setEditingSecret(key)
                            setFormData({ key, value: '' })
                          }}
                          title="Update"
                        >
                          ✏️
                        </button>
                        <button 
                          className="btn-action delete"
                          onClick={() => handleDeleteSecret(key)}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </div>
                    <div className="secret-key">
                      <code>{key}</code>
                    </div>
                  </div>
                ))}
            </div>
          </section>
        )}
      </div>

      {/* Add/Edit Secret Modal */}
      {(showAddModal || editingSecret) && (
        <div className="modal-overlay" onClick={() => {
          setShowAddModal(false)
          setEditingSecret(null)
          setFormData({ key: '', value: '' })
        }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editingSecret ? `🔐 Update: ${editingSecret}` : '➕ Add Secret'}</h2>
              <button className="modal-close" onClick={() => {
                setShowAddModal(false)
                setEditingSecret(null)
                setFormData({ key: '', value: '' })
              }}>×</button>
            </div>
            <form onSubmit={handleAddSecret}>
              {!editingSecret && (
                <div className="form-group">
                  <label>Secret Key</label>
                  <input
                    type="text"
                    value={formData.key}
                    onChange={e => setFormData({...formData, key: e.target.value})}
                    placeholder="e.g., my_api_key"
                    required
                  />
                </div>
              )}
              <div className="form-group">
                <label>Secret Value</label>
                <input
                  type="password"
                  value={formData.value}
                  onChange={e => setFormData({...formData, value: e.target.value})}
                  placeholder="Enter secret value"
                  required
                  autoComplete="new-password"
                />
                <p className="form-hint">⚠️ Values are encrypted at rest and never displayed</p>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn-cancel" onClick={() => {
                  setShowAddModal(false)
                  setEditingSecret(null)
                  setFormData({ key: '', value: '' })
                }}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  {editingSecret ? 'Update Secret' : 'Save Secret'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* CLI Instructions */}
      <div className="cli-instructions">
        <h3>🖥️ CLI Commands</h3>
        <div className="cli-grid">
          <div className="cli-command">
            <code>glassdome secrets set jwt_secret_key</code>
            <span>Set a secret (prompts for value)</span>
          </div>
          <div className="cli-command">
            <code>glassdome secrets list</code>
            <span>List all stored secret keys</span>
          </div>
          <div className="cli-command">
            <code>glassdome secrets migrate</code>
            <span>Import secrets from .env file</span>
          </div>
          <div className="cli-command">
            <code>glassdome auth emergency-reset</code>
            <span>Reset admin access when locked out</span>
          </div>
        </div>
      </div>
    </div>
  )
}

