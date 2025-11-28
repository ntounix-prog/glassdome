# Proxmox Infrastructure: Complete Storage Analysis

**Date:** 2025-11-27  
**Analysis:** Both Proxmox nodes + TrueNAS SAN configuration

---

## Executive Summary

✅ **proxmox01** and **proxmox02** can be clustered safely  
✅ **TrueNAS SAN** is already connected to proxmox02 via **dual-path iSCSI**  
✅ **Shared storage** already exists: TrueNAS NFS (on proxmox01) and esxstore (on proxmox02)  
⚠️ **proxpool ZFS** on proxmox02 is iSCSI-backed - **do not share** this specific LUN  

---

## Detailed Findings

### Proxmox01 (pve01) - 192.168.215.78

**iSCSI Initiator IQN:**
```
iqn.1993-08.org.debian:01:b58cc31af588
```

**Storage Configuration:**

| Storage ID | Type | Shared | Content | Details |
|------------|------|--------|---------|---------|
| `local` | dir | ❌ No | ISO, backups, templates | `/var/lib/vz` |
| `local-lvm` | lvmthin | ❌ No | VM disks, containers | Local LVM thin pool |
| `TrueNAS` | **NFS** | ✅ **Yes** | VM disks, templates, containers | `192.168.211.95:/mnt/NFSSTORE/vm` |

**iSCSI Status:**
- No active iSCSI sessions
- Initiator configured but not connected to any targets

**Block Devices:**
- `sda` (465.7GB): Local disk with LVM
  - Templates: 9000, 9100, 9101 (Windows Server 2022, Win11)
  - Test VMs: 114 (1TB disk)

**Key Characteristics:**
- ✅ Has TrueNAS NFS shared storage
- ✅ Can create VMs on shared NFS
- ❌ Not using iSCSI from TrueNAS
- ❌ Not clustered

---

### Proxmox02 (pve02) - 192.168.215.77

**iSCSI Initiator IQN:**
```
iqn.1993-08.org.debian:01:224b1b91acce
```

**Storage Configuration:**

| Storage ID | Type | Shared | Content | Details |
|------------|------|--------|---------|---------|
| `local` | dir | ❌ No | ISO, backups, templates | `/var/lib/vz` |
| `local-lvm` | lvmthin | ❌ No | VM disks, containers | Local LVM thin pool |
| `backup-vol` | lvm | ❌ No | VM disks, containers | `ubuntu-vg` |
| `esxstore` | dir | ✅ **Yes** | VM disks, ISO, templates, containers | `/mnt/esxstore` (2.9TB) |
| `proxpool` | **zfspool** | ❌ **No** | VM disks, containers | **29TB ZFS on iSCSI** |

**Active iSCSI Sessions (DUAL-PATH):**
```
tcp: [1] 192.168.211.95:3260,1 iqn.2005-10.org.freenas.ctl:proxmox-target
tcp: [2] 192.168.212.95:3260,1 iqn.2005-10.org.freenas.ctl:proxmox-target
```

**TrueNAS Connection:**
- ✅ Connected to **TrueNAS at 192.168.211.95** (primary path)
- ✅ Connected to **TrueNAS at 192.168.212.95** (secondary path - multipath/HA)
- ✅ Target: `iqn.2005-10.org.freenas.ctl:proxmox-target`

**ZFS Pool Details:**
```
Pool: proxpool
Size: 29TB (sdc device)
State: ONLINE
Backend: iSCSI LUN from TrueNAS (wwn-0x6589cfc000000697a7b97222d778e937)
Block size: 4096B configured, 16384B native (performance warning, but functional)
```

**Block Devices:**
- `sda` (465.7GB): Local disk with LVM
- `sdb` (3.3TB): Local disk with ubuntu-vg
  - `esxstore` partition: 2.9TB mounted at `/mnt/esxstore`
- `sdc` (29TB): **iSCSI LUN from TrueNAS** → ZFS pool `proxpool`

**Critical VMs on proxpool:**
- 100: agentx (running) ← **This VM we're on**
- 108: glassdome-prod-app (running)
- 109: glassdome-prod-db (running)
- Plus: es01, mooker, rome, mail, mnto, scribe, sunspot

**Key Characteristics:**
- ✅ Has 29TB ZFS pool backed by TrueNAS iSCSI (dual-path HA)
- ✅ Has shared esxstore (2.9TB local disk, marked shared)
- ✅ Production workloads running on proxpool
- ❌ proxpool is **single-writer** (proxmox02 owns the ZFS filesystem)
- ❌ Not clustered

---

## TrueNAS Configuration (Inferred)

**IP Addresses:**
- Primary: `192.168.211.95`
- Secondary: `192.168.212.95` (likely VLAN or multipath config)

**iSCSI Target:**
```
iqn.2005-10.org.freenas.ctl:proxmox-target
```

**Authorized Initiator (Current):**
- ✅ `iqn.1993-08.org.debian:01:224b1b91acce` (proxmox02)

**Authorized Initiator (To Add for proxmox01):**
- ❌ `iqn.1993-08.org.debian:01:b58cc31af588` (proxmox01) - **NOT YET ADDED**

**LUN/Extent:**
- ~29TB zvol backing the proxmox02 ZFS pool
- Connected to proxmox02 as `sdc` device

**NFS Export:**
- Path: `/mnt/NFSSTORE/vm`
- Accessible by proxmox01 already

---

## Storage Strategy Recommendations

### Option 1: Use Shared NFS for Lab VMs (RECOMMENDED)

**What:**
- Use existing TrueNAS NFS (`192.168.211.95:/mnt/NFSSTORE/vm`) as shared storage
- Add this NFS export to proxmox02 (it's already on proxmox01)
- Deploy Canvas lab VMs to NFS storage
- Keep production VMs on proxpool (unchanged)

**Advantages:**
- ✅ **Zero risk** to existing production VMs and proxpool
- ✅ Already working on proxmox01
- ✅ True multi-writer shared storage
- ✅ Supports live migration for lab VMs
- ✅ Simple configuration (5 minutes)

**Steps:**
1. On proxmox02, add storage via GUI:
   - Datacenter → Storage → Add → NFS
   - ID: `TrueNAS` (or `truenas-nfs`)
   - Server: `192.168.211.95`
   - Export: `/mnt/NFSSTORE/vm`
   - Content: Disk image, Container, Templates
   - **Mark as Shared: ✅**

2. Update Glassdome:
   - Change hot spare pool to use `TrueNAS` storage
   - Change Canvas deploy to use `TrueNAS` storage for lab VMs
   - Keep `agentx`, `glassdome-prod-app`, `glassdome-prod-db` on `proxpool`

**Performance:**
- Good enough for CTF/training labs
- Not ideal for IO-intensive production workloads (but that's not the use case)

---

### Option 2: Allocate Separate iSCSI LUN for proxmox01

**What:**
- On TrueNAS: Create a **new** iSCSI LUN for proxmox01 (separate from proxpool LUN)
- On proxmox01: Connect to new LUN, create ZFS pool
- Keep proxpool exclusive to proxmox02
- Use NFS for truly shared storage between nodes

**Advantages:**
- ✅ Both nodes get high-performance block storage
- ✅ Zero risk to existing proxpool
- ✅ Can replicate VMs between nodes for DR

**Disadvantages:**
- ⚠️ More complex - requires TrueNAS configuration
- ⚠️ Replication-based, not instant live migration
- ⚠️ Uses more TrueNAS capacity (allocate ~10-15TB for proxmox01?)

**Steps:**
1. On TrueNAS:
   - Create new zvol: `proxmox01-pool` (10TB+)
   - Create new iSCSI target: `iqn.2005-10.org.freenas.ctl:proxmox01-target`
   - Add extent pointing to the zvol
   - Associate target with extent
   - Add proxmox01 IQN to authorized initiators: `iqn.1993-08.org.debian:01:b58cc31af588`

2. On proxmox01:
   ```bash
   # Discover iSCSI target
   iscsiadm -m discovery -t sendtargets -p 192.168.211.95
   
   # Login to target
   iscsiadm -m node --login
   
   # Find new device (likely sdb)
   lsblk
   
   # Create ZFS pool
   zpool create -o ashift=12 proxpool01 /dev/sdb
   
   # Add to Proxmox storage
   pvesm add zfspool proxpool01 -pool proxpool01 -content images,rootdir
   ```

3. For shared storage between nodes:
   - Still use NFS for lab VMs that need to migrate

---

### Option 3: Shared iSCSI LVM (Traditional Cluster Storage)

**What:**
- Create a **new** shared iSCSI LUN from TrueNAS
- Configure as LVM or LVM-Thin on both nodes
- Use cluster locking to prevent simultaneous writes

**Advantages:**
- ✅ Industry-standard Proxmox cluster approach
- ✅ True shared block storage with live migration
- ✅ Supports HA

**Disadvantages:**
- ⚠️ Most complex option
- ⚠️ Requires clustering first
- ⚠️ Requires careful cluster lock configuration
- ⚠️ Risk of split-brain if misconfigured

**Steps:**
1. Create Proxmox cluster (see Clustering section)
2. On TrueNAS: Create shared LUN, add both IQNs to ACL
3. On both nodes: Connect to LUN, configure as clustered LVM
4. Configure distributed lock manager (DLM)

**Verdict:** Overkill for current needs, but valid for future HA requirements

---

## Clustering Implementation Plan

### Prerequisites ✅

- [x] Same Proxmox version: **9.1.1** on both nodes
- [x] Network connectivity: 192.168.215.77 ↔ 192.168.215.78
- [x] Time sync (verify NTP)
- [x] Shared storage available (NFS)

### Two-Node Quorum Strategy

**Problem:** 2-node cluster = no majority if one node fails  
**Solution:** Use QDevice (third voter) or accept 2-node limitations

**QDevice Options:**
1. Small VM on TrueNAS (if it supports VMs)
2. Raspberry Pi or similar on different network
3. Cloud micro-instance (AWS t4g.nano, $3/month)

**Without QDevice:**
- Cluster works fine if both nodes online
- If one node fails, must manually adjust quorum
- Not ideal for production HA, acceptable for lab management

### Clustering Steps (SAFE ORDER)

**Phase 1: Pre-Cluster Checks**
```bash
# On both nodes - verify NTP
timedatectl

# On both nodes - verify network latency
ping -c 10 <other-node-ip>

# On both nodes - backup configuration
tar -czf /root/pve-backup-$(date +%Y%m%d).tar.gz /etc/pve /etc/network/interfaces
```

**Phase 2: Create Cluster (on proxmox02 - production node)**
```bash
# On proxmox02 (192.168.215.77)
pvecm create glassdome-cluster

# Verify
pvecm status
# Should show: Quorum: 1 Expected: 1
```

**Phase 3: Join proxmox01 to Cluster**
```bash
# On proxmox01 (192.168.215.78)
pvecm add 192.168.215.77

# When prompted, enter root password: xisxxisx
# Wait for join to complete (~30 seconds)
```

**Phase 4: Verify Cluster**
```bash
# On either node
pvecm status
# Should show: Quorum: 2 Expected: 2, Nodes: 2

pvecm nodes
# Should list both pve01 and pve02

# Check cluster config
cat /etc/pve/corosync.conf
```

**Phase 5: Configure Shared Storage**
```bash
# Via GUI on either node (now unified):
# Datacenter → Storage → TrueNAS (or esxstore)
# Verify "Nodes" shows "All" and "Shared" is checked
```

**Phase 6: Test Migration**
```bash
# Create small test VM on shared storage
# Try offline migration: Migrate → Target Node
# Try online migration (if CPU features compatible)
```

---

## Risk Assessment

### Clustering Risks

**LOW RISK ✅:**
- Creating cluster should not disrupt running VMs
- `/etc/pve` becomes cluster filesystem but content preserved
- Can be done during business hours with proper prep

**MITIGATION:**
- Backup `/etc/pve` before clustering
- Do during low-usage window
- Have console access to both nodes
- Test on non-production first if possible

### Storage Risks

**ZERO RISK ✅:**
- Adding NFS storage to proxmox02 (read-only operation)
- Clustering with existing storage intact

**HIGH RISK ❌ NEVER DO THIS:**
- Connecting proxmox01 to the same iSCSI LUN as proxpool
- Importing proxpool ZFS on both nodes simultaneously
- = **Instant data corruption**

---

## Immediate Action Plan

### Step 1: Add Shared NFS to proxmox02 (This Week)

**Time:** 5 minutes  
**Risk:** None  
**Rollback:** Just remove storage definition

**Commands:**
```bash
# Via GUI (easier) or CLI:
pvesm add nfs TrueNAS \
  --server 192.168.211.95 \
  --export /mnt/NFSSTORE/vm \
  --content images,vztmpl,rootdir \
  --shared 1
```

**Verify:**
```bash
pvesm status | grep TrueNAS
# Should show on both nodes once clustered
```

---

### Step 2: Update Glassdome to Use Shared Storage (This Week)

**Files to modify:**
- `glassdome/reaper/hot_spare.py` - Change default storage to `TrueNAS`
- `glassdome/workers/orchestrator.py` - Use `TrueNAS` for lab deployments
- `glassdome/api/canvas_deploy.py` - Target `TrueNAS` storage

**Keep on proxpool:**
- VM 100: agentx
- VM 108: glassdome-prod-app
- VM 109: glassdome-prod-db

---

### Step 3: Cluster the Nodes (Next Week)

**Prerequisites:**
- ✅ Shared NFS working on both nodes
- ✅ Backups of /etc/pve on both nodes
- ✅ Low-usage time window

**Duration:** 30 minutes  
**Risk:** Low (with backups)

---

### Step 4: Setup QDevice (Optional, Next Month)

**Options:**
1. Raspberry Pi on office network
2. Cloud micro-instance
3. VM on TrueNAS (if supported)

**Not urgent** - cluster works fine without it for lab management purposes

---

## TrueNAS Next Steps (Manual)

To enable iSCSI for proxmox01 (if desired for Option 2):

1. **GUI:** Sharing → Block (iSCSI) → Targets
   - Find: `iqn.2005-10.org.freenas.ctl:proxmox-target`
   - Check authorized initiators/ACL

2. **Decision Point:**
   - **Add proxmox01 to same target?** ❌ **NO - UNSAFE**
   - **Create new target for proxmox01?** ✅ Yes (Option 2)
   - **Stick with NFS for shared?** ✅ Simplest (Option 1)

---

## Summary

### Current State
- **proxmox02:** 29TB ZFS over iSCSI (dual-path HA to TrueNAS)
- **proxmox01:** 465GB local + TrueNAS NFS
- **Not clustered:** Separate management
- **Shared storage:** TrueNAS NFS exists, not used by proxmox02 yet

### Recommended Path
1. ✅ Add TrueNAS NFS to proxmox02 (5 min, zero risk)
2. ✅ Update Glassdome to deploy labs on NFS (30 min)
3. ✅ Cluster the nodes (30 min, low risk with backups)
4. ✅ Keep production VMs on proxpool (no changes)
5. 🔄 Optional: Add separate iSCSI LUN for proxmox01 later

### What NOT to Do
- ❌ Share the proxpool iSCSI LUN between nodes
- ❌ Import proxpool ZFS on proxmox01
- ❌ Cluster without backups

### Ready to Proceed?
**YES** - All information gathered, low-risk path identified, production VMs safe.

