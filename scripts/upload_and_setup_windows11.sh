#!/bin/bash
# Complete Windows 11 setup: Upload ISO and configure VM

set -e

PROXMOX_HOST="${PROXMOX_HOST:-192.168.3.2}"
ISO_FILE="isos/windows/windows-11-enterprise-eval.iso"

echo "======================================================================"
echo "  WINDOWS 11 COMPLETE SETUP"
echo "======================================================================"
echo ""

# Check if ISO exists
if [ ! -f "$ISO_FILE" ]; then
    echo "❌ Windows 11 ISO not found: $ISO_FILE"
    exit 1
fi

echo "✅ Found Windows 11 ISO: $ISO_FILE"
SIZE=$(du -h "$ISO_FILE" | cut -f1)
echo "   Size: $SIZE"
echo ""

# Upload to Proxmox
echo "📤 Uploading to Proxmox..."
echo "   This may take several minutes (5.17 GB)..."
scp "$ISO_FILE" "root@${PROXMOX_HOST}:/var/lib/vz/template/iso/"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Upload complete!"
    echo ""
    echo "🚀 Starting Windows 11 installation setup..."
    echo ""
    
    # Run Python setup script
    cd "$(dirname "$0")/.."
    source venv/bin/activate
    python3 scripts/setup_windows11_complete.py
else
    echo ""
    echo "❌ Upload failed"
    echo ""
    echo "Please upload manually:"
    echo "  scp $ISO_FILE root@${PROXMOX_HOST}:/var/lib/vz/template/iso/"
    echo ""
    echo "Then run:"
    echo "  python scripts/setup_windows11_complete.py"
    exit 1
fi

