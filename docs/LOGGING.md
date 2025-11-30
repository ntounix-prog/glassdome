# Glassdome Logging System

Centralized logging with JSON output for SIEM integration.

**Version**: 0.7.3  
**Last Updated**: 2025-11-30

---

## Quick Start

```bash
# Check logging status
glassdome logs status

# View recent logs
glassdome logs tail

# Follow logs in real-time
glassdome logs tail -f

# Change log level
glassdome logs level DEBUG
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR |
| `LOG_DIR` | `logs` | Directory for log files |
| `LOG_MAX_SIZE_MB` | `10` | Max file size before rotation |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated files to keep |
| `LOG_JSON_ENABLED` | `true` | Enable JSON output for SIEM |
| `LOG_CONSOLE_ENABLED` | `true` | Enable console output |
| `LOG_FILE_ENABLED` | `true` | Enable file output |

### Example .env

```bash
# Quiet mode for production
LOG_LEVEL=WARNING
LOG_JSON_ENABLED=true
LOG_CONSOLE_ENABLED=false

# Verbose mode for development
LOG_LEVEL=DEBUG
LOG_CONSOLE_ENABLED=true
```

---

## Log Files

```
logs/
├── glassdome.log          # Human-readable (INFO+)
├── glassdome.json         # JSON for SIEM (INFO+)
├── glassdome-debug.log    # Debug logs (when LOG_LEVEL=DEBUG)
├── glassdome.log.1        # Rotated backup
├── glassdome.log.2        # Older backup
└── ...
```

### Rotation

Files rotate when they reach `LOG_MAX_SIZE_MB` (default 10MB).  
Rotated files are named `*.log.1`, `*.log.2`, etc.  
Files older than `LOG_BACKUP_COUNT` are automatically deleted.

---

## JSON Format (SIEM-Ready)

The `glassdome.json` file produces structured logs for ingestion by:
- **Filebeat** → Elasticsearch
- **Logstash**
- **Fluentd**
- **Splunk**
- **Any SIEM**

### Example Entry

```json
{
  "timestamp": "2025-11-30T15:30:45.123Z",
  "level": "INFO",
  "logger": "glassdome.api.labs",
  "message": "Lab deployed successfully",
  "module": "labs",
  "function": "create_lab",
  "line": 142,
  "request_id": "req-xyz789",
  "user": "admin",
  "lab_id": "lab-abc123"
}
```

### Fields

| Field | Description |
|-------|-------------|
| `timestamp` | ISO 8601 UTC timestamp |
| `level` | DEBUG, INFO, WARNING, ERROR |
| `logger` | Module path (e.g., `glassdome.api.labs`) |
| `message` | Log message |
| `module` | Python module name |
| `function` | Function name |
| `line` | Line number |
| `request_id` | Request correlation ID (if set) |
| `user` | Authenticated user (if set) |
| `exception` | Stack trace (if error) |

---

## SIEM Integration

### Filebeat Setup

1. Install Filebeat:
```bash
curl -L -O https://artifacts.elastic.co/downloads/beats/filebeat/filebeat-8.x-amd64.deb
sudo dpkg -i filebeat-8.x-amd64.deb
```

2. Copy the config:
```bash
sudo cp deploy/filebeat.yml /etc/filebeat/filebeat.yml
```

3. Edit Elasticsearch host:
```yaml
output.elasticsearch:
  hosts: ["your-elk-server:9200"]
```

4. Start Filebeat:
```bash
sudo systemctl enable filebeat
sudo systemctl start filebeat
```

### Kibana Dashboard

Once logs are flowing to Elasticsearch:

1. Open Kibana
2. Go to **Management** → **Index Patterns**
3. Create pattern: `glassdome-*`
4. Use **Discover** to search logs
5. Create dashboards for:
   - Error rate over time
   - Top modules by log volume
   - Authentication events
   - API response times

---

## Log Levels

| Level | Use Case | Example |
|-------|----------|---------|
| `ERROR` | Production (minimal) | Only errors and critical issues |
| `WARNING` | Production (normal) | Warnings + errors |
| `INFO` | Development (default) | Operations, API calls, deployments |
| `DEBUG` | Troubleshooting | Everything including internal state |

### Changing Level at Runtime

```bash
# Set to DEBUG for troubleshooting
glassdome logs level DEBUG

# Return to normal
glassdome logs level INFO

# Quiet mode
glassdome logs level WARNING
```

**Note**: Changes require server restart to take effect.

---

## CLI Commands

### `glassdome logs tail`

Tail log files.

```bash
glassdome logs tail                # Last 50 lines
glassdome logs tail -n 100         # Last 100 lines
glassdome logs tail -f             # Follow (like tail -f)
glassdome logs tail --json         # Tail JSON log
```

### `glassdome logs level`

Show or change log level.

```bash
glassdome logs level               # Show current
glassdome logs level DEBUG         # Set to DEBUG
glassdome logs level WARNING       # Set to WARNING
```

### `glassdome logs clear`

Clear old log files.

```bash
glassdome logs clear               # Clear > 7 days old
glassdome logs clear --older 1d    # Clear > 1 day old
glassdome logs clear --all         # Clear all logs
```

### `glassdome logs status`

Show logging configuration and file sizes.

```bash
glassdome logs status
```

Output:
```
═══════════════════════════════════════════
  Logging Status
═══════════════════════════════════════════
Level:     INFO
Directory: /home/nomad/glassdome/logs
Max Size:  10 MB
Backups:   5 files
JSON:      ✓ Enabled

File                           Size         Modified
─────────────────────────────────────────────────────────────────
glassdome.json                 2.3 MB       2025-11-30 15:30
glassdome.log                  1.8 MB       2025-11-30 15:30

Total: 4.1 MB
```

---

## Adding Context to Logs

### Request Context

Add request-scoped data to all log entries:

```python
from glassdome.core.logging import set_log_context, clear_log_context

# In middleware or request handler
set_log_context(request_id="req-123", user="admin")

# All logs in this request will include request_id and user
logger.info("Processing request")  # {"request_id": "req-123", "user": "admin", ...}

# Clear at end of request
clear_log_context()
```

### Extra Fields

Add extra fields to individual log entries:

```python
logger.info("Lab deployed", extra={"lab_id": "lab-123", "duration_ms": 1500})
```

---

## Best Practices

### DO

- Use appropriate log levels
- Include context (IDs, usernames)
- Log at operation boundaries (start/end of deployments)
- Use structured fields for searchability

### DON'T

- Log sensitive data (passwords, tokens)
- Use DEBUG in production
- Log in tight loops (performance impact)
- Include PII without consent

---

## Troubleshooting

### Logs not appearing

1. Check log directory exists: `ls -la logs/`
2. Check permissions: `touch logs/test.log`
3. Verify settings: `glassdome logs status`

### JSON logs not being collected

1. Verify Filebeat is running: `systemctl status filebeat`
2. Check Filebeat logs: `tail -f /var/log/filebeat/filebeat`
3. Test Elasticsearch connection: `curl localhost:9200`

### High disk usage

```bash
# Check log sizes
glassdome logs status

# Clear old logs
glassdome logs clear --older 3d

# Reduce max size in .env
LOG_MAX_SIZE_MB=5
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Glassdome Application                    │
├─────────────────────────────────────────────────────────────┤
│  logger = logging.getLogger(__name__)                       │
│  logger.info("...")                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              glassdome/core/logging.py                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Console      │  │ Text File    │  │ JSON File    │      │
│  │ Handler      │  │ Handler      │  │ Handler      │      │
│  │ (colored)    │  │ (rotating)   │  │ (rotating)   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
      stdout          glassdome.log     glassdome.json
                                              │
                                              ▼
                                    ┌─────────────────┐
                                    │    Filebeat     │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │  Elasticsearch  │
                                    │    / Kibana     │
                                    └─────────────────┘
```

---

## See Also

- [CLI Reference](CLI_REFERENCE.md) - Full CLI documentation
- [Quick Start](QUICKSTART.md) - Getting started guide
- [Filebeat Config](../deploy/filebeat.yml) - Sample Filebeat configuration
