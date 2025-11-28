# Glassdome User Guide

Welcome to Glassdome, the Agentic Cyber Range Deployment Framework. This guide will help you get started based on your role and responsibilities.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Logging In](#logging-in)
3. [Understanding Your Role](#understanding-your-role)
4. [Dashboard Overview](#dashboard-overview)
5. [Features by Role](#features-by-role)
6. [Common Tasks](#common-tasks)
7. [Player Portal](#player-portal)
8. [FAQ](#faq)

---

## Getting Started

### System Requirements

**Browser**: Chrome, Firefox, Safari, or Edge (latest versions)

### Accessing Glassdome

Your administrator will provide you with:
- **URL**: The web address (e.g., `https://glassdome.yourcompany.com`)
- **Username**: Your login username
- **Password**: Your initial password (change it on first login!)

---

## Logging In

1. Navigate to the Glassdome URL
2. Enter your **username** and **password**
3. Click **Sign In**

### First Login

If you're the **first user** on a new Glassdome installation:
1. You'll see a "Create first admin account" option
2. Register with your email, username, and password
3. You'll automatically become the Admin

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

### Changing Your Password

1. Click your username in the top-right corner
2. Select **Change Password**
3. Enter current password and new password
4. Click **Update**

---

## Understanding Your Role

Glassdome uses Role-Based Access Control (RBAC). Your role determines what you can see and do.

### Roles

| Role | Level | What You Can Do |
|------|-------|-----------------|
| **Observer** | 25 | View dashboards, monitor labs, read-only access |
| **Engineer** | 50 | Deploy labs, run missions, operate VMs |
| **Architect** | 75 | Design labs, create exploits, manage networks |
| **Admin** | 100 | Everything + user management + secrets |

### Checking Your Role

Your role and level are displayed next to your username in the navigation bar.

---

## Dashboard Overview

The Dashboard is your home screen showing:

### System Health
- **API Status**: Connection to backend services
- **Platform Status**: Proxmox, ESXi, AWS, Azure connectivity

### Feature Cards
Quick access to Glassdome features:
- 🔮 **Overseer**: AI assistant for lab management
- ☠️ **Reaper**: Vulnerability injection framework
- 🛡️ **WhiteKnight**: Security validation engine
- ♟️ **WhitePawn**: Continuous monitoring
- 🎮 **Player Portal**: Access lab environments

### Quick Stats
- Active labs
- Running deployments
- Pending missions

---

## Features by Role

### Observer (Level 25)

**You can:**
- View the Dashboard
- Monitor lab status
- View platform health
- Watch deployment progress
- Access the Player Portal (if assigned to a lab)

**Navigation:**
- Dashboard
- Monitor → Lab Monitor, WhitePawn, Platform Status
- Player Portal

### Engineer (Level 50)

**Everything Observers can do, plus:**
- Deploy pre-designed labs
- Start/stop/restart VMs
- Run Reaper missions (execute exploits)
- Access VM consoles

**Additional Navigation:**
- Deployments
- Full platform controls

### Architect (Level 75)

**Everything Engineers can do, plus:**
- Design labs in the Lab Canvas
- Create and edit exploit definitions (Reaper)
- Configure WhiteKnight validation rules
- Manage network topologies

**Additional Navigation:**
- Design → Lab Designer, Reaper, WhiteKnight

### Admin (Level 100)

**Everything Architects can do, plus:**
- Manage users (create, edit, deactivate)
- Configure platform credentials
- Manage secrets
- System configuration

**Additional Navigation:**
- Admin → User Management, Secrets

---

## Common Tasks

### Viewing Lab Status

1. Go to **Monitor** → **Lab Monitor**
2. See all active labs and their VMs
3. Click a lab for detailed view

### Checking Platform Health

1. Go to **Monitor** → (select platform)
2. View:
   - Connection status
   - Resource usage (CPU, RAM, Storage)
   - Running VMs

### Deploying a Lab (Engineer+)

1. Go to **Deployments**
2. Click **New Deployment**
3. Select a lab design
4. Choose target platform
5. Click **Deploy**
6. Monitor progress on the Deployments page

### Designing a Lab (Architect+)

1. Go to **Design** → **Lab Designer**
2. Use the canvas to:
   - Drag VMs from the palette
   - Draw network connections
   - Configure VM properties
3. Click **Save** to store your design
4. Click **Deploy** to launch

### Creating an Exploit (Architect+)

1. Go to **Design** → **Reaper**
2. Click **Add Exploit**
3. Fill in:
   - Name and description
   - Target vulnerability (CVE)
   - Script or Ansible playbook
4. Save the exploit

### Running a Mission (Engineer+)

1. Go to **Design** → **Reaper**
2. Find your exploit
3. Click **Run Mission**
4. Select target VM
5. Monitor execution

---

## Player Portal

The Player Portal provides isolated access to lab environments for training exercises.

### Accessing as a Player

1. Go to **Player Portal**
2. Select your assigned lab
3. Choose a VM to access
4. Connect via Guacamole (web-based console)

### Player Features

- **Web Console**: Full desktop or terminal access in browser
- **Clipboard**: Copy/paste between your computer and the VM
- **File Transfer**: Upload/download files (if enabled)

### Tips for Players

- Your session may timeout after inactivity
- Changes in the lab may not persist after lab reset
- Contact your instructor if you get locked out

---

## Using Overseer (AI Assistant)

Overseer is Glassdome's AI assistant that can help with:
- Answering questions about the platform
- Explaining security concepts
- Troubleshooting issues
- Suggesting lab configurations

### Opening Overseer

Click the chat icon (💬) in the bottom-right corner.

### Example Queries

- "How do I deploy a new lab?"
- "What's the difference between a mission and an exploit?"
- "Help me understand CVE-2021-44228"
- "What VMs are currently running?"

---

## FAQ

### Q: I forgot my password

Contact your administrator. They can reset your password via:
- The Admin → User Management page
- CLI: `glassdome auth reset-password -u yourname`

### Q: I can't see certain features

Your role may not have access. Check your role level in the user menu. Contact an Admin if you need elevated access.

### Q: A lab deployment failed

1. Check the error message in Deployments
2. Verify the platform has enough resources
3. Check platform connectivity in Monitor
4. Contact an Architect or Admin

### Q: My session expired

This is normal - sessions timeout after 30 minutes of inactivity. Simply log in again.

### Q: I can't connect to a VM in Player Portal

1. Ensure the lab is deployed and running
2. Check the VM status in Lab Monitor
3. Try refreshing the page
4. Guacamole may need time to connect - wait 30 seconds

### Q: How do I report a bug?

Contact your system administrator or submit an issue to the project repository.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + /` | Open Overseer chat |
| `Ctrl + S` | Save (in Lab Designer) |
| `Escape` | Close modals |
| `Delete` | Remove selected item (Lab Designer) |

---

## Getting Help

1. **Overseer AI**: Click the chat icon for instant help
2. **Admin Guide**: Technical documentation for administrators
3. **Your Administrator**: For account and access issues
4. **Platform Docs**: Links to Proxmox, AWS, Azure documentation

---

## Glossary

| Term | Definition |
|------|------------|
| **Lab** | A collection of VMs and networks for training |
| **Deployment** | A running instance of a lab |
| **Exploit** | A security vulnerability script |
| **Mission** | Execution of an exploit against a target |
| **Platform** | Infrastructure provider (Proxmox, AWS, etc.) |
| **Reaper** | Glassdome's vulnerability injection system |
| **WhiteKnight** | Validation engine for security checks |
| **WhitePawn** | Continuous monitoring agent |
| **Overseer** | AI assistant |
| **Registry** | Central database of lab state |

