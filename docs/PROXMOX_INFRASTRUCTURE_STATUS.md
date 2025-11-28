# Proxmox Infrastructure Status

**Last Updated:** 2025-11-27  
**Status:** ✅ COMPLETE - Ready for Production

---

## Infrastructure Summary

### Proxmox Cluster: FtC

| Node | IP (Mgmt) | IP (SAN 211) | IP (SAN 212) | Status |
|------|-----------|--------------|--------------|--------|
| pve01 | 192.168.215.78 | 192.168.211.78 | 192.168.212.78 | ✅ Online |
| pve02 | 192.168.215.77 | 192.168.211.26 | 192.168.212.26 | ✅ Online |

### Cluster Network
- **Transport:** knet (10G only)
- **Link 0:** VLAN 211 (192.168.211.x)
- **Link 1:** VLAN 212 (192.168.212.x)
- **Quorum:** 2 nodes, quorate

### Shared Storage

| Storage | Type | Server | Export | Capacity |
|---------|------|--------|--------|----------|
| truenas-nfs-labs | NFS | 192.168.215.75 | /mnt/PROXMOX/proxmox-vms | ~29TB |

---

## Network Architecture

### Per-Node Configuration

**Management (1G):**
- `vmbr0` - Bridge on nic0
- VLAN 215 - Management network

**10G Fabric (VLAN-aware):**
- `vmbr1` - Bridge on nic4, MTU 9000
- `vmbr2` - Bridge on nic5, MTU 9000
- Supported VLANs: 1, 2, 211, 212

**SAN Interfaces:**
- `vmbr1.212` - SAN B-side
- `vmbr2.211` - SAN A-side

### VLAN Purpose

| VLAN | Name | Purpose |
|------|------|---------|
| 1 | default | Native VLAN |
| 2 | Servers | VM server traffic |
| 211 | SAN-A | Storage/Cluster link 0 |
| 212 | SAN-B | Storage/Cluster link 1 |
| 215 | Management | Node management |

---

## TrueNAS Configuration

| Property | Value |
|----------|-------|
| **Hostname** | truenas |
| **Management IP** | 192.168.215.75 |
| **SAN Portal A** | 192.168.211.95 |
| **SAN Portal B** | 192.168.212.95 |
| **Pool** | PROXMOX |
| **Dataset** | proxmox-vms |
| **SLOG** | NVMe (sync write acceleration) |
| **L2ARC** | 4TB SSD (read cache) |

---

## Completed Tasks

- [x] Migrate VMs from iSCSI `proxpool` to local `esxstore`
- [x] Export/destroy ZFS pool on proxmox02
- [x] Disconnect iSCSI sessions
- [x] Create NFS share on TrueNAS
- [x] Configure Nexus 3064 switch (VLANs 1,2,211,212)
- [x] Configure VLAN-aware bridges on pve01
- [x] Mount NFS on both nodes
- [x] Create Proxmox cluster (10G only)
- [x] Test live migration (11s, 76ms downtime)

---

## Live Migration Performance

| Metric | Value |
|--------|-------|
| Migration Time | 11 seconds |
| Downtime | 76 ms |
| Transfer Rate | ~680 MiB/s |
| Network | 10G SAN (VLAN 211/212) |

---

## VM Locations

### pve02 (Primary - has VMs)
- agentx (100) - Running
- mooker (102) - Running
- rome (103) - Running
- scribe (106) - Running
- glassdome-prod-app (108) - Running
- glassdome-prod-db (109) - Running
- spare-ubuntu-110-114 - Running
- Templates (9000, 9001)

### pve01 (Secondary - ready for failover)
- Currently empty
- Ready for HA or manual migration

---

## Quick Commands

### Check Cluster Status
```bash
pvecm status
pvecm nodes
corosync-cfgtool -s
```

### Check Storage
```bash
pvesm status
```

### Live Migrate VM
```bash
qm migrate <vmid> <target-node> --online
```

### Check Network
```bash
ip -br addr show | grep vmbr
```

---

## Related Documentation

- `NEXUS_3064_SAN_SWITCH.md` - SAN switch configuration
- `TRUENAS_ARCHITECTURE_ANALYSIS.md` - TrueNAS design
- `PROXMOX_STORAGE_COMPLETE_ANALYSIS.md` - Storage analysis

---

## Future Considerations

1. **QDevice** - Add third quorum device for true HA
2. **HA Groups** - Configure automatic failover
3. **Backup** - Set up PBS or NFS backup target
4. **Monitoring** - Prometheus/Grafana for cluster metrics

