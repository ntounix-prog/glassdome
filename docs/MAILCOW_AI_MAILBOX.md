# Glassdome AI Assistant Mailbox

## Created: 2024-11-22

## Mailbox Details

- **Email**: `glassdome-ai@xisx.org`
- **Password**: `GlassdomeAI2024!`
- **Name**: Glassdome AI Assistant
- **Quota**: 1024 MB
- **Status**: ✅ Created successfully via Mailcow API

## Current Status

### ✅ Working
- Mailbox creation via API
- Mailbox exists in Mailcow system
- API authentication with X-API-Key header

### ⚠️ Known Issues
- **SMTP Authentication**: Currently failing with `535: 5.7.8 Error: authentication failed: (reason unavailable)`
- **Possible Causes**:
  1. Password sync delay in Mailcow (Postfix/Dovecot may need time to sync)
  2. Mailcow configuration issue
  3. API key permissions (may need write access for password updates)

## Next Steps

1. **Wait for Password Sync**: Mailcow may need several minutes to sync passwords to Postfix/Dovecot
2. **Check Mailcow Logs**:**
   ```bash
   docker-compose logs postfix-mailcow | grep glassdome-ai
   docker-compose logs dovecot-mailcow | grep glassdome-ai
   ```
3. **Manual Password Set**: Try setting password manually in Mailcow UI to trigger sync
4. **Check API Key Permissions**: Verify API key has write access for mailbox operations

## Usage

Once SMTP authentication is working, the mailbox can be used for:
- Sending automated emails from the AI assistant
- Receiving emails (monitoring via IMAP)
- Integration with Overseer agent for notifications

## Test Email

When SMTP is working, test email can be sent to: `ntounix@gmail.com`

