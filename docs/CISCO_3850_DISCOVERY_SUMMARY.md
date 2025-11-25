# Cisco 3850 Network Discovery Summary

**Date:** 2024-11-24  
**Switch:** Cisco 3850 (corefc)  
**IP Address:** 192.168.2.253

## Connected Interfaces (16 total)

| Port | Description | VLAN | Notes |
|------|-------------|------|-------|
| Gi1/0/3 | SAN MGMT | 215 | Storage network management |
| Gi1/0/4 | (no description) | 11 | Unknown device |
| Gi1/0/5 | (no description) | 1 | Default VLAN |
| Gi1/0/7 | (no description) | 1 | Default VLAN |
| Gi1/0/9 | (no description) | 1 | Default VLAN |
| Gi1/0/11 | (no description) | 1 | Default VLAN |
| Gi1/0/13 | (no description) | 1 | Default VLAN |
| Gi1/0/17 | (no description) | 1 | Default VLAN |
| Gi1/0/23 | (no description) | 1 | **Connected to Nexus 3064 (core3k)** |
| Gi1/0/35 | Extreme. maybe | trunk | Trunk port |
| Gi1/0/36 | ESX OBS01 MGMT | 215 | ESXi management |
| Gi1/0/37 | PROXMOX 02 mgmt | 215 | Proxmox 02 management |
| Gi1/0/38 | proxmox 01 ilo | trunk | Proxmox 01 iLO trunk |
| Gi1/0/40 | proxmox01 mgmt | 215 | Proxmox 01 management |
| Te1/1/3 | Gateway | trunk | **UniFi Gateway connection** |
| Te1/1/4 | Fiber CORE | trunk | **Nexus 3064 fiber connection** |

## CDP Neighbors

1. **Nexus 3064 (core3k)**
   - Device ID: `core3k(FOC1801R19S)`
   - IP Address: **192.168.2.244** (Note: .env has 192.168.2.224 - needs update)
   - Connected on: `GigabitEthernet1/0/23` (management) and `TenGigabitEthernet1/1/4` (fiber)
   - Platform: N3K-C3064PQ-10GX
   - Version: Cisco Nexus Operating System (NX-OS) Software, Version 6.0(2)U6(7)

2. **Self (corefc.summit.local)**
   - Connected on: `GigabitEthernet0/0` and `GigabitEthernet1/0/9`
   - This appears to be internal loopback or management interface

## VLANs Identified

- **VLAN 1**: Default VLAN (multiple ports)
- **VLAN 11**: Unknown purpose (1 port)
- **VLAN 215**: Management network (Proxmox, ESXi, SAN)
- **Trunk**: Multiple trunk ports for inter-switch connectivity

## Key Findings

1. **Nexus 3064 IP Mismatch**: CDP shows Nexus at 192.168.2.244, but .env has 192.168.2.224
2. **Unlabeled Ports**: Many ports on VLAN 1 have no descriptions
3. **Management Network**: VLAN 215 is used for Proxmox and ESXi management
4. **Trunk Ports**: Several trunk ports for inter-switch connectivity
5. **Gateway Connection**: Te1/1/3 connects to UniFi Gateway

## Next Steps

1. Update .env with correct Nexus 3064 IP (192.168.2.244)
2. Configure default gateway on Nexus 3064 (192.168.2.1)
3. Discover Nexus 3064 configuration
4. Map network topology using CDP/LLDP data
5. Label unlabeled ports based on MAC address table
6. Clean up VLAN assignments

