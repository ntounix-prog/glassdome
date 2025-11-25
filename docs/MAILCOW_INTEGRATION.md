# Mailcow Integration Guide

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
MAIL_API=your-bearer-token-here          # Mailcow API Bearer token (X-API-Key format)
MAILCOW_API_URL=https://mail.xisx.org    # Mailcow API URL
MAILCOW_DOMAIN=xisx.org                  # Domain for mailboxes
MAILCOW_IMAP_HOST=mail.xisx.org          # Optional, defaults to mail.{domain}
MAILCOW_SMTP_HOST=mail.xisx.org          # Optional, defaults to mail.{domain}
MAILCOW_SMTP_PORT=587                    # SMTP port (TLS)
MAILCOW_VERIFY_SSL=false                  # Disable SSL verification for self-signed certs
```

### API Authentication

Mailcow uses **Bearer token authentication** with the `X-API-Key` header:

```python
headers = {
    "X-API-Key": "your-bearer-token-here"
}
```

**Note:** The token is obtained from the Mailcow admin panel: Settings → API → Create Token

---

## Usage

### Initialize Agent

```python
from glassdome.agents.mailcow_agent import MailcowAgent
from glassdome.core.config import Settings

settings = Settings()

agent = MailcowAgent(
    agent_id="mailcow-agent-1",
    api_url=settings.mailcow_api_url,
    api_token=settings.mail_api,
    domain=settings.mailcow_domain
)
```

### Create Mailbox

```python
result = await agent.create_mailbox(
    email="test@xisx.org",
    password="SecurePassword123!",
    quota=1024  # MB
)

if result["success"]:
    print(f"Mailbox created: {result['email']}")
```

### List Mailboxes

```python
mailboxes = await agent.list_mailboxes()
for mailbox in mailboxes:
    print(f"{mailbox['email']} - {mailbox['quota']} MB")
```

### Send Email

```python
result = await agent.send_email(
    from_email="test@xisx.org",
    to_email="recipient@example.com",
    subject="Test Email",
    body="This is a test email from Glassdome"
)
```

### Monitor Mailbox

```python
# Check for new emails
emails = await agent.check_mailbox("test@xisx.org")
for email in emails:
    print(f"From: {email['from']}, Subject: {email['subject']}")
```

---

## API Endpoints

The Mailcow API is accessible at: `https://mail.xisx.org/api`

### Key Endpoints

- `POST /api/v1/add/mailbox` - Create mailbox
- `GET /api/v1/get/mailbox/all` - List all mailboxes
- `DELETE /api/v1/delete/mailbox/{email}` - Delete mailbox

**Full API Documentation:** Access Swagger UI at `https://mail.xisx.org/api`

---

## Troubleshooting

### Authentication Issues

**Problem:** `401 Unauthorized` or `403 Forbidden`

**Solutions:**
1. Verify `MAIL_API` token is correct in `.env`
2. Check token has proper permissions in Mailcow admin panel
3. Ensure token format is correct (Bearer token, not username:password)

### SSL Certificate Issues

**Problem:** `SSL: CERTIFICATE_VERIFY_FAILED`

**Solution:** Set `MAILCOW_VERIFY_SSL=false` in `.env` for self-signed certificates

### Connection Issues

**Problem:** Cannot connect to Mailcow API

**Solutions:**
1. Verify `MAILCOW_API_URL` is correct
2. Check network connectivity to mail server
3. Ensure Mailcow service is running

---

## Implementation Details

### Components

1. **`glassdome/integrations/mailcow_client.py`**
   - Mailcow API client
   - Handles authentication with X-API-Key header
   - Mailbox CRUD operations

2. **`glassdome/agents/mailcow_agent.py`**
   - MailcowAgent class
   - Orchestrates mailbox operations
   - Email sending/monitoring

### Email Operations

- **SMTP:** Used for sending emails (port 587, TLS)
- **IMAP:** Used for reading emails (port 993, SSL)

---

## Related Documentation

- [Mailcow API Diagnostics](MAILCOW_API_DIAGNOSTICS.md) - Detailed API troubleshooting
- [Mailcow Bearer Token Update](MAILCOW_BEARER_TOKEN_UPDATE.md) - Authentication migration notes
- [Mailcow X-API-Key Update](MAILCOW_X_API_KEY_UPDATE.md) - API key format details

---

*Last Updated: November 22, 2024*

