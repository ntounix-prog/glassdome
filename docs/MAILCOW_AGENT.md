# Mailcow Agent Documentation

**Status:** ✅ Implemented  
**Domain:** xisx.org  
**Purpose:** Autonomous mailbox management and email operations

---

## Overview

The Mailcow Agent provides automated mailbox creation, email monitoring, and email sending capabilities for the xisx.org domain. It uses the Mailcow REST API for mailbox management and IMAP/SMTP for email operations.

---

## Configuration

Add to `.env` file:

```bash
# Mailcow Configuration
MAIL_API_UID=apiadmin                    # Mailcow API username
MAIL_API_PW=your-password-here          # Mailcow API password
MAILCOW_API_URL=https://192.168.3.69     # Mailcow API URL (IP or hostname)
MAILCOW_DOMAIN=xisx.org                  # Domain for mailboxes
MAILCOW_IMAP_HOST=192.168.3.69           # Optional, defaults to API URL host
MAILCOW_SMTP_HOST=192.168.3.69           # Optional, defaults to API URL host
MAILCOW_SMTP_PORT=587                    # SMTP port
```

**Note:** Mailcow uses HTTP Basic Authentication (username/password), not an API key header.

---

## Usage

### Initialize Agent

```python
from glassdome.agents.mailcow_agent import MailcowAgent
from glassdome.core.config import Settings

settings = Settings()

agent = MailcowAgent(
    agent_id="mailcow-agent-1",
    api_url=settings.mailcow_api_url or "https://192.168.3.69",
    api_uid=settings.mail_api_uid,
    api_pw=settings.mail_api_pw,
    domain=settings.mailcow_domain
)
```

### Create Mailbox

```python
result = await agent.execute({
    'action': 'create_mailbox',
    'local_part': 'glassdome',
    'password': 'SecurePassword123!',
    'name': 'Glassdome Agent',
    'quota_mb': 1024
})

# Result:
# {
#     'success': True,
#     'mailbox': 'glassdome@xisx.org',
#     'details': {...}
# }
```

### Monitor Mailbox

```python
result = await agent.execute({
    'action': 'monitor_mailbox',
    'mailbox': 'glassdome@xisx.org',
    'password': 'SecurePassword123!',
    'unread_only': True,  # Only fetch unread messages
    'folder': 'INBOX'     # IMAP folder
})

# Result:
# {
#     'success': True,
#     'mailbox': 'glassdome@xisx.org',
#     'count': 3,
#     'messages': [
#         {
#             'id': '1',
#             'subject': 'Test Email',
#             'from': 'sender@example.com',
#             'to': 'glassdome@xisx.org',
#             'date': '...',
#             'body': 'Email body text...'
#         },
#         ...
#     ]
# }
```

### Send Email

```python
result = await agent.execute({
    'action': 'send_email',
    'mailbox': 'glassdome@xisx.org',
    'password': 'SecurePassword123!',
    'to_addresses': ['recipient@example.com'],
    'subject': 'Test Email',
    'body': 'Plain text body',
    'html_body': '<html><body><h1>HTML Body</h1></body></html>',  # Optional
    'cc': ['cc@example.com'],  # Optional
    'bcc': ['bcc@example.com']  # Optional
})

# Result:
# {
#     'success': True,
#     'from': 'glassdome@xisx.org',
#     'to': ['recipient@example.com'],
#     'subject': 'Test Email',
#     'sent_at': '2024-11-21T16:00:00'
# }
```

### List All Mailboxes

```python
result = await agent.execute({
    'action': 'list_mailboxes'
})

# Result:
# {
#     'success': True,
#     'count': 5,
#     'mailboxes': [
#         {
#             'username': 'glassdome',
#             'domain': 'xisx.org',
#             ...
#         },
#         ...
#     ]
# }
```

### Monitor All Registered Mailboxes

```python
# First, create/monitor mailboxes to register them
await agent.execute({
    'action': 'monitor_mailbox',
    'mailbox': 'glassdome@xisx.org',
    'password': 'password'
})

# Then monitor all at once
result = await agent.monitor_all_mailboxes()

# Result:
# {
#     'success': True,
#     'mailboxes_checked': 2,
#     'results': {
#         'glassdome@xisx.org': {
#             'success': True,
#             'count': 3,
#             'messages': [...]
#         },
#         ...
#     }
# }
```

---

## Continuous Monitoring

For autonomous monitoring, integrate with Overseer or run in a loop:

```python
import asyncio

async def monitor_loop(agent, interval=60):
    """Monitor mailboxes every N seconds"""
    while True:
        result = await agent.monitor_all_mailboxes()
        
        for mailbox, mb_result in result.get('results', {}).items():
            if mb_result.get('success') and mb_result.get('count', 0) > 0:
                messages = mb_result.get('messages', [])
                for msg in messages:
                    # Process new email
                    print(f"New email in {mailbox}: {msg['subject']}")
        
        await asyncio.sleep(interval)

# Run monitoring loop
asyncio.run(monitor_loop(agent, interval=60))
```

---

## Testing

Run the test script:

```bash
cd /home/nomad/glassdome
source venv/bin/activate
python scripts/testing/test_mailcow.py
```

The test script will:
1. List existing mailboxes
2. Create a test mailbox (`glassdome-test@xisx.org`)
3. Send a test email to itself
4. Monitor for new emails
5. Monitor all registered mailboxes

---

## API Reference

### MailcowClient

**Location:** `glassdome/integrations/mailcow_client.py`

**Methods:**
- `create_mailbox()` - Create mailbox via API
- `get_mailbox_messages()` - Fetch emails via IMAP
- `send_email()` - Send email via SMTP
- `list_mailboxes()` - List all mailboxes
- `delete_mailbox()` - Delete mailbox

### MailcowAgent

**Location:** `glassdome/agents/mailcow_agent.py`

**Actions:**
- `create_mailbox` - Create a new mailbox
- `monitor_mailbox` - Check for new emails
- `send_email` - Send an email
- `list_mailboxes` - List all mailboxes
- `delete_mailbox` - Delete a mailbox

**Special Methods:**
- `monitor_all_mailboxes()` - Monitor all registered mailboxes

---

## Integration with Overseer

The Mailcow agent can be integrated with the Overseer for autonomous email operations:

```python
from glassdome.agents.overseer import OverseerAgent
from glassdome.agents.mailcow_agent import MailcowAgent

# Initialize Mailcow agent
mailcow_agent = MailcowAgent(...)

# Add to Overseer monitoring
overseer.add_monitored_agent(mailcow_agent)

# Overseer will automatically:
# - Monitor mailboxes for new emails
# - Send alerts via email
# - Process email commands
```

---

## Security Considerations

1. **Password Storage:** Mailbox passwords are stored in agent memory. Consider using a secrets manager for production.

2. **API Key:** Store Mailcow API key securely in `.env` file (not committed to git).

3. **TLS:** IMAP and SMTP connections use TLS by default.

4. **Rate Limiting:** Implement rate limiting for email sending to avoid spam.

5. **Sensitive Data:** Filter sensitive data from email content before sending.

---

## Troubleshooting

### Mailbox Creation Fails

**Error:** `password_complexity`
- **Solution:** Ensure password meets Mailcow requirements (uppercase, lowercase, number, special char, min length)

**Error:** `mailbox_defquota_exceeds_mailbox_maxquota`
- **Solution:** Reduce quota or increase domain max quota in Mailcow

### IMAP Connection Fails

**Error:** `IMAP4.error: LOGIN failed`
- **Solution:** Verify mailbox password and IMAP hostname

**Error:** `Connection refused`
- **Solution:** Check IMAP hostname and firewall rules

### SMTP Sending Fails

**Error:** `SMTPAuthenticationError`
- **Solution:** Verify mailbox credentials and SMTP settings

**Error:** `Connection timeout`
- **Solution:** Check SMTP hostname, port, and firewall rules

---

## Example Use Cases

### 1. Automated Alerts

```python
# Send deployment alerts
await agent.execute({
    'action': 'send_email',
    'mailbox': 'alerts@xisx.org',
    'password': '...',
    'to_addresses': ['team@xisx.org'],
    'subject': 'VM Deployment Complete',
    'body': 'VM 115 deployed successfully at 192.168.3.55'
})
```

### 2. Command Processing

```python
# Monitor for commands
result = await agent.execute({
    'action': 'monitor_mailbox',
    'mailbox': 'commands@xisx.org',
    'password': '...',
    'unread_only': True
})

# Process commands from emails
for msg in result.get('messages', []):
    command = parse_command(msg['body'])
    execute_command(command)
```

### 3. Daily Reports

```python
# Send daily summary
await agent.execute({
    'action': 'send_email',
    'mailbox': 'reports@xisx.org',
    'password': '...',
    'to_addresses': ['team@xisx.org'],
    'subject': 'Daily Deployment Report',
    'html_body': generate_html_report()
})
```

---

**Last Updated:** November 21, 2024  
**Status:** ✅ Ready for Use

