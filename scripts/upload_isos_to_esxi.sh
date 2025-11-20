#!/bin/bash
#
# Upload Windows ISOs to ESXi
# 
# This script uploads the downloaded ISOs to ESXi storage so they can be attached to VMs.
#

set -e

# Configuration
ESXI_HOST="${ESXI_HOST:-192.168.3.11}"
ESXI_USER="${ESXI_USER:-root}"
ESXI_DATASTORE="${ESXI_DATASTORE:-NFSSTORE}"
GLASSDOME_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "============================================================"
echo "  Upload ISOs to ESXi"
echo "============================================================"
echo ""
echo "ESXi Host: $ESXI_HOST"
echo "ESXi User: $ESXI_USER"
echo "Datastore: $ESXI_DATASTORE"
echo ""

# Check if ISOs exist
WINDOWS_ISO="$GLASSDOME_ROOT/isos/windows/windows-server-2022-eval.iso"

if [ ! -f "$WINDOWS_ISO" ]; then
    echo "❌ Windows ISO not found: $WINDOWS_ISO"
    echo "   Run: python scripts/iso_manager.py download windows-server-2022"
    exit 1
fi

echo "✅ Found ISOs locally"
echo ""

# Create ISO directory on ESXi if it doesn't exist
echo "→ Creating ISO directory on ESXi datastore..."
sshpass -p "xisxxisx" ssh ${ESXI_USER}@${ESXI_HOST} "mkdir -p /vmfs/volumes/${ESXI_DATASTORE}/ISO"

# Upload Windows ISO
echo "→ Uploading Windows Server 2022 ISO (4.7 GB, this may take a few minutes)..."
sshpass -p "xisxxisx" scp "$WINDOWS_ISO" "${ESXI_USER}@${ESXI_HOST}:/vmfs/volumes/${ESXI_DATASTORE}/ISO/windows-server-2022-eval.iso"

if [ $? -eq 0 ]; then
    echo "✅ Windows ISO uploaded"
else
    echo "❌ Failed to upload Windows ISO"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ Upload Complete!"
echo "============================================================"
echo ""
echo "ISO is now available in ESXi datastore ${ESXI_DATASTORE}:"
echo "  - /vmfs/volumes/${ESXI_DATASTORE}/ISO/windows-server-2022-eval.iso"
echo ""
echo "Next step: Deploy Windows VMs!"

