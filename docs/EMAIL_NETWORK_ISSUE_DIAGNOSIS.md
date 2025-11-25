# Email Network Connectivity Issue: mxwest to mooker

## Problem Summary

After migrating mooker (Mailcow) from VMware ESX to Proxmox, mail delivery from mxwest (AWS EC2) to mooker completely stopped. **This is a network connectivity issue, not a TLS issue.**

## Current Status

- **mxwest cannot reach mooker at all**:
  - Ping to 192.168.3.69: **TIMEOUT**
  - TCP connection to port 25: **FAILED**
  - Connection times out before TLS even starts

- **mooker is running and listening**:
  - VM status: Running
  - Port 25: Listening (docker-proxy forwarding to Mailcow Postfix)
  - Network interface: ens18 with IP 192.168.3.69/24

## Network Configuration

### mooker (VM 102 on Proxmox)
- **IP**: 192.168.3.69/24
- **Interface**: ens18 (VirtIO)
- **Proxmox Bridge**: vmbr2
- **VLAN Tag**: 2
- **Gateway**: Unknown (needs verification)

### mxwest (AWS EC2)
- **Public IP**: 44.254.59.166
- **WireGuard Interface**: wg0
- **WireGuard IP**: 10.30.0.1
- **Route to 192.168.3.0/24**: Via wg0
- **WireGuard Peer**: 71.205.42.240:55920
- **Allowed IPs in tunnel**: 10.30.0.0/24, 192.168.3.0/24

### Proxmox Network
- **vmbr2**: VLAN-aware bridge (bridge-vids 2-4094)
- **vmbr2.211**: Subinterface for 192.168.211.26/24
- **Missing**: No vmbr2.2 subinterface for 192.168.3.0/24
- **VM 102**: Connected to vmbr2 with tag=2

## Root Cause Analysis

The issue is **WireGuard routing failure at Rome**:

1. **Rome (WireGuard peer) not routing to 10.30.0.3**:
   - **Rome**: WireGuard peer at 71.205.42.240 (endpoint)
   - **10.30.0.3**: Router/gateway in WireGuard network that should forward to 192.168.3.0/24
   - **Problem**: Rome is not routing traffic from mxwest (10.30.0.1) to 10.30.0.3
   - mxwest **CANNOT reach 10.30.0.3** - TIMEOUT
   - This is the **primary issue**

2. **Local network is working**:
   - Proxmox CAN reach 192.168.3.1 (gateway) ✅
   - mooker CAN reach 192.168.3.1 (gateway) ✅
   - mooker CAN reach 192.168.3.99 (WireGuard router) ✅
   - mooker has route: 10.30.0.0/24 via 192.168.3.99 ✅
   - Proxmox CANNOT ping mooker directly (expected - different VLAN)

3. **Network topology**:
   - **Expected path**: mxwest (10.30.0.1) → WireGuard → Rome (71.205.42.240) → 10.30.0.3 → 192.168.3.99 → 192.168.3.1 → mooker (192.168.3.69)
   - **Broken link**: Rome → 10.30.0.3 (Rome not forwarding traffic)
   - **Working links**: 192.168.3.99 → 192.168.3.1 → mooker (all working)

## What Changed After Migration

**Before (VMware ESX)**:
- mooker was on VMware network
- mxwest could reach it (likely different network path)

**After (Proxmox)**:
- mooker moved to Proxmox vmbr2 with VLAN tag 2
- Network path changed
- WireGuard tunnel may not be routing correctly to new location

## Diagnostic Commands

### From mxwest:
```bash
# Test connectivity
ping 192.168.3.69
telnet 192.168.3.69 25

# Check routing
ip route get 192.168.3.69
ip route | grep 192.168.3

# Check WireGuard
sudo wg show
```

### From mooker:
```bash
# Check network
ip addr show
ip route
ping 10.30.0.1  # Test to WireGuard network

# Check firewall
sudo iptables -L -n -v
```

### From Proxmox:
```bash
# Check VM network config
qm config 102 | grep net

# Check bridge configuration
ip addr show vmbr2
cat /etc/network/interfaces | grep vmbr2

# Test connectivity
ping 192.168.3.69
```

## Potential Solutions

### Option 1: Fix Rome Routing to 10.30.0.3 (PRIMARY FIX NEEDED)
**Rome (71.205.42.240) needs to route traffic to 10.30.0.3**:

- **On Rome (WireGuard peer at 71.205.42.240)**:
  ```bash
  # Check routing to 10.30.0.3
  ip route get 10.30.0.3
  
  # Check if 10.30.0.3 is reachable
  ping 10.30.0.3
  
  # Check routing table
  ip route | grep 10.30.0
  
  # Check WireGuard config
  sudo wg show
  
  # Check firewall rules
  sudo iptables -L -n -v | grep 10.30.0
  ```

- **Required fix on Rome**:
  - **Add route to 10.30.0.3**: `ip route add 10.30.0.3/32 via <next_hop>` or configure proper routing
  - **Or route 192.168.3.0/24 via 10.30.0.3**: `ip route add 192.168.3.0/24 via 10.30.0.3`
  - **Check firewall**: Ensure firewall allows traffic to/from 10.30.0.3
  - **Verify WireGuard forwarding**: Ensure IP forwarding is enabled: `sysctl net.ipv4.ip_forward=1`

- **Why this fixes it**:
  - mxwest sends traffic for 192.168.3.0/24 through WireGuard to Rome
  - Rome needs to forward this traffic to 10.30.0.3
  - 10.30.0.3 then routes to 192.168.3.99, which routes to 192.168.3.0/24
  - Without Rome → 10.30.0.3 routing, packets are dropped

### Option 2: Verify WireGuard Configuration
On mxwest, check if WireGuard is properly configured:
```bash
# Check WireGuard status
sudo wg show

# Check if tunnel is working
sudo wg show wg0

# Test WireGuard connectivity
ping 10.30.0.1  # Should work (local)
# ping 192.168.3.99  # Should work but doesn't
```

### Option 3: Check Gateway Configuration
Verify mooker's gateway:
```bash
# On mooker
ip route | grep default
# Should show gateway for 192.168.3.0/24
```

### Option 4: Firewall Rules
Check if any firewall is blocking:
- Proxmox firewall (currently disabled)
- mooker iptables (FORWARD chain policy is DROP)
- Network-level firewall between WireGuard and Proxmox

## Next Steps

1. **Fix Rome routing to 10.30.0.3** (PRIMARY ACTION):
   - Access Rome (71.205.42.240)
   - Add route: `ip route add 192.168.3.0/24 via 10.30.0.3`
   - Or ensure 10.30.0.3 is reachable and routing correctly
   - Verify IP forwarding is enabled
   - Check firewall rules allow traffic to 10.30.0.3

2. **Verify 10.30.0.3 configuration**:
   - Ensure 10.30.0.3 can reach 192.168.3.99
   - Check 10.30.0.3 routing table
   - Test connectivity: Rome → 10.30.0.3 → 192.168.3.99

3. **Test end-to-end connectivity**:
   - From mxwest: `ping 10.30.0.3` (should work after Rome fix)
   - From mxwest: `ping 192.168.3.69` (should work after Rome fix)
   - From mxwest: `telnet 192.168.3.69 25` (should work after Rome fix)

4. **Network topology (confirmed)**:
   - **Path**: mxwest (10.30.0.1) → WireGuard → Rome (71.205.42.240) → **10.30.0.3** → 192.168.3.99 → 192.168.3.1 → mooker (192.168.3.69)
   - **Broken at**: Rome → 10.30.0.3

## Related Documentation

- [TLS_TROUBLESHOOTING_MOOKER_MXWEST.md](TLS_TROUBLESHOOTING_MOOKER_MXWEST.md) - TLS configuration (secondary issue)
- [CURRENT_STATE.md](CURRENT_STATE.md) - Proxmox VLAN configuration notes

## Notes

- This is **NOT a TLS issue** - the connection fails before TLS handshake
- The problem started **immediately after VMware-to-Proxmox migration**
- Network path changed, routing needs to be reconfigured
- WireGuard tunnel is active (handshake 34 minutes ago) but routing is broken

