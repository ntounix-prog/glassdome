/**
 * React hook: useRegistry
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

/**
 * useRegistry Hook
 * 
 * Provides real-time access to the Lab Registry via WebSocket and REST API.
 * Central source of truth for all lab and infrastructure state.
 */

import { useState, useEffect, useCallback, useRef } from 'react'

// API base - uses relative URLs for proxy
const API_BASE = '/api/registry'

/**
 * Hook for accessing registry status and resources
 */
export function useRegistryStatus() {
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/status`)
      if (!response.ok) throw new Error('Failed to fetch registry status')
      const data = await response.json()
      setStatus(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStatus()
    // Poll every 5 seconds
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchStatus])

  return { status, loading, error, refresh: fetchStatus }
}

/**
 * Hook for accessing all resources with optional filtering
 */
export function useResources(options = {}) {
  const { type, platform, labId } = options
  const [resources, setResources] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchResources = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (type) params.append('resource_type', type)
      if (platform) params.append('platform', platform)
      if (labId) params.append('lab_id', labId)
      
      const url = `${API_BASE}/resources${params.toString() ? '?' + params : ''}`
      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch resources')
      const data = await response.json()
      setResources(data.resources || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [type, platform, labId])

  useEffect(() => {
    fetchResources()
    // Poll based on tier (faster for labs)
    const interval = setInterval(fetchResources, labId ? 2000 : 10000)
    return () => clearInterval(interval)
  }, [fetchResources, labId])

  return { resources, loading, error, refresh: fetchResources }
}

/**
 * Hook for accessing labs with snapshots
 */
export function useLabs() {
  const [labs, setLabs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchLabs = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/labs`)
      if (!response.ok) throw new Error('Failed to fetch labs')
      const data = await response.json()
      setLabs(data.labs || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchLabs()
    const interval = setInterval(fetchLabs, 5000)
    return () => clearInterval(interval)
  }, [fetchLabs])

  return { labs, loading, error, refresh: fetchLabs }
}

/**
 * Hook for accessing a single lab snapshot
 */
export function useLabSnapshot(labId) {
  const [snapshot, setSnapshot] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchSnapshot = useCallback(async () => {
    if (!labId) {
      setSnapshot(null)
      setLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_BASE}/labs/${labId}`)
      if (!response.ok) throw new Error('Failed to fetch lab snapshot')
      const data = await response.json()
      setSnapshot(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [labId])

  useEffect(() => {
    fetchSnapshot()
    // Fast polling for lab state (Tier 1)
    const interval = setInterval(fetchSnapshot, 2000)
    return () => clearInterval(interval)
  }, [fetchSnapshot])

  return { snapshot, loading, error, refresh: fetchSnapshot }
}

/**
 * Hook for accessing drift information
 */
export function useDrift(labId = null) {
  const [drifts, setDrifts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDrifts = useCallback(async () => {
    try {
      const url = labId 
        ? `${API_BASE}/drift?lab_id=${labId}`
        : `${API_BASE}/drift`
      const response = await fetch(url)
      if (!response.ok) throw new Error('Failed to fetch drift')
      const data = await response.json()
      setDrifts(data.drifts || [])
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [labId])

  useEffect(() => {
    fetchDrifts()
    const interval = setInterval(fetchDrifts, 5000)
    return () => clearInterval(interval)
  }, [fetchDrifts])

  const resolveDrift = async (resourceId) => {
    try {
      await fetch(`${API_BASE}/drift/${resourceId}/resolve`, { method: 'POST' })
      fetchDrifts()
    } catch (err) {
      console.error('Failed to resolve drift:', err)
    }
  }

  return { drifts, loading, error, refresh: fetchDrifts, resolveDrift }
}

/**
 * Hook for real-time events via WebSocket
 */
export function useRegistryEvents(labId = null) {
  const [events, setEvents] = useState([])
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    // Determine WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = labId 
      ? `${protocol}//${host}${API_BASE}/ws/events?lab_id=${labId}`
      : `${protocol}//${host}${API_BASE}/ws/events`

    const connect = () => {
      try {
        wsRef.current = new WebSocket(wsUrl)

        wsRef.current.onopen = () => {
          setConnected(true)
          console.log('Registry WebSocket connected')
        }

        wsRef.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            setEvents(prev => [data, ...prev.slice(0, 99)]) // Keep last 100 events
          } catch (err) {
            console.error('Failed to parse event:', err)
          }
        }

        wsRef.current.onclose = () => {
          setConnected(false)
          console.log('Registry WebSocket disconnected, reconnecting...')
          // Reconnect after 3 seconds
          setTimeout(connect, 3000)
        }

        wsRef.current.onerror = (err) => {
          console.error('Registry WebSocket error:', err)
          wsRef.current?.close()
        }
      } catch (err) {
        console.error('Failed to connect WebSocket:', err)
        setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [labId])

  const clearEvents = () => setEvents([])

  return { events, connected, clearEvents }
}

/**
 * Hook for triggering reconciliation
 */
export function useReconcile() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const reconcileLab = async (labId, autoFix = true) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await fetch(`${API_BASE}/labs/${labId}/reconcile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ auto_fix: autoFix })
      })
      
      if (!response.ok) throw new Error('Reconciliation failed')
      const data = await response.json()
      setResult(data)
      return data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { reconcileLab, loading, result, error }
}

/**
 * Combined hook for full registry access
 */
export function useRegistry(options = {}) {
  const { labId } = options
  
  const status = useRegistryStatus()
  const resources = useResources({ labId })
  const labs = useLabs()
  const drift = useDrift(labId)
  const events = useRegistryEvents(labId)
  const reconcile = useReconcile()

  return {
    status: status.status,
    resources: resources.resources,
    labs: labs.labs,
    drifts: drift.drifts,
    events: events.events,
    connected: events.connected,
    loading: status.loading || resources.loading,
    error: status.error || resources.error,
    refresh: () => {
      status.refresh()
      resources.refresh()
      labs.refresh()
      drift.refresh()
    },
    reconcileLab: reconcile.reconcileLab,
    resolveDrift: drift.resolveDrift,
  }
}

export default useRegistry

