#!/bin/bash
#
# Commands to run directly on Proxmox server to find template files
# 
# SSH to Proxmox and run these commands, or copy/paste into Proxmox console
#

echo "============================================================"
echo "  FIND TEMPLATE FILES IN /mnt"
echo "============================================================"
echo ""

# Search for VM disk images
echo "1. Searching for VM disk images (vm-*-disk-*):"
find /mnt -type f -name "vm-*-disk-*" -size +100M -exec ls -lh {} \; 2>/dev/null | head -50

echo ""
echo "2. Searching for disk image files (.qcow2, .raw, .img):"
find /mnt -type f \( -name "*.qcow2" -o -name "*.raw" -o -name "*.img" \) -size +100M -exec ls -lh {} \; 2>/dev/null | head -50

echo ""
echo "3. Searching for ISO files:"
find /mnt -type f -name "*.iso" -size +100M -exec ls -lh {} \; 2>/dev/null | head -50

echo ""
echo "4. Searching for Ubuntu cloud images:"
find /mnt -type f -name "*ubuntu*cloudimg*" -exec ls -lh {} \; 2>/dev/null

echo ""
echo "5. Searching for Windows ISOs:"
find /mnt -type f -name "*windows*.iso" -exec ls -lh {} \; 2>/dev/null

echo ""
echo "============================================================"
echo "  SUMMARY"
echo "============================================================"
echo ""
echo "Total template-related files found:"
find /mnt -type f \( -name "vm-*-disk-*" -o -name "*.qcow2" -o -name "*.raw" -o -name "*.img" -o -name "*.iso" \) -size +100M 2>/dev/null | wc -l

echo ""
echo "============================================================"
echo "  NEXT STEPS"
echo "============================================================"
echo ""
echo "1. Review the files found above"
echo "2. Identify which are templates (check VM IDs)"
echo "3. Move ISOs to: /var/lib/vz/template/iso/"
echo "4. Import VM disks using: qm importdisk <vmid> <file> local-lvm"
echo ""

