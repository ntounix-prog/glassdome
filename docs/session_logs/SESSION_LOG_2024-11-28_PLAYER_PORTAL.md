# Session Log: Player Portal & Updock Integration

**Date:** 2024-11-28  
**Focus:** Player access portal, Guacamole (Updock) integration, lab VM configuration  
**Status:** ✅ MVP Complete

---

## Summary

Built the complete player experience pipeline from lab entry to VM desktop access. Players can now enter a lab code, see their machines with mission objectives, and connect to RDP/SSH sessions via Guacamole.

---

## Major Accomplishments

### 1. Lab Network Configuration ✅

**pfSense Gateway:**
- WAN: 192.168.3.242 (management network, DHCP)
- LAN: 10.101.0.1/24 (isolated lab network)
- DHCP: 10.101.0.10-254
- Persistent SSH/HTTPS/HTTP firewall rules via `easyrule`
- NAT enabled for outbound internet access

**Lab VMs:**
- Kali: 10.101.0.10 (Attack Box)
- Ubuntu: 10.101.0.11 (Target)
- Both receive DHCP from pfSense
- Password auth enabled for SSH
- xRDP installed with XFCE desktop

### 2. Updock (Guacamole) Server ✅

**Infrastructure:**
- VM: 192.168.3.8 (updock on pve02)
- Docker Compose: PostgreSQL + guacd + Guacamole web
- Route to lab network: `10.101.0.0/24 via 192.168.3.242`

**Connections Configured:**
| ID | Name | Protocol | Target |
|----|------|----------|--------|
| 5 | 🐉 brettlab-kali | SSH | 10.101.0.10:22 |
| 6 | 🐧 brettlab-ubuntu | SSH | 10.101.0.11:22 |
| 7 | 🖥️ brettlab-kali-rdp | RDP | 10.101.0.10:3389 |
| 8 | 🖥️ brettlab-ubuntu-rdp | RDP | 10.101.0.11:3389 |

**Credentials:**
- Guacamole: `guacadmin` / `guacadmin`
- VMs: `ubuntu` / `Password123!`

### 3. Player Frontend ✅

**New Components:**
- `PlayerPortal.jsx` - Lab code entry with particle effects
- `PlayerLobby.jsx` - Machine cards, mission brief, network info
- `PlayerSession.jsx` - Guacamole integration, toolbar, chat
- `MachineCard.jsx` - VM status cards with connect buttons
- `MissionBrief.jsx` - Objectives, hints, flag submission
- `LabTimer.jsx` - Countdown timer

**Flow:**
```
/player → Enter lab code → /player/:labId → See machines → 
Click CONNECT → /player/:labId/:vmName → Open Guacamole RDP
```

**Features:**
- Dark neon aesthetic matching Glassdome theme
- Overseer chat with SomaFM radio integrated
- Machine status (online/offline)
- Mission hints with point costs
- Network info display
- Fullscreen mode for sessions

### 4. Bug Fixes

**ChatModal Props Issue:**
- Fixed `Cannot read properties of undefined (reading 'currentStation')`
- Added internal state fallback when `radioState` prop not provided
- ChatModal now works standalone in player pages

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Player Browser                                                  │
│  http://192.168.3.227:5174/player                               │
└─────────────────────│────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  Guacamole (Updock) - 192.168.3.8:8080                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Web UI   │  │  guacd   │  │ Postgres │                      │
│  │  :8080   │  │  :4822   │  │  :5432   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────│────────────────────────────────────────────┘
                      │ RDP/SSH
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  pfSense Gateway - 192.168.3.242                                │
│  WAN: 192.168.3.x ←→ LAN: 10.101.0.1                           │
└─────────────────────│────────────────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         ▼                         ▼
┌─────────────────┐       ┌─────────────────┐
│  Kali (Attack)  │       │  Ubuntu (Target)│
│  10.101.0.10    │       │  10.101.0.11    │
│  xRDP + SSH     │       │  xRDP + SSH     │
└─────────────────┘       └─────────────────┘
```

---

## Files Changed

### New Files
- `frontend/src/pages/player/PlayerPortal.jsx`
- `frontend/src/pages/player/PlayerLobby.jsx`
- `frontend/src/pages/player/PlayerSession.jsx`
- `frontend/src/pages/player/components/MachineCard.jsx`
- `frontend/src/pages/player/components/MissionBrief.jsx`
- `frontend/src/pages/player/components/LabTimer.jsx`
- `frontend/src/styles/player/*.css`
- `frontend/src/components/GuacamoleViewer/` (for future use)
- `updock/docker-compose.yml`

### Modified Files
- `frontend/src/App.jsx` - Added player routes
- `frontend/src/components/OverseerChat/ChatModal.jsx` - Fixed props handling
- `frontend/vite.config.js` - Added Guacamole proxy

---

## Known Issues / Future Work

### CORS for Embedded Guacamole
- Native guacamole-common-js embedding has CORS issues when accessing via IP
- Current workaround: "Open Desktop in Guacamole" button opens new tab
- Fix: Configure Guacamole CORS headers or use nginx reverse proxy

### Template Creation Needed
**ACTION:** Convert BOTH lab VMs to templates:

| VM | New Template ID | Name |
|----|-----------------|------|
| 115 | 9002 | kali-xrdp-template |
| 116 | 9003 | ubuntu-xrdp-template |

Both are fully configured with:
- xRDP + XFCE desktop
- SSH password auth enabled  
- DNS configured (8.8.8.8)
- Network ready for DHCP
- User: ubuntu / Password123!

### Production Deployment
- Player portal not yet on prod server (192.168.3.6)
- Need to sync frontend changes to prod

---

## Commands Reference

**Access Guacamole:**
```bash
http://192.168.3.8:8080/guacamole
# Login: guacadmin / guacadmin
```

**SSH to Updock:**
```bash
ssh updock@192.168.3.8
# Password in .env: UPDOCK_PASSWORD
```

**pfSense Console:**
```bash
sshpass -p "pfsense" ssh admin@192.168.3.242
```

**Check Lab VM Status:**
```bash
ssh root@192.168.215.77 "qm guest cmd 115 network-get-interfaces"
```

---

## Demo Script

1. Navigate to http://192.168.3.227:5174/player
2. Enter lab code: `brettlab`
3. Click "ENTER RANGE"
4. Observe machine cards: Kali (Attack) + Ubuntu (Target)
5. Read mission brief: "Root Access Challenge"
6. Click CONNECT on Kali
7. Click "Open Desktop in Guacamole"
8. Login to Guacamole, select `🖥️ brettlab-kali-rdp`
9. Get full graphical Kali desktop in browser!

---

## Next Steps

1. [ ] Create Kali template from VM 115
2. [ ] Configure Guacamole CORS for embedded sessions
3. [ ] Auto-create Guacamole connections on lab deploy
4. [ ] Add session recording/playback
5. [ ] Implement flag submission validation
6. [ ] Add scoring system

---

*Session documented by AI Assistant*

