# Session Log: November 27, 2024 - Canvas Lab Deployment

## Summary
Major infrastructure and canvas deployment work. Achieved working lab deployment with pfSense gateway architecture.

## Key Accomplishments

### 1. Proxmox Infrastructure
- **Swap fix on pve01**: Added 16GB swapfile (was 100% full at 8GB, now 24GB total)
- **Memory analysis**: agentx using 32GB is normal (27GB buff/cache, 29GB available)
- **No orphan processes**: System healthy, no zombies

### 2. Template Management
- **pfSense template (9020)**: Verified working, SSH+firewall rules configured
- **Windows Server template (9010)**: ISO attached, needs install
- **ISOs moved to SAN**: Cleaned up esxstore, moved to `truenas-nfs-labs`
- **Created Proxmox-compatible autounattend ISO** for Windows

### 3. Canvas Deployment Architecture
Implemented pfSense-as-gateway model:

```
                    Management Network (192.168.3.x)
                              │
                    ┌─────────┴─────────┐
                    │     pfSense       │
                    │  WAN: DHCP        │
                    │  LAN: 10.X.0.1    │
                    └─────────┬─────────┘
                              │
         Lab Network (VLAN 100-170, 10.X.0.0/24)
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
         │  Kali   │    │ Windows │    │ Target  │
         │  DHCP   │    │  DHCP   │    │  DHCP   │
         └─────────┘    └─────────┘    └─────────┘
```

### 4. Code Changes (`glassdome/api/canvas_deploy.py`)

#### Network Discovery via Unifi API
```python
# Query Ubiquiti Dream Router for MAC-to-IP mapping
async with httpx.AsyncClient(verify=False) as http:
    resp = await http.get(
        f"https://{unifi_host}/proxy/network/api/s/default/stat/sta",
        headers={"X-API-KEY": unifi_api_key}
    )
```

#### VM Cloning Fixed
Changed from broken `client.clone_vm()` to direct Proxmox API:
```python
client.client.nodes(node_name).qemu(template_id).clone.create(
    newid=next_vmid,
    name=vm_name,
    full=1
)
```

#### VLAN Allocation
- Pool: 100-170
- Subnet: 10.{VLAN}.0.0/24
- Gateway: 10.{VLAN}.0.1
- DHCP: 10.{VLAN}.0.10-254

### 5. Dependencies Added
```bash
pip install pexpect httpx
```

## Test Results

### Successful Deployment
```json
{
    "success": true,
    "lab_id": "test-final",
    "status": "completed",
    "network": {
        "vlan_id": 101,
        "cidr": "10.101.0.0/24",
        "gateway": "10.101.0.1"
    },
    "vms": [
        {"name": "gateway", "vm_id": "112", "role": "gateway"},
        {"name": "ubuntu-u1", "vm_id": "110", "role": "client"}
    ]
}
```

### Verified Configuration
- pfSense WAN: vmbr2,tag=2 → 192.168.3.223 (DHCP)
- pfSense LAN: vmbr1,tag=101 → 10.101.0.1
- Ubuntu: vmbr1,tag=101 → DHCP from pfSense

## Known Issues

### 1. pfSense WAN Firewall
After cloning, pfSense firewall blocks WAN access. Template rules don't fully persist.
**Workaround**: Manual firewall config via console after clone.

### 2. Deployment Time (~2.5 minutes)
Mostly due to pfSense clone (8GB disk copy). Hot spares for pfSense would help.

### 3. pve01 vs pve02 Network
Both work for 192.168.3.x access via vmbr2,tag=2. Labs deploy to pve02.

## Environment

### Services Running
- Backend API: http://localhost:8011 ✓
- Frontend: http://localhost:5174 ✓

### Credentials Used
- Proxmox API: from .env
- Unifi API: `UBIQUITI_API_KEY` in .env
- pfSense: admin/pfsense

## Files Modified
- `glassdome/api/canvas_deploy.py` - Major rewrite for pfSense gateway architecture
- `glassdome/platforms/proxmox_client.py` - No changes needed

## Related Documents (in docs/, should be in session_logs/)
- `PROXMOX_INFRASTRUCTURE_ANALYSIS.md`
- `PROXMOX_STORAGE_COMPLETE_ANALYSIS.md`
- `TRUENAS_ARCHITECTURE_ANALYSIS.md`
- `NEXUS_3064_SAN_SWITCH.md`
- `REVISED_STORAGE_STRATEGY.md`

## Next Steps
1. Fix pfSense template firewall persistence
2. Add pfSense hot spare pool for faster deployment
3. Test full lab with multiple VMs
4. Configure pfSense LAN DHCP via SSH after deployment

