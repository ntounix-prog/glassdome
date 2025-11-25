# Mail TLS Handshake Timeout - MTU Fragmentation Issue

## Problem

Mail is queuing on mxwest because TLS handshakes are timing out when connecting to mooker (192.168.3.69).

## Root Cause

**MTU Fragmentation Issue**:
- Path MTU from mxwest to mooker is approximately **1400 bytes**
- TLS handshake packets (containing certificates) are larger than 1400 bytes
- Large packets get fragmented
- Fragments are lost or not properly reassembled
- TLS handshake times out on both sides

## Symptoms

### mxwest logs:
```
SSL_connect error to mail.xisx.org[192.168.3.69]:25: Connection timed out
SSL_connect:SSLv3/TLS write client hello
(no response received)
```

### mooker logs:
```
SSL_accept error from unknown[10.30.0.1]: Connection timed out
lost connection after STARTTLS from unknown[10.30.0.1]
```

### Network Path:
```
mxwest (10.30.0.1) 
  → WireGuard (MTU 8921)
  → Rome (192.168.3.99, WireGuard MTU 8920, ens18 MTU 9000)
  → mooker (192.168.3.69)
```

## Testing Results

1. **Ping MTU Test**:
   - 1400 byte packets: ✅ Success
   - 1500 byte packets: ❌ Timeout

2. **SMTP without TLS**:
   - ✅ Works (mooker accepts non-TLS: `smtpd_tls_security_level = may`)

3. **TLS Handshake**:
   - ❌ Times out on both sides
   - Handshake starts but doesn't complete

## Solutions

### Option 1: Reduce WireGuard MTU (Recommended)

Reduce WireGuard MTU to match path MTU (~1400 bytes):

**On mxwest:**
```bash
# Edit WireGuard config
sudo nano /etc/wireguard/wg0.conf
# Add or modify:
MTU = 1400

# Restart WireGuard
sudo wg-quick down wg0
sudo wg-quick up wg0
```

**On Rome:**
```bash
# Edit WireGuard config
sudo nano /etc/wireguard/wg0.conf
# Add or modify:
MTU = 1400

# Restart WireGuard
sudo systemctl restart wg-quick@wg0
```

### Option 2: TCP MSS Clamping

Configure TCP MSS clamping on routers to prevent fragmentation:

```bash
# On Rome (if acting as router)
sudo iptables -t mangle -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1360
```

### Option 3: Fix Path MTU Discovery

Ensure PMTUD works correctly through the entire path:
- Check for firewalls blocking ICMP "Packet Too Big" messages
- Verify routers support PMTUD

### Option 4: Temporary Workaround

Disable TLS for mail.xisx.org (not recommended for production):

```bash
# On mxwest
echo "mail.xisx.org none" | sudo tee /etc/postfix/tls_policy
sudo postmap /etc/postfix/tls_policy
sudo postfix reload
```

**Note**: mooker allows non-TLS connections (`smtpd_tls_security_level = may`), so mail will work without TLS, but this is not secure.

## Current Status

- ✅ Network connectivity: Working
- ✅ SMTP without TLS: Working
- ❌ TLS handshake: Timing out due to MTU fragmentation
- ⚠️ Mail queue: Stuck (waiting for TLS handshake to complete)

## Next Steps

1. **Reduce WireGuard MTU** on both mxwest and Rome to ~1400 bytes
2. **Test TLS handshake** after MTU change
3. **Verify mail delivery** resumes
4. **Re-enable TLS** if it was disabled

## Related Documentation

- [ROME_WIREGUARD_FIX.md](ROME_WIREGUARD_FIX.md) - WireGuard setup
- [EMAIL_NETWORK_ISSUE_DIAGNOSIS.md](EMAIL_NETWORK_ISSUE_DIAGNOSIS.md) - Network connectivity issues
- [TLS_TROUBLESHOOTING_MOOKER_MXWEST.md](TLS_TROUBLESHOOTING_MOOKER_MXWEST.md) - TLS configuration

