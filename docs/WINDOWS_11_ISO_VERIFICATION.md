# Windows 11 ISO Verification Guide

**Date:** 2024-11-22  
**Purpose:** Verify Windows 11 ISO is authentic and from Microsoft

---

## Official Microsoft Sources

### 1. Windows 11 Enterprise Evaluation (Recommended for Testing)

**Official URL:** https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise

**What to Download:**
- **Product:** Windows 11 Enterprise Evaluation
- **File Name:** `SW_DVD9_Win_Pro_11_22H2.5_64BIT_English_Pro_Ent_EDU_N_MLF_X23-59285.ISO`
- **Size:** ~5.5 GB
- **Edition:** Enterprise (includes all features)

**Verification Steps:**
1. Download directly from Microsoft Eval Center
2. Check file hash (SHA256) if provided by Microsoft
3. Verify file size matches expected (~5.5 GB)
4. File should be named with Microsoft naming convention

---

### 2. Windows 11 ISO via Media Creation Tool

**Official URL:** https://www.microsoft.com/en-us/software-download/windows11

**Steps:**
1. Download Media Creation Tool
2. Run `MediaCreationTool.exe`
3. Select "Create installation media (USB flash drive, DVD, or ISO file) for another PC"
4. Choose:
   - Language: English (United States)
   - Edition: Windows 11 (multi-edition ISO)
   - Architecture: 64-bit (x64)
5. Select "ISO file" option
6. Save to location

**File Name Pattern:**
- `Win11_22H2_English_x64.iso` or similar
- Size: ~5.5 GB

---

## Verification Checklist

### ✅ File Source Verification

- [ ] Downloaded from `microsoft.com` domain
- [ ] URL contains `/evalcenter/` or `/software-download/`
- [ ] Not from third-party sites (avoid: softonic, filehippo, etc.)

### ✅ File Name Verification

**Microsoft Naming Patterns:**
- `SW_DVD9_Win_Pro_11_*` (Enterprise Evaluation)
- `Win11_*_English_x64.iso` (Media Creation Tool)
- Contains version/build number (e.g., `22H2`, `23H2`)

**Red Flags:**
- Generic names like `windows11.iso` (without version/build)
- Names with suspicious characters
- Names from unknown sources

### ✅ File Size Verification

**Expected Sizes:**
- Windows 11 Enterprise Evaluation: ~5.5 GB (5,500,000,000 bytes)
- Windows 11 Home/Pro ISO: ~5.5 GB
- **Note:** Exact size may vary slightly by build

**Red Flags:**
- Significantly smaller (< 4 GB) - may be incomplete or modified
- Significantly larger (> 7 GB) - may contain additional software

### ✅ File Hash Verification (If Available)

Microsoft sometimes provides SHA256 hashes. Verify using:

```bash
# Linux/Mac
sha256sum windows-11-enterprise-eval.iso

# Windows PowerShell
Get-FileHash windows-11-enterprise-eval.iso -Algorithm SHA256
```

Compare with hash provided by Microsoft (if available).

---

## How to Verify ISO Contents

### Method 1: Mount and Inspect (Linux/Mac)

```bash
# Mount ISO
sudo mkdir /mnt/win11
sudo mount -o loop windows-11-enterprise-eval.iso /mnt/win11

# Check for Microsoft files
ls /mnt/win11/
# Should see: sources/, boot/, efi/, setup.exe, etc.

# Check version info
cat /mnt/win11/sources/ei.cfg
# Should show Microsoft copyright

# Unmount
sudo umount /mnt/win11
```

### Method 2: Extract and Check (Windows)

1. Right-click ISO → Mount
2. Open mounted drive
3. Check for:
   - `setup.exe` (Microsoft installer)
   - `sources/` directory
   - `boot/` directory
   - `efi/` directory
4. Right-click `setup.exe` → Properties → Digital Signatures
   - Should show "Microsoft Corporation" signature

---

## Red Flags - DO NOT USE

❌ **Third-party download sites:**
- Softonic, FileHippo, CNET Downloads
- Torrent sites
- "Free Windows 11" sites

❌ **Suspicious file names:**
- `windows11-cracked.iso`
- `windows11-activator.iso`
- Generic names without version numbers

❌ **Modified ISOs:**
- Pre-activated versions
- "Lite" or "Tiny" versions
- ISOs with additional software bundled

❌ **Wrong file size:**
- Much smaller than 5 GB
- Much larger than 6 GB

---

## Recommended Download Method

**For Glassdome Templates:**

1. **Use Enterprise Evaluation ISO** (90-day trial, full features)
   - URL: https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise
   - Best for: Testing, development, cyber range labs
   - No license required for evaluation period

2. **Download directly from Microsoft**
   - Never use third-party sites
   - Verify URL is `microsoft.com`

3. **Verify file after download**
   - Check file size (~5.5 GB)
   - Check file name matches Microsoft pattern
   - Mount and verify contents if possible

---

## Current Windows 11 ISO Status

**VM 9101 (Windows 11 Template):**
- **Current ISO:** Check Proxmox storage
- **Status:** ⚠️ User reported it's actually Windows 10
- **Action Required:** Download authentic Windows 11 ISO from Microsoft

**Next Steps:**
1. Download Windows 11 Enterprise Evaluation ISO from Microsoft
2. Upload to Proxmox: `/var/lib/vz/template/iso/`
3. Re-run `scripts/setup_windows11_complete.py`
4. Verify installation shows "Windows 11" (not Windows 10)

---

## Windows 11 vs Windows 10 Identification

**During Installation:**
- Windows 11: Shows "Windows 11" branding
- Windows 10: Shows "Windows 10" branding

**After Installation:**
```powershell
# Check version
Get-ComputerInfo | Select WindowsProductName, WindowsVersion

# Windows 11 should show:
# WindowsProductName: Windows 11 Enterprise
# WindowsVersion: 10.0.22621 (or higher)
```

**Visual Differences:**
- Windows 11: Centered taskbar, rounded corners
- Windows 10: Left-aligned taskbar, square corners

---

## References

- **Microsoft Eval Center:** https://www.microsoft.com/en-us/evalcenter/
- **Windows 11 Download:** https://www.microsoft.com/en-us/software-download/windows11
- **Windows 11 Enterprise Eval:** https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise




