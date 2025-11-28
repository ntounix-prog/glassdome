# Glassdome Quick Start

Get up and running in 5 minutes.

---

## 🚀 First-Time Setup

### 1. Start the Backend

```bash
cd /home/nomad/glassdome
./glassdome_start
```

### 2. Start the Frontend (Dev Mode)

```bash
cd frontend
npm run dev
```

### 3. Create Your Admin Account

**Option A: Web UI**
1. Open `http://localhost:5173`
2. Click "Create first admin account"
3. Fill in email, username, password
4. You're in!

**Option B: CLI**
```bash
glassdome auth create-admin
# Follow prompts for username and password
```

---

## 👥 Creating Users

### Via Web UI (Recommended)

1. Login as Admin
2. Click **Admin** → **User Management**
3. Click **➕ Create User**
4. Fill in details, select role
5. Done!

### Via CLI

```bash
# List current users
glassdome auth list-users

# Create another admin
glassdome auth create-admin -u newadmin -e newadmin@example.com
```

---

## 🔐 Setting Up Secrets

Glassdome needs credentials to connect to platforms.

### Via Web UI

1. **Admin** → **Secrets**
2. Find the secret (e.g., `proxmox_password`)
3. Click **Set Value**
4. Enter the password
5. Save

### Via CLI

```bash
# Set Proxmox password
glassdome secrets set proxmox_password

# Set JWT secret (for authentication)
glassdome secrets set jwt_secret_key

# Import from .env file
glassdome secrets migrate
```

### Required Secrets

| Secret | When Needed |
|--------|-------------|
| `jwt_secret_key` | Always (auth) |
| `proxmox_password` | Proxmox labs |
| `aws_secret_access_key` | AWS labs |
| `azure_client_secret` | Azure labs |

---

## 🔑 Role Quick Reference

| Role | Level | Can Do |
|------|-------|--------|
| Observer | 25 | View only |
| Engineer | 50 | Deploy & operate |
| Architect | 75 | Design & create |
| Admin | 100 | Everything |

---

## 🆘 Locked Out?

### Reset Password
```bash
glassdome auth reset-password -u admin
```

### Emergency Admin
```bash
glassdome auth emergency-reset
# Prints temporary admin credentials
```

---

## 📍 URLs

| Service | URL |
|---------|-----|
| Frontend (dev) | http://localhost:5173 |
| API | http://localhost:8010 |
| API Docs | http://localhost:8010/docs |

---

## 📚 More Info

- [Admin Guide](ADMIN_GUIDE.md) - Full admin documentation
- [User Guide](USER_GUIDE.md) - User documentation by role
- [Architecture](COMMUNICATIONS_ARCHITECTURE.md) - System design

---

## Common Commands

```bash
# Start server
glassdome serve

# Check status  
glassdome status

# User management
glassdome auth list-users
glassdome auth reset-password -u <username>
glassdome auth create-admin

# Secrets
glassdome secrets list
glassdome secrets set <key>
glassdome secrets migrate

# Platform testing
glassdome test-platform proxmox
```
