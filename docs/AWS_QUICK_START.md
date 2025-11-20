# AWS Quick Start - Minimal Implementation

**Goal**: Get AWS working in 1 hour with minimal complexity

---

## What You Need (3 Things)

### 1. AWS Access Key ID
### 2. AWS Secret Access Key  
### 3. AWS Region (already set: `us-east-1` ✅)

---

## How to Get AWS Credentials

### Step 1: Go to IAM Console
https://console.aws.amazon.com/iam/

### Step 2: Create Access Key
1. Click **Users** (left sidebar)
2. Click **your username**
3. Click **Security credentials** tab
4. Scroll to **Access keys** section
5. Click **Create access key**
6. Select use case: **Command Line Interface (CLI)**
7. Check the box acknowledging the recommendation
8. Click **Next**
9. (Optional) Add description: "Glassdome deployment"
10. Click **Create access key**

### Step 3: Copy Keys
```
Access key ID: AKIA... (20 characters)
Secret access key: ... (40 characters)
```

**⚠️ IMPORTANT**: Save the secret key NOW! You can't view it again!

### Step 4: Add to .env
```bash
# Add these lines to /home/nomad/glassdome/.env
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-1
```

---

## Implementation Strategy

### Phase 1: Minimal (1 hour) - THIS IS WHAT WE'LL DO

**Scope**:
- ✅ Use **default VPC** (every AWS account has one)
- ✅ Auto-create **security group** (SSH only)
- ✅ Auto-lookup **Ubuntu AMIs** (no manual IDs)
- ✅ Password auth via **cloud-init** (no key pairs needed)
- ✅ Single region: **us-east-1**
- ✅ Instance type: **t2.micro** (free tier eligible)

**What I'll implement**:
```python
# This is ALL the user needs to do:
from glassdome.platforms.aws_client import AWSClient

client = AWSClient(
    access_key_id=settings.aws_access_key_id,
    secret_access_key=settings.aws_secret_access_key,
    region='us-east-1'
)

# Deploy VM
vm = await client.create_vm({
    "name": "glassdome-test",
    "os_type": "ubuntu",
    "os_version": "22.04"
})

# Done! VM created with:
# - Ubuntu 22.04
# - SSH access (password: glassdome123)
# - Public IP assigned
# - Cloud-init configured
```

**Security approach**:
- Default VPC with internet gateway (standard AWS setup)
- Security group: Allow SSH (22) from 0.0.0.0/0
- No public S3 buckets
- No IAM roles (not needed for basic VMs)
- Instances tagged with "glassdome" for easy cleanup

**Cost**:
- t2.micro: FREE (750 hours/month on free tier)
- Storage: ~$1.60/month for 20GB
- **Total for demo**: ~$0.50 for 2-hour session

---

### Phase 2: Security Hardening (Add Later)

**When you're ready** (post-12/8 presentation), we can add:

1. **Dedicated VPC**
   - Isolated network per scenario
   - Private subnets for internal VMs
   - NAT gateway for outbound only

2. **Restricted Security Groups**
   - SSH only from specific IPs
   - Separate security groups per role (web, db, etc.)
   - No default 0.0.0.0/0 rules

3. **SSH Key Pairs**
   - Generate keypairs per deployment
   - Store private keys securely
   - Rotate keys regularly

4. **IAM Roles & Policies**
   - Least-privilege policies
   - Instance profiles for AWS API access
   - Service-specific roles

5. **Network Segmentation**
   - Multi-tier architecture
   - Public/private subnet split
   - Bastion hosts for access

6. **Encryption**
   - EBS volume encryption
   - Secrets Manager for passwords
   - KMS for key management

7. **Monitoring & Logging**
   - CloudWatch alarms
   - VPC Flow Logs
   - CloudTrail for API auditing

8. **Cost Controls**
   - Resource tagging for billing
   - Budget alerts
   - Auto-shutdown for inactive instances

---

## Why Start Minimal?

### For Your 12/8 Presentation

**What you need to demo**:
- ✅ Multi-platform deployment (Proxmox, ESXi, AWS)
- ✅ Platform abstraction working
- ✅ Same code, different clouds

**What you DON'T need to demo**:
- ❌ Enterprise security architecture
- ❌ Multi-VPC networking
- ❌ IAM complexity
- ❌ Cost optimization strategies

### You Already Have Security Where It Matters

**On-Prem (Proxmox/ESXi)**:
- Behind your firewall ✅
- Private network ✅
- Your physical security ✅

**For Demos**:
- Temporary instances ✅
- Auto-cleanup ✅
- Minimal attack surface ✅

### Enterprise Security Comes Later

**After 12/8**, when customers ask about production deployment:
- That's when we implement Phase 2
- That's when we talk about VPCs, IAM, etc.
- That's when we integrate with their existing AWS organization

**For now**: Get it working, prove the concept.

---

## Addressing Your Concerns

### "Security Wrappers"

**Question**: Do we need security groups, IAM policies, etc.?

**Phase 1 Answer**: 
- Security group: YES (I'll create it automatically)
- IAM policies: NO (not needed for basic EC2)
- VPC: Use default (already exists)

**Phase 2 Answer** (later):
- Custom VPC per scenario
- IAM roles for instance profiles
- Fine-grained security groups

### "Deployments"

**Question**: How do we handle complex deployments?

**Phase 1 Answer**:
- Single instance at a time
- One region (us-east-1)
- Standard Ubuntu AMIs

**Phase 2 Answer** (later):
- Multi-instance scenarios
- Multi-region support
- Custom AMIs with pre-baked configs

### "So Many Things to Consider"

**Answer**: Yes, AWS is complex! But we don't need it all at once.

**The Beauty of Platform Abstraction**:
```python
# This is the SAME code for Proxmox, ESXi, AND AWS:
agent = UbuntuInstallerAgent(platform_client)
result = await agent.run({
    "element_type": "ubuntu_vm",
    "config": {"name": "test-vm", "os_version": "22.04"}
})

# The platform client handles the platform-specific complexity
# User doesn't need to know about AMIs, VPCs, security groups, etc.
```

---

## What Happens Next

### Once You Provide Credentials

**I'll do this (1 hour)**:

1. ✅ Update `AWSClient` to inherit from `PlatformClient`
2. ✅ Implement `create_vm()` with:
   - AMI auto-lookup (latest Ubuntu 22.04)
   - Default VPC detection
   - Security group auto-creation (SSH only)
   - Cloud-init configuration
   - Public IP assignment
3. ✅ Implement `start_vm()`, `stop_vm()`, `delete_vm()`
4. ✅ Implement `get_vm_ip()` with proper waiting
5. ✅ Add status mapping to `VMStatus` enum
6. ✅ Test with `test_three_platforms.py`

**Result**:
```
✅ Proxmox - Working
✅ ESXi    - Working  
✅ AWS     - Working

Platform abstraction PROVEN across on-prem + cloud!
```

---

## Ready to Start?

### What I Need From You

**Just add to your `.env` file**:
```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
```

Then tell me you're ready, and I'll implement it!

---

## FAQ

### Q: Will this cost me money?

**A**: Minimal.
- t2.micro: FREE (750 hours/month free tier)
- For a 2-hour demo: ~$0.50 total
- I'll implement auto-cleanup to prevent runaway costs

### Q: Is it secure enough for demos?

**A**: Yes.
- Security group restricts to SSH only
- Instances tagged for easy identification
- No sensitive data in demo VMs
- Auto-cleanup after demos

### Q: Can I use my existing VPC?

**A**: Yes! (Phase 2)
- For Phase 1, we'll use default VPC (simpler)
- For Phase 2, we can use your custom VPC
- Just provide the VPC ID in config

### Q: What about other AWS services?

**A**: Not needed now.
- EC2 only for Phase 1
- Later we can add: EBS, ELB, RDS, etc.
- One step at a time!

### Q: What if I don't have an AWS account?

**A**: Create one!
- https://aws.amazon.com/free/
- 12 months of free tier
- Credit card required (won't be charged for t2.micro)

---

**Bottom Line**: Give me your AWS credentials, and I'll have it working in 1 hour! 🚀

