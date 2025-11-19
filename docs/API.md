# Glassdome API Documentation

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently no authentication required (development mode). Production will use JWT tokens.

---

## Endpoints

### Health & Status

#### GET `/health`
Check API health status

**Response:**
```json
{
  "status": "healthy",
  "message": "Glassdome API is running",
  "version": "0.1.0"
}
```

---

### Lab Management

#### POST `/labs`
Create a new lab configuration

**Request Body:**
```json
{
  "name": "My Cyber Range Lab",
  "description": "Web security testing lab",
  "canvas_data": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response:**
```json
{
  "success": true,
  "lab_id": "lab_123",
  "message": "Lab created successfully"
}
```

#### GET `/labs`
List all lab configurations

**Response:**
```json
{
  "labs": [
    {
      "id": "lab_123",
      "name": "My Cyber Range Lab",
      "created_at": "2024-01-01T00:00:00Z",
      "elements_count": 5
    }
  ],
  "total": 1
}
```

#### GET `/labs/{lab_id}`
Get lab configuration by ID

**Response:**
```json
{
  "lab_id": "lab_123",
  "name": "My Cyber Range Lab",
  "description": "Web security testing lab",
  "canvas_data": {...},
  "elements": [...]
}
```

#### PUT `/labs/{lab_id}`
Update lab configuration

**Request Body:**
```json
{
  "name": "Updated Lab Name",
  "canvas_data": {...}
}
```

#### DELETE `/labs/{lab_id}`
Delete a lab configuration

---

### Deployments

#### POST `/deployments`
Create a new deployment

**Request Body:**
```json
{
  "lab_id": "lab_123",
  "platform_id": "platform_1",
  "name": "Production Deployment",
  "auto_shutdown_minutes": 120
}
```

**Response:**
```json
{
  "success": true,
  "deployment_id": "deploy_123",
  "status": "pending",
  "message": "Deployment initiated"
}
```

#### GET `/deployments`
List all deployments

**Response:**
```json
{
  "deployments": [
    {
      "id": "deploy_123",
      "name": "Production Deployment",
      "status": "in_progress",
      "progress": 45,
      "platform": "Proxmox",
      "resource_count": 5
    }
  ],
  "total": 1
}
```

#### GET `/deployments/{deployment_id}`
Get deployment status and details

**Response:**
```json
{
  "deployment_id": "deploy_123",
  "lab_id": "lab_123",
  "status": "in_progress",
  "progress_percentage": 45,
  "current_step": "Creating VM kali-linux",
  "resources": [
    {
      "type": "vm",
      "id": "vm-101",
      "name": "kali-linux",
      "status": "running",
      "ip": "10.0.0.101"
    }
  ],
  "started_at": "2024-01-01T00:00:00Z"
}
```

#### POST `/deployments/{deployment_id}/stop`
Stop all resources in a deployment

**Response:**
```json
{
  "success": true,
  "deployment_id": "deploy_123",
  "message": "Deployment stopped"
}
```

#### DELETE `/deployments/{deployment_id}`
Destroy a deployment and all resources

**Response:**
```json
{
  "success": true,
  "deployment_id": "deploy_123",
  "message": "Deployment destroyed"
}
```

---

### Platform Management

#### GET `/platforms`
List all configured platforms

**Response:**
```json
{
  "platforms": [
    {
      "id": "1",
      "name": "Proxmox Main",
      "type": "proxmox",
      "status": "active",
      "last_health_check": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### POST `/platforms`
Add a new platform configuration

**Request Body:**
```json
{
  "name": "Azure Production",
  "platform_type": "azure",
  "credentials": {
    "subscription_id": "...",
    "tenant_id": "...",
    "client_id": "...",
    "client_secret": "..."
  }
}
```

#### POST `/platforms/{platform_id}/test`
Test connection to a platform

**Response:**
```json
{
  "success": true,
  "platform_id": "1",
  "status": "connected",
  "response_time_ms": 45
}
```

---

### Templates

#### GET `/templates`
List all lab templates

**Response:**
```json
{
  "templates": [
    {
      "id": "1",
      "name": "Basic Web Security Lab",
      "category": "Web Security",
      "description": "DVWA + Kali Linux",
      "usage_count": 10,
      "is_public": true
    }
  ]
}
```

#### GET `/templates/{template_id}`
Get template details

**Response:**
```json
{
  "template_id": "1",
  "name": "Basic Web Security Lab",
  "category": "Web Security",
  "template_data": {...},
  "elements": [...]
}
```

#### POST `/templates`
Create a new template from a lab

**Request Body:**
```json
{
  "lab_id": "lab_123",
  "name": "My Custom Template",
  "category": "Network Security",
  "description": "Custom network pentesting environment",
  "is_public": false
}
```

---

### Agent Management

#### GET `/agents/status`
Get status of all agents

**Response:**
```json
{
  "total_agents": 3,
  "agents": {
    "agent_1": {
      "type": "deployment",
      "status": "idle",
      "error": null
    },
    "agent_2": {
      "type": "monitoring",
      "status": "running",
      "error": null
    }
  },
  "queue_size": 5,
  "running": true
}
```

#### GET `/agents/{agent_id}`
Get specific agent details

**Response:**
```json
{
  "agent_id": "agent_1",
  "type": "deployment",
  "status": "idle",
  "error": null,
  "tasks_completed": 42
}
```

---

### Element Library

#### GET `/elements`
List available lab elements

**Response:**
```json
{
  "elements": {
    "vms": [
      {
        "id": "kali-2024",
        "name": "Kali Linux 2024",
        "type": "attack",
        "description": "Latest Kali Linux for penetration testing",
        "resources": {
          "cpu": 2,
          "memory": 4096,
          "disk": 80
        }
      }
    ],
    "networks": [
      {
        "id": "isolated",
        "name": "Isolated Network",
        "type": "internal"
      }
    ],
    "services": [
      {
        "id": "web-server",
        "name": "Apache Web Server",
        "type": "service"
      }
    ]
  }
}
```

---

### Statistics

#### GET `/stats`
Get overall statistics

**Response:**
```json
{
  "total_labs": 15,
  "active_deployments": 3,
  "total_deployments": 47,
  "total_templates": 8,
  "resources_deployed": {
    "vms": 12,
    "networks": 5
  }
}
```

---

## WebSocket Events

### Connect
```javascript
const socket = io('http://localhost:8000')
```

### Events

#### `deployment_update`
Real-time deployment progress updates

**Payload:**
```json
{
  "deployment_id": "deploy_123",
  "status": "in_progress",
  "progress": 65,
  "current_step": "Configuring network",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

#### `agent_status`
Agent status changes

**Payload:**
```json
{
  "agent_id": "agent_1",
  "status": "running",
  "current_task": "deploy_vm_kali"
}
```

---

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "detail": "Error message",
  "error_code": "RESOURCE_NOT_FOUND",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### Common Error Codes

- `400` - Bad Request (validation error)
- `404` - Resource Not Found
- `409` - Conflict (resource already exists)
- `500` - Internal Server Error
- `503` - Service Unavailable (platform connection error)

---

## Rate Limiting

Currently no rate limiting in development. Production will implement:
- 100 requests per minute per IP for read operations
- 20 requests per minute per IP for write operations
- 5 deployments per hour per user

---

## Future Endpoints

Coming soon:
- `/api/research/import` - Import lab from research system
- `/api/deployments/{id}/clone` - Clone existing deployment
- `/api/templates/marketplace` - Public template marketplace
- `/api/costs/estimate` - Estimate deployment costs
- `/api/audit/logs` - Audit log access

