# Nexus 3064 SAN Switch Configuration

**Last Updated:** 2025-11-27  
**Status:** Production - Proxmox Cluster SAN  
**Next Work:** Post-demo (after 12/8)

---

## Switch Overview

| Property | Value |
|----------|-------|
| **Hostname** | core3k |
| **Model** | Cisco Nexus 3064 |
| **IP Address** | 192.168.2.244 |
| **Management VRF** | management |
| **NX-OS Version** | 6.0(2)U6(7) |
| **Ports** | 48x 10G SFP+ + 4x 40G QSFP+ |

---

## Credentials

```
Host: 192.168.2.244
Username: admin
Password: (see .env NEXUS_3064_PASSWORD)
```

**SSH Requirements:** Legacy algorithms required
```bash
ssh -o HostKeyAlgorithms=+ssh-rsa -o PubkeyAcceptedAlgorithms=+ssh-rsa admin@192.168.2.244
```

---

## Programmatic Access

**Use `netmiko` library** (NOT paramiko or sshpass directly):

```python
from netmiko import ConnectHandler

nexus = {
    'device_type': 'cisco_nxos',
    'host': '192.168.2.244',
    'username': 'admin',
    'password': '<from .env>',
    'timeout': 30,
}

connection = ConnectHandler(**nexus)
output = connection.send_command("show vlan brief")
connection.send_config_set(['interface Ethernet1/9', 'description test'])
connection.save_config()
connection.disconnect()
```

**Script Location:** `/home/nomad/glassdome/scripts/network_discovery/configure_nexus_netmiko.py`

---

## VLAN Configuration

| VLAN | Name | Purpose |
|------|------|---------|
| 1 | default | Default/Native |
| 2 | Servers | Server network traffic |
| 211 | VLAN0211 | SAN A-side |
| 212 | VLAN0212 | SAN B-side |

---

## Proxmox Node Connections

### proxmox01 (pve01) - 192.168.215.78

| Nexus Port | proxmox01 NIC | MAC Address | VLANs | Purpose |
|------------|---------------|-------------|-------|---------|
| **Eth1/9** | nic5 | 80:61:5f:11:ad:93 | 1,2,211,212 | 10G SAN + Servers |
| **Eth1/10** | nic4 | 80:61:5f:11:ad:92 | 1,2,211,212 | 10G SAN + Servers |

**proxmox01 SAN IPs:**
- VLAN 211: 192.168.211.78 (vmbr2.211)
- VLAN 212: 192.168.212.78 (vmbr1.212)

### proxmox02 (pve02) - 192.168.215.77

| Nexus Port | proxmox02 NIC | VLANs | Purpose |
|------------|---------------|-------|---------|
| **Eth1/13** | nic4 (vmbr1) | trunk | 10G SAN + Servers |
| **Eth1/23** | nic5 (vmbr2) | trunk | 10G SAN + Servers |

**proxmox02 SAN IPs:**
- VLAN 211: 192.168.211.26 (vmbr2.211)
- VLAN 212: 192.168.212.26 (vmbr1.212)

### proxmox03 (pve) - 192.168.215.79

| Nexus Port | proxmox03 NIC | MAC Address | VLANs | Purpose |
|------------|---------------|-------------|-------|---------|
| **Eth1/3** | nic4 | 80:61:5f:11:b6:27 | 1,2,211,212 | 10G SAN + Servers |
| **Eth1/19** | nic5 | 80:61:5f:11:b6:28 | 1,2,211,212 | 10G SAN + Servers |

**proxmox03 SAN IPs:**
- VLAN 211: 192.168.211.79 (vmbr2.211)
- VLAN 212: 192.168.212.79 (vmbr1.212)

---

## TrueNAS Connections

| Nexus Port | TrueNAS Interface | VLAN | IP |
|------------|-------------------|------|-----|
| **Eth1/17** | SAN A | 211 (access) | 192.168.211.95 |
| **Eth1/29** | SAN B | 212 (access) | 192.168.212.95 |

**TrueNAS Management:** 192.168.215.75 (not on Nexus, via Cisco 3850)

---

## Port Configuration Details

### Eth1/9 (proxmox01 nic5)
```
interface Ethernet1/9
  description proxmox01 nic5 (10G SAN+Servers)
  switchport
  switchport mode trunk
  switchport trunk allowed vlan 1-2,211-212
  duplex full
```

### Eth1/10 (proxmox01 nic4)
```
interface Ethernet1/10
  description proxmox01 nic4 (10G SAN+Servers)
  switchport
  switchport mode trunk
  switchport trunk allowed vlan 1-2,211-212
  duplex full
```

### Eth1/17 (TrueNAS SAN A)
```
interface Ethernet1/17
  description SAN A side VLAN 211
  switchport
  switchport access vlan 211
  spanning-tree port type edge
```

### Eth1/29 (TrueNAS SAN B)
```
interface Ethernet1/29
  description SAN B side VLAN 212
  switchport
  switchport access vlan 212
  spanning-tree port type edge
```

---

## Cluster Network Topology

```
                         ┌─────────────────────────────────────┐
                         │        Nexus 3064 (core3k)          │
                         │         192.168.2.244               │
                         └─────────────────────────────────────┘
                     ┌──────────┼───────────────┼─────────────┐
                     │          │               │             │
                Eth1/9,10   Eth1/13,23      Eth1/3,19    Eth1/17,29
                 (trunk)     (trunk)         (trunk)      (access)
                     │          │               │             │
         ┌───────────▼────┐  ┌──▼───────────┐ ┌▼─────────────┐│
         │   proxmox01    │  │  proxmox02   │ │  proxmox03   ││
         │ 192.168.215.78 │  │192.168.215.77│ │192.168.215.79││
         │                │  │              │ │              ││
         │ SAN: .211.78   │◄─┼──Cluster────►├─┤ SAN: .211.79 ││
         │      .212.78   │  │  (10G knet) ││ │      .212.79 ││
         └────────────────┘  │ SAN:.211.26 │  └──────────────┘│
                             │     .212.26 │                  │
                             └─────────────┘                  │
                                    │                         │
                         ┌──────────▼────────────────────────▼┐
                         │            TrueNAS                 │
                         │        192.168.215.75              │
                         │                                    │
                         │  SAN A: 192.168.211.95 ◄── Eth1/17 │
                         │  SAN B: 192.168.212.95 ◄── Eth1/29 │
                         │                                    │
                         │  NFS Export: /mnt/PROXMOX/         │
                         │              proxmox-vms (~29TB)   │
                         └────────────────────────────────────┘
```

---

## Useful Commands

### Show Commands
```
show vlan brief                           # All VLANs
show vlan id 211                          # Specific VLAN
show interface status                     # All port status
show interface Ethernet1/9 switchport    # Port switchport config
show running-config interface Ethernet1/9 # Full port config
show mac address-table                    # MAC table
show cdp neighbors                        # Connected devices
show lldp neighbors                       # LLDP neighbors
```

### Configuration Commands
```
configure terminal
interface Ethernet1/X
  switchport mode trunk
  switchport trunk allowed vlan add 211,212
  description <description>
  exit
copy running-config startup-config
```

---

## Discovery Scripts

| Script | Purpose |
|--------|---------|
| `scripts/network_discovery/discover_nexus_3064.py` | Full switch discovery |
| `scripts/network_discovery/configure_nexus_netmiko.py` | Configure ports |
| `scripts/network_discovery/find_proxmox01_nexus_ports.py` | Find MAC addresses |

---

## Known Issues

1. **SSH Session Handling:** Standard SSH tools (sshpass, paramiko) fail because NX-OS immediately closes non-interactive sessions. **Use netmiko.**

2. **Legacy SSH Algorithms:** Requires `ssh-rsa` which is disabled by default in modern SSH clients.

3. **Password in .env:** The correct password is `NEXUS_3064_PASSWORD=azZGR4gBvLQf_P!*Y` (the other one was incorrect).

---

## Future Work (Post 12/8 Demo)

### Potential Tasks
- [ ] Configure additional server VLANs
- [ ] Set up port-channels for link aggregation
- [ ] Configure QoS for storage traffic
- [ ] Add monitoring/SNMP
- [ ] Document full switch backup procedure
- [ ] Consider firmware upgrade (current: 6.0(2)U6(7))

### Unused Ports Available
Most ports Eth1/11-48 are available (sfpAbsent or not connected)

### Inter-Switch Connectivity
- **Eth1/5** → Cisco 3850 (Te1/1/4) - 10G trunk to core switch
- **mgmt0** → Cisco 3850 (Gi1/0/23) - Management

---

## Related Documentation

- `/home/nomad/glassdome/docs/NEXUS_3064_DISCOVERY_SUMMARY.md` - Initial discovery
- `/home/nomad/glassdome/docs/nexus_3064_discovery.json` - Raw discovery data
- `/home/nomad/glassdome/docs/port_device_mapping.json` - Port-to-device mapping
- `/home/nomad/glassdome/docs/PROXMOX_NEXT_STEPS.md` - Infrastructure status

---

## Change Log

| Date | Change | By |
|------|--------|-----|
| 2025-12-03 | Added proxmox03 on Eth1/3 and Eth1/19 with VLANs 1,2,211,212 | Agent |
| 2025-11-27 | Added VLANs 1,2,211,212 to Eth1/9, Eth1/10 for proxmox01 | Agent |
| 2025-11-27 | Documented netmiko as required tool for automation | Agent |
| 2025-11-24 | Initial switch discovery | Agent |

