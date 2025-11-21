# Operational Automation & Communication

**Purpose:** Enable autonomous AI operation for late-night deployments, troubleshooting, and team communication

---

## Use Cases

### 1. Late-Night Game Setup (Autonomous)

**Scenario:** VP schedules cyber range game for 2 AM (different timezone training)

**Requirements:**
- AI deploys 9-VM scenario unattended
- Detects and fixes common issues automatically
- Messages Slack if human intervention needed
- Sends email summary when complete

**Example Flow:**
```
02:00 - Game scheduled to start
02:01 - AI begins deployment (9 VMs across 4 networks)
02:03 - VM 3 fails (IP pool exhausted)
02:03 - AI auto-recovers: Uses fallback IP x.x.x.254
02:04 - AI detects VM 5 won't boot
02:04 - Slack message: "⚠️ VM 5 boot issue, investigating..."
02:05 - AI reboots VM 5, checks logs
02:06 - VM 5 operational
02:08 - All VMs deployed and verified
02:08 - Slack message: "✅ Cyber Range READY: 9 VMs online"
02:09 - Email sent: "Game Environment Ready - 192.168.100.10 (console)"
```

### 2. Game Completion & Scoring

**Scenario:** 6-hour capture-the-flag game ends

**Requirements:**
- AI monitors game progress
- Tracks flag captures, exploits, time-to-compromise
- Generates scoring report
- Emails summary to participants and organizers

**Example Email:**
```
Subject: CTF Game Complete - Enterprise Web Application

Duration: 6 hours 23 minutes
Participants: 12 players (3 teams)

🏆 RESULTS:
1st Place: Red Team (8/10 flags, 5h 12m)
2nd Place: Blue Team (6/10 flags, 5h 45m)
3rd Place: Green Team (4/10 flags, 5h 58m)

📊 STATISTICS:
- Fastest exploit: SQL Injection (12 minutes - Red Team)
- Most challenging: Kerberoasting (avg 3h 45m)
- Flags captured: 18/30 total attempts

🎯 FLAG CAPTURES:
✅ web-server-sqli (Red: 12m, Blue: 45m, Green: 2h)
✅ dns-zone-transfer (Red: 28m, Blue: 1h 15m)
✅ smb-eternalblue (Red: 1h 30m, Green: 2h 45m)
...

Environment: Torn down at 08:25 AM
Cost: $2.45 (AWS instances)
```

### 3. Autonomous Troubleshooting

**Common Issues & Auto-Recovery:**

| Issue | Detection | Recovery |
|-------|-----------|----------|
| VM won't boot | Check QEMU status | Reboot, check logs, rebuild if needed |
| No IP address | Ping test fails | Apply fallback IP (x.x.x.254) |
| SSH not responding | Port 22 scan | Restart SSH service via console |
| Service crashed | Health check fails | Restart service, check dependencies |
| Disk full | Usage > 90% | Clean logs, extend disk, alert team |
| Network unreachable | Route test fails | Reconfigure netplan, check bridge |

---

## Slack Integration

### Architecture

```
Glassdome AI Agent
    ↓
Slack Webhook / Bolt SDK
    ↓
#cyber-range-ops channel
    ↓
Team receives real-time updates
```

### Message Types

**1. Deployment Status:**
```
🚀 Deploying: Enterprise Web Application
   Progress: [▓▓▓▓▓░░░░░] 5/9 VMs (55%)
   ETA: 3 minutes
```

**2. Error Alerts:**
```
⚠️ Issue Detected: VM 3 (web-server)
   Problem: Boot failure after 3 attempts
   Action: Rebuilding from template
   Status: In progress...
```

**3. Resolution Updates:**
```
✅ Resolved: VM 3 (web-server)
   Fix: Disk space exhausted, extended to 40GB
   Status: Online (192.168.3.35)
   Duration: 4 minutes
```

**4. Game Events:**
```
🎯 Flag Captured: web-server-sqli
   Team: Red Team
   Time: 12 minutes into game
   Current Standings: Red (1), Blue (0), Green (0)
```

### Implementation

**Location:** `glassdome/integrations/slack_client.py`

```python
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

class SlackNotifier:
    def __init__(self, token: str, channel: str):
        self.client = WebClient(token=token)
        self.channel = channel
    
    async def send_alert(self, title: str, message: str, severity: str = "info"):
        """
        Send alert to Slack channel
        
        Args:
            title: Alert title
            message: Alert message
            severity: info, warning, error, success
        """
        emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }
        
        try:
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=f"{emoji[severity]} {title}\n{message}"
            )
            return response
        except SlackApiError as e:
            logger.error(f"Slack error: {e.response['error']}")
    
    async def send_deployment_status(self, deployment_id: str, progress: dict):
        """Send deployment progress update"""
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🚀 Deployment Progress"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*ID:* {deployment_id}"},
                    {"type": "mrkdwn", "text": f"*Status:* {progress['status']}"},
                    {"type": "mrkdwn", "text": f"*VMs:* {progress['completed']}/{progress['total']}"},
                    {"type": "mrkdwn", "text": f"*ETA:* {progress['eta']}"}
                ]
            }
        ]
        
        self.client.chat_postMessage(
            channel=self.channel,
            blocks=blocks
        )
```

### Configuration

**`.env` additions:**
```bash
# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_CHANNEL=#cyber-range-ops
SLACK_ENABLED=true
```

---

## Email Integration

### Architecture

```
Glassdome AI Agent
    ↓
SMTP Client (SendGrid/Mailgun/AWS SES)
    ↓
Email Recipients (participants, organizers)
```

### Email Types

**1. Game Ready Notification**
```
Subject: Cyber Range Ready - Enterprise Web Application

Your cyber range environment is deployed and ready:

🎯 Attack Console: ssh ubuntu@192.168.100.10
   Password: [redacted - check Slack]

📋 Scenario: Enterprise Web Application
   Duration: 6 hours
   Networks: 4 (Attack, DMZ, Internal, Management)
   Targets: 8 VMs
   Flags: 10 hidden

🚩 Objectives:
   - Gain access to DMZ web server
   - Pivot to internal network
   - Compromise domain controller
   - Exfiltrate "flag.txt" from fileserver

⏰ Game Start: 2:00 AM PST
   Game End: 8:00 AM PST

Good luck! 🔥
```

**2. Game Completion Summary**
```
Subject: Game Complete - Scoring Report

[Full scoring report as shown in Use Case #2 above]

📎 Attachments:
   - detailed_scores.csv
   - flag_capture_timeline.png
   - player_statistics.json

Next Steps:
   - Review recording: [link to session replay]
   - Feedback form: [link]
   - Schedule next game: [link]
```

**3. Error Notifications (for ops team)**
```
Subject: URGENT - Deployment Failure Requires Attention

Deployment ID: deploy-abc123
Scenario: Enterprise Web Application
Started: 02:00 AM PST

❌ FAILED: Unable to recover automatically

Issue: ESXi host unreachable
Details: 
   - Host: 192.168.3.3
   - Error: Connection timeout after 5 attempts
   - Impact: 3/9 VMs not deployed

Action Required:
   1. Check ESXi host connectivity
   2. Restart management services if needed
   3. Retry deployment: glassdome deploy resume deploy-abc123

Slack thread: [link]
Logs: [link]
```

### Implementation

**Location:** `glassdome/integrations/email_client.py`

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

class EmailNotifier:
    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    async def send_game_ready(self, recipients: list, scenario: dict, access_info: dict):
        """Send game ready notification"""
        
        html_content = f"""
        <html>
        <body>
            <h2>🎯 Cyber Range Ready</h2>
            <h3>{scenario['name']}</h3>
            
            <h4>Access Information:</h4>
            <pre>ssh {access_info['user']}@{access_info['ip']}</pre>
            
            <h4>Scenario Details:</h4>
            <ul>
                <li>Duration: {scenario['duration']}</li>
                <li>Networks: {scenario['networks']}</li>
                <li>Targets: {scenario['targets']} VMs</li>
                <li>Flags: {scenario['flags']} hidden</li>
            </ul>
            
            <p>Good luck! 🔥</p>
        </body>
        </html>
        """
        
        await self._send_email(
            recipients=recipients,
            subject=f"Cyber Range Ready - {scenario['name']}",
            html_content=html_content
        )
    
    async def send_completion_summary(self, recipients: list, game_results: dict, attachments: list = None):
        """Send game completion summary with scoring"""
        
        # Generate HTML report
        html_content = self._generate_scoring_report(game_results)
        
        await self._send_email(
            recipients=recipients,
            subject=f"Game Complete - {game_results['scenario_name']}",
            html_content=html_content,
            attachments=attachments
        )
    
    async def _send_email(self, recipients: list, subject: str, html_content: str, attachments: list = None):
        """Send email via SMTP"""
        
        msg = MIMEMultipart()
        msg['From'] = self.username
        msg['To'] = ", ".join(recipients)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Add attachments
        if attachments:
            for attachment in attachments:
                with open(attachment, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=attachment)
                    part['Content-Disposition'] = f'attachment; filename="{attachment}"'
                    msg.attach(part)
        
        # Send
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
```

### Configuration

**`.env` additions:**
```bash
# Email Integration
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=noreply@glassdome.io
EMAIL_ENABLED=true
```

---

## Autonomous Troubleshooting

### Self-Healing Capabilities

**1. Network Recovery (Implemented)**
- Fallback to x.x.x.254 if IP allocation fails
- Auto-decrement if fallback in use

**2. Service Recovery (To Implement)**
```python
async def auto_recover_service(vm_id: str, service: str):
    """
    Detect and recover failed services
    
    Checks:
    - Is service running? (systemctl status)
    - Are dependencies met?
    - Are ports listening?
    - Are logs showing errors?
    
    Recovery:
    1. Restart service
    2. Check dependencies
    3. Rebuild config if corrupted
    4. Reboot VM if needed
    5. Alert team if can't recover
    """
    pass
```

**3. VM Boot Recovery**
```python
async def auto_recover_vm_boot(vm_id: str, platform: str):
    """
    Recover VM that won't boot
    
    Steps:
    1. Check QEMU/VM status logs
    2. Verify disk integrity
    3. Check boot order
    4. Rebuild from template if corrupted
    5. Restore from snapshot if available
    """
    pass
```

**4. Disk Space Management**
```python
async def auto_manage_disk_space(vm_id: str):
    """
    Prevent and recover from disk full
    
    Prevention:
    - Monitor disk usage every 5 minutes
    - Alert at 80% full
    - Auto-clean at 90% full
    
    Auto-clean:
    1. Clear /tmp
    2. Rotate logs (keep last 7 days)
    3. Clean apt cache
    4. Extend disk if still >85%
    """
    pass
```

---

## Decision Tree for Late-Night Issues

```
Issue Detected
    ↓
Can I fix automatically?
    ├─ YES → Fix, log action, continue
    │         ↓
    │      Fixed successfully?
    │         ├─ YES → Continue, send Slack update
    │         └─ NO → Escalate to human
    │
    └─ NO → Is it critical?
              ├─ YES → Alert team immediately (Slack + Email)
              └─ NO → Log issue, attempt workaround, alert in morning
```

---

## Monitoring & Alerting Thresholds

| Metric | Warning | Critical | Action |
|--------|---------|----------|--------|
| Disk Usage | 80% | 90% | Auto-clean at 90% |
| Memory Usage | 85% | 95% | Kill non-essential processes |
| CPU Usage | 90% sustained | 95% for 5m | Investigate process, scale if needed |
| Network Errors | 5% packet loss | 10% loss | Check routes, alert team |
| Service Downtime | 2 minutes | 5 minutes | Auto-restart, then alert |
| Failed Deployments | 1 failure | 3 failures | Stop, alert team, preserve logs |

---

## Implementation Priority

### Phase 1 (Week 2 - Before Demo)
1. Basic Slack integration (alerts only)
2. Network recovery fallback (x.x.x.254)
3. Email for game completion summaries

### Phase 2 (Post-Demo)
4. Service auto-recovery
5. VM boot recovery
6. Disk space management
7. Full autonomous troubleshooting

### Phase 3 (Production)
8. Advanced monitoring
9. Predictive failure detection
10. Machine learning for pattern recognition

---

## Testing Scenarios

**Before going live with autonomous operation:**

1. **Simulate Network Failure** - Verify fallback IP works
2. **Simulate Service Crash** - Verify auto-restart works
3. **Simulate Disk Full** - Verify auto-clean works
4. **Simulate Late-Night Deployment** - End-to-end test with no human
5. **Simulate Communication Failure** - Verify alerts reach team

---

**Status:** Design complete, implementation pending  
**Priority:** High for production deployment  
**Dependencies:** RAG system (for intelligent troubleshooting decisions)

