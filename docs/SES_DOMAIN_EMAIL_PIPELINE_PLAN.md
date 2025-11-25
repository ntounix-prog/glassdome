# SES Domain Email Pipeline Automation Plan

**Date:** November 24, 2024  
**Purpose:** Automate complete email domain setup for new domains using Amazon SES and Cloudflare DNS  
**Target:** MVP demonstration on December 8, 2024

---

## Overview

Automate the complete email domain setup pipeline for a new domain using Amazon SES for outbound email delivery and Cloudflare for DNS management. This will match the configuration pattern of existing domains (ntounix.com, 403gear.com, xisx.com) and be ready for the 12/8 MVP demonstration.

**Assumptions:**
- Domain is already registered
- Nameservers are already set to Cloudflare
- Domain is added to Cloudflare account (zone exists)

---

## Phase 1: Research and Discovery

### 1.1 Query Existing Domain Configurations

**Objective:** Understand the exact DNS record pattern used for existing domains.

**Tasks:**
- Query Cloudflare API to retrieve DNS records for:
  - `ntounix.com`
  - `403gear.com`
  - `xisx.com`
- Document all TXT, CNAME, MX records related to email
- Identify DMARC, SPF, DKIM record patterns
- Note any custom MAIL FROM domain configurations

**Files to Create:**
- `docs/EXISTING_DOMAIN_DNS_ANALYSIS.md` - Analysis of existing domain DNS records
- `scripts/research/query_existing_domains.py` - Script to query Cloudflare for existing domains

**Cloudflare API Endpoints Needed:**
- `GET /zones/{zone_id}/dns_records` - List all DNS records for a zone
- `GET /zones` - List zones to find zone IDs

### 1.2 Research SES Domain Setup Process

**Objective:** Document the complete SES domain verification and configuration process.

**Tasks:**
- Research SES API operations for domain setup:
  - `CreateEmailIdentity` - Register domain in SES (with tenant association to "xisx")
  - `GetIdentityVerificationAttributes` - Get verification TXT record
  - `PutIdentityMailFromDomain` - Configure custom MAIL FROM domain
  - `GetIdentityDkimAttributes` - Get DKIM tokens/CNAME records
  - `VerifyDomainIdentity` - Alternative verification method
  - Tenant/account association (SES configuration for xisx tenant)
- Document required DNS records from SES:
  - Domain verification TXT record
  - DKIM CNAME records (3 tokens)
  - MAIL FROM domain MX record
  - MAIL FROM domain SPF TXT record
- Document MX records for inbound email:
  - MX records pointing to mxwest.xisx.org and mxeast.xisx.org
  - These are NOT through SES (inbound goes directly to mail servers)

**Files to Create:**
- `docs/SES_DOMAIN_SETUP_PROCESS.md` - Complete SES domain setup documentation
- `docs/SES_DNS_RECORDS_REFERENCE.md` - Reference for all SES DNS records

### 1.3 Identify Required API Permissions

**Objective:** Document exact API permissions needed for Cloudflare, AWS, and SSH access.

**Tasks:**
- Document Cloudflare API token permissions:
  - Zone DNS:Edit (to create/update DNS records)
  - Zone:Read (to read existing records)
  - Account:Read (to list zones)
- Document AWS IAM permissions:
  - `ses:CreateEmailIdentity`
  - `ses:GetIdentityVerificationAttributes`
  - `ses:PutIdentityMailFromDomain`
  - `ses:GetIdentityDkimAttributes`
  - `ses:VerifyDomainIdentity`
  - `ses:GetIdentityMailFromDomain`
  - `ses:ListIdentities`
  - Tenant/account association permissions (if separate)
- Document SSH access requirements:
  - SSH access to mxeast (AWS EC2)
  - Sudo access for Postfix configuration changes
  - Read access to /etc/postfix/ files
- Document Mailcow API requirements:
  - Domain creation API endpoint
  - Mailbox creation API endpoint
  - X-API-Key authentication

**Files to Create:**
- `docs/API_PERMISSIONS_REQUIRED.md` - Complete API permissions documentation

---

## Phase 2: Implementation

### 2.1 Create Cloudflare DNS Client

**Objective:** Build a Python client for Cloudflare DNS operations.

**File:** `glassdome/integrations/cloudflare_client.py`

**Features:**
- Authenticate with Cloudflare API token
- List zones (find zone by domain name)
- List DNS records for a zone
- Create DNS records (TXT, CNAME, MX)
- Update existing DNS records
- Delete DNS records (if needed)
- Handle rate limiting and errors

**Key Methods:**
```python
class CloudflareClient:
    def __init__(self, api_token: str)
    def get_zone_id(self, domain: str) -> str
    def list_dns_records(self, zone_id: str, record_type: str = None) -> List[Dict]
    def create_dns_record(self, zone_id: str, record_type: str, name: str, content: str, ttl: int = 3600) -> Dict
    def update_dns_record(self, zone_id: str, record_id: str, record_type: str, name: str, content: str) -> Dict
    def delete_dns_record(self, zone_id: str, record_id: str) -> bool
```

**Dependencies:**
- `requests` library
- Cloudflare API v4

**Configuration:**
- Add to `.env`: `CLOUDFLARE_API_TOKEN=your-token-here`

### 2.2 Create SES Domain Client

**Objective:** Build a Python client for Amazon SES domain operations supporting both regions.

**File:** `glassdome/integrations/ses_client.py`

**Features:**
- Authenticate with AWS credentials (boto3)
- Support multiple SES regions (us-east-1 and us-west-2)
- Create email identity (domain verification) with tenant association in both regions
- Associate domain with SES tenant/account (xisx) in both regions
- Get verification attributes (TXT record) from both regions
- Configure DKIM (Easy DKIM) in both regions
- Get DKIM tokens (CNAME records) from both regions
- Configure custom MAIL FROM domain in both regions
- Get MAIL FROM domain records (MX, SPF) from both regions
- Verify domain status in both regions
- Handle AWS errors and retries
- Synchronize configuration across regions

**Key Methods:**
```python
class SESClient:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, 
                 regions: List[str] = ["us-east-1", "us-west-2"], tenant: str = "xisx")
    def create_email_identity(self, domain: str, mail_from_domain: str = None, 
                             tenant: str = "xisx", regions: List[str] = None) -> Dict
    def create_email_identity_region(self, domain: str, region: str, 
                                     mail_from_domain: str = None, tenant: str = "xisx") -> Dict
    def associate_with_tenant(self, domain: str, tenant: str, region: str) -> Dict
    def get_verification_record(self, domain: str, region: str = None) -> Dict  # Returns TXT record
    def get_dkim_records(self, domain: str, region: str = None) -> List[Dict]  # Returns CNAME records
    def configure_mail_from_domain(self, domain: str, mail_from_domain: str, 
                                   region: str = None) -> Dict
    def get_mail_from_records(self, domain: str, mail_from_domain: str, 
                             region: str = None) -> Dict  # Returns MX and SPF
    def verify_domain_status(self, domain: str, region: str = None) -> str  # Returns verification status
    def verify_all_regions(self, domain: str) -> Dict  # Check status in all regions
```

**Dependencies:**
- `boto3` library
- AWS credentials from `.env`

**Configuration:**
- Uses existing `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from `.env`
- `SES_REGIONS` (default: ["us-east-1", "us-west-2"]) - Both SES East and SES West
- `SES_TENANT` (default: xisx) - for tenant association
- Note: SES configuration must be done in BOTH regions (matching mxwest and mxeast)

### 2.3 Create Postfix Relay Configuration Client

**Objective:** Build a client to configure Postfix relay domains on mxeast.

**File:** `glassdome/integrations/postfix_relay_client.py`

**Features:**
- SSH connection to mxeast (AWS EC2)
- Read existing Postfix configuration files
- Add domain to relay_domains
- Add domain to transport_maps
- Update /etc/postfix/relay_domains
- Update /etc/postfix/transport
- Reload Postfix configuration
- Match pattern from existing domains (ntounix.com, xisx.org)

**Key Methods:**
```python
class PostfixRelayClient:
    def __init__(self, host: str, username: str, ssh_key_path: str = None, password: str = None)
    def add_relay_domain(self, domain: str) -> Dict
    def add_transport_map(self, domain: str, destination: str = "mail.xisx.org") -> Dict
    def reload_postfix(self) -> Dict
    def verify_configuration(self, domain: str) -> Dict
```

**Configuration:**
- Add to `.env`: `MXEAST_HOST`, `MXEAST_USER`, `MXEAST_SSH_KEY` or `MXEAST_PASSWORD`

### 2.4 Create Domain Email Setup Orchestrator

**Objective:** Create the main automation script that orchestrates the entire process.

**File:** `scripts/email_domain_setup.py`

**Workflow:**
1. **Initialize Clients**
   - Create CloudflareClient with API token
   - Create SESClient with AWS credentials (tenant: xisx)
   - Create PostfixRelayClient for mxeast
   - Create MailcowClient for mooker

2. **SES Domain Registration**
   - Call `ses_client.create_email_identity(domain, tenant="xisx")`
   - Associate domain with xisx tenant/account
   - Wait for initial response
   - Get verification TXT record from SES

3. **Add Domain Verification Record**
   - Create TXT record in Cloudflare: `_amazonses.{domain}` with verification token
   - Wait for DNS propagation (optional check)

4. **Configure DKIM (Both Regions)**
   - Enable Easy DKIM in SES for both regions (if not automatic)
   - Get DKIM tokens from SES East (3 CNAME records)
   - Get DKIM tokens from SES West (3 CNAME records)
   - Note: DKIM tokens are region-specific, but DNS records can be the same
   - Create CNAME records in Cloudflare for each DKIM token from both regions
   - Verify DKIM is enabled in both regions

5. **Configure Custom MAIL FROM Domain (Both Regions)**
   - Set MAIL FROM domain (e.g., `mail.{domain}`) in both SES regions
   - Get MX record from SES (same for both regions)
   - Get SPF TXT record from SES (same for both regions)
   - Create MX record in Cloudflare for MAIL FROM domain
   - Create SPF TXT record in Cloudflare for MAIL FROM domain
   - Verify MAIL FROM domain is configured in both regions

6. **Configure MX Records for Inbound Email**
   - Create MX records pointing to mxwest.xisx.org (priority 10)
   - Create MX records pointing to mxeast.xisx.org (priority 20)
   - These are for INBOUND email (not through SES)

7. **Configure DMARC**
   - Create DMARC TXT record: `_dmarc.{domain}`
   - Policy: `v=DMARC1; p=none; rua=mailto:dmarc@{domain}`
   - (Match pattern from existing domains)

8. **Configure Postfix Relay on mxeast**
   - Add domain to relay_domains in /etc/postfix/relay_domains
   - Add domain to transport_maps in /etc/postfix/transport
   - Configure transport to mail.xisx.org (mooker)
   - Reload Postfix configuration
   - Match pattern from ntounix.com and xisx.org configurations

9. **Configure Mailcow Domain and Mailboxes**
   - Add domain to Mailcow via API
   - Create mailbox: brett@{domain}
   - Create mailbox: glassdome-ai@{domain}
   - Verify mailboxes are created

10. **Verify Configuration**
    - Check SES domain verification status in BOTH regions (us-east-1 and us-west-2)
    - Verify all DNS records exist in Cloudflare
    - Verify DKIM is enabled in both SES regions
    - Verify MAIL FROM domain is configured in both SES regions
    - Verify Postfix relay configuration on mxeast
    - Verify Mailcow domain and mailboxes
    - Optional: Send test email from both regions to verify delivery

**Command Line Interface:**
```bash
python scripts/email_domain_setup.py \
    --domain example.com \
    --mail-from mail.example.com \
    --dmarc-email dmarc@example.com \
    --ses-tenant xisx \
    --ses-regions us-east-1,us-west-2 \
    --mxwest mxwest.xisx.org \
    --mxeast mxeast.xisx.org \
    --mooker mail.xisx.org \
    --dry-run  # Optional: show what would be done
```

**Required Parameters:**
- `--domain`: New domain to configure
- `--mail-from`: MAIL FROM domain (default: mail.{domain})
- `--ses-tenant`: SES tenant/account (default: xisx)
- `--ses-regions`: SES regions (default: us-east-1,us-west-2) - BOTH required
- `--mxwest`: MX record for inbound (default: mxwest.xisx.org)
- `--mxeast`: MX record for inbound (default: mxeast.xisx.org)
- `--mooker`: Mailcow server (default: mail.xisx.org)

**Output:**
- JSON report of all operations
- List of DNS records created
- Verification status
- Any errors or warnings

### 2.4 Create Configuration Template

**Objective:** Create a template/configuration file for domain setup parameters.

**File:** `configs/email_domain_template.yaml`

**Structure:**
```yaml
domain: example.com
mail_from_domain: mail.example.com
dmarc:
  policy: none  # none, quarantine, reject
  rua: dmarc@example.com
  ruf: dmarc-forensics@example.com
  fo: 1
spf:
  include: amazonses.com
  # Additional SPF includes if needed
```

**Usage:**
- Load template for new domain
- Customize parameters
- Use in automation script

---

## Phase 3: Documentation

### 3.1 Create Setup Guide

**File:** `docs/SES_DOMAIN_AUTOMATION_GUIDE.md`

**Contents:**
- Overview of the automation system
- Prerequisites (domain registered, Cloudflare NS, API access)
- Step-by-step setup instructions
- API permission requirements
- Troubleshooting guide
- Examples for different scenarios

### 3.2 Create API Permissions Documentation

**File:** `docs/API_PERMISSIONS_REQUIRED.md`

**Contents:**
- Cloudflare API token setup
  - Required permissions (Zone DNS:Edit, Zone:Read)
  - How to create token
  - Token security best practices
- AWS IAM policy setup
  - Required SES permissions
  - IAM policy JSON
  - How to attach to user/role
- Testing API access

### 3.3 Create DNS Records Reference

**File:** `docs/SES_DNS_RECORDS_REFERENCE.md`

**Contents:**
- Complete list of DNS records needed
- Record types (TXT, CNAME, MX)
- Record names and values
- Examples from existing domains
- DMARC policy options

### 3.4 Create Comparison with Existing Domains

**File:** `docs/EXISTING_DOMAIN_DNS_ANALYSIS.md`

**Contents:**
- Analysis of ntounix.com DNS records
- Analysis of 403gear.com DNS records
- Analysis of xisx.com DNS records
- Common patterns identified
- Differences and variations
- Recommendations for new domains

### 3.5 Create Postfix Relay Configuration Guide

**File:** `docs/POSTFIX_RELAY_CONFIGURATION.md`

**Contents:**
- Postfix relay_domains configuration
- Postfix transport_maps configuration
- Examples from ntounix.com and xisx.org
- SSH access requirements for mxeast
- Configuration file locations (/etc/postfix/relay_domains, /etc/postfix/transport)
- Postfix reload procedures
- Validation steps

---

## Phase 4: Testing and Validation

### 4.1 Create Test Script

**File:** `scripts/test_email_domain_setup.py`

**Features:**
- Test Cloudflare API connectivity
- Test AWS SES API connectivity
- Validate API permissions
- Test DNS record creation (dry-run)
- Verify existing domain patterns

### 4.2 Create Validation Script

**File:** `scripts/validate_domain_email_setup.py`

**Features:**
- Check all required DNS records exist
- Verify DNS record values match SES requirements
- Check SES domain verification status
- Validate DMARC, SPF, DKIM configuration
- Generate validation report

---

## Implementation Files

### New Files to Create:

1. `glassdome/integrations/cloudflare_client.py` - Cloudflare DNS API client
2. `glassdome/integrations/ses_client.py` - Amazon SES API client (with tenant association)
3. `glassdome/integrations/postfix_relay_client.py` - Postfix relay configuration client for mxeast
4. `scripts/email_domain_setup.py` - Main automation orchestrator
5. `scripts/research/query_existing_domains.py` - Research existing domains
6. `scripts/research/query_postfix_config.py` - Query mxeast Postfix configuration
7. `scripts/test_email_domain_setup.py` - Test script
8. `scripts/validate_domain_email_setup.py` - Validation script
9. `configs/email_domain_template.yaml` - Configuration template
10. `docs/SES_DOMAIN_AUTOMATION_GUIDE.md` - User guide
11. `docs/API_PERMISSIONS_REQUIRED.md` - API permissions documentation
12. `docs/SES_DNS_RECORDS_REFERENCE.md` - DNS records reference
13. `docs/EXISTING_DOMAIN_DNS_ANALYSIS.md` - Existing domain analysis
14. `docs/SES_DOMAIN_SETUP_PROCESS.md` - SES setup process documentation
15. `docs/POSTFIX_RELAY_CONFIGURATION.md` - Postfix relay domain configuration guide

### Files to Modify:

1. `env.example` - Add Cloudflare API token, mxeast SSH credentials, SES tenant
2. `glassdome/core/config.py` - Add Cloudflare, mxeast, and SES tenant configuration settings
3. `glassdome/integrations/mailcow_client.py` - Add domain creation method if not present
4. `.gitignore` - Ensure API tokens and SSH keys are not committed

---

## API Permissions Required

### Cloudflare API Token

**Required Permissions:**
- **Zone DNS:Edit** - Create, update, delete DNS records
- **Zone:Read** - Read zone information and DNS records
- **Account:Read** - List zones in account (optional, for zone lookup)

**How to Create:**
1. Log into Cloudflare dashboard
2. Go to My Profile → API Tokens
3. Create Token → Custom token
4. Permissions: Zone → DNS → Edit, Zone → Zone → Read
5. Zone Resources: Include → Specific zone → Select zones or "All zones"

**Token Format:**
- Stored in `.env` as `CLOUDFLARE_API_TOKEN`

### AWS IAM Permissions

**Required IAM Policy:**
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
                "ses:DeleteEmailIdentity"
            ],
            "Resource": "*"
        }
    ]
}
```

**How to Attach:**
1. AWS Console → IAM → Users/Roles
2. Select user/role used for SES
3. Add permissions → Attach policies directly
4. Create custom policy with above JSON

---

## Workflow Summary

1. **Domain Prerequisites:**
   - Domain registered
   - Nameservers set to Cloudflare
   - Zone exists in Cloudflare account

2. **API Setup:**
   - Cloudflare API token created with required permissions
   - AWS IAM user/role with SES permissions configured
   - Credentials added to `.env`

3. **Automation Execution:**
   - Run `scripts/email_domain_setup.py --domain example.com`
   - Script orchestrates:
     - SES domain registration
     - DNS record creation in Cloudflare
     - Verification and validation

4. **Verification:**
   - Run validation script
   - Check SES console for verification status
   - Test email sending

---

## Success Criteria

- Domain verified in Amazon SES in BOTH regions:
  - SES East (us-east-1) - associated with xisx tenant
  - SES West (us-west-2) - associated with xisx tenant
- All DNS records created in Cloudflare:
  - SES verification TXT record (same for both regions)
  - DKIM CNAME records from both regions (6 total tokens, or combined if same)
  - MAIL FROM domain MX and SPF records (same for both regions)
  - MX records for inbound (mxwest.xisx.org, mxeast.xisx.org)
  - DMARC TXT record
- DKIM enabled in both SES regions
- MAIL FROM domain configured in both SES regions
- Postfix relay configured on mxeast:
  - Domain added to relay_domains
  - Domain added to transport_maps
  - Postfix reloaded successfully
- Mailcow domain and mailboxes created:
  - Domain added to Mailcow
  - brett@{domain} mailbox created
  - glassdome-ai@{domain} mailbox created
- DKIM, SPF, DMARC properly configured
- Domain matches pattern of existing domains (ntounix.com, xisx.org)
- Ready for 12/8 MVP demonstration
- Complete documentation provided
- API calls validated and tested

---

## Timeline

- **Phase 1 (Research):** 1-2 days
- **Phase 2 (Implementation):** 2-3 days
- **Phase 3 (Documentation):** 1 day
- **Phase 4 (Testing):** 1 day

**Total:** ~5-7 days

---

## Notes

- This assumes domain is already registered and Cloudflare nameservers are configured
- All DNS operations use Cloudflare API
- **SES operations must be done in BOTH regions:**
  - SES East (us-east-1) - for mxeast mail server
  - SES West (us-west-2) - for mxwest mail server
- All SES operations use boto3/SES API with tenant association (xisx) in both regions
- Inbound email goes directly to mxwest.xisx.org and mxeast.xisx.org (NOT through SES)
- Outbound email goes through Amazon SES (from both regions)
- Postfix relay configuration on mxeast matches pattern from ntounix.com and xisx.org
- Mailcow domain and mailboxes are created via Mailcow API
- Pattern matches existing domains (ntounix.com, 403gear.com, xisx.com)
- Comprehensive documentation for API permissions and setup process
- API calls will be validated during implementation
- Ready for MVP demonstration on 12/8

## First Test Pipeline Completion

After successful execution, the following will be complete:
1. Domain registered in SES (xisx tenant)
2. All DNS records configured in Cloudflare
3. Postfix relay configured on mxeast
4. Mailcow domain added
5. Two mailboxes created:
   - brett@{domain}
   - glassdome-ai@{domain}
6. Ready for email sending and receiving

