# Rome Dual ISP Configuration

## Overview

Rome has two internet service providers with different source IP addresses:
- **Primary ISP**: 71.205.42.240 (WireGuard endpoint)
- **Secondary ISP**: 174.16.51.110 (current public IP)

This dual ISP setup explains the MTU fragmentation issues encountered.

## Issue

When Rome has two ISPs with different paths:
- Different paths may have different MTUs
- WireGuard may use the wrong source IP
- Traffic may take different routes, causing MTU mismatches
- TLS handshake packets fragment and fail

## Current Configuration

### WireGuard
- **Endpoint**: 71.205.42.240:41926 (primary ISP only)
- **MTU**: 1400 (fixed to match path MTU)
- **Listening Port**: 41926
- **Secondary ISP**: 174.16.51.110 (NOT configured as endpoint)

### Why Secondary ISP Isn't Configured
**WireGuard Limitation**: Each peer can only have ONE endpoint defined. Currently, only the primary ISP (71.205.42.240:41926) is configured. The secondary ISP (174.16.51.110) is not used for WireGuard connections.

**Important Note**: Since Rome is the one connecting TO mxwest/mxeast (Rome initiates connections), Rome can use EITHER ISP as its source. The endpoint configuration on mxwest/mxeast (71.205.42.240:41926) is where Rome is listening, but Rome's source ISP doesn't matter when Rome is connecting outbound.

**Current Behavior**:
- Rome's outbound IP: 174.16.51.110 (secondary ISP - used for general traffic)
- WireGuard endpoint: 71.205.42.240:41926 (primary ISP - where Rome listens)
- Rome connects TO mxwest/mxeast using either ISP (doesn't matter)
- If mxwest/mxeast connect TO Rome, they use 71.205.42.240:41926 (primary ISP only)
- If primary ISP fails and mxwest/mxeast try to connect, connection would fail

### Network Interfaces
- **ens18**: 192.168.3.99/24 (MTU 9000)
- **wg0**: 10.30.0.3/24 (MTU 1400)

### Routing
- Default gateway: 192.168.3.1
- Single default route (no load balancing visible)

## Solutions

### Option 1: Source-Based Routing (Recommended)

Configure WireGuard to use a specific source IP:

```bash
# On Rome, add source IP to WireGuard config
# Edit /etc/wireguard/wg0.conf
[Interface]
...
PostUp = ip route add 71.205.42.240/32 via 192.168.3.1 dev ens18 src <PRIMARY_ISP_IP>
PostUp = ip route add default via 192.168.3.1 dev ens18 table 100
PostUp = ip rule add from <PRIMARY_ISP_IP> table 100
```

### Option 2: Configure Both Endpoints (Not Recommended)

**Note**: WireGuard doesn't support multiple endpoints for the same peer. This approach would require:
- Two separate peer entries with the same public key (not standard)
- External failover script to switch between endpoints
- Or use different public keys (defeats purpose)

**Better approach**: Use source-based routing on Rome to ensure WireGuard traffic uses the correct ISP.

### Option 3: Use Policy-Based Routing

Configure routing policies to ensure WireGuard traffic uses the correct ISP:

```bash
# Create routing table for primary ISP
echo "200 primary_isp" >> /etc/iproute2/rt_tables

# Add route for primary ISP
ip route add default via <PRIMARY_GATEWAY> table primary_isp

# Add rule for WireGuard traffic
ip rule add from 10.30.0.3 table primary_isp
```

## MTU Considerations

With dual ISPs:
- **Path MTU may vary** depending on which ISP is used
- **Current fix**: Set WireGuard MTU to 1400 (lowest common MTU)
- **Better solution**: Use PMTUD (Path MTU Discovery) or set MTU per path

## Verification

Check which source IP is being used:

```bash
# On Rome
curl ifconfig.me
# Currently shows: 174.16.51.110 (secondary ISP - used for general traffic)

# Check WireGuard endpoint
wg show | grep endpoint
# Shows: 71.205.42.240:41926 (primary ISP - used for WireGuard)

# Check mxwest/mxeast connections
# Both connect to: 71.205.42.240:41926 (primary ISP only)
```

**Finding**: Rome uses secondary ISP (174.16.51.110) for general outbound traffic, but WireGuard is configured to use primary ISP (71.205.42.240) only. The secondary ISP endpoint (174.16.51.110:41926) is not configured because WireGuard only supports one endpoint per peer.

## Related Documentation

- [ROME_WIREGUARD_FIX.md](ROME_WIREGUARD_FIX.md) - WireGuard setup
- [MAIL_TLS_MTU_ISSUE.md](MAIL_TLS_MTU_ISSUE.md) - MTU fragmentation issue
- [EMAIL_NETWORK_ISSUE_DIAGNOSIS.md](EMAIL_NETWORK_ISSUE_DIAGNOSIS.md) - Network diagnosis

## Notes

- The dual ISP setup was not initially visible (only one interface on Rome)
- The router (192.168.3.1) likely handles the dual ISP configuration
- WireGuard endpoint (71.205.42.240) may need to be configured on the router
- Current MTU fix (1400) works but may not be optimal for both paths

