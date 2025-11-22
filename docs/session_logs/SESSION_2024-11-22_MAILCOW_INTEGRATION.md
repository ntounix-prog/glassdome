# Session Update: Mailcow Integration - 2024-11-22

## Overview
Fixed Mailcow API integration authentication and mailbox creation error handling. Successfully created AI assistant mailbox and sent test email.

## Key Accomplishments

### 1. Authentication Fix
- **Issue**: Initially used Basic Auth, then Bearer token, but Mailcow actually requires `X-API-Key` header
- **Solution**: Updated `MailcowClient` to use `X-API-Key: {token}` header format
- **Files Changed**:
  - `glassdome/integrations/mailcow_client.py`
  - `glassdome/core/config.py` (changed from `mail_api_uid`/`mail_api_pw` to `mail_api`)
  - `glassdome/agents/mailcow_agent.py`
  - `scripts/testing/test_mailcow.py`

### 2. API Endpoint Discovery
- Discovered Mailcow OpenAPI spec at `https://mail.xisx.org/api/openapi.yaml`
- Updated `list_mailboxes()` to use correct endpoint: `/api/v1/get/mailbox/all/{domain}` (not `/api/v1/get/mailbox/all`)
- All log endpoints require `{count}` parameter: `/api/v1/get/logs/postfix/{count}`

### 3. Mailbox Creation Error Handling
- **Critical Bug**: Code was returning `success: True` even when Mailcow returned errors (status 200 with `type: 'danger'`)
- **Fix**: Added proper error detection that checks response array for `type: 'danger'` or `type: 'error'`
- **Required Fields**: Added `password2` (password confirmation) required by Mailcow API
- **Data Types**: Changed boolean/number fields to strings (Mailcow expects strings)

### 4. AI Assistant Mailbox
- Created mailbox: `glassdome-ai@xisx.org`
- Password: `GlassdomeAI2024!`
- Status: ✅ Active and verified
- Test email sent successfully to `ntounix@gmail.com`

## Technical Details

### Authentication Format
```python
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': settings.mail_api  # Not Bearer token, not Basic Auth
}
```

### Error Response Format
Mailcow returns arrays of response objects:
```json
[
  {
    "type": "success",  // or "danger" or "error"
    "msg": ["mailbox_added", "user@domain.com"],
    "log": [...]
  }
]
```

### Mailbox Creation Data Format
```python
{
    'active': '1',  # String, not boolean
    'domain': 'xisx.org',
    'local_part': 'username',
    'name': 'Display Name',
    'password': 'password',
    'password2': 'password',  # Required confirmation
    'quota': '1024',  # String, not number
    'force_pw_update': '0',
    'tls_enforce_in': '1',
    'tls_enforce_out': '1'
}
```

## Files Modified

1. **glassdome/integrations/mailcow_client.py**
   - Changed authentication from Basic Auth to X-API-Key header
   - Fixed error detection in `create_mailbox()`
   - Added `password2` field
   - Changed data types to strings
   - Updated `list_mailboxes()` endpoint format

2. **glassdome/core/config.py**
   - Removed `mail_api_uid` and `mail_api_pw`
   - Added `mail_api` (Bearer token/API key)

3. **glassdome/agents/mailcow_agent.py**
   - Updated to use `api_token` instead of `api_uid`/`api_pw`

4. **scripts/testing/test_mailcow.py**
   - Updated to use `settings.mail_api`

5. **env.example**
   - Changed from `MAIL_API_UID`/`MAIL_API_PW` to `MAIL_API`

## Documentation Created

1. **docs/MAILCOW_API_DIAGNOSTICS.md** - API endpoint discovery and diagnostics
2. **docs/MAILCOW_X_API_KEY_UPDATE.md** - Authentication method update documentation
3. **docs/MAILCOW_AI_MAILBOX.md** - AI assistant mailbox details

## Testing Results

✅ **Mailbox Creation**: Now properly detects and reports errors
✅ **Authentication**: X-API-Key header working correctly
✅ **Email Sending**: SMTP authentication working after password sync
✅ **Error Handling**: Properly detects `password_complexity`, `mailbox_quota_left_exceeded`, `object_exists` errors

## Known Issues Resolved

1. ✅ Authentication method corrected (X-API-Key header)
2. ✅ Error detection fixed (no longer returns success on errors)
3. ✅ Required fields added (`password2`)
4. ✅ Data type mismatches fixed (strings vs booleans/numbers)

## Next Steps

- [ ] Add password complexity validation before API call
- [ ] Add retry logic for password sync delays
- [ ] Implement mailbox quota checking before creation
- [ ] Add comprehensive error message mapping

## Lessons Learned

1. **Always check response content, not just status code** - Mailcow returns 200 even for errors
2. **API documentation is critical** - OpenAPI spec revealed correct endpoint formats
3. **Data type matters** - Mailcow expects strings for boolean/number fields
4. **Error arrays** - Mailcow returns arrays of response objects, need to check each one

