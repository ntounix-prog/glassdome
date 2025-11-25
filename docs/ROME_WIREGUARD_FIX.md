# Rome WireGuard Fix

## Issue (RESOLVED ✅)
WireGuard was not running on Rome (192.168.3.99), causing mail delivery failures from mxwest to mooker.

**Status**: Fixed - WireGuard is now running and mail delivery is working.

## Current Status
- **Rome**: WireGuard service is stopped
- **mxwest**: WireGuard is running and connected
- **mooker**: Running and listening on port 25
- **Problem**: No connectivity from mxwest → mooker because Rome's WireGuard is down

## Network Path
```
mxwest (10.30.0.1) 
  → WireGuard tunnel 
  → Rome (192.168.3.99) ← BROKEN HERE (WireGuard not running)
  → 10.30.0.3 
  → 192.168.3.99 
  → 192.168.3.1 
  → mooker (192.168.3.69)
```

## Fix Steps

### On Rome (192.168.3.99)

1. **SSH to Rome**:
   ```bash
   ssh nomad@192.168.3.99
   ```

2. **Check WireGuard config**:
   ```bash
   sudo ls -la /etc/wireguard/
   ```
   Look for config files (usually `wg0.conf` or similar)

3. **Start WireGuard**:
   ```bash
   # If config is wg0.conf:
   sudo systemctl start wg-quick@wg0
   
   # Or start manually:
   sudo wg-quick up wg0
   ```

4. **Enable on boot**:
   ```bash
   sudo systemctl enable wg-quick@wg0
   ```

5. **Verify it's running**:
   ```bash
   sudo wg show
   ip addr show wg0
   ```

6. **Check IP forwarding** (should be enabled):
   ```bash
   sudo sysctl net.ipv4.ip_forward
   # Should show: net.ipv4.ip_forward = 1
   # If not, enable it:
   sudo sysctl -w net.ipv4.ip_forward=1
   ```

## Verification

After starting WireGuard on Rome:

1. **From mxwest, test connectivity**:
   ```bash
   ping 192.168.3.69  # Should work
   telnet 192.168.3.69 25  # Should connect
   ```

2. **Check mail queue**:
   ```bash
   sudo postqueue -f  # Force queue flush
   ```

3. **Monitor mail delivery**:
   ```bash
   sudo tail -f /var/log/mail.log | grep mooker
   ```

## Expected Results

- ✅ mxwest can ping mooker (192.168.3.69)
- ✅ mxwest can connect to mooker port 25
- ✅ Mail queue on mxwest starts processing
- ✅ Mail delivery resumes

## Resolution (2024-11-24)

WireGuard was successfully started on Rome:
- Service started: `sudo systemctl start wg-quick@wg0`
- Enabled on boot: `sudo systemctl enable wg-quick@wg0`
- Rome WireGuard IP: 10.30.0.3
- Connectivity verified: mxwest → mooker working
- Mail queue processing: Messages being delivered

## Notes

- WireGuard config file location: `/etc/wireguard/`
- Service name: `wg-quick@wg0` (if config is `wg0.conf`)
- Rome IP: 192.168.3.99
- Rome username: nomad
- SSH key: `~/.ssh/rome_key` (on agentx)

## Related Documentation

- [EMAIL_NETWORK_ISSUE_DIAGNOSIS.md](EMAIL_NETWORK_ISSUE_DIAGNOSIS.md) - Full network diagnosis
- [TLS_TROUBLESHOOTING_MOOKER_MXWEST.md](TLS_TROUBLESHOOTING_MOOKER_MXWEST.md) - TLS configuration (secondary issue)

