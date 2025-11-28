# Revised Storage Strategy: Better Architecture

**Date:** 2025-11-27  
**Based on:** User insight about local disk vs SAN usage

---

## The Better Approach

### Current Problem
- **Critical VMs** (agentx, prod-app, prod-db) are on `proxpool` (29TB ZFS over iSCSI)
- This makes them **dependent on SAN connectivity**
- The 29TB iSCSI LUN is configured as **single-writer ZFS**
- Meanwhile, **2.8TB local disk** (`esxstore`) is underutilized

### Better Architecture
1. **Move critical VMs to local disk** (`esxstore` - 2.8TB, fast local storage)
   - Removes SAN dependency for core infrastructure
   - Faster performance (no network overhead)
   - More resilient (doesn't depend on TrueNAS being up)

2. **Reconfigure 29TB SAN pool for shared lab storage**
   - This is what it should be used for: ephemeral lab VMs
   - Can be restructured as LVM or kept as ZFS with replication
   - Much better fit for Canvas deployments

---

## Current Disk Usage on proxmox02

### Local Disk: sdb (3.3TB total)
```
sdb3 → ubuntu-vg
  ├─ ubuntu-lv: 400GB (mounted somewhere, likely root of old install)
  └─ esxstore: 2.9TB at /mnt/esxstore (currently marked as "shared" in Proxmox)
```

**Current Status:**
- Marked as "shared" in Proxmox config
- Actually a **local disk** (not accessible from proxmox01)
- **Available space:** ~2.9TB
- **Fast:** Local SATA/NVMe, no network overhead

### SAN Disk: sdc (29TB)
```
sdc → proxpool (ZFS)
  - Backend: iSCSI from TrueNAS (dual-path)
  - Contains: All current VMs (agentx, prod, etc.)
  - Performance: Good, but network-dependent
```

---

## Revised Migration Plan

### Phase 1: Move Critical VMs to Local Disk (This Week)

**VMs to Move:**
- VM 100: agentx (this VM) - Running
- VM 108: glassdome-prod-app - Running  
- VM 109: glassdome-prod-db - Running

**Target Storage:** `esxstore` (local 2.8TB disk)

**Process (Low Risk):**
```bash
# For each VM (do one at a time):

# 1. Check current disk usage
qm config 100

# 2. Shutdown VM gracefully
qm shutdown 100
# Wait for shutdown (monitor via GUI)

# 3. Move disk from proxpool to esxstore
qm move-disk 100 scsi0 esxstore
# This copies the disk, preserves original until confirmed working

# 4. Start VM on new storage
qm start 100

# 5. Verify VM boots and works correctly
# SSH in, check services, etc.

# 6. Remove old disk from proxpool (once confirmed working)
# Via GUI or CLI
```

**Estimated Time per VM:**
- Shutdown: 30 seconds
- Disk copy: 5-15 minutes (depends on disk size)
- Boot and verify: 2-3 minutes
- **Total per VM:** ~20 minutes
- **Total for 3 VMs:** ~1 hour

**Risk:** Low
- Original disk preserved until verified
- Can roll back if issues
- VMs shut down gracefully

**Benefits:**
- ✅ Critical VMs independent of SAN
- ✅ Faster local disk performance
- ✅ More resilient architecture
- ✅ Frees up 29TB for proper shared storage

---

### Phase 2: Reconfigure SAN as Shared Storage (Next Week)

Once critical VMs are off `proxpool`, we have options:

#### Option A: Convert to Shared NFS (Simplest)
**On TrueNAS:**
1. Delete the iSCSI extent/target for proxpool
2. Export the same zvol as NFS instead
3. Both Proxmox nodes mount it

**On Proxmox:**
1. Destroy the local ZFS pool (data already moved)
2. Add NFS mount to both nodes
3. Mark as shared

**Advantages:**
- ✅ True multi-writer shared storage
- ✅ Both nodes can deploy VMs simultaneously
- ✅ Native support for live migration
- ✅ Simpler than iSCSI LVM

**Disadvantages:**
- ⚠️ Slightly lower performance (acceptable for labs)

---

#### Option B: Convert to Shared iSCSI LVM (Best Performance)
**On TrueNAS:**
1. Keep iSCSI target, add proxmox01 IQN to ACL
2. Both nodes connect to same LUN

**On Both Proxmox Nodes:**
1. After clustering, configure as clustered LVM
2. Enable distributed locking (DLM)
3. Both nodes can safely access

**Advantages:**
- ✅ Better performance than NFS
- ✅ True shared block storage
- ✅ Industry-standard cluster setup

**Disadvantages:**
- ⚠️ Requires clustering first
- ⚠️ More complex configuration
- ⚠️ Requires distributed lock manager

---

#### Option C: Keep as ZFS, Use Replication
**On proxmox02:**
1. Keep using proxpool for proxmox02 VMs

**On TrueNAS:**
2. Allocate separate LUN for proxmox01

**Between nodes:**
3. Set up Proxmox ZFS replication for failover

**Advantages:**
- ✅ Each node gets high-performance ZFS
- ✅ Replication for DR/backup

**Disadvantages:**
- ⚠️ Not true shared storage
- ⚠️ Can't live-migrate between nodes
- ⚠️ More complex failover process

---

### Phase 3: Cluster the Nodes

Same as before, but now with better storage architecture:
1. Critical VMs on local disk (immune to clustering changes)
2. SAN properly configured as shared storage
3. Cluster provides unified management

---

## Immediate Action Plan (REVISED)

### Step 1: Verify Local Disk Space (Now)
```bash
# On proxmox02
df -h /mnt/esxstore
pvesm status | grep esxstore

# Check VM disk sizes
qm config 100 | grep scsi0
qm config 108 | grep scsi0  
qm config 109 | grep scsi0
```

**Expected:**
- esxstore: ~2.9TB available
- agentx: ~32GB (typical)
- prod-app: ~32-100GB
- prod-db: ~32-100GB
- **Total needed:** ~200GB max
- **Plenty of room** ✅

---

### Step 2: Move Critical VMs to Local Disk (This Week, Low-Usage Window)

**Order:** (Least critical first)
1. glassdome-prod-db (VM 109) - Test the process
2. glassdome-prod-app (VM 108) - Verify apps work
3. agentx (VM 100) - Last, since we're on it

**For Each VM:**
```bash
# Shutdown gracefully
qm shutdown <vmid>

# Move disk
qm move-disk <vmid> scsi0 esxstore

# Start and verify
qm start <vmid>

# Check it works
# (SSH, curl endpoints, check logs)

# Once confirmed, old disk removed automatically
```

**Rollback if needed:**
```bash
# Move back to proxpool
qm move-disk <vmid> scsi0 proxpool
```

---

### Step 3: Plan SAN Restructuring (After VMs Moved)

**Decision point:** NFS vs iSCSI LVM?

**For Glassdome Canvas Labs:**
- NFS is simpler and sufficient
- Can always upgrade to iSCSI LVM later if needed

**Recommendation:**
1. Move VMs first (this week)
2. Test current setup for a few days
3. Then reconfigure SAN as NFS (next week)
4. Cluster nodes (following week)

---

## Updated Risk Assessment

### Moving VMs to Local Disk
**Risk:** Low ✅
- `qm move-disk` is safe, copies data
- Can test with prod-db first (least critical)
- Can roll back if issues
- Brief downtime per VM (~5-10 min)

**Mitigation:**
- Do during low-usage window
- Have console access ready
- Move DB first, then app, then agent last
- Take snapshots before moving (optional)

### SAN Reconfiguration
**Risk:** Medium (after VMs moved) ⚠️
- Data already moved off, so safe to wipe/reconfigure
- Requires coordination with TrueNAS
- Can take time to complete

**Mitigation:**
- Only start after all critical VMs confirmed working on local disk
- Can keep proxpool as-is for non-critical VMs during transition

---

## Why This is Better

### Old Approach (Keep as-is)
- ❌ Critical VMs depend on SAN
- ❌ 29TB SAN wasted on single-node ZFS
- ❌ Hard to share storage between nodes
- ⚠️ Network becomes single point of failure for core services

### New Approach (Your Suggestion)
- ✅ Critical VMs on fast local disk
- ✅ Independent of SAN/network
- ✅ 29TB SAN freed up for proper shared storage
- ✅ Much better fit for lab VMs
- ✅ More resilient architecture

---

## Summary

### Immediate Plan
1. **Tonight/Tomorrow:** Verify disk space on esxstore
2. **This Week:** Move 3 critical VMs to local disk (1 hour total, off-hours)
3. **Next Week:** Reconfigure 29TB SAN as shared NFS
4. **Following Week:** Cluster the nodes

### Why This Order
- Gets critical infrastructure off SAN dependency first
- Makes SAN reconfiguration risk-free (data already moved)
- Sets up proper shared storage for lab deployments
- Enables clustering with confidence

### What I Need
- ✅ Confirmation to proceed with VM moves
- ✅ Preferred low-usage window (time of day)
- ✅ Decision on SAN format: NFS (simple) vs iSCSI LVM (complex, faster)

Ready to start with Step 1 (verify disk space)?

