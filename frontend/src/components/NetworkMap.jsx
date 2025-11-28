/**
 * Networkmap component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import './NetworkMap.css'

/**
 * NetworkMap - PewPew-style network visualization
 * 
 * Shows real-time traffic between VMs in a lab network.
 * Hub-and-spoke topology with central network switch.
 * Animated beams show ping activity, color-coded by latency.
 */
function NetworkMap({ matrix, targets, labId, networkName }) {
  const canvasRef = useRef(null)
  const animationRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 })
  const nodesRef = useRef([])
  const hubRef = useRef(null)
  const beamsRef = useRef([])

  // Calculate node positions in a circle around central hub
  const calculateNodePositions = useCallback((nodes, width, height) => {
    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) * 0.35
    
    // Create central hub/switch node
    hubRef.current = {
      id: 'hub',
      name: networkName || 'Network Switch',
      type: 'hub',
      x: centerX,
      y: centerY,
      radius: 35,
      status: 'online',
      pulsePhase: 0
    }
    
    // Position VM nodes around the hub
    return nodes.map((node, index) => {
      const angle = (2 * Math.PI * index) / nodes.length - Math.PI / 2
      return {
        ...node,
        type: 'vm',
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
        radius: 25,
        pulsePhase: Math.random() * Math.PI * 2
      }
    })
  }, [networkName])

  // Initialize nodes when targets change
  useEffect(() => {
    if (!targets || targets.length === 0) {
      nodesRef.current = []
      hubRef.current = null
      return
    }
    
    const nodeData = targets.map(t => ({
      ip: t.ip || t,
      name: t.name || t.ip || t,
      status: 'unknown'
    }))
    
    nodesRef.current = calculateNodePositions(nodeData, dimensions.width, dimensions.height)
  }, [targets, dimensions, calculateNodePositions])

  // Update node status from matrix
  useEffect(() => {
    if (!matrix) return
    
    nodesRef.current = nodesRef.current.map(node => {
      const matrixEntry = matrix[node.ip]
      if (matrixEntry) {
        return {
          ...node,
          status: matrixEntry.reachable ? 'online' : 'offline',
          latency: matrixEntry.latency_ms,
          name: matrixEntry.name || node.name
        }
      }
      return node
    })
  }, [matrix])

  // Create beam between node and hub (and optionally to another node)
  const createBeam = useCallback((sourceNode, targetNode, latency) => {
    const color = getLatencyColor(latency)
    const hub = hubRef.current
    
    return {
      id: `${sourceNode.ip}-${targetNode?.ip || 'hub'}-${Date.now()}`,
      source: sourceNode,
      hub: hub,
      target: targetNode,
      progress: 0,
      phase: 'to-hub', // 'to-hub' then 'from-hub'
      color,
      latency,
      createdAt: Date.now()
    }
  }, [])

  // Generate random beams to simulate traffic (through hub)
  useEffect(() => {
    if (nodesRef.current.length < 1 || !hubRef.current) return
    
    const beamInterval = setInterval(() => {
      const onlineNodes = nodesRef.current.filter(n => n.status === 'online')
      if (onlineNodes.length < 1) return
      
      // Create 1-2 random beams
      const numBeams = Math.floor(Math.random() * 2) + 1
      for (let i = 0; i < numBeams; i++) {
        const sourceIdx = Math.floor(Math.random() * onlineNodes.length)
        const source = onlineNodes[sourceIdx]
        
        // Sometimes just ping the hub, sometimes go to another node
        let target = null
        if (onlineNodes.length > 1 && Math.random() > 0.3) {
          let targetIdx = Math.floor(Math.random() * onlineNodes.length)
          while (targetIdx === sourceIdx) {
            targetIdx = Math.floor(Math.random() * onlineNodes.length)
          }
          target = onlineNodes[targetIdx]
        }
        
        const latency = source.latency || (target?.latency) || Math.random() * 50
        beamsRef.current.push(createBeam(source, target, latency))
      }
      
      // Limit active beams
      if (beamsRef.current.length > 50) {
        beamsRef.current = beamsRef.current.slice(-30)
      }
    }, 600)
    
    return () => clearInterval(beamInterval)
  }, [createBeam])

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    let lastTime = 0
    
    const animate = (timestamp) => {
      const deltaTime = timestamp - lastTime
      lastTime = timestamp
      
      // Clear canvas
      ctx.fillStyle = 'rgba(10, 14, 26, 0.3)'
      ctx.fillRect(0, 0, dimensions.width, dimensions.height)
      
      // Draw grid
      drawGrid(ctx, dimensions.width, dimensions.height)
      
      // Draw connections (spoke lines from hub to each node)
      if (hubRef.current) {
        drawHubConnections(ctx, hubRef.current, nodesRef.current)
      }
      
      // Update and draw beams
      beamsRef.current = beamsRef.current.filter(beam => {
        const speed = 3 // Faster travel
        beam.progress += (deltaTime / 1000) * speed
        
        if (beam.phase === 'to-hub') {
          if (beam.progress >= 1) {
            if (beam.target) {
              // Continue to target
              beam.phase = 'from-hub'
              beam.progress = 0
            } else {
              return false // Just hub ping, done
            }
          }
        } else if (beam.phase === 'from-hub') {
          if (beam.progress >= 1) {
            return false // Completed full journey
          }
        }
        
        drawBeam(ctx, beam)
        return true
      })
      
      // Draw hub node
      if (hubRef.current) {
        hubRef.current.pulsePhase += deltaTime / 400
        drawHubNode(ctx, hubRef.current, timestamp)
      }
      
      // Draw VM nodes
      nodesRef.current.forEach(node => {
        node.pulsePhase += deltaTime / 500
        drawNode(ctx, node, timestamp)
      })
      
      // Draw legend
      drawLegend(ctx, dimensions.width)
      
      animationRef.current = requestAnimationFrame(animate)
    }
    
    animationRef.current = requestAnimationFrame(animate)
    
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [dimensions])

  // Handle resize
  useEffect(() => {
    const container = canvasRef.current?.parentElement
    if (!container) return
    
    const updateSize = () => {
      setDimensions({
        width: container.clientWidth,
        height: container.clientHeight || 500
      })
    }
    
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  return (
    <div className="network-map-container">
      <canvas 
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        className="network-map-canvas"
      />
      {(!targets || targets.length === 0) && (
        <div className="no-targets-overlay">
          <span>No targets to monitor</span>
          <span className="hint">Deploy a lab to see network activity</span>
        </div>
      )}
    </div>
  )
}

// Draw functions
function drawGrid(ctx, width, height) {
  ctx.strokeStyle = 'rgba(100, 200, 255, 0.05)'
  ctx.lineWidth = 1
  
  const gridSize = 40
  
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, height)
    ctx.stroke()
  }
  
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }
}

function drawHubConnections(ctx, hub, nodes) {
  ctx.strokeStyle = 'rgba(100, 200, 255, 0.15)'
  ctx.lineWidth = 2
  
  nodes.forEach(node => {
    ctx.beginPath()
    ctx.moveTo(hub.x, hub.y)
    ctx.lineTo(node.x, node.y)
    ctx.stroke()
  })
}

function drawHubNode(ctx, hub, timestamp) {
  const pulseSize = Math.sin(hub.pulsePhase) * 4
  const baseRadius = hub.radius + pulseSize
  
  // Outer glow ring
  const gradient = ctx.createRadialGradient(
    hub.x, hub.y, baseRadius * 0.5,
    hub.x, hub.y, baseRadius * 2.5
  )
  gradient.addColorStop(0, 'rgba(64, 196, 255, 0.4)')
  gradient.addColorStop(0.5, 'rgba(64, 196, 255, 0.15)')
  gradient.addColorStop(1, 'transparent')
  
  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.arc(hub.x, hub.y, baseRadius * 2.5, 0, Math.PI * 2)
  ctx.fill()
  
  // Hub body (hexagon-ish shape for switch look)
  ctx.fillStyle = 'rgba(30, 40, 60, 0.95)'
  ctx.strokeStyle = '#40c4ff'
  ctx.lineWidth = 3
  
  const sides = 6
  ctx.beginPath()
  for (let i = 0; i < sides; i++) {
    const angle = (2 * Math.PI * i) / sides - Math.PI / 2
    const x = hub.x + baseRadius * Math.cos(angle)
    const y = hub.y + baseRadius * Math.sin(angle)
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fill()
  ctx.stroke()
  
  // Inner detail - port lights
  const innerRadius = baseRadius * 0.5
  for (let i = 0; i < 4; i++) {
    const angle = (2 * Math.PI * i) / 4
    const x = hub.x + innerRadius * Math.cos(angle)
    const y = hub.y + innerRadius * Math.sin(angle)
    
    ctx.fillStyle = i % 2 === 0 ? '#00ff88' : '#40c4ff'
    ctx.beginPath()
    ctx.arc(x, y, 3, 0, Math.PI * 2)
    ctx.fill()
  }
  
  // Center icon (network symbol)
  ctx.fillStyle = '#40c4ff'
  ctx.beginPath()
  ctx.arc(hub.x, hub.y, 5, 0, Math.PI * 2)
  ctx.fill()
  
  // Label
  ctx.font = 'bold 12px JetBrains Mono, monospace'
  ctx.textAlign = 'center'
  ctx.fillStyle = '#40c4ff'
  ctx.fillText('⬡', hub.x, hub.y + 4) // Unicode hexagon as switch icon
  
  ctx.font = '11px JetBrains Mono, monospace'
  ctx.fillStyle = '#fff'
  ctx.fillText(hub.name, hub.x, hub.y + baseRadius + 25)
}

function drawNode(ctx, node, timestamp) {
  const pulseSize = Math.sin(node.pulsePhase) * 3
  const baseRadius = node.radius + pulseSize
  
  // Glow effect
  const gradient = ctx.createRadialGradient(
    node.x, node.y, 0,
    node.x, node.y, baseRadius * 2
  )
  
  const color = getNodeColor(node.status)
  gradient.addColorStop(0, color.glow)
  gradient.addColorStop(0.5, color.glowFade)
  gradient.addColorStop(1, 'transparent')
  
  ctx.fillStyle = gradient
  ctx.beginPath()
  ctx.arc(node.x, node.y, baseRadius * 2, 0, Math.PI * 2)
  ctx.fill()
  
  // Main circle
  ctx.fillStyle = color.fill
  ctx.strokeStyle = color.stroke
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.arc(node.x, node.y, baseRadius, 0, Math.PI * 2)
  ctx.fill()
  ctx.stroke()
  
  // Server icon (simple rectangle)
  ctx.fillStyle = 'rgba(255, 255, 255, 0.3)'
  ctx.fillRect(node.x - 8, node.y - 6, 16, 12)
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.5)'
  ctx.lineWidth = 1
  ctx.strokeRect(node.x - 8, node.y - 6, 16, 12)
  
  // Server lines
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)'
  ctx.fillRect(node.x - 5, node.y - 3, 10, 2)
  ctx.fillRect(node.x - 5, node.y + 1, 10, 2)
  
  // Label
  ctx.font = '11px JetBrains Mono, monospace'
  ctx.textAlign = 'center'
  ctx.fillStyle = '#fff'
  ctx.fillText(node.name || node.ip, node.x, node.y + baseRadius + 20)
  
  // Latency badge
  if (node.latency !== undefined && node.status === 'online') {
    const latencyText = `${node.latency.toFixed(0)}ms`
    ctx.font = '10px JetBrains Mono, monospace'
    ctx.fillStyle = getLatencyColor(node.latency)
    ctx.fillText(latencyText, node.x, node.y + baseRadius + 32)
  }
}

function drawBeam(ctx, beam) {
  const { source, hub, target, progress, phase, color } = beam
  
  let startNode, endNode
  if (phase === 'to-hub') {
    startNode = source
    endNode = hub
  } else {
    startNode = hub
    endNode = target
  }
  
  if (!startNode || !endNode) return
  
  // Calculate current position
  const x = startNode.x + (endNode.x - startNode.x) * progress
  const y = startNode.y + (endNode.y - startNode.y) * progress
  
  // Draw beam trail
  const trailLength = 0.2
  const trailStart = Math.max(0, progress - trailLength)
  
  const gradient = ctx.createLinearGradient(
    startNode.x + (endNode.x - startNode.x) * trailStart,
    startNode.y + (endNode.y - startNode.y) * trailStart,
    x, y
  )
  
  gradient.addColorStop(0, 'transparent')
  gradient.addColorStop(1, color)
  
  ctx.strokeStyle = gradient
  ctx.lineWidth = 3
  ctx.lineCap = 'round'
  ctx.beginPath()
  ctx.moveTo(
    startNode.x + (endNode.x - startNode.x) * trailStart,
    startNode.y + (endNode.y - startNode.y) * trailStart
  )
  ctx.lineTo(x, y)
  ctx.stroke()
  
  // Draw beam head (glow)
  ctx.fillStyle = color
  ctx.shadowBlur = 15
  ctx.shadowColor = color
  ctx.beginPath()
  ctx.arc(x, y, 4, 0, Math.PI * 2)
  ctx.fill()
  ctx.shadowBlur = 0
}

function drawLegend(ctx, width) {
  const x = width - 120
  const y = 20
  
  ctx.font = '10px JetBrains Mono, monospace'
  ctx.textAlign = 'left'
  
  // Title
  ctx.fillStyle = '#888'
  ctx.fillText('LATENCY', x, y)
  
  // Legend items
  const items = [
    { color: '#00ff88', label: '< 50ms' },
    { color: '#ffaa00', label: '50-100ms' },
    { color: '#ff6464', label: '> 100ms' }
  ]
  
  items.forEach((item, i) => {
    const itemY = y + 15 + i * 15
    
    ctx.fillStyle = item.color
    ctx.beginPath()
    ctx.arc(x + 5, itemY - 3, 4, 0, Math.PI * 2)
    ctx.fill()
    
    ctx.fillStyle = '#888'
    ctx.fillText(item.label, x + 15, itemY)
  })
}

function getNodeColor(status) {
  switch (status) {
    case 'online':
      return {
        fill: 'rgba(0, 255, 136, 0.8)',
        stroke: '#00ff88',
        glow: 'rgba(0, 255, 136, 0.3)',
        glowFade: 'rgba(0, 255, 136, 0.1)'
      }
    case 'offline':
      return {
        fill: 'rgba(255, 100, 100, 0.8)',
        stroke: '#ff6464',
        glow: 'rgba(255, 100, 100, 0.3)',
        glowFade: 'rgba(255, 100, 100, 0.1)'
      }
    default:
      return {
        fill: 'rgba(100, 100, 100, 0.8)',
        stroke: '#666',
        glow: 'rgba(100, 100, 100, 0.2)',
        glowFade: 'rgba(100, 100, 100, 0.05)'
      }
  }
}

function getLatencyColor(latency) {
  if (latency < 50) return '#00ff88'
  if (latency < 100) return '#ffaa00'
  return '#ff6464'
}

export default NetworkMap
