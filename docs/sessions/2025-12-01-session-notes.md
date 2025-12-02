# Session Notes - December 1, 2025

## Version: 0.7.5

## Summary
Major session focused on AWS integration testing and platform stability fixes. Successfully completed end-to-end AWS deployment test including VPC creation, subnet configuration, security groups, and EC2 instance launch.

## Key Accomplishments

### 1. AWS Integration - WORKING ✅
- Full VPC deployment pipeline operational in us-west-2 (Oregon)
- Successfully created and cleaned up:
  - VPC with custom CIDR (10.100.0.0/16)
  - Public subnet with auto-assign public IP
  - Internet Gateway with proper routing
  - Security groups with SSH/ICMP rules
  - EC2 instance (t2.micro Ubuntu 22.04)
- IAM permissions finalized (ec2:* for simplicity, can be tightened later)

### 2. Platform Stability Fixes
- **CORS Bug Fixed**: `allow_credentials=True` with `allow_origins=["*"]` violates CORS spec
  - Browsers reject this combination
  - Fixed in `main.py` to disable credentials when using wildcard origins
- **Vite Proxy Fixed**: Was pointing to port 8011 instead of 8000
  - Updated `vite.config.js` to correct port
- **AWS Credentials**: Added to `/home/nomad/glassdome/.env` (were only in `~/.env`)

### 3. IAM Policy Management
- Created minified policy file: `deploy/aws/glassdome-iam-policy-mini.json` (1331 chars)
- Learned inline policy limit is 2048 chars TOTAL for all policies on a user
- Recommended approach: Use Customer Managed Policies (6144 char limit)
- Final working policy uses `ec2:*` for full EC2 access

## Files Modified
- `glassdome/core/config.py` - Version bump, CORS origin handling
- `glassdome/main.py` - CORS middleware fix for wildcard origins
- `frontend/vite.config.js` - Fixed proxy port 8011 → 8000
- `frontend/package.json` - Version bump
- `deploy/aws/glassdome-iam-policy-core.json` - Full IAM policy
- `deploy/aws/glassdome-iam-policy-mini.json` - Minified version

## Services Status (End of Session)
| Service | Status | Port |
|---------|--------|------|
| Backend (uvicorn) | ✅ Running | 8000 |
| Frontend (vite) | ✅ Running | 5174 |
| Redis | ✅ Running | 6379 |
| PostgreSQL | ✅ Running | 5432 (192.168.3.7) |
| AWS Integration | ✅ Configured | - |

## AWS Resources (us-west-2)
- `mx-west` instance: Running (i-056edbe6ff6cab2b8) - DO NOT DELETE
- Test resources: All cleaned up

## Tomorrow's Focus: Stability Testing
- [ ] Test backend resilience under load
- [ ] Verify services survive restarts
- [ ] Test frontend/backend reconnection
- [ ] Monitor for memory leaks in uvicorn
- [ ] Test AWS deployment from UI canvas
- [ ] Verify all dashboard indicators working

## Known Issues
- `dump_bash_state: command not found` - Cursor IDE artifact, harmless
- `HOT_SPARE_PROXMOX_INSTANCE` warning on startup - Non-fatal, config not set
- ELK stack runs on mooker (192.168.3.26), not this server

## Commands to Start Services
```bash
# Backend
cd /home/nomad/glassdome && source venv/bin/activate
uvicorn glassdome.main:app --host 0.0.0.0 --port 8000 &

# Frontend
cd /home/nomad/glassdome/frontend && npm run dev &
```

## Git Commit
- Branch: main
- Message: "v0.7.5: AWS integration working, CORS/proxy fixes, stability improvements"

