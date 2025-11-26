/**
 * Glassdome Demo Showcase
 * 
 * An impressive 30-40 second animated presentation
 * showcasing Glassdome capabilities for VP demos.
 */

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './DemoShowcase.css'

const PHASES = [
  { id: 'intro', duration: 4000 },
  { id: 'platforms', duration: 5000 },
  { id: 'overseer', duration: 6000 },
  { id: 'deploy', duration: 5000 },
  { id: 'security', duration: 5000 },
  { id: 'stats', duration: 5000 },
  { id: 'finale', duration: 4000 },
]

const TOTAL_DURATION = PHASES.reduce((sum, p) => sum + p.duration, 0)

export default function DemoShowcase({ isOpen, onClose }) {
  const [currentPhase, setCurrentPhase] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!isOpen) {
      setCurrentPhase(0)
      setProgress(0)
      return
    }

    let elapsed = 0
    const interval = setInterval(() => {
      elapsed += 50
      setProgress((elapsed / TOTAL_DURATION) * 100)

      // Calculate current phase
      let phaseTime = 0
      for (let i = 0; i < PHASES.length; i++) {
        phaseTime += PHASES[i].duration
        if (elapsed < phaseTime) {
          setCurrentPhase(i)
          break
        }
      }

      // Auto-close at end
      if (elapsed >= TOTAL_DURATION) {
        clearInterval(interval)
        setTimeout(() => onClose(), 500)
      }
    }, 50)

    return () => clearInterval(interval)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const phase = PHASES[currentPhase]?.id

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

      {/* Skip button */}
      <button className="demo-skip" onClick={onClose}>
        Skip Demo →
      </button>

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
              <motion.div 
                className="pulse-ring"
                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </motion.div>
          )}

          {/* PHASE 2: PLATFORMS */}
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
              <div className="platform-grid">
                {[
                  { icon: '🖥️', name: 'Proxmox', color: '#e57000' },
                  { icon: '☁️', name: 'AWS', color: '#ff9900' },
                  { icon: '🔷', name: 'Azure', color: '#0078d4' },
                  { icon: '💠', name: 'ESXi', color: '#78be20' },
                ].map((platform, i) => (
                  <motion.div
                    key={platform.name}
                    className="platform-card"
                    initial={{ opacity: 0, y: 50, scale: 0.8 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ delay: 0.2 + i * 0.15, type: "spring", stiffness: 200 }}
                    style={{ '--accent': platform.color }}
                  >
                    <div className="platform-icon">{platform.icon}</div>
                    <div className="platform-name">{platform.name}</div>
                    <motion.div 
                      className="platform-status"
                      initial={{ width: 0 }}
                      animate={{ width: '100%' }}
                      transition={{ delay: 0.8 + i * 0.1, duration: 0.5 }}
                    >
                      <span>● Connected</span>
                    </motion.div>
                  </motion.div>
                ))}
              </div>
              <motion.p
                className="platform-subtitle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.5 }}
              >
                One interface. Every platform.
              </motion.p>
            </motion.div>
          )}

          {/* PHASE 3: OVERSEER AI */}
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
                    '0 0 60px rgba(0, 212, 255, 0.3)',
                    '0 0 100px rgba(0, 212, 255, 0.6)',
                    '0 0 60px rgba(0, 212, 255, 0.3)',
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
                Meet <span className="highlight">Overseer</span>
              </motion.h2>
              <motion.p
                className="ai-subtitle"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Your AI Operations Co-Pilot
              </motion.p>
              <motion.div 
                className="chat-demo"
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 }}
              >
                <div className="chat-message user">
                  <TypeWriter text="Deploy a security lab to AWS" delay={1.5} />
                </div>
                <motion.div 
                  className="chat-message assistant"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 3.5 }}
                >
                  <span className="typing-indicator">
                    <span></span><span></span><span></span>
                  </span>
                  ✅ Lab deployed in 47 seconds
                </motion.div>
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 4: DEPLOYMENT */}
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
              <div className="deploy-timeline">
                {[
                  { step: 'Network Created', time: '0.8s', icon: '🌐' },
                  { step: 'VMs Provisioned', time: '12s', icon: '🖥️' },
                  { step: 'Services Configured', time: '8s', icon: '⚙️' },
                  { step: 'Lab Ready', time: '✓', icon: '🚀' },
                ].map((item, i) => (
                  <motion.div
                    key={item.step}
                    className="timeline-item"
                    initial={{ opacity: 0, x: -30 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.3 + i * 0.6 }}
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
                      transition={{ delay: 0.5 + i * 0.6, duration: 0.4 }}
                    />
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* PHASE 5: SECURITY */}
          {phase === 'security' && (
            <motion.div
              key="security"
              className="demo-phase security"
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
                <span className="highlight">Reaper</span> Vulnerability Engine
              </motion.h2>
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.8 }}
              >
                Inject real-world vulnerabilities for training
              </motion.p>
              <motion.div 
                className="vuln-list"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1.2 }}
              >
                {['SQL Injection', 'XSS', 'Privilege Escalation', 'Weak SSH'].map((vuln, i) => (
                  <motion.span
                    key={vuln}
                    className="vuln-tag"
                    initial={{ opacity: 0, scale: 0 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 1.5 + i * 0.2 }}
                  >
                    {vuln}
                  </motion.span>
                ))}
              </motion.div>
            </motion.div>
          )}

          {/* PHASE 6: STATS */}
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
                Enterprise Ready
              </motion.h2>
              <div className="stats-grid">
                {[
                  { value: '4', label: 'Platforms', suffix: '' },
                  { value: '12', label: 'AI Tools', suffix: '+' },
                  { value: '47', label: 'Sec Deploy', suffix: 's' },
                  { value: '100', label: 'Automated', suffix: '%' },
                ].map((stat, i) => (
                  <motion.div
                    key={stat.label}
                    className="stat-card"
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + i * 0.15 }}
                  >
                    <div className="stat-value">
                      <CountUp to={parseInt(stat.value)} delay={0.5 + i * 0.15} />
                      <span className="stat-suffix">{stat.suffix}</span>
                    </div>
                    <div className="stat-label">{stat.label}</div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* PHASE 7: FINALE */}
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
                Ready to Transform Your Training?
              </motion.div>
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

