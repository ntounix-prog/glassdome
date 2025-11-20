# Azure Quick Setup - Service Principal

**Goal**: Get Azure credentials in 5 minutes, start deploying!

**Time Sensitive**: Use those $200 credits wisely!

---

## Quick Steps (5 minutes)

### 1. Go to Azure Portal
https://portal.azure.com

### 2. Open Cloud Shell (Top Right)
Click the `>_` icon (Cloud Shell)

### 3. Run This Command
```bash
az ad sp create-for-rbac \
  --name glassdome-deploy \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)
```

### 4. Copy the Output
```json
{
  "appId": "12345678-1234-1234-1234-123456789abc",
  "displayName": "glassdome-deploy",
  "password": "your-secret-here",
  "tenant": "87654321-4321-4321-4321-abcdefghijkl"
}
```

### 5. Get Your Subscription ID
```bash
az account show --query id -o tsv
```

---

## Add to .env

```bash
# Azure Configuration
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id-from-json
AZURE_CLIENT_ID=appId-from-json
AZURE_CLIENT_SECRET=password-from-json
AZURE_REGION=eastus
AZURE_RESOURCE_GROUP=glassdome-rg
```

---

## What These Mean

| Field | What It Is | Example |
|-------|-----------|---------|
| Subscription ID | Your Azure account | `12345678-abcd-...` |
| Tenant ID | Your Azure AD tenant | `tenant` from JSON |
| Client ID | Service principal app ID | `appId` from JSON |
| Client Secret | Service principal password | `password` from JSON |
| Resource Group | Container for resources | `glassdome-rg` |

---

## Test It

```bash
cd /home/nomad/glassdome
source venv/bin/activate
python -c "
from glassdome.core.config import settings
print('Azure Config Check:')
print(f'Subscription: {settings.azure_subscription_id[:8]}...' if settings.azure_subscription_id else 'Missing')
print(f'Tenant: {settings.azure_tenant_id[:8]}...' if settings.azure_tenant_id else 'Missing')
print(f'Client ID: {settings.azure_client_id[:8]}...' if settings.azure_client_id else 'Missing')
print(f'Secret: {settings.azure_client_secret[:8]}...' if settings.azure_client_secret else 'Missing')
"
```

---

## Cost Tracking

### B1s Instance (Cheapest)
- **Cost**: $0.0104/hour (~$7.50/month)
- **Your Credits**: $200 / $0.0104 = ~19,200 hours of B1s!
- **13 Days**: 312 hours available
- **Max Instances**: Can run ~60 B1s instances 24/7 for 13 days!

**Bottom Line**: You have PLENTY of credits for testing! 🚀

---

## Regions Available

```
US:
- eastus (Virginia)
- westus2 (Washington)
- centralus (Iowa)

Europe:
- westeurope (Netherlands)
- northeurope (Ireland)
- uksouth (London)

Asia:
- southeastasia (Singapore)
- eastasia (Hong Kong)
```

---

## What I'll Build (Next 1-2 Hours)

1. ✅ AzureClient (implements PlatformClient)
2. ✅ Auto Ubuntu image lookup
3. ✅ Resource group management
4. ✅ Virtual network auto-creation
5. ✅ Network security group management
6. ✅ B1s instance support (cheapest!)
7. ✅ Cloud-init integration
8. ✅ Test script

**Then**: Network architecture for multi-VM scenarios!

---

## Ready?

**Once you have the 4 credentials, just:**
1. Add them to `.env`
2. Tell me "ready"
3. I'll implement Azure in ~1 hour
4. Test with B1s (~$0.01 per test)
5. Move to network architecture!

**Fast track to 4-platform deployment!** 🚀

