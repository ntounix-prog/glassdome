import React, { useState, useEffect } from 'react';
import './LabTemplates.css';

/**
 * Lab Templates Component
 * 
 * For COMPLETE LAB deployments - goes to orchestrator
 * Orchestrator coordinates multiple agents and full configuration
 */
export default function LabTemplates() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [deploying, setDeploying] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const response = await fetch('/api/labs/templates');
      const data = await response.json();
      setTemplates(data.templates);
    } catch (error) {
      console.error('Failed to load templates:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSelect = (template) => {
    setSelectedTemplate(template);
    setResult(null);
  };

  const handleDeploy = async () => {
    if (!selectedTemplate) return;

    setDeploying(true);
    setResult(null);

    try {
      // Get full template specification
      const specResponse = await fetch(`/api/labs/templates/${selectedTemplate.id}`);
      const labSpec = await specResponse.json();

      // Deploy via orchestrator
      const response = await fetch('/api/labs/deploy', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          lab_spec: labSpec,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setResult({
          success: true,
          lab_id: data.lab_id,
          execution_plan: data.execution_plan,
          result: data.result,
          message: 'Lab deployed successfully!',
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

  if (loading) {
    return (
      <div className="lab-templates loading">
        <p>Loading lab templates...</p>
      </div>
    );
  }

  return (
    <div className="lab-templates">
      <div className="templates-header">
        <h2>🎯 Lab Templates</h2>
        <p className="templates-subtitle">
          Deploy complete labs with orchestration (multiple VMs, users, packages)
        </p>
      </div>

      <div className="templates-grid">
        {templates.map((template) => (
          <div
            key={template.id}
            className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
            onClick={() => handleTemplateSelect(template)}
          >
            <h3>{template.name}</h3>
            <p className="template-description">{template.description}</p>
            
            <div className="template-info">
              <div className="info-item">
                <span className="info-label">VMs:</span>
                <span className="info-value">{template.vm_count}</span>
              </div>
            </div>

            <div className="template-vms">
              {template.vms.map((vm, idx) => (
                <div key={idx} className="vm-chip">
                  <strong>{vm.name}</strong>
                  <span>{vm.os}</span>
                  <span className="vm-resources">
                    {vm.resources.cores}c / {vm.resources.memory}MB / {vm.resources.disk_size}GB
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {selectedTemplate && (
        <div className="deploy-section">
          <h3>Deploy: {selectedTemplate.name}</h3>
          <p>This will create {selectedTemplate.vm_count} VMs with full configuration</p>
          
          <button
            className="deploy-button"
            onClick={handleDeploy}
            disabled={deploying}
          >
            {deploying ? 'Deploying Lab...' : 'Deploy Complete Lab'}
          </button>
        </div>
      )}

      {result && (
        <div className={`result ${result.success ? 'success' : 'error'}`}>
          <h3>{result.success ? '✅ Lab Deployed' : '❌ Deployment Failed'}</h3>
          <p>{result.message}</p>
          
          {result.success && (
            <div className="lab-details">
              <p><strong>Lab ID:</strong> {result.lab_id}</p>
              
              {result.execution_plan && (
                <div className="execution-plan">
                  <h4>Execution Plan:</h4>
                  {result.execution_plan.map((layer, idx) => (
                    <div key={idx} className="plan-layer">
                      <strong>Layer {idx + 1}:</strong> {layer.join(', ')}
                    </div>
                  ))}
                </div>
              )}
              
              {result.result && (
                <div className="deployment-stats">
                  <p><strong>Total tasks:</strong> {result.result.total_tasks}</p>
                  <p><strong>Completed:</strong> {result.result.completed}</p>
                  <p><strong>Duration:</strong> {result.result.duration_seconds?.toFixed(2)}s</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className="info-box">
        <h4>🎯 Orchestrated Lab Deployment</h4>
        <ul>
          <li>✅ Multiple VMs coordinated by orchestrator</li>
          <li>✅ User accounts created with SSH keys</li>
          <li>✅ Packages installed (system + Python + Docker)</li>
          <li>✅ Network configuration (static IPs, VLANs)</li>
          <li>✅ Dependencies managed (execution order)</li>
          <li>✅ Post-installation scripts run</li>
          <li>⏱️ Takes longer but creates complete environment</li>
        </ul>
      </div>
    </div>
  );
}

