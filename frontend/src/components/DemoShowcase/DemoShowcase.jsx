/**
 * Glassdome Demo Showcase
 * 
 * An impressive 90+ second animated presentation
 * showcasing all Glassdome capabilities for executive demos.
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './DemoShowcase.css'

// Synthwave music generator using Web Audio API
class SynthwaveGenerator {
  constructor() {
    this.audioContext = null
    this.isPlaying = false
    this.nodes = []
  }

  start() {
    if (this.isPlaying) return
    
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)()
    this.isPlaying = true
    
    // Create a dark synthwave pattern
    this.playBassline()
    this.playPad()
    this.playArpeggio()
  }

  playBassline() {
    const bassNotes = [55, 55, 73.42, 55, 82.41, 55, 73.42, 55] // A1, D2, E2 pattern
    let noteIndex = 0
    
    const playNote = () => {
      if (!this.isPlaying) return
      
      const osc = this.audioContext.createOscillator()
      const gain = this.audioContext.createGain()
      const filter = this.audioContext.createBiquadFilter()
      
      osc.type = 'sawtooth'
      osc.frequency.value = bassNotes[noteIndex]
      
      filter.type = 'lowpass'
      filter.frequency.value = 400
      filter.Q.value = 5
      
      gain.gain.setValueAtTime(0.3, this.audioContext.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.4)
      
      osc.connect(filter)
      filter.connect(gain)
      gain.connect(this.audioContext.destination)
      
      osc.start()
      osc.stop(this.audioContext.currentTime + 0.5)
      
      this.nodes.push(osc)
      noteIndex = (noteIndex + 1) % bassNotes.length
      
      setTimeout(playNote, 500)
    }
    playNote()
  }

  playPad() {
    const osc1 = this.audioContext.createOscillator()
    const osc2 = this.audioContext.createOscillator()
    const gain = this.audioContext.createGain()
    const filter = this.audioContext.createBiquadFilter()
    
    osc1.type = 'sawtooth'
    osc2.type = 'sawtooth'
    osc1.frequency.value = 220 // A3
    osc2.frequency.value = 277.18 // C#4
    osc2.detune.value = 10
    
    filter.type = 'lowpass'
    filter.frequency.value = 800
    
    gain.gain.value = 0.08
    
    osc1.connect(filter)
    osc2.connect(filter)
    filter.connect(gain)
    gain.connect(this.audioContext.destination)
    
    osc1.start()
    osc2.start()
    
    this.nodes.push(osc1, osc2)
  }

  playArpeggio() {
    const notes = [440, 554.37, 659.25, 554.37, 440, 329.63, 440, 554.37] // A4, C#5, E5 arp
    let noteIndex = 0
    
    const playNote = () => {
      if (!this.isPlaying) return
      
      const osc = this.audioContext.createOscillator()
      const gain = this.audioContext.createGain()
      
      osc.type = 'triangle'
      osc.frequency.value = notes[noteIndex]
      
      gain.gain.setValueAtTime(0.15, this.audioContext.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.2)
      
      osc.connect(gain)
      gain.connect(this.audioContext.destination)
      
      osc.start()
      osc.stop(this.audioContext.currentTime + 0.25)
      
      this.nodes.push(osc)
      noteIndex = (noteIndex + 1) % notes.length
      
      setTimeout(playNote, 250)
    }
    
    setTimeout(playNote, 125) // Offset from bass
  }

  stop() {
    this.isPlaying = false
    this.nodes.forEach(node => {
      try { node.stop() } catch(e) {}
    })
    this.nodes = []
    if (this.audioContext) {
      this.audioContext.close()
      this.audioContext = null
    }
  }
}

// Phase definitions - All dashboard feature cards included
const PHASES = [
  { id: 'intro', title: 'Introduction' },
  { id: 'problem', title: 'The Problem' },
  { id: 'agents', title: 'Autonomous Agents' },
  { id: 'platforms', title: 'Multi-Platform' },
  { id: 'designer', title: 'Lab Designer' },
  { id: 'orchestration', title: 'Orchestration' },
  { id: 'overseer', title: 'Overseer AI' },
  { id: 'deploy', title: 'Rapid Deployment' },
  { id: 'reaper', title: 'Reaper Engine' },
  { id: 'updock', title: 'Player Access' },
  { id: 'validation', title: 'WhiteKnight' },
  { id: 'monitoring', title: 'WhitePawn' },
  { id: 'security', title: 'Security & Access' },
  { id: 'api', title: 'API Platform' },
  { id: 'stats', title: 'By The Numbers' },
  { id: 'finale', title: 'Finale' },
]

export default function DemoShowcase({ isOpen, onClose }) {
  const [currentPhase, setCurrentPhase] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [audioStatus, setAudioStatus] = useState('🎵 Click for Music')
  const [customAudio, setCustomAudio] = useState(null)
  const [customFileName, setCustomFileName] = useState(null)
  const synthRef = useRef(null)
  const audioRef = useRef(null)
  const fileInputRef = useRef(null)

  // Keyboard controls: Space/Right = next, Left = prev, Escape = close
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e) => {
      if (e.code === 'Space' || e.code === 'ArrowRight') {
        e.preventDefault()
        setCurrentPhase(prev => {
          if (prev >= PHASES.length - 1) {
            onClose()
            return prev
          }
          return prev + 1
        })
      } else if (e.code === 'ArrowLeft') {
        e.preventDefault()
        setCurrentPhase(prev => Math.max(0, prev - 1))
      } else if (e.code === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  // Cleanup when demo closes
  useEffect(() => {
    if (!isOpen) {
      stopAllAudio()
      setCurrentPhase(0)
    }
    return () => {
      stopAllAudio()
    }
  }, [isOpen])

  const stopAllAudio = () => {
    if (synthRef.current) {
      synthRef.current.stop()
      synthRef.current = null
    }
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
    }
    setIsPlaying(false)
  }

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      const url = URL.createObjectURL(file)
      setCustomAudio(url)
      setCustomFileName(file.name)
      setAudioStatus(`🎵 ${file.name.slice(0, 20)}...`)
      
      const audio = new Audio(url)
      audio.loop = true
      audio.volume = 0.5
      audioRef.current = audio
    }
  }

  // Toggle music
  const toggleSound = () => {
    try {
      if (isPlaying) {
        stopAllAudio()
        setAudioStatus(customAudio ? `🎵 ${customFileName?.slice(0, 15)}...` : '🎵 Click for Music')
      } else {
        if (customAudio && audioRef.current) {
          audioRef.current.play()
          setIsPlaying(true)
          setAudioStatus(`🔊 ${customFileName?.slice(0, 15)}...`)
        } else {
          synthRef.current = new SynthwaveGenerator()
          synthRef.current.start()
          setIsPlaying(true)
          setAudioStatus('🔊 Synthwave Playing')
        }
      }
    } catch (e) {
      console.error('Audio error:', e)
      setAudioStatus(`❌ ${e.message}`)
    }
  }

  const openFilePicker = () => {
    fileInputRef.current?.click()
  }

  const goToNext = () => {
    if (currentPhase >= PHASES.length - 1) {
      onClose()
    } else {
      setCurrentPhase(prev => prev + 1)
    }
  }

  const goToPrev = () => {
    setCurrentPhase(prev => Math.max(0, prev - 1))
  }

  if (!isOpen) return null

  const phase = PHASES[currentPhase]?.id
  const progress = ((currentPhase + 1) / PHASES.length) * 100

  return (
    <motion.div 
      className="demo-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      {/* Progress bar */}
      <div className="demo-progress">
        <div className="demo-progress-bar" style={{ width: `${progress}%` }} />
      </div>

      {/* Slide counter and title */}
      <div className="demo-slide-info">
        <span className="slide-counter">{currentPhase + 1} / {PHASES.length}</span>
        <span className="slide-title">{PHASES[currentPhase]?.title}</span>
      </div>

      {/* Keyboard hint */}
      <div className="demo-keyboard-hint">
        <span>SPACE</span> or <span>→</span> Next &nbsp;|&nbsp; <span>←</span> Back &nbsp;|&nbsp; <span>ESC</span> Exit
      </div>

      {/* Controls */}
      <div className="demo-controls">
        <input
          ref={fileInputRef}
          type="file"
          accept="audio/*"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />
        <button 
          className="demo-nav-btn"
          onClick={goToPrev}
          disabled={currentPhase === 0}
          title="Previous slide (←)"
        >
          ← Prev
        </button>
        <button 
          className="demo-upload"
          onClick={openFilePicker}
          title="Upload your own music"
        >
          📁 {customFileName ? 'Change' : 'Music'}
        </button>
        <button 
          className={`demo-sound ${isPlaying ? 'playing' : ''}`} 
          onClick={toggleSound}
          title={audioStatus}
        >
          {isPlaying ? '🔊' : '🎵'}
        </button>
        <button 
          className="demo-nav-btn primary"
          onClick={goToNext}
          title="Next slide (SPACE or →)"
        >
          {currentPhase >= PHASES.length - 1 ? 'Finish ✓' : 'Next →'}
        </button>
        <button className="demo-skip" onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Main content */}
      <div className="demo-content">
        <AnimatePresence mode="wait">
          
          {/* PHASE 1: INTRO */}
          {phase === 'intro' && (
            <motion.div
              key="intro"
              className="demo-phase intro"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 1.1 }}
              transition={{ duration: 0.8 }}
            >
              <motion.div 
                className="logo-container"
                initial={{ y: 50 }}
                animate={{ y: 0 }}
                transition={{ delay: 0.3, duration: 0.8, type: "spring" }}
              >
                <div className="logo-icon">🔮</div>
                <h1 className="logo-text">
                  <span className="glass">GLASS</span>
                  <span className="dome">DOME</span>
                </h1>
              </motion.div>
              <motion.p 
                className="tagline"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1, duration: 0.6 }}
              >
                Autonomous Cyber Range Operations
              </motion.p>
              <motion.p 
                className="version-tag"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
              >
                Version 0.7.0 • November 2025
              </motion.p>
              <motion.div 
                className="pulse-ring"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.div>
          )}

          {/* PHASE 2: THE PROBLEM */}
          {phase === 'problem' && (
            <motion.div
              key="problem"
              className="demo-phase problem"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.h2
                initial={{ y: -30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                The <span className="highlight-red">Problem</span>
              </motion.h2>
              <div className="problem-grid">
                {[
                  { icon: '⏰', title: 'Hours to Deploy', desc: 'Manual lab setup takes 4-8 hours per environment' },
                  { icon: '🔧', title: 'Platform Fragmentation', desc: 'Different tools for AWS, Azure, Proxmox, ESXi' },
                  { icon: '📋', title: 'Inconsistent Labs', desc: 'No two deployments are exactly the same' },
                  { icon: '💸', title: 'Expensive Expertise', desc: 'Requires specialized engineers for each platform' },
                ].map((item, i) => (
                  <motion.div
                    key={item.title}
                    className="problem-card"
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + i * 0.4 }}
                  >
                    <div className="problem-icon">{item.icon}</div>
                    <div className="problem-content">
                      <h3>{item.title}</h3>
                      <p>{item.desc}</p>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* PHASE 3: AUTONOMOUS AGENTS */}
          {phase === 'agents' && (
            <motion.div
              key="agents"
              className="demo-phase agents"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="agent-icon"
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: "spring", stiffness: 200 }}
              >
                🤖
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <span className="highlight-blue">Autonomous</span> Agents
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                AI-powered deployment agents handle complex orchestration automatically
              </motion.p>
              <motion.div 
                className="agent-grid"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                {[
                  { icon: '🧠', label: 'Intelligent Planning', desc: 'Analyzes lab requirements' },
                  { icon: '⚡', label: 'Parallel Execution', desc: 'Concurrent task processing' },
                  { icon: '🔄', label: 'Self-Correcting', desc: 'Automatic error recovery' },
                  { icon: '📋', label: 'Task Queuing', desc: 'Priority-based scheduling' },
                ].map((item, i) => (
                  <motion.div
                    key={item.label}
                    className="agent-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1 + i * 0.15 }}
                  >
                    <div className="agent-card-icon">{item.icon}</div>
                    <div className="agent-card-label">{item.label}</div>
                    <div className="agent-card-desc">{item.desc}</div>
                  </motion.div>
                ))}
              </motion.div>
              <motion.div 
                className="agent-flow"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.8 }}
              >
                <span>Request</span> → <span>Plan</span> → <span>Execute</span> → <span>Verify</span> → <span>Report</span>
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 4: PLATFORMS */}
          {phase === 'platforms' && (
            <motion.div
              key="platforms"
              className="demo-phase platforms"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.h2
                initial={{ y: -30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                Multi-Platform Orchestration
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                One unified interface for all your infrastructure
              </motion.p>
              <div className="platform-grid">
                {[
                  { icon: '🖥️', name: 'Proxmox VE', color: '#e57000', status: 'Production Ready' },
                  { icon: '☁️', name: 'AWS EC2', color: '#ff9900', status: 'Production Ready' },
                  { icon: '🔷', name: 'Microsoft Azure', color: '#0078d4', status: 'Production Ready' },
                  { icon: '💠', name: 'VMware ESXi', color: '#78be20', status: 'Planned' },
                ].map((platform, i) => (
                  <motion.div
                    key={platform.name}
                    className="platform-card"
                    initial={{ opacity: 0, y: 50, scale: 0.8 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ delay: 0.4 + i * 0.2, type: "spring", stiffness: 200 }}
                    style={{ '--accent': platform.color }}
                  >
                    <div className="platform-icon">{platform.icon}</div>
                    <div className="platform-name">{platform.name}</div>
                    <motion.div 
                      className="platform-status"
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                      transition={{ delay: 1 + i * 0.1, duration: 0.5 }}
                    >
                      <span>● {platform.status}</span>
                    </motion.div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* PHASE 4: LAB DESIGNER */}
          {phase === 'designer' && (
            <motion.div
              key="designer"
              className="demo-phase designer"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="designer-icon"
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: "spring", stiffness: 200 }}
              >
                🎨
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                Visual Lab Designer
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Drag-and-drop lab creation with ReactFlow canvas
              </motion.p>
              <motion.div 
                className="feature-tags"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                {['Drag & Drop VMs', 'Visual Networking', 'pfSense Gateways', 'Template Library', 'One-Click Deploy', 'Save & Load'].map((tag, i) => (
                  <motion.span
                    key={tag}
                    className="feature-tag"
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 1 + i * 0.15 }}
                  >
                    {tag}
                  </motion.span>
                ))}
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 6: ORCHESTRATION */}
          {phase === 'orchestration' && (
            <motion.div
              key="orchestration"
              className="demo-phase orchestration"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="orchestration-icon"
                animate={{ rotate: 360 }}
                transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              >
                🔄
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                Intelligent <span className="highlight-orange">Orchestration</span>
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Complex dependency management and parallel execution
              </motion.p>
              <motion.div 
                className="orchestration-visual"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                <div className="dependency-tree">
                  {[
                    { level: 0, items: [{ name: 'pfSense Gateway', status: 'complete' }] },
                    { level: 1, items: [
                      { name: 'Domain Controller', status: 'complete' },
                      { name: 'Database Server', status: 'complete' },
                    ]},
                    { level: 2, items: [
                      { name: 'Web Server', status: 'running' },
                      { name: 'App Server', status: 'running' },
                      { name: 'Kali Attacker', status: 'pending' },
                    ]},
                  ].map((level, li) => (
                    <motion.div 
                      key={li}
                      className="tree-level"
                      initial={{ opacity: 0, x: -20 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 1 + li * 0.3 }}
                    >
                      {level.items.map((item, ii) => (
                        <div key={item.name} className={`tree-node ${item.status}`}>
                          <span className="node-status">
                            {item.status === 'complete' ? '✓' : item.status === 'running' ? '◉' : '○'}
                          </span>
                          <span className="node-name">{item.name}</span>
                        </div>
                      ))}
                    </motion.div>
                  ))}
                </div>
              </motion.div>
              <motion.div 
                className="orchestration-features"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 2 }}
              >
                <span>⚡ Parallel Cloning</span>
                <span>🔗 Dependency Aware</span>
                <span>🎯 Smart Ordering</span>
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 7: OVERSEER AI */}
          {phase === 'overseer' && (
            <motion.div
              key="overseer"
              className="demo-phase overseer"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="ai-orb"
                animate={{ 
                  boxShadow: [
                    '0 0 60px rgba(52, 211, 153, 0.3)',
                    '0 0 100px rgba(52, 211, 153, 0.6)',
                    '0 0 60px rgba(52, 211, 153, 0.3)',
                  ]
                }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                🧠
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                Meet <span className="highlight-green">Overseer</span>
              </motion.h2>
              <motion.p
                className="ai-subtitle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Your AI Operations Co-Pilot • Claude 3.5 Sonnet + GPT-4o
              </motion.p>
              <motion.div 
                className="chat-demo"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 }}
              >
                <div className="chat-message user">
                  <TypeWriter text="Deploy a Windows AD lab with Kali attacker" delay={1.5} />
                </div>
                <motion.div 
                  className="chat-message assistant"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 4 }}
                >
                  <span className="typing-indicator">
                    <span></span><span></span><span></span>
                  </span>
                  ✅ Deploying 4 VMs to Proxmox... Lab ready in 47s
                </motion.div>
              </motion.div>
              <motion.div 
                className="ai-features"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 5 }}
              >
                <span>💬 Natural Language</span>
                <span>🔧 Infrastructure Tools</span>
                <span>📧 Email Integration</span>
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 6: DEPLOYMENT */}
          {phase === 'deploy' && (
            <motion.div
              key="deploy"
              className="demo-phase deploy"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.h2
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
              >
                Deploy in <span className="highlight">Seconds</span>
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                Parallel VM provisioning with automatic networking
              </motion.p>
              <div className="deploy-timeline">
                {[
                  { step: 'pfSense Gateway Created', time: '8s', icon: '🛡️' },
                  { step: 'VMs Cloned in Parallel', time: '15s', icon: '🖥️' },
                  { step: 'DHCP & Networking', time: '5s', icon: '🌐' },
                  { step: 'Vulnerabilities Injected', time: '12s', icon: '☠️' },
                  { step: 'Lab Ready for Players', time: '✓', icon: '🚀' },
                ].map((item, i) => (
                  <motion.div
                    key={item.step}
                    className="timeline-item"
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.4 + i * 0.5 }}
                  >
                    <div className="timeline-icon">{item.icon}</div>
                    <div className="timeline-content">
                      <div className="timeline-step">{item.step}</div>
                      <div className="timeline-time">{item.time}</div>
                    </div>
                    <motion.div 
                      className="timeline-line"
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ delay: 0.6 + i * 0.5, duration: 0.4 }}
                    />
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* PHASE 7: REAPER */}
          {phase === 'reaper' && (
            <motion.div
              key="reaper"
              className="demo-phase reaper"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="reaper-icon"
                initial={{ scale: 0, rotate: -180 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: "spring", stiffness: 200 }}
              >
                ☠️
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <span className="highlight-red">Reaper</span> Vulnerability Engine
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                "Configure in Place" - Deploy anywhere, identical state every time
              </motion.p>
              <motion.div 
                className="vuln-list"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                {['Weak SSH ✓', 'SQL Injection', 'XSS', 'Privilege Escalation', 'SMB Exploits', 'AD Misconfig'].map((vuln, i) => (
                  <motion.span
                    key={vuln}
                    className={`vuln-tag ${vuln.includes('✓') ? 'active' : ''}`}
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 1.5 + i * 0.15 }}
                  >
                    {vuln}
                  </motion.span>
                ))}
              </motion.div>
              <motion.p
                className="reaper-note"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 2.5 }}
              >
                Powered by Ansible playbooks • No platform lock-in
              </motion.p>
            </motion.div>
          )}

          {/* PHASE 8: UPDOCK */}
          {phase === 'updock' && (
            <motion.div
              key="updock"
              className="demo-phase updock"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="updock-icon"
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ type: "spring", stiffness: 150 }}
              >
                🚀
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <span className="highlight-cyan">Updock</span> Player Access
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Browser-based RDP/SSH • No client software required
              </motion.p>
              <motion.div 
                className="updock-features"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                <div className="updock-flow">
                  <motion.div 
                    className="flow-step"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1.4 }}
                  >
                    <span className="flow-icon">🎫</span>
                    <span>Enter Lab Code</span>
                  </motion.div>
                  <motion.div 
                    className="flow-arrow"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 1.6 }}
                  >→</motion.div>
                  <motion.div 
                    className="flow-step"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1.8 }}
                  >
                    <span className="flow-icon">🖥️</span>
                    <span>Select Machine</span>
                  </motion.div>
                  <motion.div 
                    className="flow-arrow"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 2 }}
                  >→</motion.div>
                  <motion.div 
                    className="flow-step"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 2.2 }}
                  >
                    <span className="flow-icon">🎮</span>
                    <span>Full Desktop</span>
                  </motion.div>
                </div>
              </motion.div>
              <motion.p
                className="updock-note"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 2.8 }}
              >
                Powered by Apache Guacamole • Custom Glassdome UI
              </motion.p>
            </motion.div>
          )}

          {/* PHASE 9: WHITEKNIGHT VALIDATION */}
          {phase === 'validation' && (
            <motion.div
              key="validation"
              className="demo-phase validation"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="knight-icon"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 200 }}
              >
                🛡️
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <span className="highlight-gold">WhiteKnight</span> Validation
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Verify vulnerabilities are exploitable before training begins
              </motion.p>
              <motion.div 
                className="validation-checks"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                {[
                  { check: 'SSH Credentials Verified', status: '✓' },
                  { check: 'Port Scan Complete', status: '✓' },
                  { check: 'Services Accessible', status: '✓' },
                  { check: 'Exploit Paths Confirmed', status: '✓' },
                ].map((item, i) => (
                  <motion.div
                    key={item.check}
                    className="check-item"
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 1.4 + i * 0.3 }}
                  >
                    <span className="check-status">{item.status}</span>
                    <span className="check-name">{item.check}</span>
                  </motion.div>
                ))}
              </motion.div>
              <motion.div
                className="training-ready"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 2.8 }}
              >
                🎯 Lab Ready for Training
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 10: WHITEPAWN MONITORING */}
          {phase === 'monitoring' && (
            <motion.div
              key="monitoring"
              className="demo-phase monitoring"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div 
                className="pawn-icon"
                initial={{ y: -50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ type: "spring" }}
              >
                ♙
              </motion.div>
              <motion.h2
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.5 }}
              >
                <span className="highlight-purple">WhitePawn</span> Monitoring
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Real-time visibility into all deployed resources
              </motion.p>
              <motion.div 
                className="monitor-grid"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                {[
                  { icon: '📊', label: 'Live Dashboard', desc: 'VM states, IPs, uptime' },
                  { icon: '🔔', label: 'Smart Alerts', desc: 'Drift detection' },
                  { icon: '🔄', label: 'Self-Healing', desc: 'Auto-restart failed VMs' },
                  { icon: '📈', label: 'Lab Registry', desc: 'Central source of truth' },
                ].map((item, i) => (
                  <motion.div
                    key={item.label}
                    className="monitor-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 1.4 + i * 0.2 }}
                  >
                    <div className="monitor-icon">{item.icon}</div>
                    <div className="monitor-label">{item.label}</div>
                    <div className="monitor-desc">{item.desc}</div>
                  </motion.div>
                ))}
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 13: SECURITY & ACCESS */}
          {phase === 'security' && (
            <motion.div
              key="security"
              className="demo-phase security"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.h2
                initial={{ y: -30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                Enterprise <span className="highlight-emerald">Security</span>
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                Production-ready security controls built-in from day one
              </motion.p>
              <div className="security-grid">
                <motion.div
                  className="security-card rbac"
                  initial={{ opacity: 0, x: -30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <div className="security-icon">🔐</div>
                  <h3>Role-Based Access Control</h3>
                  <div className="role-list">
                    {[
                      { role: 'Admin', color: '#ff6b6b', perms: 'Full system access' },
                      { role: 'Architect', color: '#fbbf24', perms: 'Design & deploy labs' },
                      { role: 'Engineer', color: '#34d399', perms: 'Operate & monitor' },
                      { role: 'Observer', color: '#60a5fa', perms: 'View only' },
                    ].map((item, i) => (
                      <motion.div 
                        key={item.role}
                        className="role-item"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.8 + i * 0.1 }}
                        style={{ '--role-color': item.color }}
                      >
                        <span className="role-badge">{item.role}</span>
                        <span className="role-perms">{item.perms}</span>
                      </motion.div>
                    ))}
                  </div>
                  <span className="active-badge">✓ Active</span>
                </motion.div>
                <motion.div
                  className="security-card vault"
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.7 }}
                >
                  <div className="security-icon">🔒</div>
                  <h3>HashiCorp Vault</h3>
                  <div className="vault-features">
                    {[
                      '🔑 API Key Management',
                      '🎫 Token Rotation',
                      '📜 Audit Logging',
                      '🔐 Encrypted Storage',
                    ].map((feature, i) => (
                      <motion.div 
                        key={feature}
                        className="vault-feature"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1 + i * 0.1 }}
                      >
                        {feature}
                      </motion.div>
                    ))}
                  </div>
                  <span className="active-badge">✓ Active</span>
                </motion.div>
              </div>
            </motion.div>
          )}

          {/* PHASE 14: API PLATFORM */}
          {phase === 'api' && (
            <motion.div
              key="api"
              className="demo-phase api"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.h2
                initial={{ y: -30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                Developer <span className="highlight-indigo">API Platform</span>
              </motion.h2>
              <motion.p
                className="section-desc"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                Full-featured REST API with comprehensive documentation and testing
              </motion.p>
              <div className="api-grid">
                <motion.div
                  className="api-card docs"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5 }}
                >
                  <div className="api-icon">📖</div>
                  <h3>Documented & Versioned API</h3>
                  <div className="api-features">
                    <div className="api-feature">
                      <span className="api-bullet">●</span>
                      Interactive OpenAPI/Swagger UI
                    </div>
                    <div className="api-feature">
                      <span className="api-bullet">●</span>
                      Full schema validation
                    </div>
                    <div className="api-feature">
                      <span className="api-bullet">●</span>
                      Versioned endpoints (v1, v2)
                    </div>
                    <div className="api-feature">
                      <span className="api-bullet">●</span>
                      Try-it-now testing
                    </div>
                  </div>
                  <span className="active-badge">✓ Active</span>
                </motion.div>
                <motion.div
                  className="api-card testing"
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.7 }}
                >
                  <div className="api-icon">🧪</div>
                  <h3>Test & Validation Pipeline</h3>
                  <div className="test-results">
                    {[
                      { name: 'Smoke Tests', status: 'pass', count: '12/12' },
                      { name: 'Auth Tests', status: 'pass', count: '8/8' },
                      { name: 'Endpoint Tests', status: 'pass', count: '45/45' },
                      { name: 'Schema Validation', status: 'pass', count: '100%' },
                    ].map((test, i) => (
                      <motion.div 
                        key={test.name}
                        className="test-row"
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 1 + i * 0.15 }}
                      >
                        <span className="test-status">✓</span>
                        <span className="test-name">{test.name}</span>
                        <span className="test-count">{test.count}</span>
                      </motion.div>
                    ))}
                  </div>
                  <span className="active-badge">✓ Active</span>
                </motion.div>
              </div>
            </motion.div>
          )}

          {/* PHASE 15: STATS */}
          {phase === 'stats' && (
            <motion.div
              key="stats"
              className="demo-phase stats"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.h2
                initial={{ y: -20, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
              >
                By The Numbers
              </motion.h2>
              <div className="stats-grid">
                {[
                  { value: '4', label: 'Platforms', suffix: '', desc: 'Proxmox, AWS, Azure, ESXi' },
                  { value: '15', label: 'Core Features', suffix: '', desc: 'Production-ready' },
                  { value: '47', label: 'Deploy Time', suffix: 's', desc: 'Average lab ready' },
                  { value: '4', label: 'Active Services', suffix: '', desc: 'RBAC, Vault, API, Tests' },
                ].map((stat, i) => (
                  <motion.div
                    key={stat.label}
                    className="stat-card"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + i * 0.2 }}
                  >
                    <div className="stat-value">
                      <CountUp to={parseInt(stat.value)} delay={0.5 + i * 0.15} />
                      <span className="stat-suffix">{stat.suffix}</span>
                    </div>
                    <div className="stat-label">{stat.label}</div>
                    <div className="stat-desc">{stat.desc}</div>
                  </motion.div>
                ))}
              </div>
              <motion.div
                className="systems-row"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
              >
                <span>🤖 Agents</span>
                <span>🧠 Overseer</span>
                <span>☠️ Reaper</span>
                <span>🚀 Updock</span>
                <span>🛡️ WhiteKnight</span>
                <span>♙ WhitePawn</span>
              </motion.div>
              <motion.div
                className="systems-row secondary"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.8 }}
              >
                <span>🎨 Designer</span>
                <span>🔄 Orchestration</span>
                <span>🔐 RBAC</span>
                <span>🔒 Vault</span>
                <span>📖 API Docs</span>
                <span>🧪 Testing</span>
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 12: FINALE */}
          {phase === 'finale' && (
            <motion.div
              key="finale"
              className="demo-phase finale"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div
                className="finale-logo"
                initial={{ scale: 0.5, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ type: "spring", stiffness: 150 }}
              >
                🔮
              </motion.div>
              <motion.h1
                initial={{ y: 30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.3 }}
              >
                <span className="glass">GLASS</span>
                <span className="dome">DOME</span>
              </motion.h1>
              <motion.p
                className="finale-tagline"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                The Future of Cyber Range Operations
              </motion.p>
              <motion.div
                className="finale-cta"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 }}
              >
                Ready for Questions?
              </motion.div>
              <motion.p
                className="finale-author"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.8 }}
              >
                Built by Brett Turner • November 2025
              </motion.p>
            </motion.div>
          )}

        </AnimatePresence>
      </div>

      {/* Animated background */}
      <div className="demo-bg">
        <div className="grid-lines" />
        <div className="gradient-orb orb-1" />
        <div className="gradient-orb orb-2" />
        <div className="gradient-orb orb-3" />
      </div>
    </motion.div>
  )
}

// TypeWriter component
function TypeWriter({ text, delay = 0 }) {
  const [displayText, setDisplayText] = useState('')
  
  useEffect(() => {
    const timeout = setTimeout(() => {
      let i = 0
      const interval = setInterval(() => {
        if (i < text.length) {
          setDisplayText(text.slice(0, i + 1))
          i++
        } else {
          clearInterval(interval)
        }
      }, 50)
      return () => clearInterval(interval)
    }, delay * 1000)
    
    return () => clearTimeout(timeout)
  }, [text, delay])
  
  return <span>{displayText}<span className="cursor">|</span></span>
}

// CountUp component
function CountUp({ to, delay = 0 }) {
  const [count, setCount] = useState(0)
  
  useEffect(() => {
    const timeout = setTimeout(() => {
      const duration = 1000
      const steps = 30
      const increment = to / steps
      let current = 0
      
      const interval = setInterval(() => {
        current += increment
        if (current >= to) {
          setCount(to)
          clearInterval(interval)
        } else {
          setCount(Math.floor(current))
        }
      }, duration / steps)
      
      return () => clearInterval(interval)
    }, delay * 1000)
    
    return () => clearTimeout(timeout)
  }, [to, delay])
  
  return <span>{count}</span>
}
