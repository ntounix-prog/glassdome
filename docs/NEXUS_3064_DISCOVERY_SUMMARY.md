# Nexus 3064 Network Discovery Summary

**Date:** 2024-11-24  
**Switch:** Nexus 3064 (core3k)  
**IP Address:** 192.168.2.244  
**VRF:** Management interface in `management` VRF

## Key Configuration

- **Hostname:** core3k
- **Version:** Cisco Nexus Operating System (NX-OS) Software, Version 6.0(2)U6(7)
- **Management Interface:** mgmt0 (192.168.2.244/24) in VRF `management`
- **Default Route (Management VRF):** 0.0.0.0/0 → 192.168.2.1 (UniFi Gateway)
- **Default Route (Global):** 0.0.0.0/0 → 192.168.2.1

## VRFs

1. **default** (VRF-ID: 1) - Up
2. **management** (VRF-ID: 2) - Up (contains mgmt0 interface)

## VLANs

- **VLAN 1:** Default VLAN (active on many trunk ports)
- **VLAN 2:** Servers
- **VLAN 11:** Unknown purpose
- **VLAN 211:** SAN A side
- **VLAN 212:** SAN B side
- **VLAN 100-150:** Range configured on Eth1/35

## Interface Configuration

Most interfaces are configured as **trunk ports** for inter-switch connectivity.

### Key Interfaces:

- **Ethernet1/3:** Connection to obs01 (trunk)
- **Ethernet1/10:** Access VLAN 212
- **Ethernet1/13:** Trunk with allowed VLANs: 2, 11, 212
- **Ethernet1/17:** SAN A side VLAN 211 (access, edge port)
- **Ethernet1/19:** Connection to obs03 (trunk)
- **Ethernet1/23:** Trunk with allowed VLANs: 2, 11, 211 (edge trunk)
- **Ethernet1/25:** Connection to obs02 (trunk)
- **Ethernet1/27:** 10G to OBS01 (trunk)
- **Ethernet1/29:** SAN B side VLAN 212 (access, edge port)
- **Ethernet1/33:** Connection to obs04 (trunk)
- **Ethernet1/35:** Connection to obs05 (trunk, allowed VLANs: 1, 100-150)

## CDP Neighbors

- **2 CDP neighbors** discovered
- Connected to Cisco 3850 (corefc) via multiple paths

## Network Topology

The Nexus 3064 serves as the **core datacenter switch** with:
- Multiple trunk connections to other switches (obs01, obs02, obs03, obs04, obs05)
- SAN connectivity (VLANs 211, 212)
- Server network (VLAN 2)
- Management network access

## Connection to Cisco 3850

Based on CDP from Cisco 3850:
- Nexus 3064 connected on Cisco 3850's `GigabitEthernet1/0/23` (management)
- Nexus 3064 connected on Cisco 3850's `TenGigabitEthernet1/1/4` (fiber, 10G)

## Notes

- Uses legacy SSH algorithms (ssh-rsa) - requires special SSH options
- Management interface requires VRF-aware routing
- Primarily configured as a trunk switch for inter-switch connectivity
- SAN networks isolated on dedicated VLANs (211, 212)

