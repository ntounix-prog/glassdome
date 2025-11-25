# Securityd Deployment Guide

## Prerequisites

- Python 3.10+
- Glassdome core installed
- Existing secrets in `~/.glassdome/secrets.encrypted`
- SSL certificates (for HTTPS mode)

## Installation Methods

### 1. Systemd Service (Bare Metal)

Recommended for dedicated hosts running Glassdome agents.

#### Create Service User

```bash
# Create dedicated user (no login shell)
sudo useradd -r -s /usr/sbin/nologin glassdome

# Create required directories
sudo mkdir -p /var/log/glassdome
sudo mkdir -p /run/glassdome
sudo mkdir -p /etc/glassdome/certs

# Set ownership
sudo chown glassdome:glassdome /var/log/glassdome
sudo chown glassdome:glassdome /run/glassdome
```

#### Install Configuration

```bash
# Copy configuration
sudo cp /home/nomad/glassdome/etc/securityd.conf.example /etc/glassdome/securityd.conf

# Edit configuration
sudo nano /etc/glassdome/securityd.conf
```

#### Create Systemd Unit

```ini
# /etc/systemd/system/glassdome-securityd.service

[Unit]
Description=Glassdome Security Daemon
Documentation=file:///home/nomad/glassdome/docs/securityd/README.md
After=network.target
Wants=network-online.target

[Service]
Type=notify
User=glassdome
Group=glassdome

# Security hardening
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
NoNewPrivileges=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictRealtime=true

# Allow binding to privileged port (if needed)
AmbientCapabilities=CAP_NET_BIND_SERVICE

# Working directory
WorkingDirectory=/home/nomad/glassdome
RuntimeDirectory=glassdome
RuntimeDirectoryMode=0755

# Environment
Environment=GLASSDOME_CONFIG=/etc/glassdome/securityd.conf
Environment=PYTHONUNBUFFERED=1

# Command
ExecStart=/home/nomad/glassdome/venv/bin/python -m glassdome.securityd.daemon
ExecReload=/bin/kill -HUP $MAINPID

# Restart policy
Restart=on-failure
RestartSec=5
StartLimitIntervalSec=60
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=glassdome-securityd

[Install]
WantedBy=multi-user.target
```

#### Enable and Start

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable glassdome-securityd

# Start service (will prompt for master password via systemd-ask-password)
sudo systemctl start glassdome-securityd

# Check status
sudo systemctl status glassdome-securityd

# View logs
sudo journalctl -u glassdome-securityd -f
```

#### Master Password Input

The daemon needs the master password at startup. Options:

**Option A: Interactive (systemd-ask-password)**
```bash
# Start will prompt on console/wall
sudo systemctl start glassdome-securityd
```

**Option B: Password file (less secure)**
```bash
# Create password file (600 permissions)
echo "your_master_password" | sudo tee /etc/glassdome/master.key
sudo chmod 600 /etc/glassdome/master.key
sudo chown glassdome:glassdome /etc/glassdome/master.key

# Update service to use file
# Add to [Service] section:
# Environment=GLASSDOME_MASTER_KEY_FILE=/etc/glassdome/master.key
```

**Option C: TPM/HSM (enterprise)**
```bash
# Store master key in TPM
# Requires tpm2-tools and configuration
# See: docs/securityd/TPM_INTEGRATION.md (future)
```

### 2. Docker Container

For containerized deployments or testing.

#### Dockerfile

```dockerfile
# Dockerfile.securityd

FROM python:3.12-slim

# Create non-root user
RUN useradd -r -s /usr/sbin/nologin glassdome

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY glassdome/ glassdome/
COPY etc/securityd.conf.example /etc/glassdome/securityd.conf

# Create directories
RUN mkdir -p /var/log/glassdome /run/glassdome && \
    chown -R glassdome:glassdome /var/log/glassdome /run/glassdome

# Switch to non-root user
USER glassdome

# Expose ports
EXPOSE 8443

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8443/health || exit 1

# Entry point
ENTRYPOINT ["python", "-m", "glassdome.securityd.daemon"]
```

#### Docker Compose

```yaml
# docker-compose.securityd.yml

version: '3.8'

services:
  securityd:
    build:
      context: .
      dockerfile: Dockerfile.securityd
    container_name: glassdome-securityd
    restart: unless-stopped
    
    # Mount secrets (encrypted file only)
    volumes:
      - ${HOME}/.glassdome/secrets.encrypted:/secrets/secrets.encrypted:ro
      - ${HOME}/.glassdome/master_key.enc:/secrets/master_key.enc:ro
      - ./certs:/etc/glassdome/certs:ro
      - securityd-logs:/var/log/glassdome
      - securityd-run:/run/glassdome
    
    # Environment
    environment:
      - GLASSDOME_SECRETS_FILE=/secrets/secrets.encrypted
      - GLASSDOME_MASTER_KEY_FILE=/secrets/master_key.enc
      - GLASSDOME_CONFIG=/etc/glassdome/securityd.conf
    
    # Network
    ports:
      - "8443:8443"
    networks:
      - glassdome
    
    # Security
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.1'
          memory: 64M

volumes:
  securityd-logs:
  securityd-run:

networks:
  glassdome:
    external: true
```

#### Run with Docker

```bash
# Build image
docker build -f Dockerfile.securityd -t glassdome-securityd .

# Run (interactive for master password)
docker run -it --rm \
  -v ~/.glassdome:/secrets:ro \
  -v ./certs:/etc/glassdome/certs:ro \
  -p 8443:8443 \
  glassdome-securityd

# Or with Docker Compose
docker-compose -f docker-compose.securityd.yml up -d
```

### 3. Docker Sidecar Pattern

For agents running in containers that need secret access.

```yaml
# docker-compose.agent-with-sidecar.yml

version: '3.8'

services:
  # Sidecar provides secrets to agent
  securityd-sidecar:
    image: glassdome-securityd
    container_name: agent-securityd
    volumes:
      - ${HOME}/.glassdome:/secrets:ro
      - ./certs:/etc/glassdome/certs:ro
      - sidecar-socket:/run/glassdome
    environment:
      - GLASSDOME_SOCKET_ONLY=true  # No HTTPS, Unix socket only
    networks:
      - agent-internal

  # Agent connects to sidecar via shared socket
  agent:
    image: glassdome-agent
    container_name: my-agent
    depends_on:
      - securityd-sidecar
    volumes:
      - sidecar-socket:/run/glassdome:ro
    environment:
      - GLASSDOME_SECURITYD_SOCKET=/run/glassdome/securityd.sock
    networks:
      - agent-internal
      - external

volumes:
  sidecar-socket:

networks:
  agent-internal:
    internal: true  # No external access
  external:
```

### 4. Kubernetes DaemonSet

For Kubernetes clusters running Glassdome agents.

```yaml
# k8s/securityd-daemonset.yaml

apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: glassdome-securityd
  namespace: glassdome
  labels:
    app: glassdome-securityd
spec:
  selector:
    matchLabels:
      app: glassdome-securityd
  template:
    metadata:
      labels:
        app: glassdome-securityd
    spec:
      serviceAccountName: glassdome-securityd
      
      # Run on every node
      tolerations:
        - operator: Exists
      
      containers:
        - name: securityd
          image: glassdome-securityd:latest
          
          ports:
            - containerPort: 8443
              hostPort: 8443
          
          volumeMounts:
            - name: secrets
              mountPath: /secrets
              readOnly: true
            - name: certs
              mountPath: /etc/glassdome/certs
              readOnly: true
            - name: socket
              mountPath: /run/glassdome
          
          env:
            - name: GLASSDOME_SECRETS_FILE
              value: /secrets/secrets.encrypted
            - name: GLASSDOME_MASTER_KEY
              valueFrom:
                secretKeyRef:
                  name: glassdome-master-key
                  key: password
          
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
            requests:
              cpu: 100m
              memory: 64Mi
          
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
          
          livenessProbe:
            httpGet:
              path: /health
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 10
            periodSeconds: 30
          
          readinessProbe:
            httpGet:
              path: /health
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 5
            periodSeconds: 10
      
      volumes:
        - name: secrets
          secret:
            secretName: glassdome-encrypted-secrets
        - name: certs
          secret:
            secretName: glassdome-tls
        - name: socket
          hostPath:
            path: /run/glassdome
            type: DirectoryOrCreate

---
apiVersion: v1
kind: Service
metadata:
  name: glassdome-securityd
  namespace: glassdome
spec:
  type: ClusterIP
  selector:
    app: glassdome-securityd
  ports:
    - port: 8443
      targetPort: 8443
```

## Configuration Reference

### Full Configuration File

```yaml
# /etc/glassdome/securityd.conf

# Daemon settings
daemon:
  # Process settings
  pid_file: /run/glassdome/securityd.pid
  user: glassdome
  group: glassdome
  
  # Unix socket (local access)
  socket:
    enabled: true
    path: /run/glassdome/securityd.sock
    permissions: 0660
    group: glassdome
  
  # HTTPS (remote access)
  https:
    enabled: true
    bind: 127.0.0.1  # Change to 0.0.0.0 for remote access
    port: 8443
    
    # TLS settings
    tls:
      cert: /etc/glassdome/certs/server.crt
      key: /etc/glassdome/certs/server.key
      ca: /etc/glassdome/certs/ca.crt
      require_client_cert: true
      min_version: TLSv1.2
      ciphers: ECDHE+AESGCM:DHE+AESGCM

# Secrets storage
secrets:
  # Encrypted secrets file
  encrypted_file: /home/nomad/.glassdome/secrets.encrypted
  
  # Master key (encrypted with password)
  master_key_file: /home/nomad/.glassdome/master_key.enc
  
  # Key derivation
  kdf:
    algorithm: pbkdf2
    iterations: 100000
    hash: sha256

# Authentication
auth:
  # Session settings
  session:
    timeout: 8h
    max_per_client: 10
    token_algorithm: HS256
  
  # Local process validation
  process_validation:
    enabled: true
    allowed_executables:
      - /usr/bin/python3
      - /home/nomad/glassdome/venv/bin/python
    allowed_users:
      - nomad
      - glassdome
  
  # Certificate validation (for HTTPS)
  certificate_validation:
    enabled: true
    allowed_cns:
      - agent-*
      - overseer-*

# Authorization
authorization:
  default_policy: deny
  rules:
    - name: agent-platform
      clients: ["agent-*"]
      secrets: ["proxmox_*", "esxi_*", "aws_*", "azure_*"]
      actions: [read]

# Audit logging
audit:
  enabled: true
  
  # File logging
  file:
    path: /var/log/glassdome/securityd-audit.log
    rotation: daily
    retention_days: 90
  
  # Syslog (optional)
  syslog:
    enabled: false
    server: localhost
    port: 514
    facility: auth

# Rate limiting
rate_limit:
  enabled: true
  auth_requests: 10/minute
  secret_requests: 100/minute
  admin_requests: 5/minute

# Monitoring
monitoring:
  # Prometheus metrics
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
  
  # Health check
  health:
    enabled: true
    path: /health
```

## SSL Certificate Setup

### Generate Self-Signed CA and Certificates

```bash
#!/bin/bash
# scripts/generate_securityd_certs.sh

CERT_DIR="/etc/glassdome/certs"
DAYS_VALID=365
CA_DAYS_VALID=3650

mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

# 1. Generate CA key and certificate
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days $CA_DAYS_VALID -key ca.key -out ca.crt \
    -subj "/CN=glassdome-ca/O=Glassdome/OU=Security"

# 2. Generate server key and CSR
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/CN=securityd.glassdome.local/O=Glassdome/OU=Security"

# 3. Create server certificate with SAN
cat > server.ext << EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names

[alt_names]
DNS.1 = securityd.glassdome.local
DNS.2 = securityd.local
DNS.3 = localhost
IP.1 = 127.0.0.1
IP.2 = 192.168.215.78
EOF

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days $DAYS_VALID -extfile server.ext

# 4. Generate client certificate (for agents)
openssl genrsa -out client-agent.key 2048
openssl req -new -key client-agent.key -out client-agent.csr \
    -subj "/CN=agent-01/O=Glassdome/OU=Agents"
openssl x509 -req -in client-agent.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out client-agent.crt -days 90

# 5. Set permissions
chmod 600 *.key
chmod 644 *.crt

# 6. Cleanup
rm -f *.csr *.ext *.srl

echo "Certificates generated in $CERT_DIR"
ls -la "$CERT_DIR"
```

## Monitoring and Alerting

### Prometheus Metrics

The daemon exposes metrics at `/metrics`:

```
# HELP securityd_requests_total Total number of requests
# TYPE securityd_requests_total counter
securityd_requests_total{action="auth",result="success"} 42
securityd_requests_total{action="get_secret",result="success"} 156
securityd_requests_total{action="get_secret",result="denied"} 3

# HELP securityd_active_sessions Number of active sessions
# TYPE securityd_active_sessions gauge
securityd_active_sessions 5

# HELP securityd_secrets_loaded Number of secrets loaded
# TYPE securityd_secrets_loaded gauge
securityd_secrets_loaded 17

# HELP securityd_uptime_seconds Daemon uptime in seconds
# TYPE securityd_uptime_seconds gauge
securityd_uptime_seconds 3600
```

### Alerting Rules (Prometheus)

```yaml
# prometheus/rules/securityd.yml

groups:
  - name: securityd
    rules:
      - alert: SecuritydDown
        expr: up{job="securityd"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Securityd daemon is down"
          
      - alert: SecuritydHighDeniedRate
        expr: rate(securityd_requests_total{result="denied"}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High rate of denied requests"
          
      - alert: SecuritydNoActiveSessions
        expr: securityd_active_sessions == 0
        for: 10m
        labels:
          severity: info
        annotations:
          summary: "No active sessions (might be normal)"
```

## Backup and Recovery

### Backup Script

```bash
#!/bin/bash
# scripts/backup_securityd.sh

BACKUP_DIR="/backup/glassdome"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/securityd_backup_$DATE.tar.gz"

mkdir -p "$BACKUP_DIR"

# Backup encrypted secrets and config (NOT master key!)
tar -czf "$BACKUP_FILE" \
    ~/.glassdome/secrets.encrypted \
    /etc/glassdome/securityd.conf \
    /etc/glassdome/certs/*.crt \
    /var/log/glassdome/securityd-audit.log

# Set permissions
chmod 600 "$BACKUP_FILE"

# Rotate old backups (keep last 30)
ls -t "$BACKUP_DIR"/securityd_backup_*.tar.gz | tail -n +31 | xargs -r rm

echo "Backup created: $BACKUP_FILE"
```

### Recovery Procedure

1. **Stop daemon:** `sudo systemctl stop glassdome-securityd`
2. **Restore files:** `tar -xzf securityd_backup_YYYYMMDD.tar.gz -C /`
3. **Verify permissions:** Ensure 600 on sensitive files
4. **Start daemon:** `sudo systemctl start glassdome-securityd`
5. **Enter master password** when prompted
6. **Verify:** `glassdome secrets daemon status`

### Disaster Recovery (Master Password Lost)

If the master password is lost, secrets cannot be recovered. You must:

1. Generate new master key: `glassdome secrets init --new`
2. Re-enter all secrets manually
3. Update all client certificates
4. Document new master password securely

**Prevention:** Store master password in a secure vault (e.g., 1Password, Bitwarden) with MFA.

