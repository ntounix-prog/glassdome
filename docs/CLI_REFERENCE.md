# Glassdome CLI Reference

Complete command reference for the `glassdome` command-line interface.

**Version**: 0.7.2  
**Last Updated**: 2025-11-30

---

## Quick Reference

```bash
glassdome --help              # Show all commands
glassdome --version           # Show version
glassdome <command> --help    # Show help for specific command
```

---

## Core Commands

### `glassdome serve`

Start the Glassdome API server.

```bash
glassdome serve [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind to |
| `--port` | `8010` | Port to bind to |
| `--reload` | `false` | Enable auto-reload for development |

**Examples:**
```bash
glassdome serve                        # Start on default port
glassdome serve --port 8080            # Custom port
glassdome serve --host 127.0.0.1       # Localhost only
glassdome serve --reload               # Dev mode with auto-reload
```

---

### `glassdome init`

Initialize Glassdome (database, admin user, platform checks).

```bash
glassdome init [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--skip-admin` | Skip admin user creation |

**What it does:**
1. Creates database tables
2. Creates default admin user (unless `--skip-admin`)
3. Tests platform connections (Proxmox, etc.)

**Examples:**
```bash
glassdome init                # Full initialization
glassdome init --skip-admin   # Just database setup
```

**Output:**
```
Initializing Glassdome...
Database: postgresql+asyncpg://...

📦 Initializing database...
   ✓ Database tables created

👤 Checking admin user...
   ✓ Admin user created: admin
     Default password: changeme123!

🔌 Testing platform connections...
   ✓ Proxmox connected

✅ Glassdome initialized successfully
```

---

### `glassdome status`

Check full system status.

```bash
glassdome status
```

**Output:**
```
═══════════════════════════════════════════
  Glassdome v0.7.2
═══════════════════════════════════════════
Environment: development

📊 Agent Manager:
   Agents: 3
   Queue: 0
   Running: true

🔌 Platforms:
   Proxmox: ✓ Connected
   ESXi: ✓ Connected
   AWS: ✓ Configured
   Azure: ✓ Configured

🚀 Active Deployments:
   Labs: 5
   Deployed VMs: 12
```

---

### `glassdome test-platform`

Test connectivity to a specific platform.

```bash
glassdome test-platform --platform <name>
```

| Platform | Description |
|----------|-------------|
| `proxmox` | Test Proxmox VE connection |
| `azure` | Test Azure connection |
| `aws` | Test AWS connection |

**Examples:**
```bash
glassdome test-platform --platform proxmox
glassdome test-platform --platform aws
glassdome test-platform --platform azure
```

---

## Lab Commands

### `glassdome lab list`

List all labs in the database.

```bash
glassdome lab list [OPTIONS]
```

| Option | Values | Description |
|--------|--------|-------------|
| `--format` | `table`, `json` | Output format (default: table) |

**Examples:**
```bash
glassdome lab list                    # Table format
glassdome lab list --format json      # JSON output (for scripting)
```

**Table Output:**
```
ID                                       Name                           Status       VMs
──────────────────────────────────────────────────────────────────────────────────────────
lab-abc12345                             Web Security Training          deployed     4
lab-def67890                             Network Pentest                draft        0

Total: 2 labs
```

**JSON Output:**
```json
[
  {"id": "lab-abc12345", "name": "Web Security Training", "status": "deployed"},
  {"id": "lab-def67890", "name": "Network Pentest", "status": "draft"}
]
```

---

### `glassdome lab create`

Create a new lab.

```bash
glassdome lab create --name <name> [OPTIONS]
```

| Option | Required | Description |
|--------|----------|-------------|
| `--name` | Yes | Lab name |
| `--description` | No | Lab description |
| `--template` | No | Template ID to use |

**Examples:**
```bash
glassdome lab create --name "My Lab"
glassdome lab create --name "Red Team Lab" --description "For offensive exercises"
glassdome lab create --name "Quick Lab" --template default-web-security
```

---

### `glassdome lab show`

Show details of a specific lab.

```bash
glassdome lab show <lab_id>
```

**Example:**
```bash
glassdome lab show lab-abc12345
```

**Output:**
```
══════════════════════════════════════════════════
Lab: Web Security Training
══════════════════════════════════════════════════
ID:          lab-abc12345
Status:      deployed
Description: OWASP Top 10 training environment
Created:     2025-11-30 10:00:00

Elements (4):
  - DVWA: vm
  - Kali: vm
  - Attacker: vm
  - lab-network: network
```

---

### `glassdome lab delete`

Delete a lab.

```bash
glassdome lab delete <lab_id>
```

**Example:**
```bash
glassdome lab delete lab-abc12345
# Prompts: Are you sure you want to delete this lab? [y/N]
```

---

## Deployment Commands

### `glassdome deploy list`

List all deployed VMs.

```bash
glassdome deploy list [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--format` | Output format: `table` or `json` |
| `--lab-id` | Filter by lab ID |

**Examples:**
```bash
glassdome deploy list                        # All deployments
glassdome deploy list --lab-id lab-abc123    # Filter by lab
glassdome deploy list --format json          # JSON output
```

**Output:**
```
ID     Lab ID          Name                 Platform   Status       IP
─────────────────────────────────────────────────────────────────────────────
1      lab-abc123      dvwa-server          proxmox    running      10.10.10.5
2      lab-abc123      kali-attacker        proxmox    running      10.10.10.10
3      lab-abc123      target-windows       proxmox    stopped      

Total: 3 deployed VMs
```

---

### `glassdome deploy create`

Deploy a lab to a platform.

```bash
glassdome deploy create --lab-id <lab_id> [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--lab-id` | Required | Lab ID to deploy |
| `--platform` | `proxmox` | Target: `proxmox`, `esxi`, `azure`, `aws` |
| `--instance` | `01` | Platform instance ID |

**Examples:**
```bash
glassdome deploy create --lab-id lab-abc123
glassdome deploy create --lab-id lab-abc123 --platform azure
glassdome deploy create --lab-id lab-abc123 --platform proxmox --instance 02
```

---

### `glassdome deploy status`

Check deployment status for a lab.

```bash
glassdome deploy status <lab_id>
```

**Example:**
```bash
glassdome deploy status lab-abc123
```

**Output:**
```
════════════════════════════════════════════════════════════
Deployment Status: Web Security Training
════════════════════════════════════════════════════════════
Lab ID: lab-abc123
Status: deploying
Deployed VMs: 3

Name                      Status       IP              Platform
─────────────────────────────────────────────────────────────────
dvwa-server               running      10.10.10.5      proxmox
kali-attacker             running      10.10.10.10     proxmox
target-windows            starting     pending         proxmox

Progress: 2/3 VMs (67%)
```

---

### `glassdome deploy destroy`

Destroy a deployment.

```bash
glassdome deploy destroy <deployment_id> [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `--force` | Skip confirmation prompt |

**Examples:**
```bash
glassdome deploy destroy lab-abc123           # Destroy by lab ID
glassdome deploy destroy 5                    # Destroy by VM ID
glassdome deploy destroy lab-abc123 --force   # No confirmation
```

**What it does:**
1. Stops VMs on the platform
2. Deletes VMs from the platform
3. Removes deployment records from database

---

## Authentication Commands

### `glassdome auth create-admin`

Create or reset the admin user.

```bash
glassdome auth create-admin [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-e`, `--email` | `admin@glassdome.local` | Admin email |
| `-u`, `--username` | `admin` | Admin username |
| `-p`, `--password` | (prompted) | Admin password |
| `-f`, `--force` | false | Overwrite existing admin |

**Examples:**
```bash
glassdome auth create-admin                              # Interactive
glassdome auth create-admin -u superadmin                # Custom username
glassdome auth create-admin --force                      # Reset existing
glassdome auth create-admin -p MySecurePass123!          # Non-interactive
```

---

### `glassdome auth reset-password`

Reset a user's password.

```bash
glassdome auth reset-password -u <username> [-p <password>]
```

**Examples:**
```bash
glassdome auth reset-password -u admin              # Prompts for password
glassdome auth reset-password -u john -p NewPass1!  # Non-interactive
```

---

### `glassdome auth list-users`

List all users.

```bash
glassdome auth list-users
```

**Output:**
```
ID    Username             Email                          Role         Level  Active
─────────────────────────────────────────────────────────────────────────────────────
1     admin                admin@glassdome.local          admin        100    ✓
2     john                 john@example.com               engineer     50     ✓
3     jane                 jane@example.com               architect    75     ✓

Total: 3 users
```

---

### `glassdome auth emergency-reset`

Emergency admin recovery (creates temporary account).

```bash
glassdome auth emergency-reset
```

**Output:**
```
🔓 Emergency admin account created!

╔══════════════════════════════════════════════════════╗
║  EMERGENCY ADMIN CREDENTIALS                         ║
╠══════════════════════════════════════════════════════╣
║  Username: emergency_admin                           ║
║  Password: aB3dEf9GhI2jKlMn                          ║
╠══════════════════════════════════════════════════════╣
║  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY                 ║
║  ⚠️  DELETE THIS ACCOUNT AFTER RECOVERY               ║
╚══════════════════════════════════════════════════════╝
```

---

## Secrets Commands

### `glassdome secrets list`

List all stored secret keys.

```bash
glassdome secrets list
```

---

### `glassdome secrets set`

Set a secret value.

```bash
glassdome secrets set <key> [--value <value>]
```

**Examples:**
```bash
glassdome secrets set proxmox_password           # Prompts for value
glassdome secrets set jwt_secret --value abc123  # Non-interactive
```

---

### `glassdome secrets get`

Retrieve a secret value (use with caution).

```bash
glassdome secrets get <key>
```

---

### `glassdome secrets delete`

Delete a secret.

```bash
glassdome secrets delete <key>
```

---

### `glassdome secrets migrate`

Migrate secrets from `.env` file to secure store.

```bash
glassdome secrets migrate [--env-file <path>]
```

**Example:**
```bash
glassdome secrets migrate                    # From .env
glassdome secrets migrate --env-file .env.prod
```

---

## Agent Commands

### `glassdome agent list`

List all registered agents.

```bash
glassdome agent list
```

**Output:**
```
Total Agents: 3
Queue Size: 0
Running: true

Agents:
  proxmox-agent: platform - active
  reaper-agent: security - active
  whitepawn-agent: monitor - active
```

---

### `glassdome agent start`

Start the agent manager.

```bash
glassdome agent start
```

---

## Scripting & Automation

### JSON Output

Use `--format json` for machine-readable output:

```bash
# Get labs as JSON
glassdome lab list --format json | jq '.[].name'

# Check deployment status
glassdome deploy list --format json | jq '.[] | select(.status=="running")'
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |

### Batch Operations

```bash
# Deploy all draft labs
for lab in $(glassdome lab list --format json | jq -r '.[] | select(.status=="draft") | .id'); do
  glassdome deploy create --lab-id "$lab"
done

# Destroy all labs for a project
glassdome deploy list --format json | jq -r '.[].lab_id' | sort -u | while read lab; do
  glassdome deploy destroy "$lab" --force
done
```

---

## Log Commands

### `glassdome logs tail`

Tail log files.

```bash
glassdome logs tail [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-n`, `--lines` | Number of lines (default: 50) |
| `-f`, `--follow` | Follow output (like tail -f) |
| `--json` | Tail JSON log instead of text |

**Examples:**
```bash
glassdome logs tail                # Last 50 lines
glassdome logs tail -n 100         # Last 100 lines
glassdome logs tail -f             # Follow in real-time
glassdome logs tail --json         # Tail SIEM-formatted JSON log
```

---

### `glassdome logs level`

Show or change log level.

```bash
glassdome logs level [LEVEL]
```

| Level | Description |
|-------|-------------|
| `DEBUG` | Everything (verbose) |
| `INFO` | Normal operations (default) |
| `WARNING` | Warnings and errors only |
| `ERROR` | Errors only (quiet) |

**Examples:**
```bash
glassdome logs level               # Show current level
glassdome logs level DEBUG         # Set to DEBUG (requires restart)
glassdome logs level WARNING       # Set to WARNING (quiet mode)
```

---

### `glassdome logs clear`

Clear old log files.

```bash
glassdome logs clear [OPTIONS]
```

| Option | Description |
|--------|-------------|
| `-o`, `--older` | Clear logs older than (e.g., 7d, 24h) |
| `--all` | Clear all logs |

**Examples:**
```bash
glassdome logs clear               # Clear > 7 days old
glassdome logs clear --older 1d    # Clear > 1 day old
glassdome logs clear --all         # Clear everything
```

---

### `glassdome logs status`

Show logging configuration and file sizes.

```bash
glassdome logs status
```

**Output:**
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

## Environment Variables

The CLI respects these environment variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Database connection string |
| `REDIS_URL` | Redis connection string |
| `VAULT_ADDR` | HashiCorp Vault address |
| `SECRETS_BACKEND` | `vault` or `encrypted_file` |

---

## See Also

- [Quick Start Guide](QUICKSTART.md)
- [Admin Guide](ADMIN_GUIDE.md)
- [User Guide](USER_GUIDE.md)
- [API Documentation](http://localhost:8010/docs)
