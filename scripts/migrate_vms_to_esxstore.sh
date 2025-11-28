#!/bin/bash
# Live migrate all VMs from proxpool to esxstore
# VMs stay ONLINE during migration - zero downtime!

# VMs to migrate (smallest to largest, VM 106 already done)
VMS=(
    "103:rome:5.57GB"
    "102:mooker:8.21GB"
    "107:sunspot:14.6GB"
    "101:es01:18.3GB"
    "105:mnto:122.5GB (2 disks)"
    "100:agentx:169GB"
)

echo "========================================="
echo "Live VM Disk Migration: proxpool → esxstore"
echo "VMs remain ONLINE during migration"
echo "========================================="
echo ""

for vm_info in "${VMS[@]}"; do
    IFS=':' read -r vmid name size <<< "$vm_info"
    
    echo "[$vmid] $name ($size)"
    echo "  Status: $(qm status $vmid)"
    echo "  Starting migration at $(date +%H:%M:%S)..."
    
    # Migrate scsi0 (main disk)
    qm disk move $vmid scsi0 esxstore --delete 1
    
    # Check if VM has scsi1 (VM 105 - mnto has 2 disks)
    if qm config $vmid | grep -q "^scsi1:"; then
        echo "  Found second disk (scsi1), migrating..."
        qm disk move $vmid scsi1 esxstore --delete 1
    fi
    
    echo "  ✅ Completed at $(date +%H:%M:%S)"
    echo "  Status: $(qm status $vmid)"
    echo ""
done

echo "========================================="
echo "Migration Complete!"
echo "========================================="
echo ""
echo "Verifying all VMs are still running..."
for vm_info in "${VMS[@]}"; do
    IFS=':' read -r vmid name size <<< "$vm_info"
    status=$(qm status $vmid)
    if [[ "$status" == *"running"* ]]; then
        echo "  ✅ $vmid ($name): running"
    else
        echo "  ⚠️  $vmid ($name): $status"
    fi
done

echo ""
echo "Checking proxpool (should be empty or nearly empty)..."
zfs list -r proxpool -t volume

echo ""
echo "Checking esxstore usage..."
df -h /mnt/esxstore

