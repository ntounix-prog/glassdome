# API Permissions Required for SES Domain Email Pipeline

**Date:** November 24, 2024  
**Purpose:** Document all API permissions and access requirements for automated domain email setup

---

## Overview

This document lists all API permissions, credentials, and access requirements needed to automate the complete email domain setup pipeline using Amazon SES, Cloudflare DNS, Postfix relay configuration, and Mailcow mailbox creation.

---

## 1. Cloudflare API Access

### Required Permissions

**API Token Permissions:**
- **Zone DNS:Edit** - Create, update, delete DNS records
- **Zone:Read** - Read zone information and DNS records
- **Account:Read** - List zones in account (optional, for zone lookup)

### How to Create Cloudflare API Token

1. Log into Cloudflare dashboard: https://dash.cloudflare.com
2. Go to **My Profile** → **API Tokens**
3. Click **Create Token**
4. Select **Custom token** or use **Edit zone DNS** template
5. Configure permissions:
   - **Zone** → **DNS** → **Edit**
   - **Zone** → **Zone** → **Read**
   - **Account** → **Account** → **Read** (optional)
6. **Zone Resources:**
   - Select **Include** → **Specific zone**
   - Choose zones: `ntounix.com`, `403gear.com`, `xisx.com`, and new domain
   - OR select **All zones** (if managing multiple accounts)
7. Click **Continue to summary** → **Create Token**
8. **Copy token immediately** (only shown once)

### Token Format

- Stored in `.env` as: `CLOUDFLARE_API_TOKEN=your-token-here`
- Token format: Long alphanumeric string (e.g., `abc123def456...`)

### API Endpoints Used

- `GET /zones` - List zones
- `GET /zones/{zone_id}/dns_records` - List DNS records
- `POST /zones/{zone_id}/dns_records` - Create DNS record
- `PUT /zones/{zone_id}/dns_records/{record_id}` - Update DNS record
- `DELETE /zones/{zone_id}/dns_records/{record_id}` - Delete DNS record

### Testing Access

```bash
curl -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json"
```

---

## 2. Amazon SES API Access

### Required IAM Permissions

**IAM Policy JSON:**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ses:CreateEmailIdentity",
                "ses:GetIdentityVerificationAttributes",
                "ses:PutIdentityMailFromDomain",
                "ses:GetIdentityDkimAttributes",
                "ses:VerifyDomainIdentity",
                "ses:GetIdentityMailFromDomain",
                "ses:ListIdentities",
                "ses:DeleteEmailIdentity",
                "ses:GetAccount"
            ],
            "Resource": "*"
        }
    ]
}
```

### Additional Requirements

**SES Tenant/Account Association:**
- Domain must be associated with SES tenant/account: **xisx**
- This may require additional permissions or configuration in SES console
- May need to specify `ConfigurationSetName` or account-level settings

### How to Attach IAM Policy

1. AWS Console → **IAM** → **Users** or **Roles**
2. Select the user/role used for SES operations
3. Click **Add permissions** → **Attach policies directly**
4. Click **Create policy**
5. Select **JSON** tab
6. Paste the policy JSON above
7. Click **Next** → Name policy (e.g., `SESDomainManagement`)
8. Click **Create policy**
9. Go back to user/role → **Add permissions** → Attach the new policy

### AWS Credentials

**Required in `.env`:**
```bash
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=us-east-1
SES_REGIONS=us-east-1,us-west-2
SES_TENANT=xisx
```

**Note:** SES configuration must be done in **BOTH regions**:
- **us-east-1** (SES East) - for mxeast mail server
- **us-west-2** (SES West) - for mxwest mail server

### Testing Access

**Test SES East (us-east-1):**
```python
import boto3

ses_east = boto3.client('ses',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='us-east-1'
)

# Test: List identities
response = ses_east.list_identities()
print(f"SES East: {response}")
```

**Test SES West (us-west-2):**
```python
ses_west = boto3.client('ses',
    aws_access_key_id='YOUR_ACCESS_KEY',
    aws_secret_access_key='YOUR_SECRET_KEY',
    region_name='us-west-2'
)

# Test: List identities
response = ses_west.list_identities()
print(f"SES West: {response}")
```

**Note:** Permissions must work in **both regions**.

---

## 3. SSH Access to mxeast

### Required Access

**SSH Access:**
- Host: mxeast (AWS EC2 instance)
- Username: `ubuntu` (or appropriate user)
- Authentication: SSH key or password
- Sudo access: Required for Postfix configuration changes

### SSH Key Method (Recommended)

**Configuration:**
```bash
MXEAST_HOST=mxeast.xisx.org  # or IP address
MXEAST_USER=ubuntu
MXEAST_SSH_KEY=/path/to/private/key
```

**SSH Key Setup:**
1. Generate SSH key pair (if not exists):
   ```bash
   ssh-keygen -t rsa -b 4096 -f ~/.ssh/mxeast_key
   ```
2. Copy public key to mxeast:
   ```bash
   ssh-copy-id -i ~/.ssh/mxeast_key.pub ubuntu@mxeast.xisx.org
   ```
3. Test connection:
   ```bash
   ssh -i ~/.ssh/mxeast_key ubuntu@mxeast.xisx.org
   ```

### Password Method (Alternative)

**Configuration:**
```bash
MXEAST_HOST=mxeast.xisx.org
MXEAST_USER=ubuntu
MXEAST_PASSWORD=your-password
```

**Note:** Less secure, not recommended for production

### Sudo Access

**Required sudo permissions:**
- Read `/etc/postfix/relay_domains`
- Write `/etc/postfix/relay_domains`
- Read `/etc/postfix/transport`
- Write `/etc/postfix/transport`
- Execute `postmap` command
- Execute `postfix reload` command

**Sudoers Configuration (on mxeast):**
```bash
# Add to /etc/sudoers.d/postfix-config
ubuntu ALL=(ALL) NOPASSWD: /usr/sbin/postmap /etc/postfix/*
ubuntu ALL=(ALL) NOPASSWD: /usr/sbin/postfix reload
```

### Testing Access

```bash
ssh -i ~/.ssh/mxeast_key ubuntu@mxeast.xisx.org "sudo cat /etc/postfix/relay_domains"
```

---

## 4. Mailcow API Access

### Required Access

**API Authentication:**
- API URL: `https://192.168.3.69` (or `https://mail.xisx.org`)
- Authentication: X-API-Key header
- API Token: Obtained from Mailcow admin panel

### How to Get Mailcow API Token

1. Log into Mailcow admin panel: `https://mail.xisx.org`
2. Go to **Settings** → **API**
3. Click **Create Token** or **Add API Key**
4. Enter description (e.g., "Glassdome Domain Automation")
5. Select permissions:
   - **Domain management** (add domains)
   - **Mailbox management** (create mailboxes)
6. Click **Create**
7. **Copy token immediately** (only shown once)

### Token Format

- Stored in `.env` as: `MAIL_API=your-api-token-here`
- Used in header: `X-API-Key: your-api-token-here`

### API Endpoints Used

- `POST /api/v1/add/domain` - Add domain to Mailcow
- `POST /api/v1/add/mailbox` - Create mailbox
- `GET /api/v1/get/domain/all` - List all domains
- `GET /api/v1/get/mailbox/all` - List all mailboxes

### Testing Access

```bash
curl -X GET "https://192.168.3.69/api/v1/get/domain/all" \
  -H "X-API-Key: YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -k
```

**Note:** `-k` flag disables SSL verification (for self-signed certs)

---

## 5. Summary of Required Credentials

### Environment Variables (.env)

```bash
# Cloudflare
CLOUDFLARE_API_TOKEN=your-cloudflare-token

# AWS SES
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_DEFAULT_REGION=us-east-1
SES_TENANT=xisx

# mxeast SSH
MXEAST_HOST=mxeast.xisx.org
MXEAST_USER=ubuntu
MXEAST_SSH_KEY=/path/to/private/key
# OR
MXEAST_PASSWORD=your-password

# Mailcow
MAIL_API=your-mailcow-api-token
MAILCOW_API_URL=https://192.168.3.69
MAILCOW_DOMAIN=xisx.org  # Default domain
```

---

## 6. Validation Checklist

Before running the automation, verify:

- [ ] Cloudflare API token created with correct permissions
- [ ] Cloudflare API token tested (can list zones)
- [ ] AWS IAM policy attached to user/role
- [ ] AWS credentials tested (can list SES identities)
- [ ] SES tenant/account association verified (xisx)
- [ ] SSH access to mxeast working
- [ ] Sudo access on mxeast verified
- [ ] Can read/write Postfix configuration files on mxeast
- [ ] Mailcow API token created
- [ ] Mailcow API token tested (can list domains)
- [ ] All credentials added to `.env` file
- [ ] `.env` file is in `.gitignore` (not committed)

---

## 7. Security Best Practices

1. **API Tokens:**
   - Use least privilege principle (only required permissions)
   - Rotate tokens regularly
   - Never commit tokens to git
   - Use environment variables, not hardcoded values

2. **SSH Keys:**
   - Use SSH keys, not passwords
   - Protect private keys (chmod 600)
   - Use key passphrases
   - Rotate keys periodically

3. **AWS Credentials:**
   - Use IAM users/roles, not root credentials
   - Enable MFA where possible
   - Use separate credentials for automation
   - Monitor CloudTrail for API usage

4. **Mailcow API:**
   - Limit API token scope
   - Rotate tokens regularly
   - Monitor API usage logs

---

## 8. Troubleshooting

### Cloudflare API Issues

**Error: "Invalid API Token"**
- Verify token is correct
- Check token hasn't expired
- Verify token has correct permissions

**Error: "Zone not found"**
- Verify zone exists in Cloudflare account
- Check zone name spelling
- Verify token has access to zone

### AWS SES Issues

**Error: "Access Denied"**
- Verify IAM policy is attached
- Check policy permissions are correct
- Verify AWS credentials are valid
- Check region is correct (us-east-1)

**Error: "Domain not associated with tenant"**
- Verify SES tenant/account configuration
- Check if domain needs manual association in SES console
- Verify ConfigurationSetName if required

### SSH Access Issues

**Error: "Permission denied"**
- Verify SSH key is correct
- Check key permissions (chmod 600)
- Verify user has sudo access
- Test SSH connection manually

**Error: "Cannot write to /etc/postfix/"**
- Verify sudo access
- Check file permissions
- Verify user is in sudoers

### Mailcow API Issues

**Error: "Unauthorized"**
- Verify API token is correct
- Check X-API-Key header format
- Verify token hasn't expired
- Check API URL is correct

---

## 9. Next Steps

1. **Create all API tokens and credentials**
2. **Add credentials to `.env` file**
3. **Test each API access individually**
4. **Run validation script: `scripts/test_email_domain_setup.py`**
5. **Proceed with domain setup automation**

---

*This document should be kept secure and not committed to git. Update as API requirements change.*

