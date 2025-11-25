# Securityd Protocol Specification

## Overview

The securityd daemon exposes two interfaces:
1. **Unix Socket** - For local process communication (preferred for same-host access)
2. **HTTPS API** - For remote/container access (requires mTLS)

Both interfaces use the same JSON-based protocol.

## Transport Layer

### Unix Socket

**Path:** `/run/glassdome/securityd.sock`
**Permissions:** `0660` (owner and group read/write)
**Group:** `glassdome`

```python
import socket

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/run/glassdome/securityd.sock')
```

### HTTPS (mTLS)

**Default Port:** `8443`
**TLS Version:** TLS 1.3 (minimum TLS 1.2)
**Client Certificate:** Required

```python
import requests

response = requests.get(
    'https://securityd.local:8443/health',
    cert=('/path/to/client.crt', '/path/to/client.key'),
    verify='/path/to/ca.crt'
)
```

## Message Format

All messages are JSON objects with a newline delimiter for Unix socket communication.

### Request Format

```json
{
  "action": "string",
  "token": "string (optional, required after auth)",
  "params": {}
}
```

### Response Format

```json
{
  "status": "ok | error",
  "data": {},
  "error": {
    "code": "string",
    "message": "string"
  }
}
```

## Endpoints / Actions

### Authentication

#### `auth` (Unix Socket) / `POST /auth/validate` (HTTPS)

Authenticate a client and obtain a session token.

**Request (Unix Socket):**
```json
{
  "action": "auth",
  "params": {
    "pid": 12345,
    "exe": "/usr/bin/python3",
    "cmdline": "python scripts/test_platform_connections.py"
  }
}
```

**Request (HTTPS):**
```http
POST /auth/validate HTTP/1.1
Host: securityd.local:8443
Content-Type: application/json

{
  "client_id": "agent-01",
  "metadata": {
    "hostname": "agentX",
    "version": "0.1.0"
  }
}
```

**Response (Success):**
```json
{
  "status": "ok",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2024-11-25T18:55:26Z",
    "allowed_secrets": ["*"]
  }
}
```

**Response (Error):**
```json
{
  "status": "error",
  "error": {
    "code": "AUTH_DENIED",
    "message": "Process /usr/bin/malware not in allowed list"
  }
}
```

### Secret Retrieval

#### `get_secret` (Unix Socket) / `GET /secrets/{key}` (HTTPS)

Retrieve a single secret by key.

**Request (Unix Socket):**
```json
{
  "action": "get_secret",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "params": {
    "key": "proxmox_password"
  }
}
```

**Request (HTTPS):**
```http
GET /secrets/proxmox_password HTTP/1.1
Host: securityd.local:8443
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response (Success):**
```json
{
  "status": "ok",
  "data": {
    "key": "proxmox_password",
    "value": "secret123"
  }
}
```

**Response (Not Found):**
```json
{
  "status": "error",
  "error": {
    "code": "SECRET_NOT_FOUND",
    "message": "Secret 'nonexistent_key' not found"
  }
}
```

**Response (Access Denied):**
```json
{
  "status": "error",
  "error": {
    "code": "ACCESS_DENIED",
    "message": "Client not authorized to access 'admin_password'"
  }
}
```

### Secret Listing

#### `list_secrets` (Unix Socket) / `GET /secrets` (HTTPS)

List available secret keys (not values).

**Request (Unix Socket):**
```json
{
  "action": "list_secrets",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Request (HTTPS):**
```http
GET /secrets HTTP/1.1
Host: securityd.local:8443
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "secrets": [
      "proxmox_password",
      "proxmox_token_value",
      "esxi_password",
      "openai_api_key",
      "anthropic_api_key"
    ],
    "count": 5
  }
}
```

### Bulk Secret Retrieval

#### `get_secrets` (Unix Socket) / `POST /secrets/batch` (HTTPS)

Retrieve multiple secrets in one request.

**Request (Unix Socket):**
```json
{
  "action": "get_secrets",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "params": {
    "keys": ["proxmox_password", "proxmox_token_value", "openai_api_key"]
  }
}
```

**Request (HTTPS):**
```http
POST /secrets/batch HTTP/1.1
Host: securityd.local:8443
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "keys": ["proxmox_password", "proxmox_token_value", "openai_api_key"]
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "secrets": {
      "proxmox_password": "secret123",
      "proxmox_token_value": "44fa1891-0b3f-487a-b1ea-0800284f79d9",
      "openai_api_key": "sk-..."
    },
    "missing": []
  }
}
```

### Health Check

#### `health` (Unix Socket) / `GET /health` (HTTPS)

Check daemon status (no authentication required).

**Request (Unix Socket):**
```json
{
  "action": "health"
}
```

**Request (HTTPS):**
```http
GET /health HTTP/1.1
Host: securityd.local:8443
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "daemon": "running",
    "version": "0.1.0",
    "uptime_seconds": 3600,
    "secrets_loaded": 17,
    "active_sessions": 3,
    "last_access": "2024-11-25T10:55:26Z"
  }
}
```

### Session Management

#### `refresh` (Unix Socket) / `POST /auth/refresh` (HTTPS)

Refresh an expiring session token.

**Request:**
```json
{
  "action": "refresh",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...(new)",
    "expires_at": "2024-11-25T18:55:26Z"
  }
}
```

#### `logout` (Unix Socket) / `POST /auth/logout` (HTTPS)

Invalidate a session token.

**Request:**
```json
{
  "action": "logout",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "message": "Session invalidated"
  }
}
```

### Administration

#### `rotate_master` (Unix Socket) / `POST /admin/rotate` (HTTPS)

Rotate the master encryption key (admin only).

**Request:**
```json
{
  "action": "rotate_master",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "params": {
    "new_password": "new_master_password"
  }
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "message": "Master key rotated successfully",
    "rotated_at": "2024-11-25T10:55:26Z"
  }
}
```

#### `reload` (Unix Socket) / `POST /admin/reload` (HTTPS)

Reload secrets from disk without restarting daemon.

**Request:**
```json
{
  "action": "reload",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "status": "ok",
  "data": {
    "secrets_loaded": 17,
    "reloaded_at": "2024-11-25T10:55:26Z"
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTH_REQUIRED` | 401 | No token provided |
| `AUTH_EXPIRED` | 401 | Token has expired |
| `AUTH_INVALID` | 401 | Token is malformed or invalid |
| `AUTH_DENIED` | 403 | Client not authorized |
| `ACCESS_DENIED` | 403 | Not authorized for this secret |
| `SECRET_NOT_FOUND` | 404 | Secret key does not exist |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Daemon internal error |
| `DAEMON_LOCKED` | 503 | Daemon not yet initialized |

## Rate Limiting

To prevent abuse, the daemon implements rate limiting:

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/auth/validate` | 10 | 1 minute |
| `/secrets/*` | 100 | 1 minute |
| `/admin/*` | 5 | 1 minute |

Rate limit headers in HTTPS responses:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700920526
```

## Token Format

Session tokens are JWTs signed with the daemon's secret key:

```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "client-12345",
    "iat": 1700916926,
    "exp": 1700945726,
    "jti": "unique-session-id",
    "allowed": ["*"]
  }
}
```

## Example Client Implementation

### Python (Unix Socket)

```python
import socket
import json

class SecuritydClient:
    def __init__(self, socket_path='/run/glassdome/securityd.sock'):
        self.socket_path = socket_path
        self.token = None
    
    def _send(self, message: dict) -> dict:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.socket_path)
        
        # Send request
        sock.sendall(json.dumps(message).encode() + b'\n')
        
        # Receive response
        data = b''
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            if b'\n' in data:
                break
        
        sock.close()
        return json.loads(data.decode().strip())
    
    def authenticate(self) -> bool:
        import os
        response = self._send({
            'action': 'auth',
            'params': {
                'pid': os.getpid(),
                'exe': '/usr/bin/python3'
            }
        })
        if response['status'] == 'ok':
            self.token = response['data']['token']
            return True
        return False
    
    def get_secret(self, key: str) -> str:
        if not self.token:
            self.authenticate()
        
        response = self._send({
            'action': 'get_secret',
            'token': self.token,
            'params': {'key': key}
        })
        
        if response['status'] == 'ok':
            return response['data']['value']
        raise KeyError(response['error']['message'])
```

### Python (HTTPS)

```python
import requests

class SecuritydHTTPClient:
    def __init__(self, url='https://securityd.local:8443',
                 cert=('/path/to/client.crt', '/path/to/client.key'),
                 ca='/path/to/ca.crt'):
        self.url = url
        self.cert = cert
        self.ca = ca
        self.token = None
    
    def authenticate(self) -> bool:
        response = requests.post(
            f'{self.url}/auth/validate',
            json={'client_id': 'my-agent'},
            cert=self.cert,
            verify=self.ca
        )
        if response.status_code == 200:
            self.token = response.json()['data']['token']
            return True
        return False
    
    def get_secret(self, key: str) -> str:
        if not self.token:
            self.authenticate()
        
        response = requests.get(
            f'{self.url}/secrets/{key}',
            headers={'Authorization': f'Bearer {self.token}'},
            cert=self.cert,
            verify=self.ca
        )
        
        if response.status_code == 200:
            return response.json()['data']['value']
        raise KeyError(response.json()['error']['message'])
```

