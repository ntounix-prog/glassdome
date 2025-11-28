/**
 * Playerlobby page component
 * 
 * @author Brett Turner (ntounix-prog)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

/**
 * PlayerLobby - Lab machine selection and mission brief
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ChatModal from '../../components/OverseerChat/ChatModal';
import ChatToggle from '../../components/OverseerChat/ChatToggle';
import MachineCard from './components/MachineCard';
import MissionBrief from './components/MissionBrief';
import LabTimer from './components/LabTimer';
import '../../styles/player/PlayerLobby.css';

export default function PlayerLobby() {
  const { labId } = useParams();
  const navigate = useNavigate();
  const [lab, setLab] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isMusicPlaying, setIsMusicPlaying] = useState(false);

  useEffect(() => {
    fetchLabDetails();
  }, [labId]);

  const fetchLabDetails = async () => {
    try {
      setLoading(true);
      
      // Try to get deployment info
      const response = await fetch(`/api/deployments/${labId}`);
      
      if (response.ok) {
        const data = await response.json();
        setLab(data);
      } else {
        // Mock data for testing
        setLab({
          lab_id: labId,
          name: labId.toUpperCase(),
          status: 'running',
          network: {
            vlan_id: 101,
            cidr: '10.101.0.0/24',
            gateway: '10.101.0.1'
          },
          vms: [
            {
              node_id: 'kali-1',
              name: `${labId}-kali-00`,
              vm_id: '115',
              role: 'attack',
              status: 'running',
              os: 'kali',
              ip_address: '10.101.0.10'
            },
            {
              node_id: 'ubuntu-1',
              name: `${labId}-ubuntu-01`,
              vm_id: '116',
              role: 'target',
              status: 'running',
              os: 'ubuntu',
              ip_address: '10.101.0.11'
            }
          ],
          mission: {
            title: 'Root Access Challenge',
            objective: 'Gain root access to the Ubuntu target server.',
            flag_format: 'FLAG{...}',
            difficulty: 'Medium',
            points: 100,
            hints: [
              { id: 1, text: 'Check for common services...', cost: 10, revealed: false },
              { id: 2, text: 'SSH might have weak credentials', cost: 20, revealed: false },
              { id: 3, text: 'Try user: admin, pass: admin123', cost: 50, revealed: false }
            ]
          },
          time_limit: 7200, // 2 hours
          started_at: new Date().toISOString()
        });
      }
    } catch (err) {
      console.error('Failed to fetch lab:', err);
      setError('Unable to load lab details');
    } finally {
      setLoading(false);
    }
  };

  const handleConnect = (vm) => {
    navigate(`/player/${labId}/${vm.name}`);
  };

  const handleExit = () => {
    if (confirm('Are you sure you want to exit the lab?')) {
      navigate('/player');
    }
  };

  if (loading) {
    return (
      <div className="player-lobby loading-screen">
        <div className="loading-content">
          <div className="loading-spinner" />
          <p>Initializing lab environment...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="player-lobby error-screen">
        <div className="error-content">
          <span className="error-icon">⚠️</span>
          <h2>Connection Error</h2>
          <p>{error}</p>
          <button onClick={() => navigate('/player')}>Return to Portal</button>
        </div>
      </div>
    );
  }

  return (
    <div className="player-lobby">
      {/* Header */}
      <header className="lobby-header">
        <div className="header-left">
          <button className="exit-button" onClick={handleExit}>
            ← Exit Lab
          </button>
        </div>
        <div className="header-center">
          <h1 className="lab-title">
            <span className="operation-label">OPERATION:</span>
            <span className="lab-name">{lab?.name || labId.toUpperCase()}</span>
          </h1>
        </div>
        <div className="header-right">
          <LabTimer 
            startTime={lab?.started_at} 
            timeLimit={lab?.time_limit} 
          />
        </div>
      </header>

      {/* Main Content */}
      <main className="lobby-main">
        {/* Machines Section */}
        <section className="machines-section">
          <h2 className="section-title">
            <span className="title-icon">🖥️</span>
            YOUR MACHINES
          </h2>
          <div className="machines-grid">
            {lab?.vms?.map((vm) => (
              <MachineCard
                key={vm.vm_id}
                vm={vm}
                onConnect={() => handleConnect(vm)}
              />
            ))}
          </div>
        </section>

        {/* Mission Brief */}
        <section className="mission-section">
          <MissionBrief mission={lab?.mission} />
        </section>

        {/* Network Info */}
        <section className="network-section">
          <h2 className="section-title">
            <span className="title-icon">🌐</span>
            NETWORK INFO
          </h2>
          <div className="network-info">
            <div className="info-item">
              <span className="info-label">VLAN</span>
              <span className="info-value">{lab?.network?.vlan_id}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Subnet</span>
              <span className="info-value">{lab?.network?.cidr}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Gateway</span>
              <span className="info-value">{lab?.network?.gateway}</span>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="lobby-footer">
        <div className="footer-left">
          <span className="status-indicator online" />
          Lab Status: <strong>Active</strong>
        </div>
        <div className="footer-right">
          <button className="help-button" onClick={() => setIsChatOpen(true)}>
            💬 Need Help?
          </button>
        </div>
      </footer>

      {/* Overseer Chat */}
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

