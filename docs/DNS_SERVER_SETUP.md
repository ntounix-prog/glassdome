# Technitium DNS Server Setup

**Created:** 2025-11-29  
**VM ID:** 118  
**Hostname:** dns-technitium  
**IP Address:** 192.168.3.10

## Overview

Technitium DNS Server provides centralized, authoritative DNS for all network segments. It runs on Ubuntu 22.04 via Docker.

## Access Credentials

**Credentials stored in HashiCorp Vault:**
```bash
# Retrieve credentials
vault kv get glassdome/dns_server
```

**Quick Reference (for emergencies only):**
| Item | Value |
|------|-------|
| VM IP | 192.168.3.10 |
| OS User | ubuntu |
| OS Password | (in Vault: `glassdome/dns_server`) |
| Web Interface | http://192.168.3.10:5380 |
| Admin User | admin |
| Admin Password | (in Vault: `glassdome/dns_server`) |

## Network Configuration

The DNS server is accessible from all network segments:

| Network | VLAN | Subnet | Purpose |
|---------|------|--------|---------|
| VM Network | 2 | 192.168.3.0/24 | VMs and servers |
| User Network | - | 192.168.2.0/24 | Client devices |
| Management | - | 192.168.215.0/24 | Proxmox management |
| SAN/Cluster 1 | 211 | 192.168.211.0/24 | Storage/migration |
| SAN/Cluster 2 | 212 | 192.168.212.0/24 | Storage/migration |

## Configured Zones

### Forward Zones

**lan.local** - Primary zone for all internal hosts:

| Hostname | IP Address |
|----------|------------|
| dns.lan.local | 192.168.3.10 |
| dns-technitium.lan.local | 192.168.3.10 |
| agentx.lan.local | 192.168.3.5 |
| glassdome-prod-app.lan.local | 192.168.3.6 |
| glassdome-prod-db.lan.local | 192.168.3.7 |
| vault.lan.local | 192.168.3.7 |
| app-403press.lan.local | 192.168.3.65 |
| pve01.lan.local | 192.168.215.78 |
| pve02.lan.local | 192.168.215.77 |

### Reverse Zones

- `3.168.192.in-addr.arpa` - Reverse DNS for 192.168.3.x
- `2.168.192.in-addr.arpa` - Reverse DNS for 192.168.2.x  
- `215.168.192.in-addr.arpa` - Reverse DNS for 192.168.215.x
- `211.168.192.in-addr.arpa` - Reverse DNS for 192.168.211.x
- `212.168.192.in-addr.arpa` - Reverse DNS for 192.168.212.x

## Upstream DNS (Forwarders)

- 8.8.8.8 (Google)
- 8.8.4.4 (Google)
- 1.1.1.1 (Cloudflare)

## Docker Management

```bash
# SSH into DNS server
ssh ubuntu@192.168.3.10

# Check container status
sudo docker ps

# View logs
sudo docker logs technitium-dns

# Restart DNS
sudo docker restart technitium-dns

# Stop DNS
sudo docker stop technitium-dns

# Start DNS
sudo docker start technitium-dns
```

## API Examples

```bash
# Login and get token
TOKEN=$(curl -s 'http://192.168.3.10:5380/api/user/login?user=admin&pass=PASSWORD' | grep -oP '"token":"\K[^"]+')

# Add A record
curl "http://192.168.3.10:5380/api/zones/records/add?token=$TOKEN&zone=lan.local&domain=newhost.lan.local&type=A&ipAddress=192.168.3.100&ttl=3600"

# List zones
curl "http://192.168.3.10:5380/api/zones/list?token=$TOKEN"

# Query records
curl "http://192.168.3.10:5380/api/zones/records/get?token=$TOKEN&zone=lan.local"
```

## Client Configuration

### Configure clients to use this DNS server:

**Linux (systemd-resolved):**
```bash
# Edit /etc/systemd/resolved.conf
[Resolve]
DNS=192.168.3.10
Domains=lan.local
```

**Linux (netplan):**
```yaml
network:
  ethernets:
    eth0:
      nameservers:
        addresses: [192.168.3.10]
        search: [lan.local]
```

**Ubiquiti/DHCP:**
Set DNS server option in DHCP settings to 192.168.3.10

## Testing

```bash
# Forward lookup
nslookup dns.lan.local 192.168.3.10

# Reverse lookup  
nslookup 192.168.3.10 192.168.3.10

# External domain
nslookup google.com 192.168.3.10
```

## Backup & Recovery

DNS configuration is stored in `/opt/technitium-data` on the VM.

```bash
# Backup
ssh ubuntu@192.168.3.10 "sudo tar czf - /opt/technitium-data" > dns-backup-$(date +%Y%m%d).tar.gz

# Restore
cat dns-backup-YYYYMMDD.tar.gz | ssh ubuntu@192.168.3.10 "sudo tar xzf - -C /"
```

## Web Interface

Access the full web interface at: **http://192.168.3.10:5380**

Features:
- Zone management
- Record management  
- DNS analytics and logging
- Caching statistics
- DHCP scope configuration (optional)
- DNS-over-HTTPS (DoH) support
- DNS-over-TLS (DoT) support

## DHCP Server (192.168.3.x)

Technitium also provides DHCP for the Servers network with automatic DNS registration.

**Scope: Servers**
| Setting | Value |
|---------|-------|
| Range | 192.168.3.100 - 192.168.3.250 |
| Subnet | 255.255.255.0 |
| Gateway | 192.168.3.1 |
| DNS | 192.168.3.10 |
| Domain | lan.local |
| Lease Time | 1 day |

**Auto-Registration:** When a server gets a DHCP lease, Technitium automatically creates:
- A record: `hostname.lan.local` → IP address
- PTR record: IP → `hostname.lan.local`

**Ubiquiti:** DHCP disabled for Servers (192.168.3.x) network.

### DHCP API Examples

```bash
# List leases
curl "http://192.168.3.10:5380/api/dhcp/leases/list?token=$TOKEN&name=Servers"

# Add static reservation
curl "http://192.168.3.10:5380/api/dhcp/scopes/addReservedLease?token=$TOKEN&name=Servers&hardwareAddress=AA:BB:CC:DD:EE:FF&ipAddress=192.168.3.50&hostName=myserver"
```

## Ports Used

| Port | Protocol | Purpose |
|------|----------|---------|
| 53 | TCP/UDP | DNS queries |
| 67 | UDP | DHCP server |
| 5380 | TCP | Web interface |
| 853 | TCP | DNS-over-TLS |
| 443 | TCP | DNS-over-HTTPS |
| 80 | TCP | HTTP redirect |

