# Mailcow X-API-Key Header Authentication Update

## Date: 2024-11-22

## Change Summary
Updated Mailcow integration to use **X-API-Key header** authentication instead of Basic Auth (username/password).

## Changes Made

### 1. Configuration (`glassdome/core/config.py`)
- **Removed**: `mail_api_uid` and `mail_api_pw` fields
- **Added**: `mail_api` field (Bearer token from `MAIL_API` env var)

### 2. Mailcow Client (`glassdome/integrations/mailcow_client.py`)
- **Updated**: `__init__` to accept `api_token` instead of `api_uid` and `api_pw`
- **Changed**: Authentication header from `Authorization: Basic {base64}` to `X-API-Key: {token}`
- **Updated**: `list_mailboxes()` to use correct endpoint format: `/api/v1/get/mailbox/all/{domain}`

### 3. Mailcow Agent (`glassdome/agents/mailcow_agent.py`)
- **Updated**: `__init__` to accept `api_token` parameter
- **Updated**: Client initialization to pass `api_token` instead of `api_uid`/`api_pw`

### 4. Test Script (`scripts/testing/test_mailcow.py`)
- **Updated**: To use `settings.mail_api` instead of `settings.mail_api_uid`/`settings.mail_api_pw`

### 5. Environment Example (`env.example`)
- **Changed**: From `MAIL_API_UID` and `MAIL_API_PW` to single `MAIL_API` token

## Environment Variable

```bash
# Old format (removed)
MAIL_API_UID=apiadmin
MAIL_API_PW=your-password

# New format
MAIL_API=your-bearer-token
```

## Testing

X-API-Key header authentication is confirmed working:
- ✅ API calls return 200 status codes
- ✅ Authentication header format: `X-API-Key: {token}`
- ✅ Endpoint format updated: `/api/v1/get/mailbox/all/{domain}`

## Notes

- API key/token is obtained from Mailcow UI: Configuration > Access > Edit administrator details > API
- Token should be added to `.env` file as `MAIL_API=your-token-here`
- No username/password needed - just the API key
- Header format: `X-API-Key: {token}` (not `Authorization: Bearer`)

