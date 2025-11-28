/**
 * Playerportal page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

/**
 * PlayerPortal - Entry point for players to access their labs
 * 
 * "What's Updock?" 🥕🐰
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatModal from '../../components/OverseerChat/ChatModal';
import ChatToggle from '../../components/OverseerChat/ChatToggle';
import '../../styles/player/PlayerPortal.css';

export default function PlayerPortal() {
  const [labCode, setLabCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMusicPlaying, setIsMusicPlaying] = useState(false);
  const navigate = useNavigate();

  // Particle effect for background
  useEffect(() => {
    const canvas = document.getElementById('particle-canvas');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    
    const particles = [];
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        size: Math.random() * 2 + 1,
        opacity: Math.random() * 0.5 + 0.2
      });
    }
    
    function animate() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(p => {
        p.x += p.vx;
        p.y += p.vy;
        
        if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
        if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
        
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(0, 255, 200, ${p.opacity})`;
        ctx.fill();
      });
      
      // Draw connections
      particles.forEach((p1, i) => {
        particles.slice(i + 1).forEach(p2 => {
          const dx = p1.x - p2.x;
          const dy = p1.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p1.x, p1.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(0, 255, 200, ${0.1 * (1 - dist / 150)})`;
            ctx.stroke();
          }
        });
      });
      
      requestAnimationFrame(animate);
    }
    
    animate();
    
    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener('resize', handleResize);
    
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!labCode.trim()) {
      setError('Please enter a lab code');
      return;
    }
    
    setLoading(true);
    setError('');
    
    try {
      // Check if lab exists - but navigate anyway for demo
      const response = await fetch(`/api/deployments/${labCode.trim()}`);
      
      // Always navigate - lobby has mock data fallback
      navigate(`/player/${labCode.trim().toLowerCase()}`);
    } catch (err) {
      // Navigate anyway - we'll validate later
      navigate(`/player/${labCode.trim().toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="player-portal">
      <canvas id="particle-canvas" className="particle-background" />
      
      <div className="portal-content">
        <div className="portal-header">
          <div className="logo-container">
            <div className="logo-glow" />
            <h1 className="logo-text">
              <span className="logo-glass">GLASS</span>
              <span className="logo-dome">DOME</span>
            </h1>
          </div>
          <p className="tagline">Cyber Range Platform</p>
        </div>
        
        <div className="portal-card">
          <div className="card-header">
            <div className="card-icon">🎯</div>
            <h2>Enter the Range</h2>
          </div>
          
          <form onSubmit={handleSubmit} className="portal-form">
            <div className="input-group">
              <label htmlFor="labCode">Lab Access Code</label>
              <input
                id="labCode"
                type="text"
                value={labCode}
                onChange={(e) => setLabCode(e.target.value.toUpperCase())}
                placeholder="BRETTLAB"
                autoFocus
                autoComplete="off"
                spellCheck="false"
              />
              <div className="input-glow" />
            </div>
            
            {error && (
              <div className="error-message">
                <span className="error-icon">⚠️</span>
                {error}
              </div>
            )}
            
            <button 
              type="submit" 
              className={`enter-button ${loading ? 'loading' : ''}`}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner" />
                  Connecting...
                </>
              ) : (
                <>
                  <span className="button-icon">🚀</span>
                  ENTER RANGE
                </>
              )}
            </button>
          </form>
          
          <div className="card-footer">
            <p>Your mission awaits, operator.</p>
          </div>
        </div>
        
        <div className="portal-footer">
          <p className="footer-text">
            Powered by <span className="highlight">Updock</span> • 
            Secured by <span className="highlight">Glassdome</span>
          </p>
        </div>
      </div>
      
      {/* Overseer Chat with Music */}
      <ChatToggle 
        onClick={() => setIsChatOpen(true)} 
        isMusicPlaying={isMusicPlaying}
      />
      <ChatModal 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)}
        onMusicStateChange={setIsMusicPlaying}
      />
    </div>
  );
}

