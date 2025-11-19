# How to Get Proxmox API Credentials

## You Need These To Connect Glassdome to Proxmox!

Glassdome can't magically connect to your Proxmox server - you need to give it credentials. Here's how to get them:

---

## Option 1: API Token (Recommended) 🔐

API tokens are more secure than passwords because:
- They can be revoked without changing your password
- They can have limited permissions
- They don't expose your actual password

### Step-by-Step: Create API Token

1. **Open Proxmox Web Interface**
   ```
   https://your-proxmox-ip:8006
   ```

2. **Login** with your admin account (usually `root`)

3. **Navigate to API Tokens**
   - Click `Datacenter` (left sidebar)
   - Click `Permissions`
   - Click `API Tokens`

4. **Add New Token**
   - Click `Add` button
   - **User**: Select `root@pam`
   - **Token ID**: Enter `glassdome-token` (or any name you like)
   - **Privilege Separation**: **UNCHECK THIS BOX** ⚠️
     - (If checked, token has limited permissions)
   - Click `Add`

5. **SAVE THE SECRET!** ⚠️⚠️⚠️
   ```
   The secret is shown ONLY ONCE!
   
   It will look like:
   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
   - Copy it immediately!
   - Store it somewhere safe
   - You'll need it for the .env file

### Your Token Credentials:
```bash
User: root@pam
Token Name: glassdome-token
Token Secret: <the long string you just copied>
```

---

## Option 2: Password Authentication 🔑

Simpler but less secure.

### What You Need:
```bash
User: root@pam
Password: <your Proxmox root password>
```

That's it! Just use the same credentials you use to login to the Proxmox Web UI.

---

## Command Line Alternative (For API Token)

If you prefer CLI:

```bash
# SSH into Proxmox
ssh root@your-proxmox-server

# Create API token
pveum user token add root@pam glassdome-token --privsep 0

# Output will show:
# ┌───────────────┬──────────────────────────────────────┐
# │ key           │ value                                │
# ╞═══════════════╪══════════════════════════════════════╡
# │ full-tokenid  │ root@pam!glassdome-token             │
# ├───────────────┼──────────────────────────────────────┤
# │ info          │                                      │
# ├───────────────┼──────────────────────────────────────┤
# │ value         │ xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx │
# └───────────────┴──────────────────────────────────────┘

# COPY THE VALUE! You won't see it again!
```

---

## Configure Glassdome

### Method 1: Interactive Setup (Easiest)

```bash
python3 setup_proxmox.py
```

This wizard will:
1. Ask for your Proxmox host
2. Ask for authentication method
3. Ask for credentials
4. Test the connection
5. Save to `.env` automatically

### Method 2: Manual .env File

Create `.env` in the project root:

**With API Token:**
```bash
# Proxmox Configuration
PROXMOX_HOST=your-proxmox-ip-or-hostname
PROXMOX_USER=root@pam
PROXMOX_TOKEN_NAME=glassdome-token
PROXMOX_TOKEN_VALUE=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
PROXMOX_VERIFY_SSL=false
PROXMOX_NODE=pve

# Template IDs
UBUNTU_2204_TEMPLATE_ID=9000
UBUNTU_2004_TEMPLATE_ID=9001
```

**With Password:**
```bash
# Proxmox Configuration
PROXMOX_HOST=your-proxmox-ip-or-hostname
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your-password-here
PROXMOX_VERIFY_SSL=false
PROXMOX_NODE=pve

# Template IDs
UBUNTU_2204_TEMPLATE_ID=9000
UBUNTU_2004_TEMPLATE_ID=9001
```

---

## How Glassdome Uses These Credentials

When you make an API call to Glassdome:

```bash
curl -X POST http://localhost:8001/api/agents/ubuntu/create \
  -d '{"name": "my-vm", "version": "22.04"}'
```

Behind the scenes, Glassdome:
1. Reads credentials from `.env`
2. Creates `ProxmoxClient` with your credentials
3. Calls Proxmox API: `https://your-proxmox:8006/api2/json/...`
4. Authenticates using token or password
5. Creates the VM
6. Returns result to you

**Code path:**
```
API Request 
  ↓
FastAPI endpoint (/api/agents/ubuntu/create)
  ↓
UbuntuInstallerAgent
  ↓
ProxmoxClient (uses credentials from .env)
  ↓
Proxmox API (your server)
```

---

## Security Best Practices

### ✅ DO:
- Use API tokens instead of passwords
- Store `.env` file securely
- Add `.env` to `.gitignore` (already done)
- Use `PROXMOX_VERIFY_SSL=true` in production with valid certificates
- Create separate tokens for different applications
- Revoke tokens you're not using

### ❌ DON'T:
- Commit `.env` to git
- Share your token/password publicly
- Use password auth in production
- Disable SSL verification in production
- Use root@pam in production (create dedicated user)

---

## Testing Your Credentials

### Quick Test:

```bash
python3 test_vm_creation.py
```

This will:
1. Try to connect to Proxmox
2. List nodes
3. List templates
4. Tell you if credentials work

### Manual Test:

```bash
# With token
curl -k -H "Authorization: PVEAPIToken=root@pam!glassdome-token=YOUR-SECRET-HERE" \
  https://your-proxmox:8006/api2/json/version

# With password
curl -k -u root@pam:your-password \
  https://your-proxmox:8006/api2/json/version

# Should return Proxmox version info
```

---

## Troubleshooting

### "Connection refused"
- Check Proxmox is accessible: `ping your-proxmox-host`
- Check API port: `telnet your-proxmox-host 8006`
- Check firewall allows port 8006

### "Authentication failed"
- Token: Make sure you copied the ENTIRE secret
- Password: Try logging into Web UI with same credentials
- Check for typos in `.env`

### "Permission denied"
- Token: Make sure "Privilege Separation" was UNCHECKED when creating token
- Or: Grant specific permissions to token in Proxmox

### "SSL verification failed"
- Use `PROXMOX_VERIFY_SSL=false` for testing
- Or: Add Proxmox certificate to trusted CAs

---

## Summary

**What You Need:**

1. **Proxmox Server**
   - Hostname or IP
   - Accessible on port 8006

2. **Credentials** (choose one):
   - API Token (recommended)
     - User: `root@pam`
     - Token Name: `glassdome-token`
     - Token Secret: `<long string>`
   
   - OR Password
     - User: `root@pam`
     - Password: `<your password>`

3. **Configuration**
   - Run: `python3 setup_proxmox.py`
   - OR manually create `.env` file

**That's it!** Once configured, Glassdome can deploy VMs to your Proxmox server.

---

## Quick Start Commands

```bash
# 1. Run setup wizard
python3 setup_proxmox.py

# 2. Test connection
python3 test_vm_creation.py

# 3. Start API server
glassdome serve

# 4. Create VM
curl -X POST http://localhost:8001/api/agents/ubuntu/create \
  -H "Content-Type: application/json" \
  -d '{"name": "test-vm", "version": "22.04"}'
```

