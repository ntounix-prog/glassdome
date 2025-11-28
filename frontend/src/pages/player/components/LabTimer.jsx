/**
 * Labtimer page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

/**
 * LabTimer - Countdown timer for lab sessions
 */

import { useState, useEffect } from 'react';
import '../../../styles/player/LabTimer.css';

export default function LabTimer({ startTime, timeLimit = 7200, compact = false }) {
  const [remaining, setRemaining] = useState(timeLimit);
  const [isWarning, setIsWarning] = useState(false);
  const [isCritical, setIsCritical] = useState(false);

  useEffect(() => {
    if (!startTime) {
      setRemaining(timeLimit);
      return;
    }

    const updateTimer = () => {
      const started = new Date(startTime).getTime();
      const now = Date.now();
      const elapsed = Math.floor((now - started) / 1000);
      const left = Math.max(0, timeLimit - elapsed);
      
      setRemaining(left);
      setIsWarning(left <= 600); // 10 minutes
      setIsCritical(left <= 120); // 2 minutes
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    
    return () => clearInterval(interval);
  }, [startTime, timeLimit]);

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hrs > 0) {
      return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getTimerClass = () => {
    let className = 'lab-timer';
    if (compact) className += ' compact';
    if (isWarning) className += ' warning';
    if (isCritical) className += ' critical';
    return className;
  };

  return (
    <div className={getTimerClass()}>
      <span className="timer-icon">⏱️</span>
      <span className="timer-value">{formatTime(remaining)}</span>
      {!compact && <span className="timer-label">remaining</span>}
    </div>
  );
}

