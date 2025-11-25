# Template Migration Approaches Comparison

## Overview

Two approaches are available for migrating templates from the original Proxmox (192.168.215.78) to the current Proxmox server. Choose the approach that best fits your network configuration.

## Approach 1: Direct Network Access (Recommended)

**Add secondary network interface to agentX and server VM on 192.168.215.0/24**

### Advantages
- ✅ **Simpler**: No VLAN configuration needed
- ✅ **Direct**: Direct connection, no routing overhead
- ✅ **Optimal**: Uses existing network infrastructure
- ✅ **Flexible**: Can access any host on 192.168.215.0/24

### Requirements
- Add secondary network interface to agentX VM
- Add secondary network interface to server VM
- Configure static IPs (no gateway) on 192.168.215.0/24
- Bridge on current Proxmox must serve 192.168.215.0/24

### Implementation
1. Run: `python3 scripts/add_secondary_network_interface.py --execute`
2. Run: `python3 scripts/migrate_templates_from_original_proxmox.py --original-ip 192.168.215.78 --execute`

**Documentation**: [PROXMOX_DIRECT_NETWORK_TEMPLATE_MIGRATION.md](PROXMOX_DIRECT_NETWORK_TEMPLATE_MIGRATION.md)

---

## Approach 2: VLAN 10 Network

**Configure VLAN 10 on storage networks to create 10.0.0.0/24 access**

### Advantages
- ✅ **Isolated**: Separate VLAN for migration traffic
- ✅ **Flexible**: Can be used for other purposes
- ✅ **Scalable**: Easy to add more hosts to VLAN

### Requirements
- Configure VLAN 10 on storage network (nic4 or nic5)
- Create vmbr3 bridge (VLAN-aware) on both Proxmox servers
- Configure IPs: 10.0.0.3 (original), 10.0.0.77 (current)
- Router/switch must support VLAN 10

### Implementation
1. Run: `./scripts/configure_proxmox_vlan10.sh 192.168.215.78 10.0.0.3 nic4`
2. Run: `./scripts/configure_proxmox_vlan10.sh 192.168.215.77 10.0.0.77 nic4`
3. Run: `python3 scripts/migrate_templates_from_original_proxmox.py --original-ip 10.0.0.3 --execute`

**Documentation**: [PROXMOX_VLAN10_TEMPLATE_MIGRATION.md](PROXMOX_VLAN10_TEMPLATE_MIGRATION.md)

---

## Comparison

| Feature | Direct Network | VLAN 10 |
|---------|---------------|---------|
| **Complexity** | Low | Medium |
| **Network Changes** | Add VM interfaces | Configure VLAN on both servers |
| **Performance** | Optimal (direct) | Good (routed) |
| **Isolation** | None | Separate VLAN |
| **Flexibility** | High | Medium |
| **Setup Time** | ~5 minutes | ~15 minutes |

## Recommendation

**Use Direct Network Access (Approach 1)** if:
- You want the simplest solution
- You don't need network isolation
- You want optimal performance
- You have direct access to 192.168.215.0/24 network

**Use VLAN 10 (Approach 2)** if:
- You need network isolation
- You want to keep migration traffic separate
- You plan to use VLAN 10 for other purposes
- Your network infrastructure supports VLANs

---

*Last Updated: November 24, 2024*

