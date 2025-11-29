# Email Domain Setup Guide - End to End

**Last Updated:** November 29, 2025  
**Purpose:** Complete guide for setting up email for a new domain from scratch  
**Demo Ready:** Yes - use this document as the instruction set

---

## Overview

This guide covers the complete process of setting up email infrastructure for a new domain, including:

1. **SES Configuration** - AWS Simple Email Service for outbound email (both regions)
2. **DNS Configuration** - Cloudflare DNS records (MX, DKIM, SPF, DMARC)
3. **MX Server Configuration** - Postfix transport and relay on mxwest/mxeast
4. **Mailcow Configuration** - Domain and mailbox creation on mooker
5. **Testing** - Verify email flow works end-to-end

**Architecture:**
```
                    INBOUND EMAIL FLOW
┌──────────────────────────────────────────────────────────────┐
│  Internet → MX Records → mxwest/mxeast → Rome → Mooker      │
│                (port 25)            (WireGuard)  (Mailcow)   │
└──────────────────────────────────────────────────────────────┘

                    OUTBOUND EMAIL FLOW
┌──────────────────────────────────────────────────────────────┐
│  Mooker → mxwest:2525 → SES (us-west-2) → Internet          │
│  (Mailcow)  (internal)    (SMTP relay)                       │
└──────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

Before starting, ensure you have:

- [ ] Domain registered and nameservers pointed to Cloudflare
- [ ] Domain zone active in Cloudflare account
- [ ] AWS credentials with SES permissions (`glassdome-deploy` user)
- [ ] SSH access to mxwest (10.30.0.1), mxeast (10.30.0.2), and mooker (192.168.3.69)
- [ ] Cloudflare API token with DNS edit permissions

**Required Credentials:**

| Credential | Storage Location | Description |
|------------|------------------|-------------|
| AWS_ACCESS_KEY_ID | HashiCorp Vault: `glassdome/aws/access_key` | glassdome-deploy IAM user |
| AWS_SECRET_ACCESS_KEY | HashiCorp Vault: `glassdome/aws/secret_key` | glassdome-deploy IAM user |
| CLOUDFLARE_API_TOKEN | HashiCorp Vault: `glassdome/cloudflare/api_token` | Zone DNS edit permissions |

**Secrets Access:**
```bash
# Via Vault CLI
vault kv get glassdome/aws/access_key
vault kv get glassdome/cloudflare/api_token

# Via Glassdome CLI
glassdome secrets get aws_access_key_id
glassdome secrets get cloudflare_api_token
```

**Note:** All secrets are stored in HashiCorp Vault. Never commit credentials to git.
See `docs/SECRETS_MANAGEMENT.md` for full documentation.

**SSH Keys:**
```
~/.ssh/mxwest_key   - Access to mxwest (ubuntu@10.30.0.1)
~/.ssh/mxeast_key   - Access to mxeast (ubuntu@10.30.0.2)
~/.ssh/mooker_key   - Access to mooker (nomad@192.168.3.69)
```

---

## Step 1: Add Domain to SES (Both Regions)

SES must be configured in **BOTH** regions because:
- mxwest (Oregon) uses SES us-west-2
- mxeast (Virginia) uses SES us-east-1

### 1.1 Create Email Identity in SES West

```bash
export AWS_DEFAULT_REGION=us-west-2

# Create the email identity
aws sesv2 create-email-identity --email-identity example.com

# Get DKIM tokens
aws sesv2 get-email-identity --email-identity example.com \
    --query 'DkimAttributes.Tokens' --output text
```

**Expected Output:**
```
token1  token2  token3
```

Save these tokens - you'll need them for DNS.

### 1.2 Create Email Identity in SES East

```bash
export AWS_DEFAULT_REGION=us-east-1

# Create the email identity
aws sesv2 create-email-identity --email-identity example.com

# Get DKIM tokens
aws sesv2 get-email-identity --email-identity example.com \
    --query 'DkimAttributes.Tokens' --output text
```

**Note:** Each region generates different DKIM tokens. You need all 6 CNAMEs in DNS.

---

## Step 2: Configure DNS in Cloudflare

### 2.1 Get Zone ID

```bash
# Load token from Vault
CF_TOKEN=$(vault kv get -field=value glassdome/cloudflare/api_token)
# Or via Glassdome CLI
CF_TOKEN=$(glassdome secrets get cloudflare_api_token)

curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=example.com" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" | jq '.result[0].id'
```

### 2.2 Add MX Records

```bash
ZONE_ID="your-zone-id"

# Primary MX (mxwest)
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    --data '{
        "type": "MX",
        "name": "@",
        "content": "mxwest.xisx.org",
        "priority": 10,
        "ttl": 300
    }'

# Secondary MX (mxeast)
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    --data '{
        "type": "MX",
        "name": "@",
        "content": "mxeast.xisx.org",
        "priority": 20,
        "ttl": 300
    }'
```

### 2.3 Add DKIM Records (6 CNAMEs)

For each DKIM token from both SES regions:

```bash
# SES West tokens (3)
for TOKEN in token1_west token2_west token3_west; do
    curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CF_TOKEN" \
        -H "Content-Type: application/json" \
        --data '{
            "type": "CNAME",
            "name": "'${TOKEN}'._domainkey",
            "content": "'${TOKEN}'.dkim.amazonses.com",
            "ttl": 300,
            "proxied": false
        }'
done

# SES East tokens (3)
for TOKEN in token1_east token2_east token3_east; do
    curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
        -H "Authorization: Bearer $CF_TOKEN" \
        -H "Content-Type: application/json" \
        --data '{
            "type": "CNAME",
            "name": "'${TOKEN}'._domainkey",
            "content": "'${TOKEN}'.dkim.amazonses.com",
            "ttl": 300,
            "proxied": false
        }'
done
```

### 2.4 Add SPF Record

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    --data '{
        "type": "TXT",
        "name": "@",
        "content": "v=spf1 include:amazonses.com include:_spf.mx.cloudflare.net ~all",
        "ttl": 300
    }'
```

### 2.5 Add DMARC Record

```bash
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
    -H "Authorization: Bearer $CF_TOKEN" \
    -H "Content-Type: application/json" \
    --data '{
        "type": "TXT",
        "name": "_dmarc",
        "content": "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com",
        "ttl": 300
    }'
```

### 2.6 Verify DNS Propagation

```bash
# Check MX records
dig +short MX example.com

# Check DKIM (one record)
dig +short CNAME token1._domainkey.example.com

# Check SPF
dig +short TXT example.com | grep spf
```

---

## Step 3: Wait for SES Verification

SES automatically verifies DKIM once DNS records propagate (typically 1-5 minutes).

### 3.1 Check Verification Status

```bash
# Check SES West
AWS_DEFAULT_REGION=us-west-2 aws sesv2 get-email-identity \
    --email-identity example.com \
    --query '{Status: DkimAttributes.Status, Verified: VerifiedForSendingStatus}'

# Check SES East
AWS_DEFAULT_REGION=us-east-1 aws sesv2 get-email-identity \
    --email-identity example.com \
    --query '{Status: DkimAttributes.Status, Verified: VerifiedForSendingStatus}'
```

**Expected Output (when verified):**
```json
{
    "Status": "SUCCESS",
    "Verified": true
}
```

---

## Step 4: Configure MX Servers

Both mxwest and mxeast need to know about the new domain.

### 4.1 Configure mxwest

```bash
ssh -i ~/.ssh/mxwest_key ubuntu@10.30.0.1

# Add to transport (route to mooker)
echo "example.com               smtp:[192.168.3.69]:25" | sudo tee -a /etc/postfix/transport
sudo postmap /etc/postfix/transport

# Add to relay_domains
echo "example.com OK" | sudo tee -a /etc/postfix/relay_domains
sudo postmap /etc/postfix/relay_domains

# Reload Postfix
sudo postfix reload

# Verify
cat /etc/postfix/transport | grep example.com
```

### 4.2 Configure mxeast

```bash
ssh -i ~/.ssh/mxeast_key ubuntu@10.30.0.2

# Add to transport (route to mooker)
echo "example.com               smtp:[192.168.3.69]:25" | sudo tee -a /etc/postfix/transport
sudo postmap /etc/postfix/transport

# Add to relay_domains
echo "example.com OK" | sudo tee -a /etc/postfix/relay_domains
sudo postmap /etc/postfix/relay_domains

# Reload Postfix
sudo postfix reload

# Verify
cat /etc/postfix/transport | grep example.com
```

---

## Step 5: Configure Mailcow (mooker)

### 5.1 Add Domain to Mailcow

```bash
ssh -i ~/.ssh/mooker_key nomad@192.168.3.69

# Get database password
DBPASS=$(sudo grep "^DBPASS=" /opt/mailcow-dockerized/mailcow.conf | cut -d= -f2)

# Insert domain
sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -u mailcow -p${DBPASS} mailcow -e "
INSERT INTO domain (domain, description, aliases, mailboxes, defquota, maxquota, quota, relayhost, backupmx, gal, relay_all_recipients, relay_unknown_only, active)
VALUES ('example.com', 'Example Domain', 400, 10, 3072, 51200, 102400, '0', 0, 1, 0, 0, 1);
"

# Verify
sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -u mailcow -p${DBPASS} mailcow -e \
    "SELECT domain, active FROM domain WHERE domain='example.com';"
```

### 5.2 Create Mailboxes

```bash
# Get template attributes from existing mailbox
ATTRS=$(sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -u mailcow -p${DBPASS} mailcow -sN -e \
    "SELECT attributes FROM mailbox WHERE username='ntounix@ntounix.com';")

# Generate password hash
PASS_HASH=$(sudo docker exec mailcowdockerized-dovecot-mailcow-1 doveadm pw -s BLF-CRYPT -p "TempPassword123!")

# Create mailbox (e.g., user@example.com)
sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -u mailcow -p${DBPASS} mailcow -e "
INSERT INTO mailbox (username, password, name, local_part, domain, quota, attributes, custom_attributes, kind, active)
VALUES ('user@example.com', '${PASS_HASH}', 'User Name', 'user', 'example.com', 10737418240, '${ATTRS}', '{}', '', 1);
"

# Reload Dovecot
sudo docker exec mailcowdockerized-dovecot-mailcow-1 doveadm reload

# Verify mailbox lookup
sudo docker exec mailcowdockerized-postfix-mailcow-1 postmap -q "user@example.com" \
    mysql:/opt/postfix/conf/sql/mysql_virtual_mailbox_maps.cf
```

**Expected Output:**
```
maildir:/var/vmail/example.com/user/
```

---

## Step 6: Test Email Flow

### 6.1 Send Test Email (Outbound)

```bash
ssh -i ~/.ssh/mooker_key nomad@192.168.3.69

# Send test email via Mailcow
sudo docker exec mailcowdockerized-postfix-mailcow-1 bash -c '
echo "Subject: Test from example.com
From: user@example.com
To: test@gmail.com
Content-Type: text/plain

This is a test email from the new domain.
Sent at: $(date)
" | /usr/sbin/sendmail -t -f user@example.com
'

# Check logs
sleep 5
sudo docker logs mailcowdockerized-postfix-mailcow-1 2>&1 | tail -10
```

### 6.2 Check mxwest Delivery

```bash
ssh -i ~/.ssh/mxwest_key ubuntu@10.30.0.1

# Check for successful relay to SES
sudo tail -20 /var/log/mail.log | grep -E "(example.com|status=sent)"
```

**Expected log entry:**
```
status=sent (250 Ok 0101019ace2185f7-xxxxx)
```

### 6.3 Verify Inbound (Optional)

Send an email TO user@example.com from an external account and verify it arrives in Mailcow.

---

## Quick Reference: All DNS Records Needed

| Type | Name | Value | Priority |
|------|------|-------|----------|
| MX | @ | mxwest.xisx.org | 10 |
| MX | @ | mxeast.xisx.org | 20 |
| CNAME | {token1}._domainkey | {token1}.dkim.amazonses.com | - |
| CNAME | {token2}._domainkey | {token2}.dkim.amazonses.com | - |
| CNAME | {token3}._domainkey | {token3}.dkim.amazonses.com | - |
| CNAME | {token4}._domainkey | {token4}.dkim.amazonses.com | - |
| CNAME | {token5}._domainkey | {token5}.dkim.amazonses.com | - |
| CNAME | {token6}._domainkey | {token6}.dkim.amazonses.com | - |
| TXT | @ | v=spf1 include:amazonses.com include:_spf.mx.cloudflare.net ~all | - |
| TXT | _dmarc | v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com | - |

---

## Troubleshooting

### SES DKIM Not Verifying
```bash
# Check if CNAME records are propagated
for token in token1 token2 token3; do
    dig +short CNAME ${token}._domainkey.example.com
done
```

### Mailbox Not Found Error
```bash
# Check SQL lookup
sudo docker exec mailcowdockerized-postfix-mailcow-1 postmap -q "user@example.com" \
    mysql:/opt/postfix/conf/sql/mysql_virtual_mailbox_maps.cf

# If empty, check attributes field is not NULL
sudo docker exec mailcowdockerized-mysql-mailcow-1 mysql -u mailcow -p${DBPASS} mailcow -e \
    "SELECT username, attributes FROM mailbox WHERE username='user@example.com';"
```

### Email Stuck in Queue
```bash
# Check mxwest queue
ssh -i ~/.ssh/mxwest_key ubuntu@10.30.0.1 'mailq'

# Check mooker queue
ssh -i ~/.ssh/mooker_key nomad@192.168.3.69 \
    'sudo docker exec mailcowdockerized-postfix-mailcow-1 mailq'

# Force flush
ssh -i ~/.ssh/mxwest_key ubuntu@10.30.0.1 'sudo postqueue -f'
```

### SES Sending Errors
```bash
# Check SES sandbox status (if in sandbox, can only send to verified addresses)
aws ses get-account --region us-west-2

# Check sending statistics
aws ses get-send-statistics --region us-west-2
```

---

## Complete Domain Setup Checklist

- [ ] Domain nameservers pointed to Cloudflare
- [ ] Domain zone active in Cloudflare
- [ ] SES identity created in us-west-2
- [ ] SES identity created in us-east-1
- [ ] MX records added to Cloudflare (mxwest priority 10, mxeast priority 20)
- [ ] DKIM CNAMEs added (6 total - 3 from each SES region)
- [ ] SPF TXT record added
- [ ] DMARC TXT record added
- [ ] SES DKIM verified in us-west-2 (Status: SUCCESS)
- [ ] SES DKIM verified in us-east-1 (Status: SUCCESS)
- [ ] Transport added to mxwest (/etc/postfix/transport)
- [ ] Transport added to mxeast (/etc/postfix/transport)
- [ ] Relay domain added to mxwest (/etc/postfix/relay_domains)
- [ ] Relay domain added to mxeast (/etc/postfix/relay_domains)
- [ ] Domain added to Mailcow (mooker)
- [ ] Mailbox(es) created in Mailcow
- [ ] Test email sent successfully (outbound)
- [ ] Test email received successfully (inbound)

---

## Server Reference

| Server | IP | SSH Access | Role |
|--------|-----|------------|------|
| mxwest | 10.30.0.1 (WireGuard) | `ssh -i ~/.ssh/mxwest_key ubuntu@10.30.0.1` | MX relay (Oregon), SES West |
| mxeast | 10.30.0.2 (WireGuard) | `ssh -i ~/.ssh/mxeast_key ubuntu@10.30.0.2` | MX relay (Virginia), SES East |
| rome | 192.168.3.99 | `ssh -i ~/.ssh/rome_key nomad@192.168.3.99` | WireGuard hub, VPN gateway |
| mooker | 192.168.3.69 | `ssh -i ~/.ssh/mooker_key nomad@192.168.3.69` | Mailcow (IMAP/SMTP/Webmail) |

---

## Example: Domain Setup Session Log

A complete domain (403press.com) was set up using this exact process on Nov 29, 2025.

**Results:**
- SES verified in both regions (us-west-2 and us-east-1)
- All DNS records created in Cloudflare
- Transport configured on mxwest and mxeast
- Domain and mailboxes created in Mailcow
- Test email delivered successfully

**Session logs and DKIM tokens are stored in:**
- `docs/session_logs/` - Detailed session transcripts
- AWS SES Console - DKIM tokens for each domain
- Cloudflare Dashboard - DNS records

---

## Security Notes

1. **All credentials in HashiCorp Vault** - Never store secrets in code or `.env` files
2. **SSH keys** - Store in `~/.ssh/` with proper permissions (600)
3. **DKIM tokens** - Retrieve from AWS SES console per-domain, per-region
4. **API tokens** - Rotate periodically via Vault, use least-privilege permissions
5. **SES SMTP credentials** - Generated per-region, stored in Vault at `glassdome/ses/{region}/smtp`

**Vault Paths for Email Infrastructure:**
```
glassdome/
├── aws/
│   ├── access_key
│   └── secret_key
├── cloudflare/
│   └── api_token
├── ses/
│   ├── us-west-2/smtp    # mxwest SMTP credentials
│   └── us-east-1/smtp    # mxeast SMTP credentials
└── ssh/
    ├── mxwest_key
    ├── mxeast_key
    └── mooker_key
```

---

*Document maintained by Glassdome AI Agent*

