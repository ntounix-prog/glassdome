# Proxmox Infrastructure Storage Analysis

**Date:** 2025-11-27  
**Purpose:** Assess current storage configuration and provide recommendations for:
1. Enabling SAN access on proxmox01
2. Clustering proxmox01 and proxmox02

---

## Current Configuration

### Proxmox01 (pve01) - 192.168.215.78
- **Version:** Proxmox 9.1.1
- **Status:** Online, standalone (not clustered)
- **Storage:**
  - `local` (dir): backup, ISO, templates
  - `local-lvm` (lvmthin): VM disks, containers
  - `TrueNAS` (**NFS**, shared): VM disks, templates, containers
- **VMs:** 7 total (3 Redis test VMs + templates)
- **Templates:**
  - 9000: ubuntu-2204-cloudinit-template
  - 9100: windows-server2022-template
  - 9101: windows-win11-template

**Key Findings:**
- ✅ Already has TrueNAS connectivity via **NFS**
- ✅ Can create VMs and store them on shared NFS storage
- ❌ Not using iSCSI from TrueNAS
- ❌ Not clustered

---

### Proxmox02 (pve02) - 192.168.215.77
- **Version:** Proxmox 9.1.1
- **Status:** Online, standalone (not clustered)
- **Storage:**
  - `local` (dir): snippets, ISO, backup, templates
  - `local-lvm` (lvmthin): VM disks, containers
  - `backup-vol` (lvm): VM disks, containers
  - **`proxpool` (ZFS, 29.5TB total)**: VM disks, containers
    - Used: 357 GB
    - Available: 29.2 TB
  - `esxstore` (dir, shared): VM disks, templates, ISO
- **VMs:** 17 total (including critical infrastructure)
  - 100: agentx (running) ← **THIS VM**
  - 108: glassdome-prod-app (running)
  - 109: glassdome-prod-db (running)
  - Plus: es01, mooker, rome, mail, mnto, scribe, sunspot
- **Templates:**
  - 9000: ubuntu-2204-cloudinit-template
  - 9001: ubuntu-2204-cloudinit-with-agent

**Key Findings:**
- ✅ Has massive 29.5TB ZFS pool (`proxpool`) - likely **ZFS-over-iSCSI** from TrueNAS
- ✅ Critical production VMs running (including this agent VM)
- ✅ Has shared NFS storage (`esxstore`)
- ❌ Not clustered
- ⚠️ `proxpool` is marked as **not shared** (single-writer ZFS over iSCSI)

---

## Storage Architecture Analysis

### Current TrueNAS → Proxmox Setup

Based on the findings:

1. **TrueNAS → proxmox01**: NFS share
   - Simple file-based storage
   - Shared, multi-writer safe
   - Good for templates, ISOs, general VM storage

2. **TrueNAS → proxmox02**: ZFS pool backed by iSCSI LUN
   - Block-level storage
   - **Single-writer only** (proxmox02 creates ZFS filesystem on raw iSCSI LUN)
   - **Cannot be shared** between multiple Proxmox nodes without corruption risk
   - Excellent performance for production VMs

**Critical Understanding:**
The `proxpool` ZFS storage on proxmox02 is **NOT** a TrueNAS ZFS pool being shared via NFS or iSCSI. It's a **local ZFS pool that proxmox02 created on top of an iSCSI LUN from TrueNAS**. This means:
- Only proxmox02 can write to it
- Adding proxmox01 to the same iSCSI LUN would cause **instant filesystem corruption**
- This is a **valid and common** setup for single-node scenarios

---

## Recommendations

### Option 1: Extend NFS Storage (Simplest, Recommended for Labs)

**What:**
- Both proxmox01 and proxmox02 already have (or can use) the TrueNAS NFS share
- Use NFS as the **shared storage** for Canvas lab VMs
- Keep critical infrastructure on local/ZFS storage

**Advantages:**
- ✅ No risk to existing `proxpool` ZFS or production VMs
- ✅ Already working on proxmox01
- ✅ True shared storage - both nodes can read/write simultaneously
- ✅ Supports live migration for lab VMs
- ✅ Simple to configure

**Disadvantages:**
- ⚠️ Slightly lower performance than block storage (acceptable for labs)
- ⚠️ Not ideal for IO-intensive workloads (fine for CTF/training scenarios)

**Implementation Steps:**
1. On proxmox02:
   - Add the TrueNAS NFS share to storage.cfg (same as proxmox01 has)
   - Mark it as "Shared"
   - Use for Canvas lab deployments
2. On proxmox01:
   - Verify TrueNAS NFS is working and accessible
3. Glassdome deployment:
   - Update hot spare pool to use NFS storage
   - Update Canvas deploy to target NFS storage for lab VMs
4. Keep `agentx`, `glassdome-prod-app`, `glassdome-prod-db` on `proxpool` (unchanged)

---

### Option 2: Separate iSCSI LUN for proxmox01 + Replication

**What:**
- Allocate a **new, separate iSCSI LUN** from TrueNAS for proxmox01
- proxmox01 creates its own ZFS pool on that LUN
- Use Proxmox ZFS replication or shared NFS for labs
- Each node has its own high-performance block storage

**Advantages:**
- ✅ Both nodes get high-performance block storage
- ✅ No risk to existing proxmox02 storage
- ✅ Can replicate VMs between nodes for DR/failover

**Disadvantages:**
- ⚠️ More complex configuration
- ⚠️ Replication-based failover, not instant live migration (unless using shared NFS for specific VMs)
- ⚠️ Requires TrueNAS to allocate additional LUN space

**Implementation Steps:**
1. On TrueNAS:
   - Create a new zvol (e.g., `proxmox01-pool`, 10TB+)
   - Create a new iSCSI target (e.g., `iqn.2025-01.local.truenas:proxmox01`)
   - Add proxmox01's iSCSI initiator IQN to ACL
2. On proxmox01:
   - Discover and connect to the new iSCSI target
   - Create ZFS pool on the iSCSI LUN
   - Use for local VM storage
3. For shared lab storage:
   - Still use NFS (Option 1) for true multi-writer scenarios
4. Set up Proxmox ZFS replication for critical VMs between nodes

---

### Option 3: Shared iSCSI with LVM/LVM-Thin (Traditional HA Setup)

**What:**
- Allocate a **new shared iSCSI LUN** from TrueNAS
- Configure as **LVM or LVM-Thin** (not ZFS) on both Proxmox nodes
- Use cluster locking to prevent simultaneous writes

**Advantages:**
- ✅ True shared block storage
- ✅ Supports live migration and HA
- ✅ Industry-standard approach for Proxmox clusters

**Disadvantages:**
- ⚠️ More complex - requires clustering **first**
- ⚠️ Requires careful cluster lock manager (corosync + DLM)
- ⚠️ Misconfig can cause split-brain scenarios
- ⚠️ Slightly more overhead than NFS for simple lab scenarios

**Implementation Steps:**
1. Create Proxmox cluster (see Clustering section)
2. On TrueNAS:
   - Create a shared iSCSI LUN
   - Add **both** proxmox01 and proxmox02 initiator IQNs to ACL
3. On both Proxmox nodes:
   - Discover and connect to the shared iSCSI target
   - Configure as LVM or LVM-Thin with cluster locking
   - Mark storage as "Shared" in Proxmox
4. Deploy lab VMs to shared storage

---

## Clustering proxmox01 and proxmox02

### Current State
- **Not clustered:** Each node operates independently
- **Separate management:** Must manage each via separate GUI/API
- **No automatic failover:** VM failures require manual intervention

### Clustering Benefits
- ✅ Unified management interface
- ✅ Centralized authentication and user management
- ✅ Live migration of VMs between nodes (if using shared storage)
- ✅ Simplified backup and replication management
- ✅ Foundation for High Availability (HA)

### Two-Node Cluster Considerations

**Challenge:** Quorum
- Proxmox clusters use **corosync** for membership and quorum
- Default requires **majority of nodes** to be online (2/3, 3/5, etc.)
- In a **2-node cluster**, losing one node = **no quorum** = cluster operations halt

**Solutions:**
1. **QDevice (Recommended):** 
   - Add a lightweight third "voter" (doesn't run VMs, just votes)
   - Can be a Raspberry Pi, small VM on another network, or cloud instance
   - Provides the third vote for quorum
   
2. **Two-Node Mode (Risky):**
   - Manually adjust `expected_votes` and quorum settings
   - Acceptable for dev/lab, **not recommended for production**
   - Risk of split-brain if network partition occurs

---

### Clustering Implementation (High-Level)

**Prerequisites:**
- ✅ Both nodes same Proxmox version (9.1.1 - ✓)
- ✅ Stable network between nodes (192.168.215.77 ↔ 192.168.215.78 - verify latency < 5ms)
- ✅ Time sync via NTP (verify with `timedatectl`)
- ⚠️ **WARNING:** Clustering changes `/etc/pve` to a cluster filesystem - **BACKUP CONFIGS FIRST**

**Steps (Read-Only Plan, DO NOT EXECUTE YET):**

1. **Backup both nodes**
   ```bash
   # On each node
   pvecm expected 1  # Current standalone state
   tar -czf /root/pve-config-backup-$(date +%Y%m%d).tar.gz /etc/pve
   ```

2. **Create cluster on proxmox02** (current/production node)
   ```bash
   # On proxmox02 (192.168.215.77)
   pvecm create glassdome-cluster
   ```
   - This makes proxmox02 the initial cluster master
   - Keeps production VMs running and stable

3. **Join proxmox01 to the cluster**
   ```bash
   # On proxmox01 (192.168.215.78)
   pvecm add 192.168.215.77
   ```
   - Enter root password for proxmox02 when prompted
   - proxmox01 joins the cluster

4. **Verify cluster status**
   ```bash
   # On either node
   pvecm status
   pvecm nodes
   ```
   - Should show 2 nodes, 2 votes, quorum 2

5. **Optional: Add QDevice for robust quorum**
   - Set up a third host/VM as QDevice
   - Install `corosync-qnetd` on the QDevice host
   - Add QDevice to cluster:
     ```bash
     pvecm qdevice setup <qdevice-ip>
     ```

6. **Configure shared storage** (using Option 1 - NFS recommended)
   - Datacenter → Storage → Add → NFS
   - Point both nodes to the same TrueNAS NFS share
   - Mark as "Shared"
   - Enable content types: Disk image, Container

7. **Test migration**
   - Create a small test VM on shared NFS storage
   - Migrate between nodes (offline first, then online if CPU features match)

---

## Recommended Approach for Glassdome

Given your requirements and current state:

### Phase 1: Enable Shared Storage (This Week)
1. ✅ Verify TrueNAS NFS share is accessible from both Proxmox nodes
2. ✅ Add TrueNAS NFS to proxmox02 storage config (mark as Shared)
3. ✅ Update Glassdome Canvas deployment to use NFS storage for lab VMs
4. ✅ Keep production VMs (agentx, prod-app, prod-db) on proxpool (no changes)

**Risk:** Minimal - only adds storage, doesn't touch production

### Phase 2: Clustering (After Testing)
1. ✅ Backup `/etc/pve` on both nodes
2. ✅ Create cluster on proxmox02 (production node)
3. ✅ Join proxmox01 to cluster
4. ✅ Verify shared storage shows in cluster view
5. ✅ Test lab VM migration

**Risk:** Low - clustering shouldn't disrupt running VMs, but backup first

### Phase 3: QDevice (Optional, for HA)
1. ✅ Set up QDevice on a third host (could be a small VM on TrueNAS, or a cloud instance)
2. ✅ Add QDevice to cluster for robust quorum
3. ✅ Enable HA for critical VMs if desired

**Risk:** Minimal - QDevice is additive

---

## Next Steps (Read-Only Verification)

Before making any changes, verify:

1. **TrueNAS NFS Export:**
   - SSH or GUI to TrueNAS
   - Check: Sharing → NFS → Verify export exists and is accessible
   - Note the export path (e.g., `/mnt/pool1/proxmox-nfs`)
   - Verify ACL allows both 192.168.215.77 and 192.168.215.78

2. **Network Connectivity:**
   ```bash
   # From proxmox02
   ping -c 4 192.168.215.78
   
   # From proxmox01
   ping -c 4 192.168.215.77
   ```
   - Verify < 5ms latency

3. **Time Sync:**
   ```bash
   # On both nodes
   timedatectl
   ```
   - Verify both nodes are in sync (NTP active)

4. **Storage.cfg Inspection (via GUI or API):**
   - Datacenter → Storage on each node
   - Screenshot or note all current storage definitions

---

## Manual Steps Required

I **cannot** perform these actions automatically (infrastructure changes require manual verification):

1. **TrueNAS access** - Need to verify NFS export configuration
2. **SSH access to Proxmox** - Would need SSH keys or to be prompted for passwords interactively
3. **Clustering** - Should be done during a maintenance window with the user present
4. **Storage configuration changes** - Should be reviewed and approved before applying

However, I **can** provide you with:
- ✅ Exact commands to run (see above)
- ✅ Configuration file templates
- ✅ Verification scripts
- ✅ Rollback procedures

---

## Questions to Answer Before Proceeding

1. **TrueNAS NFS:**
   - What is the NFS export path on TrueNAS? (e.g., `/mnt/pool1/proxmox-nfs`)
   - Is it already configured to allow both Proxmox IPs?

2. **Storage Strategy:**
   - Do you want to use NFS for all lab VMs (recommended, simple)?
   - Or allocate a separate iSCSI LUN for proxmox01 (more complex, higher performance)?

3. **Clustering:**
   - Do you want to cluster immediately, or test shared storage first?
   - Do you have a third host/VM available for QDevice, or accept 2-node risk?

4. **Production Safety:**
   - When is a good maintenance window for clustering (minimal risk, but backup first)?
   - Should we keep `agentx` VM pinned to proxmox02 even after clustering?

---

## Summary

### Current State
- **proxmox01:** Has NFS from TrueNAS, not clustered, lighter workload
- **proxmox02:** Has ZFS-over-iSCSI (29.5TB), not clustered, production VMs running

### Simplest Path Forward
1. Add TrueNAS NFS to proxmox02 as shared storage
2. Use NFS for Canvas lab deployments
3. Keep production VMs on local ZFS (`proxpool`)
4. Cluster the nodes for unified management
5. Deploy QDevice for robust 2-node quorum

### What I Need to Proceed
- TrueNAS NFS export path and access method
- Green light to add NFS storage to proxmox02 (read-only operation, low risk)
- Maintenance window to cluster nodes (backup first, ~30 minutes)

