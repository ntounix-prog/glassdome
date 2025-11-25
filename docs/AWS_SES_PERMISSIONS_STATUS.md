# AWS SES Permissions Status

**Date:** November 24, 2024  
**Status:** ❌ **PERMISSIONS MISSING**

---

## Current Status

### ✅ What's Working
- AWS credentials are configured in `.env`
- AWS Access Key ID: `AKIA6LJKJK...` (loaded successfully)
- AWS region: `us-east-1`
- boto3 library is installed and working
- Can connect to AWS API

### ❌ What's Missing
**All SES permissions are missing from the IAM user/role.**

**Tested Permissions (All Failed):**
- ❌ `ses:ListIdentities` - **ACCESS DENIED**
- ❌ `ses:GetIdentityVerificationAttributes` - **ACCESS DENIED**
- ❌ `ses:GetIdentityDkimAttributes` - **ACCESS DENIED**
- ⚠️  `ses:GetAccount` - **ACCESS DENIED** (optional)

**Untested Permissions (Likely Also Missing):**
- ❌ `ses:CreateEmailIdentity` - Not tested (would create resource)
- ❌ `ses:PutIdentityMailFromDomain` - Not tested
- ❌ `ses:GetIdentityMailFromDomain` - Not tested
- ❌ `ses:VerifyDomainIdentity` - Not tested
- ❌ `ses:DeleteEmailIdentity` - Not tested

---

## Required Action

### Step 1: Identify IAM User/Role

The AWS credentials in use need SES permissions attached. You need to:

1. **Find the IAM user or role** associated with access key `AKIA6LJKJK...`
   - AWS Console → IAM → Users
   - Or: AWS Console → IAM → Roles
   - Look for the user/role using this access key

### Step 2: Attach SES Policy

**Option A: Attach AWS Managed Policy (Easiest)**
1. Go to IAM → Users (or Roles) → Select the user/role
2. Click **Add permissions** → **Attach policies directly**
3. Search for: `AmazonSESFullAccess`
4. Select it and click **Add permissions**

**Note:** `AmazonSESFullAccess` gives full SES access. For more restrictive access, use Option B.

**Option B: Create Custom Policy (Recommended)**

1. Go to IAM → **Policies** → **Create policy**
2. Click **JSON** tab
3. Paste the following policy:

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

4. Click **Next**
5. Name the policy: `SESDomainManagement`
6. Description: "Allow domain email setup operations for SES"
7. Click **Create policy**
8. Go back to IAM → Users (or Roles) → Select the user/role
9. Click **Add permissions** → **Attach policies directly**
10. Search for: `SESDomainManagement`
11. Select it and click **Add permissions**

### Step 3: Verify Permissions (Both Regions)

After attaching the policy, wait 1-2 minutes for propagation, then test **both regions**:

```bash
cd /home/nomad/glassdome
source venv/bin/activate
python3 scripts/test_email_domain_setup.py
```

Or test manually for both regions:
```python
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Test SES East (us-east-1)
ses_east = boto3.client(
    'ses',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-east-1'
)

response_east = ses_east.list_identities()
print(f"✅ SES East: Found {len(response_east['Identities'])} identities")

# Test SES West (us-west-2)
ses_west = boto3.client(
    'ses',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name='us-west-2'
)

response_west = ses_west.list_identities()
print(f"✅ SES West: Found {len(response_west['Identities'])} identities")
```

**Important:** Permissions must work in **both regions** (us-east-1 and us-west-2).

---

## Additional Considerations

### SES Tenant/Account Association

The plan requires associating domains with the "xisx" tenant/account. This may require:

1. **Configuration Set** - If SES uses configuration sets for tenant isolation
2. **Account-level settings** - May need to verify SES account configuration
3. **Manual association** - May need to associate domain in SES console first

**Action:** After permissions are fixed, test creating a domain identity and check if tenant association is automatic or requires additional configuration.

### SES Account Status

Check if the SES account is:
- ✅ **Out of sandbox mode** - Can send to any email address
- ⚠️  **In sandbox mode** - Can only send to verified email addresses

**Check:** AWS Console → SES → Account dashboard

**If in sandbox:** Request production access:
1. AWS Console → SES → Account dashboard
2. Click **Request production access**
3. Fill out the form
4. Wait for approval (usually 24-48 hours)

---

## Summary

**Current Status:** ❌ **Cannot proceed** - SES permissions missing

**Required:** Attach SES IAM policy to the AWS user/role

**Next Steps:**
1. Attach `AmazonSESFullAccess` or custom `SESDomainManagement` policy
2. Wait 1-2 minutes for propagation
3. Re-run permission test
4. Verify tenant association works
5. Proceed with domain setup automation

---

*This document will be updated once permissions are fixed.*

