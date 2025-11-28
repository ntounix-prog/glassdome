/**
 * Missionbrief page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2024
 * @copyright (c) 2024 Brett Turner. All rights reserved.
 */

/**
 * MissionBrief - Mission objectives and hints
 */

import { useState } from 'react';
import '../../../styles/player/MissionBrief.css';

export default function MissionBrief({ mission }) {
  const [expandedHints, setExpandedHints] = useState(new Set());
  const [revealedHints, setRevealedHints] = useState(new Set());

  if (!mission) {
    return (
      <div className="mission-brief empty">
        <h2 className="section-title">
          <span className="title-icon">📋</span>
          MISSION BRIEF
        </h2>
        <p className="no-mission">No mission assigned. Explore freely!</p>
      </div>
    );
  }

  const handleRevealHint = (hintId, cost) => {
    if (confirm(`Reveal hint for ${cost} points?`)) {
      setRevealedHints(prev => new Set([...prev, hintId]));
    }
  };

  const toggleHint = (hintId) => {
    setExpandedHints(prev => {
      const next = new Set(prev);
      if (next.has(hintId)) {
        next.delete(hintId);
      } else {
        next.add(hintId);
      }
      return next;
    });
  };

  return (
    <div className="mission-brief">
      <h2 className="section-title">
        <span className="title-icon">📋</span>
        MISSION BRIEF
      </h2>
      
      <div className="mission-content">
        <div className="mission-header">
          <h3 className="mission-title">{mission.title}</h3>
          <div className="mission-meta">
            <span className={`difficulty difficulty-${mission.difficulty?.toLowerCase()}`}>
              {mission.difficulty}
            </span>
            <span className="points">{mission.points} pts</span>
          </div>
        </div>
        
        <div className="objective-section">
          <h4>Objective</h4>
          <p className="objective-text">{mission.objective}</p>
        </div>
        
        {mission.flag_format && (
          <div className="flag-format">
            <span className="format-label">Flag Format:</span>
            <code>{mission.flag_format}</code>
          </div>
        )}
        
        {mission.hints && mission.hints.length > 0 && (
          <div className="hints-section">
            <h4>Hints ({revealedHints.size}/{mission.hints.length} used)</h4>
            <div className="hints-list">
              {mission.hints.map((hint, index) => (
                <div 
                  key={hint.id} 
                  className={`hint-item ${revealedHints.has(hint.id) ? 'revealed' : ''}`}
                >
                  <div 
                    className="hint-header"
                    onClick={() => revealedHints.has(hint.id) && toggleHint(hint.id)}
                  >
                    <span className="hint-number">Hint {index + 1}</span>
                    {!revealedHints.has(hint.id) ? (
                      <button 
                        className="reveal-button"
                        onClick={() => handleRevealHint(hint.id, hint.cost)}
                      >
                        🔓 Reveal (-{hint.cost} pts)
                      </button>
                    ) : (
                      <span className="expand-icon">
                        {expandedHints.has(hint.id) ? '▼' : '▶'}
                      </span>
                    )}
                  </div>
                  {revealedHints.has(hint.id) && expandedHints.has(hint.id) && (
                    <div className="hint-content">
                      <p>{hint.text}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
        
        <div className="submit-section">
          <input 
            type="text" 
            placeholder="Enter flag here..."
            className="flag-input"
          />
          <button className="submit-button">
            🚩 Submit Flag
          </button>
        </div>
      </div>
    </div>
  );
}

