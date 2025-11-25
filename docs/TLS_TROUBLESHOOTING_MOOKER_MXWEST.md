# TLS Troubleshooting: Mooker (Mailcow) and mxwest Mail Delivery

## Problem Summary

After migrating mooker (Mailcow mail server) from VMware ESX to Proxmox, mail delivery from mxwest (AWS EC2 instance) to mooker began failing with TLS handshake errors. Mail was queuing on mxwest with errors like "Cannot start TLS: handshake failure".

## Root Cause Analysis

The issue was multi-faceted:

1. **Certificate Verification Mismatch**: mxwest was connecting to mooker by IP (192.168.3.69) but the certificate is only valid for the hostname (mail.xisx.org), causing certificate verification failures.

2. **High Proxmox Load**: Proxmox server had elevated load (3.3-3.6) which was contributing to TLS handshake timeouts.

3. **VMware-to-Proxmox Migration Issues**: Network path changes, VM adapter differences, or routing issues from the migration may have contributed.

## Servers Involved

- **mooker**: Mailcow mail server running on Proxmox (VM ID 102)
  - IP: 192.168.3.69
  - Hostname: mail.xisx.org
  - Location: Proxmox hypervisor

- **mxwest**: Postfix mail relay on AWS EC2
  - IP: 44.254.59.166
  - Location: AWS us-west-2 (Oregon)

## Configuration Changes Applied

### On mooker (Mailcow Postfix Container)

1. **Increased TLS Logging**:
   ```bash
   smtpd_tls_loglevel = 2
   ```
   - Changed from 1 to 2 for detailed TLS debugging

2. **Enabled TLS Session Cache**:
   ```bash
   smtpd_tls_session_cache_database = btree:${data_directory}/smtpd_scache
   ```
   - Improves TLS performance by caching sessions

3. **Increased STARTTLS Timeout**:
   ```bash
   smtpd_starttls_timeout = 600s
   ```
   - Changed from 300s to 600s to allow more time for handshake

4. **Improved ECDH Grade**:
   ```bash
   smtpd_tls_eecdh_grade = strong
   ```
   - Changed from `auto` to `strong` for better key exchange

5. **Aligned Cipher Suites**:
   ```bash
   smtpd_tls_ciphers = high
   smtpd_tls_mandatory_ciphers = high
   ```
   - Changed from `medium`/`high` mismatch to consistent `high`

6. **Configured CA Path**:
   ```bash
   smtpd_tls_CApath = /etc/ssl/certs
   ```
   - Ensures proper certificate chain validation

### On mxwest (Postfix)

1. **Disabled Certificate Verification**:
   ```bash
   smtp_tls_verify_cert_match = none
   ```
   - Allows TLS to work even when certificate doesn't match IP address

2. **Increased STARTTLS Timeout**:
   ```bash
   smtp_starttls_timeout = 300s
   ```
   - Changed from 60s to 300s to allow more time for handshake

3. **Updated TLS Policy**:
   ```bash
   # /etc/postfix/tls_policy
   mail.xisx.org may
   ```
   - Changed from `encrypt` to `may` (allows TLS but not strictly required)
   - Policy map: `smtp_tls_policy_maps = hash:/etc/postfix/tls_policy`

## Certificate Status

- **Certificate**: Valid Let's Encrypt certificate
- **CN**: mail.xisx.org
- **Expires**: Feb 3, 2026
- **Chain**: Complete (server + intermediate cert)
- **Issue**: Certificate only valid for hostname, not IP address

## Scripts Created

### `scripts/fix_mxwest_tls.sh`
Automated script to configure mxwest Postfix TLS settings:
- Creates/updates TLS policy map
- Disables certificate verification
- Updates Postfix configuration
- Reloads Postfix

### `scripts/monitor_mooker_tls.sh`
Monitoring script to watch mooker TLS connections in real-time.

### `scripts/test_tls_connection.sh`
Test script to verify TLS connectivity from mxwest.

## Current Status

As of troubleshooting session:
- ✅ TLS configuration changes applied on both servers
- ✅ Certificate verification disabled on mxwest
- ⚠️ TLS handshakes still timing out (likely due to high Proxmox load)
- ⚠️ Mail still queuing on mxwest

## Next Steps

1. **Reboot Proxmox** to clear high load (3.3-3.6 load average)
2. **Monitor mail queue** after reboot: `sudo postqueue -f` on mxwest
3. **Check TLS logs** on mooker for successful connections
4. **Verify mail delivery** is working

## Network Configuration

### mooker Network (Proxmox)
- **Bridge**: vmbr2
- **VLAN**: tag=2
- **MTU**: 9000 (jumbo frames on physical interface)
- **IP**: 192.168.3.69/24

### mxwest Network (AWS)
- **Public IP**: 44.254.59.166
- **Region**: us-west-2 (Oregon)

## Troubleshooting Commands

### Check mooker TLS logs:
```bash
docker logs mailcowdockerized-postfix-mailcow-1 --tail 50 | grep TLS
```

### Check mxwest mail queue:
```bash
sudo postqueue -p
sudo postqueue -f  # Force queue flush
```

### Test TLS connection:
```bash
openssl s_client -connect mail.xisx.org:25 -starttls smtp
```

### Check Proxmox load:
```bash
ssh root@10.0.0.1 "uptime"
```

## Files Modified

- `/etc/postfix/tls_policy` (mxwest)
- `/etc/postfix/main.cf` (mxwest)
- Mailcow Postfix container configuration (mooker)

## Related Documentation

- Mailcow TLS configuration
- Postfix TLS policy maps
- VMware to Proxmox migration notes

## Notes

- The high Proxmox load (3.3-3.6) is likely contributing to TLS handshake timeouts
- Certificate is valid and doesn't need renewal
- The issue started after VMware-to-Proxmox migration
- Network connectivity is working (ping successful), but TLS handshakes are timing out

