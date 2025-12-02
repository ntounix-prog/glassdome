# ELK Stack Deployment for Glassdome

This directory contains the complete ELK (Elasticsearch, Logstash, Kibana) stack configuration for centralized logging of all Glassdome components.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Glassdome Application                              │
│  ┌─────────┐ ┌────────────┐ ┌─────────┐ ┌─────────────┐ ┌──────────────┐   │
│  │ Backend │ │Orchestrator│ │ Reapers │ │ WhiteKnights│ │  WhitePawns  │   │
│  └────┬────┘ └─────┬──────┘ └────┬────┘ └──────┬──────┘ └──────┬───────┘   │
│       │            │             │             │               │            │
│       └────────────┴─────────────┴─────────────┴───────────────┘            │
│                                  │                                          │
│                     ┌────────────┴────────────┐                             │
│                     │     Log Shipping        │                             │
│                     │ (TCP or Filebeat)       │                             │
│                     └────────────┬────────────┘                             │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    ELK Stack (192.168.3.26)                                  │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                         Logstash (:5044/:5045/:5046)                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │
│  │  │ Beats Input │  │  TCP Input  │  │ HTTP Input  │  │Syslog Input │   │   │
│  │  │   :5044     │  │   :5045     │  │   :5046     │  │   :5514     │   │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │   │
│  │         └────────────────┴────────────────┴────────────────┘          │   │
│  │                                  │                                    │   │
│  │                          ┌───────▼───────┐                            │   │
│  │                          │   Pipeline    │                            │   │
│  │                          │   Processing  │                            │   │
│  │                          └───────┬───────┘                            │   │
│  └──────────────────────────────────┼────────────────────────────────────┘   │
│                                     │                                        │
│  ┌──────────────────────────────────▼────────────────────────────────────┐   │
│  │                    Elasticsearch (:9200)                              │   │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │   │
│  │  │ glassdome-*    │  │infrastructure-*│  │   .kibana      │           │   │
│  │  │   (30 days)    │  │   (14 days)    │  │                │           │   │
│  │  └────────────────┘  └────────────────┘  └────────────────┘           │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                     │                                        │
│  ┌──────────────────────────────────▼────────────────────────────────────┐   │
│  │                      Kibana (:5601)                                   │   │
│  │  ┌─────────┐  ┌────────────────┐  ┌─────────────┐  ┌───────────────┐  │   │
│  │  │Discover │  │   Dashboards   │  │ Visualize   │  │   Alerts      │  │   │
│  │  └─────────┘  └────────────────┘  └─────────────┘  └───────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Deploy ELK Stack on 192.168.3.26

```bash
# SSH to ELK server
ssh 192.168.3.26

# Create directory
sudo mkdir -p /opt/elk
cd /opt/elk

# Copy files (from Glassdome server)
# Or clone/copy the deploy/elk directory

# Set proper permissions
sudo chown -R 1000:1000 /opt/elk

# Start the stack
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check Elasticsearch health
curl http://localhost:9200/_cluster/health?pretty

# Access Kibana
# Open browser: http://192.168.3.26:5601
```

### 2. Configure Glassdome for ELK Logging

Add to your `.env` file:

```bash
# ELK Stack Configuration
LOGSTASH_ENABLED=true
LOGSTASH_HOST=192.168.3.26
LOGSTASH_PORT=5045
LOG_LEVEL=INFO
LOG_JSON_ENABLED=true
```

### 3. Restart Glassdome Services

```bash
cd /path/to/glassdome
docker-compose down
docker-compose up -d
```

## Components

### Elasticsearch (Port 9200)
- Single-node cluster for lab environment
- Stores all indexed logs
- 2GB heap size (adjustable)
- Indices:
  - `glassdome-*`: Application logs (30-day retention)
  - `infrastructure-*`: System/syslog (14-day retention)

### Logstash (Ports 5044, 5045, 5046, 5514)
- **5044**: Beats input (Filebeat)
- **5045**: TCP/JSON input (Python direct shipping)
- **5046**: HTTP input (webhooks)
- **5514**: Syslog input (infrastructure)

### Kibana (Port 5601)
- Web UI for log visualization
- Dashboards and alerts
- Index pattern: `glassdome-*`

### Curator (Background)
- Automated index lifecycle management
- Closes indices after 7 days
- Deletes indices after 30 days
- Force merges for storage optimization

## Log Shipping Options

### Option 1: Direct TCP (Recommended for Containers)

The Python logging module ships logs directly to Logstash via TCP:

```python
# Automatically enabled when LOGSTASH_ENABLED=true
from glassdome.core.logging import get_logger
logger = get_logger(__name__)
logger.info("This goes directly to ELK")
```

### Option 2: Filebeat (For File-Based Logs)

Filebeat reads JSON log files and ships to Logstash:

```bash
# Install Filebeat on Glassdome server
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.11.3-amd64.deb
sudo dpkg -i filebeat-8.11.3-amd64.deb

# Configure
sudo cp deploy/filebeat.yml /etc/filebeat/filebeat.yml

# Start
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

### Option 3: Docker Sidecar

The docker-compose.yml includes a Filebeat sidecar that ships container logs automatically.

## Log Format

All Glassdome logs follow this JSON structure:

```json
{
  "@timestamp": "2025-12-01T15:30:45.123456Z",
  "level": "INFO",
  "logger": "api.labs",
  "message": "Lab deployed successfully",
  "module": "labs",
  "function": "deploy_lab",
  "line": 142,
  "application": "glassdome",
  "host": "glassdome-backend",
  "worker_id": "orchestrator",
  "glassdome_mode": "backend",
  "request_id": "req-abc123",
  "user": "admin",
  "lab_id": "lab-xyz789"
}
```

## Kibana Setup

### Create Index Pattern

1. Go to **Stack Management** → **Index Patterns**
2. Create pattern: `glassdome-*`
3. Set time field: `@timestamp`

### Useful Queries

```
# All errors
level: ERROR

# Specific worker
worker_id: "reaper-1"

# Lab deployment events
category: "deployment"

# Exceptions
has_exception: true

# Specific request trace
request_id: "req-abc123"

# Last hour of backend logs
glassdome_mode: "backend" AND @timestamp >= now-1h
```

### Suggested Dashboards

1. **Operations Overview**
   - Log volume by level
   - Errors per hour
   - Active workers
   - Request latency

2. **Lab Deployments**
   - Deployment success rate
   - Average deployment time
   - Failed deployments

3. **Security Events**
   - Vulnerability injections (Reaper)
   - Validation results (WhiteKnight)
   - Authentication events

## Troubleshooting

### Check Logstash is Receiving Logs

```bash
# On ELK server
docker logs -f elk-logstash

# Check pipeline stats
curl http://192.168.3.26:9600/_node/stats/pipelines?pretty
```

### Check Elasticsearch Index

```bash
# List indices
curl http://192.168.3.26:9200/_cat/indices?v

# Check glassdome index
curl "http://192.168.3.26:9200/glassdome-*/_count"
```

### Test Direct TCP Connection

```bash
# From Glassdome server
echo '{"test": "message"}' | nc 192.168.3.26 5045
```

### Check Filebeat

```bash
# Filebeat status
sudo systemctl status filebeat

# Filebeat logs
sudo journalctl -u filebeat -f

# Test config
sudo filebeat test config
sudo filebeat test output
```

## Resource Requirements

| Component     | CPU  | Memory | Disk   |
|---------------|------|--------|--------|
| Elasticsearch | 2    | 4GB    | 50GB+  |
| Logstash      | 1    | 1GB    | 5GB    |
| Kibana        | 1    | 1GB    | 1GB    |
| **Total**     | 4    | 6GB    | 56GB+  |

## Security Notes

⚠️ **Lab Environment Configuration**

This configuration has security disabled for ease of use in a lab environment:

- No authentication on Elasticsearch
- No TLS/SSL encryption
- Open network access

For production, enable:
- X-Pack Security
- TLS certificates
- Role-based access control
- Network firewalls

## Files

```
deploy/elk/
├── docker-compose.yml          # Main ELK stack
├── README.md                   # This file
├── logstash/
│   ├── config/
│   │   └── logstash.yml        # Logstash settings
│   └── pipeline/
│       └── glassdome.conf      # Log processing pipeline
└── curator/
    ├── config.yml              # Curator settings
    └── actions.yml             # Lifecycle actions
```

## Support

- ELK Stack: https://www.elastic.co/guide/
- Filebeat: https://www.elastic.co/guide/en/beats/filebeat/
- Logstash: https://www.elastic.co/guide/en/logstash/

---

Author: Brett Turner (ntounix)
Created: December 2025

