import React, { useState } from 'react';
import './QuickDeploy.css';

/**
 * Quick Deploy Component
 * 
 * For SINGLE VM deployments - goes directly to agent endpoints
 * No orchestration, just creates one VM quickly
 */
export default function QuickDeploy() {
  const [vmType, setVmType] = useState('');
  const [vmName, setVmName] = useState('');
  const [cores, setCores] = useState(2);
  const [memory, setMemory] = useState(4096);
  const [diskSize, setDiskSize] = useState(20);
  const [deploying, setDeploying] = useState(false);
  const [result, setResult] = useState(null);

  const OS_OPTIONS = [
    { value: 'ubuntu', label: 'Ubuntu 22.04', version: '22.04', agent: 'ubuntu' },
    { value: 'ubuntu-20', label: 'Ubuntu 20.04', version: '20.04', agent: 'ubuntu' },
    { value: 'kali', label: 'Kali Linux 2024.1', version: '2024.1', agent: 'kali' },
    { value: 'debian', label: 'Debian 12', version: '12', agent: 'debian' },
    { value: 'centos', label: 'CentOS Stream 9', version: '9', agent: 'centos' },
  ];

  const handleDeploy = async () => {
    if (!vmType || !vmName) {
      alert('Please select OS type and enter VM name');
      return;
    }

    setDeploying(true);
    setResult(null);

    try {
      const selectedOS = OS_OPTIONS.find(os => os.value === vmType);
      
      // Direct API call to agent endpoint (no orchestrator)
      const response = await fetch(`/api/agents/${selectedOS.agent}/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: vmName,
          version: selectedOS.version,
          cores: cores,
          memory: memory,
          disk_size: diskSize,
          use_template: true,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult({
          success: true,
          vm_id: data.vm_id,
          ip_address: data.ip_address,
          message: `VM created successfully!`,
        });
      } else {
        setResult({
          success: false,
          message: data.detail || 'Deployment failed',
        });
      }
    } catch (error) {
      setResult({
        success: false,
        message: `Error: ${error.message}`,
      });
    } finally {
      setDeploying(false);
    }
  };

  return (
    <div className="quick-deploy">
      <div className="deploy-header">
        <h2>🚀 Quick Deploy</h2>
        <p className="deploy-subtitle">
          Deploy a single VM directly (no orchestration)
        </p>
      </div>

      <div className="deploy-form">
        <div className="form-group">
          <label>Operating System</label>
          <select
            value={vmType}
            onChange={(e) => setVmType(e.target.value)}
            disabled={deploying}
          >
            <option value="">Select OS...</option>
            {OS_OPTIONS.map((os) => (
              <option key={os.value} value={os.value}>
                {os.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label>VM Name</label>
          <input
            type="text"
            value={vmName}
            onChange={(e) => setVmName(e.target.value)}
            placeholder="my-ubuntu-vm"
            disabled={deploying}
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>CPU Cores</label>
            <input
              type="number"
              value={cores}
              onChange={(e) => setCores(parseInt(e.target.value))}
              min="1"
              max="16"
              disabled={deploying}
            />
          </div>

          <div className="form-group">
            <label>Memory (MB)</label>
            <input
              type="number"
              value={memory}
              onChange={(e) => setMemory(parseInt(e.target.value))}
              min="1024"
              max="32768"
              step="1024"
              disabled={deploying}
            />
          </div>

          <div className="form-group">
            <label>Disk Size (GB)</label>
            <input
              type="number"
              value={diskSize}
              onChange={(e) => setDiskSize(parseInt(e.target.value))}
              min="10"
              max="500"
              disabled={deploying}
            />
          </div>
        </div>

        <button
          className="deploy-button"
          onClick={handleDeploy}
          disabled={deploying || !vmType || !vmName}
        >
          {deploying ? 'Deploying...' : 'Deploy VM'}
        </button>
      </div>

      {result && (
        <div className={`result ${result.success ? 'success' : 'error'}`}>
          <h3>{result.success ? '✅ Success' : '❌ Failed'}</h3>
          <p>{result.message}</p>
          {result.success && (
            <div className="vm-details">
              <p><strong>VM ID:</strong> {result.vm_id}</p>
              {result.ip_address && (
                <p><strong>IP Address:</strong> {result.ip_address}</p>
              )}
            </div>
          )}
        </div>
      )}

      <div className="info-box">
        <h4>ℹ️ Quick Deploy Info</h4>
        <ul>
          <li>✅ Fast: Creates single VM directly via agent</li>
          <li>✅ Simple: No user accounts or packages</li>
          <li>✅ Good for: Testing, basic infrastructure</li>
          <li>⚠️ For complex labs with users/packages, use Lab Designer</li>
        </ul>
      </div>
    </div>
  );
}

