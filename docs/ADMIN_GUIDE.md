# Glassdome Administrator Guide

This guide covers system administration tasks including user management, secrets configuration, and recovery procedures.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [User Management](#user-management)
3. [Secrets Management](#secrets-management)
4. [Role-Based Access Control](#role-based-access-control)
5. [Recovery Procedures](#recovery-procedures)
6. [CLI Reference](#cli-reference)

---

## Initial Setup

### First-Time Bootstrap

When Glassdome is first deployed, there are no users in the system. The **first user to register automatically becomes an Admin**.

#### Option 1: Web UI (Recommended)

1. Navigate to `http://your-server:5173` (dev) or your production URL
2. You'll see the login page
3. Click **"Create first admin account"** (only appears when no users exist)
4. Fill in:
   - Email address
   - Username (3+ characters)
   - Password (8+ characters, must include uppercase, lowercase, and number)
5. Submit - you're now logged in as Admin

#### Option 2: CLI

```bash
# Create admin via CLI
glassdome auth create-admin

# With options
glassdome auth create-admin -u myadmin -e admin@company.com
```

You'll be prompted for a password.

---

## User Management

### Accessing User Management

1. Login as Admin
2. Click **Admin** in the navigation bar
3. Select **User Management**

### Creating Users

#### Via Web UI

1. Go to Admin → User Management
2. Click **➕ Create User**
3. Fill in the form:
   - **Email**: Valid email address
   - **Username**: 3+ characters, unique
   - **Password**: 8+ characters
   - **Full Name**: Optional
   - **Role**: Select from Admin/Architect/Engineer/Observer
4. Click **Create User**

#### Via CLI

```bash
# Create user interactively (prompts for password)
glassdome auth create-admin -u newadmin -e newadmin@company.com

# For non-admin users, use the API or web UI
```

### Editing Users

1. In User Management, find the user
2. Click the ✏️ edit button
3. Modify:
   - Email
   - Username
   - Full Name
   - Role
   - Active status (checkbox)
4. Click **Save Changes**

### Deactivating Users

Glassdome uses **soft delete** - users are deactivated, not permanently removed.

1. Click the 🗑️ delete button next to the user
2. Confirm the action

Deactivated users:
- Cannot log in
- Retain their history/audit trail
- Can be reactivated by editing and checking "Active"

### Bulk Operations

Currently, bulk operations are handled via CLI:

```bash
# List all users
glassdome auth list-users
```

---

## Secrets Management

Secrets are sensitive values like API keys, passwords, and tokens that Glassdome needs to connect to various platforms.

### Storage Backends

Glassdome supports three secrets backends (in priority order):

1. **HashiCorp Vault** (Enterprise) - Centralized, audited, rotatable
2. **OS Keyring** - Uses macOS Keychain, Linux Secret Service, or Windows Credential Manager
3. **Encrypted File** - Fallback, AES-256 encrypted local file

### Accessing Secrets Management

1. Login as Admin
2. Click **Admin** → **Secrets**

### Common Secrets

| Key | Description | Used By |
|-----|-------------|---------|
| `jwt_secret_key` | Signs authentication tokens | Auth system |
| `proxmox_password` | Proxmox API access | Lab deployment |
| `esxi_password` | VMware ESXi access | Lab deployment |
| `aws_access_key_id` | AWS API access | Cloud labs |
| `aws_secret_access_key` | AWS API secret | Cloud labs |
| `azure_client_secret` | Azure service principal | Cloud labs |
| `guacamole_password` | Player portal access | Guacamole |
| `database_password` | PostgreSQL password | Database |
| `redis_password` | Redis password | Caching/Registry |

### Setting Secrets via UI

1. In Secrets Management, find the secret
2. Click **Set Value** (if unset) or ✏️ (to update)
3. Enter the secret value
4. Click **Save Secret**

⚠️ **Note**: Secret values are never displayed after saving - only whether they are set.

### Setting Secrets via CLI

```bash
# Set a secret (prompts for value)
glassdome secrets set jwt_secret_key

# Set with value directly (less secure - visible in shell history)
glassdome secrets set proxmox_password --value "mypassword"

# List all stored secrets
glassdome secrets list

# Delete a secret
glassdome secrets delete old_api_key

# Migrate from .env file
glassdome secrets migrate --env-file /path/to/.env
```

### Migrating from Environment Variables

If you have secrets in a `.env` file, migrate them to secure storage:

```bash
# From project root
glassdome secrets migrate

# Or specify path
glassdome secrets migrate --env-file /opt/glassdome/.env
```

This imports recognized secrets and stores them securely.

---

## Role-Based Access Control

### Role Hierarchy

| Role | Level | Description |
|------|-------|-------------|
| **Admin** | 100 | Full system access, user management |
| **Architect** | 75 | Design labs, create exploits, manage networks |
| **Engineer** | 50 | Deploy labs, run missions, operate VMs |
| **Observer** | 25 | Read-only access to dashboards |

### Permission Matrix

| Feature | Observer | Engineer | Architect | Admin |
|---------|----------|----------|-----------|-------|
| View Dashboard | ✅ | ✅ | ✅ | ✅ |
| View Deployments | ✅ | ✅ | ✅ | ✅ |
| View Platform Status | ✅ | ✅ | ✅ | ✅ |
| Lab Monitor | ✅ | ✅ | ✅ | ✅ |
| Deploy Labs | ❌ | ✅ | ✅ | ✅ |
| Design Labs | ❌ | ❌ | ✅ | ✅ |
| Reaper (Exploits) | ❌ | ❌ | ✅ | ✅ |
| WhiteKnight | ❌ | ❌ | ✅ | ✅ |
| User Management | ❌ | ❌ | ❌ | ✅ |
| Secrets Management | ❌ | ❌ | ❌ | ✅ |

### Assigning Roles

When creating or editing a user, select the appropriate role from the dropdown. The level is automatically set based on role.

### Custom Permissions

For fine-grained control, users can have `extra_permissions` added via the API:

```json
{
  "extra_permissions": ["deploy_labs", "view_exploits"]
}
```

This allows exceptions without changing the user's base role.

---

## Recovery Procedures

### Scenario 1: Forgot Admin Password

**If you have CLI access:**

```bash
# Reset password (prompts for new password)
glassdome auth reset-password -u admin
```

**If you have database access:**

```sql
-- Generate a bcrypt hash externally and update
UPDATE users SET hashed_password = '$2b$12$...' WHERE username = 'admin';
```

### Scenario 2: Admin Account Deactivated

**Via CLI:**

```bash
# Reactivate the account
glassdome auth reset-password -u admin
# This also reactivates the account
```

### Scenario 3: Completely Locked Out

**Emergency Reset (creates new admin account):**

```bash
glassdome auth emergency-reset
```

This outputs:
```
╔══════════════════════════════════════════════════════╗
║  EMERGENCY ADMIN CREDENTIALS                         ║
╠══════════════════════════════════════════════════════╣
║  Username: emergency_admin                           ║
║  Password: <random-secure-password>                  ║
╠══════════════════════════════════════════════════════╣
║  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY                 ║
║  ⚠️  DELETE THIS ACCOUNT AFTER RECOVERY               ║
╚══════════════════════════════════════════════════════╝
```

**After recovery:**
1. Login with emergency_admin
2. Reset your main admin password or create a new admin
3. Deactivate/delete the emergency_admin account

### Scenario 4: Database Connection Issues

1. Check PostgreSQL is running:
   ```bash
   systemctl status postgresql
   ```

2. Verify connection string in settings:
   ```bash
   cat /opt/glassdome/.env | grep DATABASE
   ```

3. Test connection:
   ```bash
   psql -U glassdome -h localhost -d glassdome
   ```

---

## CLI Reference

### Authentication Commands

```bash
# User management
glassdome auth create-admin         # Create/reset admin user
glassdome auth reset-password -u X  # Reset user password
glassdome auth list-users           # List all users
glassdome auth emergency-reset      # Emergency admin recovery

# Options for create-admin
  -u, --username    Username (default: admin)
  -e, --email       Email (default: admin@glassdome.local)
  -p, --password    Password (prompted if not provided)
  -f, --force       Overwrite existing user
```

### Secrets Commands

```bash
glassdome secrets set KEY           # Set a secret
glassdome secrets get KEY           # Get a secret (careful!)
glassdome secrets list              # List secret keys
glassdome secrets delete KEY        # Delete a secret
glassdome secrets migrate           # Import from .env file
```

### Other Commands

```bash
glassdome serve                     # Start the API server
glassdome status                    # Check system status
glassdome init                      # Initialize database
glassdome test-platform proxmox     # Test platform connection
```

---

## Monitoring & Audit

### User Activity

User actions are logged with:
- Timestamp
- User ID
- Action type
- Target resource
- IP address (where available)

View logs:
```bash
# Application logs
journalctl -u glassdome -f

# Or if running manually
tail -f /var/log/glassdome/app.log
```

### Security Best Practices

1. **Change default passwords** immediately after setup
2. **Use strong passwords** (12+ characters recommended)
3. **Regularly review user list** and deactivate unused accounts
4. **Rotate secrets** periodically, especially after personnel changes
5. **Use HashiCorp Vault** in production for centralized secret management
6. **Enable HTTPS** in production (configure reverse proxy)

---

## Troubleshooting

### "User already exists"

The username or email is taken. Use a different one or use `--force` with CLI to overwrite.

### "Incorrect username or password"

- Check caps lock
- Verify username (not email) if using CLI
- Try password reset

### "Not authorized"

Your role level doesn't have permission for this action. Contact an Admin to upgrade your role.

### "Secret not found"

The secret hasn't been set. Use the Secrets page or CLI to set it:
```bash
glassdome secrets set <key>
```

### API returns 401 Unauthorized

Your JWT token has expired. Logout and login again to get a fresh token.

---

## Support

For issues not covered here:
1. Check the [User Guide](USER_GUIDE.md)
2. Review application logs
3. Open an issue on the project repository

