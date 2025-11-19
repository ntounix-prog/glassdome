import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [healthStatus, setHealthStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setHealthStatus(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('API Error:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="App">
      <header className="App-header">
        <h1>🔮 Glassdome</h1>
        <p>Full Stack Application</p>
        
        <div className="status-card">
          <h3>Backend Status</h3>
          {loading ? (
            <p>Checking...</p>
          ) : healthStatus ? (
            <div className="status-success">
              <p>✅ {healthStatus.message}</p>
              <p>Status: {healthStatus.status}</p>
            </div>
          ) : (
            <p className="status-error">❌ Backend not responding</p>
          )}
        </div>

        <div className="tech-stack">
          <h3>Tech Stack</h3>
          <div className="tech-badges">
            <span className="badge">⚛️ React</span>
            <span className="badge">🐍 Python</span>
            <span className="badge">⚡ FastAPI</span>
            <span className="badge">🐳 Docker</span>
          </div>
        </div>
      </header>
    </div>
  )
}

export default App

