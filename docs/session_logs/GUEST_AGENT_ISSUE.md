# Guest Agent Deployment Issue

**Date:** 2024-11-21  
**Issue:** QEMU guest agent not running in deployed VMs

## Problem

- Template 9000 has `agent: enabled=1` in Proxmox config
- But `qemu-guest-agent` package is NOT installed inside the Ubuntu image
- VMs cloned from template don't have guest agent running
- IP detection fails because guest agent is required

## Root Cause

The template creation process:
1. ✅ Enables agent in Proxmox: `qm set 9000 --agent enabled=1`
2. ❌ Does NOT install `qemu-guest-agent` package inside the Ubuntu image
3. ❌ Does NOT configure cloud-init to install it on first boot

## Solution

**Option 1: Install in Template (Recommended)**
- Boot template VM
- Install `qemu-guest-agent`
- Enable and start service
- Convert back to template

**Option 2: Install via Cloud-Init (Current Attempt)**
- Pass `packages: ["qemu-guest-agent"]` to cloud-init during clone
- Cloud-init installs it on first boot
- But this requires cloud-init to be properly configured

**Current Status:**
- Deployment script includes `qemu-guest-agent` in packages list
- But cloud-init may not be processing packages correctly
- Need to verify cloud-init user-data is being set properly

## Fix Required

1. Update template creation to install qemu-guest-agent in template
2. OR ensure cloud-init properly installs it on first boot
3. Verify guest agent is running after deployment

