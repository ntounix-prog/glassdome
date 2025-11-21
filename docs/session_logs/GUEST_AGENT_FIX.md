# Guest Agent Fix - Template 9000

**Date:** 2024-11-21  
**Issue:** qemu-guest-agent not installed in template, causing IP detection failures

## Problem Identified

- Template 9000 has `agent: enabled=1` in Proxmox config ✅
- But `qemu-guest-agent` package is NOT installed inside the Ubuntu image ❌
- VMs cloned from template don't have guest agent running
- IP detection fails: `QEMU guest agent is not running`

## Root Cause

Proxmox's cloud-init API integration is limited:
- ✅ Supports: user, password, SSH keys, IP config, DNS
- ❌ Does NOT support: custom packages, custom user-data

The template was created from a cloud image that doesn't include qemu-guest-agent by default.

## Solution Options

### Option 1: Install in Template (Best for Performance)
1. Convert template back to VM
2. Boot VM
3. Install `qemu-guest-agent` via SSH or guest agent
4. Enable and start service
5. Convert back to template

**Pros:** Fast - all cloned VMs have it pre-installed  
**Cons:** Requires manual intervention or automation script

### Option 2: Install via Cloud-Init on Clone (Current Attempt)
- Use cloud-init user-data to install packages
- Requires custom cloud-init ISO or user-data injection
- Proxmox API doesn't support this easily

**Pros:** Template stays clean  
**Cons:** Slower first boot, requires cloud-init configuration

### Option 3: Post-Deployment Installation
- Deploy VM
- Wait for SSH
- Install qemu-guest-agent via SSH
- Start service

**Pros:** Works reliably  
**Cons:** Adds deployment time, requires SSH access

## Recommended Fix

**For Template 9000:**
1. Boot template as VM
2. Install qemu-guest-agent: `apt install -y qemu-guest-agent`
3. Enable service: `systemctl enable qemu-guest-agent`
4. Start service: `systemctl start qemu-guest-agent`
5. Convert back to template

**For Future Templates:**
- Update template creation script to install qemu-guest-agent
- Or use cloud-init user-data with packages list

## Status

- ✅ Issue identified
- ⏳ Fix in progress (template needs to be booted and configured)
- ⏳ Need to verify guest agent works after fix

