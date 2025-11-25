# Windows 10 Deployment Guide

**Date:** 2024-11-22  
**Status:** ✅ Script Created (Ready for Testing)

---

## Overview

Windows 10 deployment script has been created based on the Windows 11 deployment script. The template that was created as "Windows 11" is actually Windows 10, so this script handles that correctly.

---

## Script Location

**File:** `scripts/setup_windows10_complete.py`

**Template ID:** 9102 (Windows 10 template)

---

## Usage

```bash
python scripts/setup_windows10_complete.py
```

This script will:
1. Find Windows 10 ISO locally or on Proxmox
2. Upload ISO if needed (via API or SSH)
3. Configure VM with correct specs (4 vCPU, 16GB RAM, 30GB disk)
4. Generate autounattend.xml for Windows 10
5. Upload autounattend floppy
6. Attach ISOs (Windows 10 + VirtIO drivers)
7. Set boot order
8. Start VM and send Enter key

---

## Configuration

**VM Settings:**
- **VM ID:** 9102
- **CPU:** 4 vCPU
- **Memory:** 16GB (16384 MB)
- **Disk:** 30GB SATA
- **Network:** VLAN 2 (192.168.3.x)
- **Template Name:** `windows10-template`

**Autounattend:**
- **Windows Version:** `win10`
- **Image Index:** 1 (Windows 10 Enterprise)
- **Hostname:** `windows10-template`
- **Admin Password:** `Glassdome123!`
- **RDP:** Enabled

---

## Windows 10 ISO Download

**Official Source:**
- **URL:** https://www.microsoft.com/en-us/evalcenter/download-windows-10-enterprise
- **File Name:** `SW_DVD9_Win_Pro_Ent_10_22H2.5_64BIT_English_Pro_Ent_EDU_N_MLF_X23-59284.ISO`
- **Size:** ~5.5 GB

**Verification:**
- Download from `microsoft.com` domain only
- Verify file size (~5.5 GB)
- Check file name matches Microsoft pattern

---

## Differences from Windows 11 Script

1. **VM ID:** 9102 (instead of 9101)
2. **Template Name:** `windows10-template` (instead of `windows11-template`)
3. **ISO Search:** Looks for Windows 10 ISOs (not Windows 11)
4. **Autounattend:** Uses `windows_version: "win10"`

---

## Current Status

**VM 9101:**
- **Status:** Template completed
- **Actual OS:** Windows 10 (not Windows 11)
- **Action:** Use Windows 10 script for this template

**VM 9102:**
- **Status:** Ready for Windows 10 template creation
- **Action:** Run `scripts/setup_windows10_complete.py`

---

## Next Steps

1. **For VM 9101 (Windows 10):**
   - Template is already created
   - Can be used as Windows 10 template
   - Update template name in Proxmox to reflect Windows 10

2. **For VM 9102 (New Windows 10 Template):**
   - Run `scripts/setup_windows10_complete.py`
   - Follow installation process
   - After installation, convert to template: `qm template 9102`

3. **For Windows 11:**
   - Download authentic Windows 11 ISO from Microsoft
   - Verify it's actually Windows 11 (not Windows 10)
   - Use `scripts/setup_windows11_complete.py` with correct ISO

---

## Autounattend Support

Windows 10 is now supported in `glassdome/utils/windows_autounattend.py`:

```python
from glassdome.utils.windows_autounattend import generate_autounattend_xml

config = {
    "windows_version": "win10",  # ✅ Now supported
    "hostname": "windows10-vm",
    "admin_password": "Glassdome123!",
    "enable_rdp": True
}

xml = generate_autounattend_xml(config)
```

---

## References

- **Windows 10 Eval Center:** https://www.microsoft.com/en-us/evalcenter/download-windows-10-enterprise
- **Windows 11 ISO Verification:** See `docs/WINDOWS_11_ISO_VERIFICATION.md`




