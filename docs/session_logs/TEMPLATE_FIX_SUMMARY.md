# Template 9000 Guest Agent Fix Summary

**Date:** 2024-11-21  
**Issue:** qemu-guest-agent not installed in template, causing IP detection failures

## Problem

- Template 9000 has `agent: enabled=1` in Proxmox config ✅
- But `qemu-guest-agent` package is NOT installed inside Ubuntu image ❌
- VMs cloned from template don't have guest agent running
- IP detection fails: `QEMU guest agent is not running`

## Automated Fix Attempted

**Script Created:** `fix_template_guest_agent()`
- Converts template to VM
- Configures cloud-init with SSH keys
- Starts VM and waits for IP
- Installs qemu-guest-agent via SSH
- Converts back to template

**Current Status:** 
- ⚠️ VM not getting IP automatically (VLAN 2, DHCP, or cloud-init issue)
- Manual intervention may be required

## Manual Fix Required

**Option 1: Via Console (Recommended)**
1. Convert template to VM: `qm set 9000 --template 0`
2. Start VM: `qm start 9000`
3. Access console via Proxmox web UI
4. Login as `ubuntu` (password may be needed if SSH keys not set)
5. Install: `sudo apt update && sudo apt install -y qemu-guest-agent`
6. Enable: `sudo systemctl enable qemu-guest-agent`
7. Start: `sudo systemctl start qemu-guest-agent`
8. Stop VM: `qm stop 9000`
9. Convert back: `qm template 9000`

**Option 2: Via SSH (If IP known)**
1. Get VM IP from Proxmox or network scan
2. SSH: `ssh -i /tmp/glassdome_key ubuntu@<ip>`
3. Install and enable guest agent (same commands as above)

## Future Automation

**Overseer Integration:**
- ✅ Created `GuestAgentFixer` class
- ✅ Detects guest agent issues
- ✅ Auto-fixes via SSH when IP is available
- ✅ Integrated into `OverseerAgent.check_vm()`

**How It Works:**
1. Overseer checks each VM's guest agent status
2. If not working, attempts to fix via SSH
3. Requires VM to have IP address (chicken-and-egg problem)
4. For new deployments, ensures guest agent is installed post-deployment

## Next Steps

1. **Immediate:** Manually fix template 9000 (see Option 1 above)
2. **Short-term:** Update template creation to install qemu-guest-agent
3. **Long-term:** Overseer will auto-fix guest agent issues in deployed VMs

## Files Created/Modified

- `glassdome/agents/guest_agent_fixer.py` - New guest agent fixer class
- `glassdome/agents/overseer.py` - Updated with guest agent checking
- `docs/session_logs/GUEST_AGENT_ISSUE.md` - Issue documentation
- `docs/session_logs/GUEST_AGENT_FIX.md` - Fix documentation

