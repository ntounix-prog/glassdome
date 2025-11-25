# Incident #002: mxeast WireGuard Endpoint Configuration

**Date**: November 24, 2024  
**Status**: ✅ Resolved  
**Severity**: Medium  
**Related to**: INC-001 (Email delivery failure)  
**Resolution Time**: ~30 minutes

---

## Problem Statement

mxeast (secondary mail exchanger) needs the second WireGuard endpoint defined in its configuration, similar to what was done for mxwest during INC-001 resolution.

## Discovery

**Method**: Found mxeast information from Rome's WireGuard configuration
- **Public IP**: 52.86.226.84 (from Rome WireGuard peer endpoint)
- **WireGuard IP**: 10.30.0.2 or 10.30.0.5
- **Endpoint**: mxeast.xisx.org:51820
- **Location**: AWS us-east-1 (Virginia)
- **Public Key**: qougjzAuau/MTwbF+sxNIDSpJFLmswG+LO3LShiGtn4=

## Required Action

Add Rome's endpoint to mxeast WireGuard configuration:
```
Endpoint = 71.205.42.240:41926
```

This matches what was done for mxwest to ensure proper WireGuard connectivity.

## Current Status

- ✅ mxeast IP identified: 52.86.226.84
- ✅ WireGuard peer information retrieved from Rome
- ✅ SSH access obtained (ubuntu@52.86.226.84)
- ✅ WireGuard endpoint configuration completed
- ✅ Connectivity verified

## Access Requirements

1. **SSH Access**: Need key for ubuntu@52.86.226.84
2. **AWS Console**: For EC2 instance management and key association
3. **WireGuard Config**: `/etc/wireguard/wg0.conf` on mxeast

## Resolution Steps (Completed)

1. ✅ Generated SSH key for mxeast (`agentx-mxeast-access`)
2. ✅ Connected to mxeast (ubuntu@52.86.226.84)
3. ✅ Validated security (authorized keys, login history)
4. ✅ Edited WireGuard config: `/etc/wireguard/wg0.conf`
5. ✅ Added endpoint: `Endpoint = 71.205.42.240:41926` to Rome peer
6. ✅ Restarted WireGuard: `wg-quick down wg0 && wg-quick up wg0`
7. ✅ Verified connectivity to Rome (ping successful, handshake active)

## Security Validation

**Authorized SSH Keys** (3 total, all legitimate):
- `MX-GW-West` (RSA) - Gateway key
- `agentx-mxeast-access` (ED25519) - Our access key
- `emailserver` (RSA) - Email server key

**Login History**:
- All recent logins from Rome IPs (71.205.42.240, 174.16.51.110)
- No failed login attempts
- No unauthorized access detected

**System Users**:
- Only `ubuntu` and `root` (normal for AWS instance)
- `ubuntu` has sudo access (standard AWS configuration)

## Related Documentation

- [INCIDENT_001_RESOLUTION.md](session_logs/INCIDENT_001_RESOLUTION.md) - Similar fix for mxwest
- [ROME_WIREGUARD_FIX.md](ROME_WIREGUARD_FIX.md) - WireGuard configuration
- [ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md](ROOT_CAUSE_ANALYSIS_EMAIL_DELIVERY.md) - INC-001 details

## Verification Results

- ✅ WireGuard endpoint configured: `71.205.42.240:41926`
- ✅ Connectivity to Rome verified: ping successful (52-108ms latency)
- ✅ Latest handshake: Active (2 seconds ago)
- ✅ WireGuard status: Both peers connected
- ✅ Security check: No unauthorized access detected

## Configuration Applied

**Initial Issue**: Endpoint was accidentally added to both peers (Rome and bmt iphone).  
**Fix Applied**: Removed endpoint from bmt iphone peer (mobile device doesn't need static endpoint).

**Final Configuration**:
```ini
[Peer]
Endpoint = 71.205.42.240:41926
# Rome
PublicKey = 1XtuyH3SS4dIiWZvRPRYPTipk44cOVXCuivFGuNGcSA=
AllowedIPs = 10.30.0.3/32, 192.168.3.0/24

[Peer]
#bmt iphone
PublicKey = 51t6aG6QSRkI6zROZJyEG1N2vcQ6Fhn164qhxIopDlo=
AllowedIPs = 10.30.0.5/32
```

**Note**: This matches mxwest's pattern - only the Rome peer has a static endpoint. Mobile devices connect without static endpoints.

---

**Note**: mxeast is a secondary mail exchanger but still important for mail delivery redundancy. The endpoint configuration ensures reliable WireGuard connectivity to Rome, matching the configuration applied to mxwest during INC-001.

