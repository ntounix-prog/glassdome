# Glassdome API Documentation

> **Updated:** November 2025 (v1 API Refactor)

## Base URL

```
http://localhost:8011/api/v1
```

Production (via nginx):
```
https://your-domain.com/api/v1
```

## Authentication

All endpoints (except `/api/v1/health` and `/api/v1/auth/login`) require JWT authentication.

**Header:**
```
Authorization: Bearer <token>
```

### Role-Based Access Control (RBAC)

| Role | Level | Access |
|------|-------|--------|
| Admin | 100 | Full system access, user management |
| Architect | 75 | Lab design, deployment, configuration |
| Engineer | 50 | Operate labs, run missions, monitoring |
| Observer | 25 | Read-only access, view dashboards |

---

## Core Endpoints

### Health & Status

#### GET `/api/v1/health`
Check API health status (no auth required)

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-29T12:00:00Z"
}
```

---

### Authentication (`/api/v1/auth`)

#### POST `/api/v1/auth/login`
Authenticate and receive JWT token

**Request Body:**
```json
{
  "username": "engineer@glassdome.local",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "engineer",
    "email": "engineer@glassdome.local",
    "role": "engineer",
    "level": 50
  }
}
```

#### POST `/api/v1/auth/register`
Create a new user (Admin only)

#### GET `/api/v1/auth/me`
Get current user info

#### GET `/api/v1/auth/users`
List all users (Admin only)

#### PUT `/api/v1/auth/users/{user_id}`
Update user role/level (Admin only)

#### POST `/api/v1/auth/change-password`
Change current user's password

---

### Lab Registry (`/api/v1/registry`)

#### GET `/api/v1/registry/status`
Get registry connection status and resource counts

**Response:**
```json
{
  "connected": true,
  "resource_counts": {
    "lab_vm": 3,
    "vm": 30,
    "template": 8
  },
  "total_resources": 41,
  "lab_count": 3,
  "active_drifts": 0,
  "agents": 1,
  "agent_names": ["unifi"]
}
```

#### GET `/api/v1/registry/resources`
List all registered resources

#### GET `/api/v1/registry/labs`
List all labs

#### GET `/api/v1/registry/labs/{lab_id}`
Get specific lab details

---

### Labs (`/api/v1/labs`)

#### POST `/api/v1/labs`
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

#### GET `/api/v1/labs`
List all lab configurations

#### GET `/api/v1/labs/{lab_id}`
Get lab configuration by ID

#### PUT `/api/v1/labs/{lab_id}`
Update lab configuration

#### DELETE `/api/v1/labs/{lab_id}`
Delete a lab configuration

---

### Canvas Deployment (`/api/v1/canvas`)

#### POST `/api/v1/canvas/deploy`
Deploy a lab from canvas design (Architect+)

**Request Body:**
```json
{
  "lab_id": "lab_123",
  "platform": "proxmox",
  "proxmox_instance": "01"
}
```

**Response:**
```json
{
  "success": true,
  "deployment_id": "deploy-mylab-143022",
  "vlan_id": 101,
  "message": "Deployment started"
}
```

#### GET `/api/v1/canvas/deployments/{deployment_id}/status`
Get deployment status

---

### Reaper - Vulnerability Engine (`/api/v1/reaper`)

#### GET `/api/v1/reaper/exploits`
List all exploits (Engineer+)

#### POST `/api/v1/reaper/exploits`
Create a new exploit definition (Architect+)

#### GET `/api/v1/reaper/exploits/{exploit_id}`
Get exploit details

#### GET `/api/v1/reaper/exploits/template`
Get JSON template for creating exploits

#### GET `/api/v1/reaper/exploits/export`
Export all exploits as JSON (Architect+)

#### POST `/api/v1/reaper/exploits/import`
Import exploits from JSON (Architect+)

#### GET `/api/v1/reaper/missions`
List all missions (Engineer+)

#### POST `/api/v1/reaper/missions`
Create a vulnerability injection mission

#### GET `/api/v1/reaper/stats`
Get Reaper statistics

**Response:**
```json
{
  "exploits": {
    "total": 25,
    "enabled": 20,
    "verified": 15,
    "by_type": {"CREDENTIAL": 5, "WEB": 10, "NETWORK": 5, "PRIVESC": 5},
    "by_severity": {"high": 10, "medium": 10, "low": 5}
  },
  "missions": {
    "total": 12,
    "by_status": {"completed": 8, "running": 2, "pending": 2}
  }
}
```

---

### WhiteKnight - Validation (`/api/v1/whiteknight`)

#### POST `/api/v1/whiteknight/validate`
Validate vulnerabilities on target VMs

#### GET `/api/v1/whiteknight/status/{validation_id}`
Get validation status

#### GET `/api/v1/whiteknight/results/{validation_id}`
Get validation results

---

### WhitePawn - Monitoring (`/api/v1/whitepawn`)

#### GET `/api/v1/whitepawn/status`
Get WhitePawn orchestrator status

#### GET `/api/v1/whitepawn/deployments`
List monitored deployments

#### GET `/api/v1/whitepawn/alerts`
Get network alerts

#### POST `/api/v1/whitepawn/deploy`
Deploy WhitePawn monitoring for a lab

---

### Platforms (`/api/v1/platforms`)

#### GET `/api/v1/platforms`
List all configured platforms

#### GET `/api/v1/platforms/{platform_id}/status`
Get platform connection status

#### POST `/api/v1/platforms/{platform_id}/test`
Test platform connectivity

---

### Secrets Management (`/api/v1/secrets`)

#### GET `/api/v1/secrets`
List all secrets (Admin only - returns keys, not values)

#### GET `/api/v1/secrets/{key}`
Get a specific secret value (Admin only)

#### POST `/api/v1/secrets`
Create/update a secret (Admin only)

#### DELETE `/api/v1/secrets/{key}`
Delete a secret (Admin only)

---

### Network Probes (`/api/v1/probes`)

#### GET `/api/v1/probes/mxwest`
Get MXWEST network probe status

---

### Chat/Overseer (`/api/v1/chat`)

#### POST `/api/v1/chat/conversations`
Create a new conversation

#### GET `/api/v1/chat/conversations`
List conversations

#### POST `/api/v1/chat/conversations/{id}/messages`
Send a message to Overseer

#### WebSocket `/api/v1/chat/ws`
Real-time chat connection

---

## WebSocket Events

### Connect
```javascript
const ws = new WebSocket('ws://localhost:8011/api/v1/chat/ws');
```

### Events

#### `deployment_update`
Real-time deployment progress

#### `registry_update`
Lab registry state changes

#### `alert`
WhitePawn monitoring alerts

---

## Error Responses

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

### Common Status Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource Not Found |
| 422 | Unprocessable Entity (validation failed) |
| 500 | Internal Server Error |

---

## Legacy API Redirect

For backward compatibility, requests to `/api/*` are redirected (307) to `/api/v1/*`.

Example:
- `GET /api/health` → redirects to → `GET /api/v1/health`

**Note:** Update your clients to use `/api/v1/` directly for best performance.

---

## API Versioning

The API uses URL versioning. Current version: `v1`

Future versions will be available at `/api/v2/`, `/api/v3/`, etc.

---

*Last updated: November 2025*
