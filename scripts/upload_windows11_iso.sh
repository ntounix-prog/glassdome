#!/bin/bash
# Upload Windows 11 ISO to Proxmox

PROXMOX_HOST="${PROXMOX_HOST:-192.168.3.2}"
PROXMOX_USER="${PROXMOX_USER:-root}"

# Check for Windows 11 ISO locally
WINDOWS11_ISO=""

# Check common locations
if [ -f "isos/windows/windows-11-enterprise-eval.iso" ]; then
    WINDOWS11_ISO="isos/windows/windows-11-enterprise-eval.iso"
elif [ -f "windows-11-enterprise-eval.iso" ]; then
    WINDOWS11_ISO="windows-11-enterprise-eval.iso"
elif [ -f "windows-11*.iso" ]; then
    WINDOWS11_ISO=$(ls windows-11*.iso | head -1)
fi

if [ -z "$WINDOWS11_ISO" ]; then
    echo "❌ Windows 11 ISO not found locally"
    echo ""
    echo "Please download Windows 11 ISO from:"
    echo "  https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise"
    echo ""
    echo "Then place it in: isos/windows/windows-11-enterprise-eval.iso"
    echo "Or run this script with the ISO path:"
    echo "  WINDOWS11_ISO=/path/to/windows-11.iso ./upload_windows11_iso.sh"
    exit 1
fi

echo "📦 Uploading Windows 11 ISO to Proxmox..."
echo "   Source: $WINDOWS11_ISO"
echo "   Destination: ${PROXMOX_USER}@${PROXMOX_HOST}:/var/lib/vz/template/iso/"

# Get file size
SIZE=$(du -h "$WINDOWS11_ISO" | cut -f1)
echo "   Size: $SIZE"
echo ""

# Upload
scp "$WINDOWS11_ISO" "${PROXMOX_USER}@${PROXMOX_HOST}:/var/lib/vz/template/iso/"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Windows 11 ISO uploaded successfully!"
    echo ""
    echo "Next: Run python scripts/fix_windows11_iso.py to attach it to VM 9101"
else
    echo ""
    echo "❌ Upload failed"
    exit 1
fi

