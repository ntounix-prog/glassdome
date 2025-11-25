/**
 * ActionConfirm Component
 * 
 * Displays a pending action that needs operator confirmation.
 */

import './ActionConfirm.css'

export default function ActionConfirm({ action, onConfirm, onReject }) {
  if (!action) return null

  return (
    <div className="action-confirm">
      <div className="action-header">
        <div className="action-icon">⚡</div>
        <div className="action-title">Confirm Action</div>
      </div>
      
      <div className="action-summary">
        {action.summary}
      </div>
      
      {action.details && Object.keys(action.details).length > 0 && (
        <div className="action-details">
          <div className="details-header">Details:</div>
          <ul className="details-list">
            {Object.entries(action.details).map(([key, value]) => (
              <li key={key}>
                <span className="detail-key">{formatKey(key)}:</span>
                <span className="detail-value">{formatValue(value)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {action.warnings && action.warnings.length > 0 && (
        <div className="action-warnings">
          {action.warnings.map((warning, index) => (
            <div key={index} className="warning-item">
              ⚠️ {warning}
            </div>
          ))}
        </div>
      )}
      
      <div className="action-buttons">
        <button 
          className="action-btn action-btn-reject"
          onClick={onReject}
        >
          Cancel
        </button>
        <button 
          className="action-btn action-btn-confirm"
          onClick={onConfirm}
        >
          Confirm
        </button>
      </div>
    </div>
  )
}

function formatKey(key) {
  return key
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .split(' ')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.join(', ')
  }
  if (typeof value === 'object') {
    return JSON.stringify(value, null, 2)
  }
  if (typeof value === 'boolean') {
    return value ? 'Yes' : 'No'
  }
  return String(value)
}

