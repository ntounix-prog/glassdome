# AWS IAM Setup for Glassdome

**TL;DR**: Create user with **programmatic access only** (no console), attach EC2 permissions.

---

## Quick Answer

### Does Glassdome User Need Console Access?

**NO!** ❌

- ✅ **Programmatic access** (API keys) - YES
- ❌ **Console access** (web UI) - NO
- ❌ **Password** - NO

**This is MORE secure!** The user can only do what the API keys allow, and can't log into the AWS console.

---

## Step-by-Step: Create Dedicated User

### Step 1: Go to IAM Console

https://console.aws.amazon.com/iam/home#/users

(You need to be logged in with admin/root account to create users)

### Step 2: Create User

Click **"Create user"** button (top right)

### Step 3: User Details

```
User name: glassdome-deploy
```

**Access type** (depends on AWS console version):

#### New AWS Console (2023+):
- ✅ **Provide user access to the AWS Management Console** - UNCHECK THIS
- Or select: **"I want to create an IAM user"**
- Then: **"Custom password"** - LEAVE BLANK
- Select: **"Users must create a new password at next sign-in"** - UNCHECK

**Result**: User has NO console access (what we want!)

#### Old AWS Console:
- ✅ **Access type**: CHECK "Programmatic access"
- ❌ **Access type**: UNCHECK "AWS Management Console access"

### Step 4: Set Permissions

Choose: **"Attach policies directly"**

#### Option A: Quick & Easy (for testing)

Search for and select:
- ✅ **AmazonEC2FullAccess** (managed policy)

**Pros**: Simple, works immediately  
**Cons**: More permissions than strictly needed

#### Option B: Minimal Permissions (recommended for production)

Click **"Create policy"** → **JSON** tab → Paste this:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "GlassdomeEC2Management",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:RebootInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceStatus",
        "ec2:DescribeImages",
        "ec2:DescribeKeyPairs",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "ec2:DescribeAvailabilityZones",
        "ec2:CreateSecurityGroup",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:DeleteSecurityGroup",
        "ec2:CreateTags",
        "ec2:DescribeTags",
        "ec2:DescribeRegions"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Sid": "GlassdomeNetworkManagement",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpc",
        "ec2:CreateSubnet",
        "ec2:CreateInternetGateway",
        "ec2:AttachInternetGateway",
        "ec2:CreateRouteTable",
        "ec2:CreateRoute",
        "ec2:AssociateRouteTable"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    }
  ]
}
```

**Policy name**: `GlassdomeEC2Policy`

**Pros**: Least-privilege, secure, auditable  
**Cons**: Slightly more complex

### Step 5: Tags (Optional but Recommended)

Add tags for tracking:
```
Key: Project     Value: Glassdome
Key: Purpose     Value: CyberRangeDeployment
Key: Owner       Value: your-name
```

### Step 6: Review and Create

Review everything, then click **"Create user"**

### Step 7: SAVE THE CREDENTIALS!

After creation, you'll see:
```
Access key ID:     AKIA...
Secret access key: (show button to reveal)
```

**⚠️ CRITICAL**: Copy BOTH values NOW!

The secret access key is **only shown once**. If you lose it, you'll need to create new keys.

---

## What Permissions Does Glassdome Need?

### Core Permissions (Required)

| Permission | Why Needed |
|-----------|------------|
| `ec2:RunInstances` | Create new VMs |
| `ec2:TerminateInstances` | Delete VMs |
| `ec2:StartInstances` | Start stopped VMs |
| `ec2:StopInstances` | Stop running VMs |
| `ec2:DescribeInstances` | Get VM status, IP addresses |
| `ec2:DescribeImages` | Look up Ubuntu AMIs |
| `ec2:CreateSecurityGroup` | Create firewall rules |
| `ec2:AuthorizeSecurityGroupIngress` | Allow SSH access |
| `ec2:CreateTags` | Tag resources for tracking |

### Network Permissions (Optional, Phase 2)

| Permission | Why Needed |
|-----------|------------|
| `ec2:CreateVpc` | Create isolated networks |
| `ec2:CreateSubnet` | Create network segments |
| `ec2:DescribeVpcs` | List available networks |
| `ec2:DescribeSubnets` | List available subnets |

### What Glassdome Does NOT Need

| Permission | Why NOT Needed |
|-----------|----------------|
| `iam:*` | No IAM role management needed |
| `s3:*` | No S3 storage needed (yet) |
| `rds:*` | No databases needed |
| `lambda:*` | No serverless functions |
| `*:*` | Never give full access! |

---

## Add Credentials to .env

Once you have the keys, add them to `/home/nomad/glassdome/.env`:

```bash
# AWS Configuration
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_REGION=us-east-1
```

**Verify**:
```bash
cd /home/nomad/glassdome
source venv/bin/activate
python -c "from glassdome.core.config import settings; print('AWS configured!' if settings.aws_access_key_id else 'AWS not configured')"
```

---

## Security Best Practices

### ✅ DO

1. **Dedicated User**: Create separate user for Glassdome (you're doing this! ✅)
2. **Programmatic Only**: No console access (you're doing this! ✅)
3. **Minimal Permissions**: Use least-privilege policy
4. **Tag Resources**: Tag all instances with "glassdome"
5. **Rotate Keys**: Rotate access keys every 90 days
6. **Monitor Usage**: Use CloudTrail to audit API calls
7. **Secure .env**: Never commit .env to git (already in .gitignore)

### ❌ DON'T

1. **Don't Use Root**: Never use root account credentials
2. **Don't Over-Permit**: Avoid wildcard (*) permissions when possible
3. **Don't Share Keys**: Each deployment should have unique keys
4. **Don't Hardcode**: Never hardcode keys in source code
5. **Don't Expose**: Don't push keys to GitHub/GitLab
6. **Don't Forget Cleanup**: Always terminate test instances

---

## Testing After Setup

### Quick Test (from your machine)

```bash
cd /home/nomad/glassdome
source venv/bin/activate

python -c "
import boto3
from glassdome.core.config import settings

try:
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region
    )
    
    # Test: List regions (requires minimal permissions)
    regions = ec2.describe_regions()
    print('✅ AWS credentials working!')
    print(f'✅ Can access {len(regions[\"Regions\"])} regions')
    
    # Test: List instances in us-east-1
    instances = ec2.describe_instances()
    print(f'✅ Permissions look good!')
    
except Exception as e:
    print(f'❌ Error: {e}')
    print('Check your credentials in .env')
"
```

Expected output:
```
✅ AWS credentials working!
✅ Can access 16 regions
✅ Permissions look good!
```

---

## What Happens with These Credentials

### Glassdome Will:

1. **Create EC2 instances** (VMs) in us-east-1
2. **Create security groups** for SSH access
3. **Tag resources** with "glassdome" for tracking
4. **Look up Ubuntu AMIs** (no downloads, AWS provides them)
5. **Manage instance lifecycle** (start, stop, terminate)
6. **Read IP addresses** for SSH access

### Glassdome Will NOT:

1. ❌ Access your existing resources (unless tagged "glassdome")
2. ❌ Modify other users or permissions
3. ❌ Create IAM roles or policies
4. ❌ Access S3, RDS, or other services
5. ❌ Deploy outside us-east-1 (unless configured)

---

## Cost Control

### Adding Budget Alerts (Recommended)

1. Go to: https://console.aws.amazon.com/billing/home#/budgets
2. Click **"Create budget"**
3. Select **"Use a template"** → **"Monthly cost budget"**
4. Budget name: `GlassdomeMonthly`
5. Budget amount: `$10` (or your preference)
6. Email: your-email@example.com
7. Click **"Create budget"**

You'll get alerts when spending approaches the limit!

### Tagging for Cost Tracking

All Glassdome instances are tagged with:
```
Project: glassdome
ManagedBy: glassdome-platform
```

View costs by tag in Cost Explorer:
https://console.aws.amazon.com/cost-management/home#/tags

---

## Auditing

### View API Calls (CloudTrail)

See what the Glassdome user is doing:

1. Go to: https://console.aws.amazon.com/cloudtrail/
2. Click **"Event history"**
3. Filter by:
   - **User name**: glassdome-deploy
   - **Time range**: Last hour / Last day

You'll see all EC2 API calls!

---

## Troubleshooting

### Error: "AuthFailure"

**Cause**: Invalid credentials

**Fix**:
- Check .env file has correct keys
- Verify no extra spaces in keys
- Ensure keys are from the correct AWS account

### Error: "UnauthorizedOperation"

**Cause**: Missing permissions

**Fix**:
- Add missing permission to IAM policy
- Or use `AmazonEC2FullAccess` for testing

### Error: "You are not authorized to perform this operation"

**Cause**: Region restriction or permission issue

**Fix**:
- Check policy allows operations in `us-east-1`
- Verify policy is attached to user

---

## Summary

### What You're Doing (Perfect! ✅)

1. ✅ Creating dedicated user (`glassdome-deploy`)
2. ✅ Programmatic access only (no console)
3. ✅ Scoped permissions (EC2 only)

### What I Need From You

Just the two keys:
```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

### What I'll Build

Complete AWS integration in ~1 hour:
- ✅ Platform abstraction
- ✅ Auto AMI lookup
- ✅ Security group management
- ✅ Cloud-init support
- ✅ Full VM lifecycle

---

**Ready to create the user and get those keys?** 🚀

