# Redis Vulnerable Server Deployment - Complete

**Date:** 2024-11-21  
**CVE:** CVE-2025-49844 (RediShell)  
**Status:** ✅ Deployed and Ready

## Deployment Summary

**Server Details:**
- **IP Address:** 192.168.3.207 (not name-resolvable)
- **Port:** 6379
- **Password:** glassdome123
- **Version:** Redis 8.2.1 (vulnerable)
- **Vulnerability:** Use-after-free in Redis embedded Lua parser

## Configuration

**Redis Config:**
- Lua scripting: Enabled (required for exploit)
- Protected mode: Disabled
- Password authentication: Enabled
- ACL: Default user has full permissions including scripting

**Network:**
- VLAN 2 (192.168.3.x network)
- DHCP assigned IP
- Not name-resolvable (use IP directly)

## Current Status

✅ **Redis 8.2.1 installed and running**  
✅ **Lua scripting enabled**  
✅ **Service configured and started**  
✅ **Ready for exploit development/testing**

## Next Steps

**For Exploit Development:**
1. Develop exploit code for CVE-2025-49844
2. Test against deployed server at 192.168.3.207:6379
3. Verify use-after-free vulnerability in Lua parser
4. Document exploit steps

**Connection Test:**
```bash
redis-cli -h 192.168.3.207 -p 6379 -a glassdome123 PING
redis-cli -h 192.168.3.207 -p 6379 -a glassdome123 EVAL "return 1" 0
redis-cli -h 192.168.3.207 -p 6379 -a glassdome123 INFO server | grep redis_version
```

## Notes

- Exploit code not yet developed (user will create)
- Server is intentionally vulnerable for evaluation
- Do not expose to untrusted networks
- Template 9000 now has DHCP and password configured for future deployments

