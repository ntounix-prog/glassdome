# Mailcow API Diagnostics

## Date: 2024-11-22

## Issue
SMTP authentication consistently failing with error `535: 5.7.8 Error: authentication failed: (reason unavailable)` for mailbox `glassdome-test@xisx.org`.

## API Discovery

### OpenAPI Specification
- **Location**: `https://mail.xisx.org/api/openapi.yaml`
- **Version**: 1.0.0
- **Format**: OAS 3.1

### Updated Endpoints

#### Mailbox Endpoints
- **List mailboxes by domain**: `GET /api/v1/get/mailbox/all/{domain}` (NOT `/api/v1/get/mailbox/all`)
- **Get specific mailbox**: `GET /api/v1/get/mailbox/{id}` where `{id}` can be:
  - `"all"` - all mailboxes
  - `"user@domain.tld"` - specific mailbox

#### Log Endpoints
All log endpoints require a `{count}` parameter:
- `GET /api/v1/get/logs/postfix/{count}`
- `GET /api/v1/get/logs/dovecot/{count}`
- `GET /api/v1/get/logs/auth/{count}`
- `GET /api/v1/get/logs/api/{count}`
- etc.

### Authentication
- **Method**: X-API-Key Header (not Basic Auth or Bearer token)
- **Format**: `X-API-Key: {token}`
- **Environment Variable**: `MAIL_API` (contains the API key/token)

## Findings

### Mailbox Creation
- ✅ Mailbox creation via API works (returns 200)
- ✅ Mailbox exists in system (confirmed via database)
- ❌ Mailbox queries return empty responses (even though mailbox exists)

### Logs
- ❌ All log endpoints return empty responses
- ❌ No authentication failures visible in logs
- **Possible reasons**:
  - Logs may be stored differently in this Mailcow version
  - Logs may require different permissions
  - Logs may be in a different location

### SMTP Authentication
- ❌ Consistent failure: `535: 5.7.8 Error: authentication failed: (reason unavailable)`
- ❌ Works with neither IP (`192.168.3.69`) nor domain (`mail.xisx.org`)
- **Possible causes**:
  1. Password not properly synced to Postfix/Dovecot
  2. Mailbox not fully activated
  3. Authentication source mismatch (`authsource` parameter)
  4. Mailcow configuration issue

## Recommendations

1. **Check Mailcow UI**:
   - Verify mailbox exists and is active
   - Check if password needs to be manually set in UI
   - Verify mailbox authentication source

2. **Check Mailcow Configuration**:
   - Verify Postfix/Dovecot are running
   - Check if password sync is working
   - Review Mailcow logs via Docker: `docker-compose logs postfix-mailcow`

3. **Try Alternative Authentication**:
   - Use app passwords instead of mailbox password
   - Check if `authsource` parameter needs to be set during creation

4. **Update Code**:
   - ✅ Updated `list_mailboxes()` to use `/api/v1/get/mailbox/all/{domain}`
   - Consider adding retry logic for password sync delays
   - Add better error handling for empty responses

## Code Updates Made

### `glassdome/integrations/mailcow_client.py`
- Updated `list_mailboxes()` to use correct endpoint format: `/api/v1/get/mailbox/all/{domain}`

## Next Steps

1. Manually verify mailbox in Mailcow UI
2. Check if password needs manual setting
3. Review Mailcow container logs directly
4. Consider using app passwords for SMTP authentication
5. Test with different `authsource` values during mailbox creation

