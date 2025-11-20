# ESXi Template Quick Reference

**Status**: ✅ Production Ready (2024-11-20)  
**Proof**: glassdome-ubuntu-test @ 192.168.3.207

---

## Build Template (Once)

```bash
cd /home/nomad/glassdome
source venv/bin/activate

# Ubuntu 22.04 (default)
python scripts/build_esxi_template.py \
    --name ubuntu-2204-glassdome \
    --username ubuntu \
    --password glassdome123

# Time: ~2-4 minutes
```

---

## Create VM from Template (Many Times)

```python
from glassdome.platforms.esxi_template_builder import ESXiTemplateBuilder
from glassdome.core.config import settings

builder = ESXiTemplateBuilder(
    esxi_host=settings.esxi_host,
    esxi_user=settings.esxi_user,
    esxi_password=settings.esxi_password,
    datastore=settings.esxi_datastore,
    network=settings.esxi_network
)

# Template info (from build step or stored config)
template = {
    "template_name": "ubuntu-2204-glassdome",
    "vmdk_path": "[NFSSTORE] ubuntu-2204-glassdome/ubuntu-2204-glassdome.vmdk",
    "iso_path": "[NFSSTORE] ubuntu-2204-glassdome/seed.iso",
    "username": "ubuntu",
    "password": "glassdome123"
}

# Create VM
vm_info = builder.create_vm_from_template(
    vm_name="my-vm-001",
    template_info=template,
    cores=2,
    memory_mb=2048
)

# Time: ~70-100 seconds
```

---

## Test SSH Access

```bash
# Wait 90 seconds after VM creation for cloud-init
sleep 90

# SSH to VM
sshpass -p "glassdome123" ssh ubuntu@<VM_IP> hostname

# Or without sshpass
ssh ubuntu@<VM_IP>
# Password: glassdome123
```

---

## Files on ESXi

```
/vmfs/volumes/NFSSTORE/ubuntu-2204-glassdome/
├── ubuntu-2204-glassdome.vmdk         # ✅ Use this
├── ubuntu-2204-glassdome-flat.vmdk    # ✅ Use this
├── seed.iso                           # ✅ Use this
├── ubuntu-flat.vmdk                   # Intermediate file
└── ubuntu-flat-flat.vmdk              # Intermediate file
```

---

## Default Credentials

```
Username: ubuntu
Password: glassdome123
Sudo: NOPASSWD
SSH: Enabled (password auth)
```

---

## Troubleshooting

### SSH not working?
```bash
# 1. Check if VM has IP
# 2. Wait 90 seconds for cloud-init
# 3. Verify from ESXi console that cloud-init completed:
cloud-init status --long
```

### Template build fails?
```bash
# 1. Check sshpass installed
sudo apt-get install sshpass

# 2. Check qemu-img installed
sudo apt-get install qemu-utils

# 3. Check genisoimage installed
sudo apt-get install genisoimage

# 4. Verify ESXi SSH access
ssh root@192.168.3.3
```

---

## Required .env Variables

```bash
ESXI_HOST=192.168.3.3
ESXI_USER=root
ESXI_PASSWORD=your_password
ESXI_DATASTORE=NFSSTORE
ESXI_NETWORK=VM Network
ESXI_VERIFY_SSL=false
ESXI_UBUNTU_TEMPLATE=ubuntu-2204-glassdome
```

---

## Integration with ESXiClient

```python
from glassdome.platforms.esxi_client import ESXiClient

client = ESXiClient(
    host="192.168.3.3",
    user="root",
    password="password",
    datastore_name="NFSSTORE"
)

# Use template in create_vm
vm_config = {
    "name": "glassdome-vm",
    "cores": 2,
    "memory": 2048,
    "vmdk_path": "[NFSSTORE] ubuntu-2204-glassdome/ubuntu-2204-glassdome.vmdk",
    "iso_path": "[NFSSTORE] ubuntu-2204-glassdome/seed.iso"
}

result = await client.create_vm(vm_config)
```

---

## Performance

| Operation | Time |
|-----------|------|
| Build template | 2-4 minutes |
| Create VM | 70-100 seconds |
| SSH ready | +90 seconds (cloud-init) |
| **Total** | **~3-4 minutes** |

---

## Best Practices

1. **Build template once** - Reuse for all VMs
2. **Change default password** - Use strong passwords or SSH keys
3. **Version templates** - Keep old versions for rollback
4. **Test before production** - Always test new templates
5. **Document changes** - Track what's in each template version

---

**Full Documentation**: `docs/ESXI_TEMPLATE_GUIDE.md`

