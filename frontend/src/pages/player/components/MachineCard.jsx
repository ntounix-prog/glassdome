/**
 * Machinecard page component
 * 
 * @author Brett Turner (ntounix)
 * @created November 2025
 * @copyright (c) 2025 Brett Turner. All rights reserved.
 */

/**
 * MachineCard - VM card for the lobby
 */

import '../../../styles/player/MachineCard.css';

export default function MachineCard({ vm, onConnect }) {
  const getOSIcon = (os) => {
    switch (os?.toLowerCase()) {
      case 'kali': return '🐉';
      case 'ubuntu': return '🐧';
      case 'linux': return '🐧';
      case 'windows': return '🪟';
      case 'pfsense': return '🔥';
      default: return '🖥️';
    }
  };

  const getRoleLabel = (role) => {
    switch (role?.toLowerCase()) {
      case 'attack': return 'Attack Box';
      case 'target': return 'Target';
      case 'gateway': return 'Gateway';
      default: return 'Machine';
    }
  };

  const getRoleClass = (role) => {
    switch (role?.toLowerCase()) {
      case 'attack': return 'role-attack';
      case 'target': return 'role-target';
      case 'gateway': return 'role-gateway';
      default: return '';
    }
  };

  const isOnline = vm.status === 'running';
  const osName = vm.os || vm.name?.split('-')[1] || 'unknown';

  return (
    <div className={`machine-card ${isOnline ? 'online' : 'offline'} ${getRoleClass(vm.role)}`}>
      <div className="card-header">
        <span className="os-icon">{getOSIcon(osName)}</span>
        <span className="os-name">{osName.toUpperCase()}</span>
      </div>
      
      <div className="card-body">
        <h3 className="machine-name">{vm.name}</h3>
        <p className="machine-role">{getRoleLabel(vm.role)}</p>
        
        <div className="machine-details">
          {vm.ip_address && (
            <div className="detail-item">
              <span className="detail-label">IP</span>
              <span className="detail-value">{vm.ip_address}</span>
            </div>
          )}
          <div className="detail-item">
            <span className="detail-label">Status</span>
            <span className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
              {isOnline ? '● Online' : '○ Offline'}
            </span>
          </div>
        </div>
      </div>
      
      <div className="card-footer">
        {isOnline ? (
          <button className="connect-button" onClick={onConnect}>
            <span className="button-icon">🔗</span>
            CONNECT
          </button>
        ) : (
          <button className="start-button" disabled>
            <span className="button-icon">▶️</span>
            START
          </button>
        )}
      </div>
    </div>
  );
}

