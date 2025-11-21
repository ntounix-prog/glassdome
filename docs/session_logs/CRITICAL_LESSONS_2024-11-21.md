# Critical Lessons Learned - November 21, 2024

**Purpose:** Key mistakes and insights to feed into RAG system

---

## ❌ MISTAKE: Cloud-Init Template Requires SSH Keys, Not Password Auth

**Date:** 2024-11-21  
**Context:** Deploying Redis vulnerable server, SSH connection failed  
**User Correction:** "you've been through this before.. the cloud agent doesn't allow ID login, you must create keys.. this, like the vlan issue you should have known"

**Root Cause:**
- Ubuntu cloud-init templates are configured with `disable_root: true` and `ssh_pwauth: false` by default
- Password authentication is disabled for security
- Only SSH key-based authentication is allowed
- AI forgot this requirement from previous sessions

**Correct Approach:**

### Cloud-Init Template Authentication: SSH KEYS ONLY

**Configuration:**
- **REQUIRED:** SSH public key must be provided via `sshkeys` parameter
- **Format:** Base64 encoded public key string
- **Proxmox Command:** `qm set <vmid> --sshkeys <base64_encoded_key>`
- **Alternative:** Can also pass key content directly (Proxmox accepts both)

**Correct Deployment Pattern:**
```python
# Read SSH public key
ssh_key_path = Path("/tmp/glassdome_key")
ssh_pub_key_path = Path("/tmp/glassdome_key.pub")

if not ssh_pub_key_path.exists() and ssh_key_path.exists():
    # Generate public key from private key
    result = subprocess.run(
        ["ssh-keygen", "-y", "-f", str(ssh_key_path)],
        capture_output=True,
        text=True,
        check=True
    )
    ssh_pub_key = result.stdout.strip()

# Configure VM with SSH key
vm_config = {
    "ssh_user": "ubuntu",
    "ssh_key_path": "/tmp/glassdome_key",  # CRITICAL: Required for cloud-init
    # NO password - cloud-init template doesn't support it
}

# In ProxmoxClient.clone_vm_from_template():
if ssh_pub_key:
    import base64
    ssh_key_b64 = base64.b64encode(ssh_pub_key.encode()).decode()
    vm_config_updates["sshkeys"] = ssh_key_b64
```

**SSH Connection:**
```python
# Use SSH key, NOT password
ssh.connect(
    ip_address,
    username="ubuntu",
    key_filename="/tmp/glassdome_key",  # Use key file
    timeout=10
)
```

**Why This Matters:**
- VMs deployed without SSH keys cannot be accessed
- Wastes time debugging "Permission denied" errors
- Blocks all post-deployment configuration
- Template must be configured with SSH keys at creation time

**RAG Query Pattern:**
- "How to authenticate to cloud-init Ubuntu VMs?" → Answer: SSH keys only, no password
- "Proxmox cloud-init SSH authentication" → Answer: Use `sshkeys` parameter with base64 encoded public key

---

## ❌ MISTAKE: Forgot VLAN Tag Requirement (Repeated)

**Date:** 2024-11-21  
**Context:** Redis deployment, IP detection failing  
**User Correction:** "you do know you have to set the vlan to 2 correct?"

**Root Cause:**
- AI forgot VLAN tag requirement from previous session
- 192.168.3.x network requires VLAN tag 2 on vmbr0
- Without VLAN tag, VM gets wrong network (192.168.2.x)

**Solution:**
- Always set `vlan_tag: 2` for 192.168.3.x network deployments
- Proxmox command: `qm set <vmid> --net0 virtio,bridge=vmbr0,tag=2`

**RAG Query Pattern:**
- "Proxmox 192.168.3.x network configuration" → Answer: Requires VLAN tag 2

---

## ✅ FIXED: ProxmoxClient SSH Key Configuration

**Implementation:**
- Updated `clone_vm_from_template()` to read SSH key from config
- Generate public key from private key if needed
- Base64 encode and set via `sshkeys` parameter
- Proper logging for debugging

**Location:** `glassdome/platforms/proxmox_client.py:405-437`

---

## ✅ FIXED: DHCP Support

**Change:**
- Removed static IP requirement from deployment script
- Now uses DHCP for IP assignment
- Waits for guest agent to report IP
- Falls back to hostname if IP not available

**Location:** `scripts/deploy_redis_vulnerable.py`

---

## 📋 Template Recreation Required

**Issue:** Template 9000 was deleted during cleanup  
**Action Required:** Recreate Ubuntu 22.04 template

**Steps:**
1. SSH to Proxmox: `ssh root@192.168.3.2`
2. Download cloud image: `wget https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img`
3. Create VM 9000 and import disk
4. Configure cloud-init with SSH keys
5. Convert to template

**Or use automated script:**
```bash
python scripts/deployment/create_template_auto.py
```

---

**For RAG System:** These patterns must be remembered:
1. Cloud-init templates = SSH keys only (no password)
2. 192.168.3.x network = VLAN tag 2 required
3. Always check existing documentation before deploying

