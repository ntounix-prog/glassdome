#!/bin/bash
#
# Upload Windows and VirtIO ISOs to Proxmox
# 
# This script uploads the downloaded ISOs to Proxmox storage so they can be attached to VMs.
#

set -e

# Configuration
PROXMOX_HOST="${PROXMOX_HOST:-192.168.3.2}"
PROXMOX_USER="${PROXMOX_USER:-root}"
PROXMOX_STORAGE="${PROXMOX_STORAGE:-local}"
GLASSDOME_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "============================================================"
echo "  Upload ISOs to Proxmox"
echo "============================================================"
echo ""
echo "Proxmox Host: $PROXMOX_HOST"
echo "Proxmox User: $PROXMOX_USER"
echo "Storage: $PROXMOX_STORAGE"
echo ""

# Check if ISOs exist
WINDOWS_ISO="$GLASSDOME_ROOT/isos/windows/windows-server-2022-eval.iso"
VIRTIO_ISO="$GLASSDOME_ROOT/isos/drivers/virtio-win.iso"

if [ ! -f "$WINDOWS_ISO" ]; then
    echo "❌ Windows ISO not found: $WINDOWS_ISO"
    echo "   Run: python scripts/iso_manager.py download windows-server-2022"
    exit 1
fi

if [ ! -f "$VIRTIO_ISO" ]; then
    echo "❌ VirtIO ISO not found: $VIRTIO_ISO"
    echo "   Run: python scripts/iso_manager.py download virtio-win"
    exit 1
fi

echo "✅ Found ISOs locally"
echo ""

# Upload Windows ISO
echo "→ Uploading Windows Server 2022 ISO (4.7 GB, this may take a few minutes)..."
scp "$WINDOWS_ISO" "${PROXMOX_USER}@${PROXMOX_HOST}:/var/lib/vz/template/iso/windows-server-2022-eval.iso"

if [ $? -eq 0 ]; then
    echo "✅ Windows ISO uploaded"
else
    echo "❌ Failed to upload Windows ISO"
    exit 1
fi

echo ""

# Upload VirtIO drivers ISO
echo "→ Uploading VirtIO drivers ISO (753 MB)..."
scp "$VIRTIO_ISO" "${PROXMOX_USER}@${PROXMOX_HOST}:/var/lib/vz/template/iso/virtio-win.iso"

if [ $? -eq 0 ]; then
    echo "✅ VirtIO ISO uploaded"
else
    echo "❌ Failed to upload VirtIO ISO"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ Upload Complete!"
echo "============================================================"
echo ""
echo "ISOs are now available in Proxmox:"
echo "  - windows-server-2022-eval.iso"
echo "  - virtio-win.iso"
echo ""
echo "Next step: Deploy Windows VMs!"

