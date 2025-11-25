# VLAN 215 Interface Setup Commands

## Quick Setup

Add VLAN 215 interfaces to Proxmox host and agentX VM to enable direct access to 192.168.215.0/24 network.

## Commands to Run

### On Proxmox Host (10.0.0.1)

**1. Add network interface to agentX VM (VM 100):**

```bash
ssh root@10.0.0.1
qm set 100 --net1 virtio,bridge=vmbr0,tag=215,firewall=0
```

**2. Verify interface was added:**

```bash
qm config 100 | grep net
```

**3. (Optional) Add interface to server VM if needed:**

```bash
# Find server VM ID first
qm list | grep server

# Add interface (replace <VMID> with actual ID)
qm set <VMID> --net1 virtio,bridge=vmbr0,tag=215,firewall=0
```

### On agentX VM (10.0.0.2)

**1. Check if new interface appeared:**

```bash
ip link show
# Look for new interface (usually ens7, ens8, or similar)
```

**2. The interface should get IP via DHCP automatically. Check:**

```bash
ip addr show | grep 192.168.215
# Or
ip addr show <interface_name>
```

**3. If IP not assigned, wait a moment or restart networking:**

```bash
# Wait for DHCP (usually happens automatically)
# Or manually trigger:
sudo dhclient <interface_name>
```

**4. Verify connectivity to original Proxmox:**

```bash
ping 192.168.215.78
ssh root@192.168.215.78 "echo 'Connected to original Proxmox!'"
```

## Expected Results

- agentX VM gets an IP on 192.168.215.0/24 via DHCP
- Can ping and SSH to 192.168.215.78 (original Proxmox)
- Can access templates on original Proxmox directly

## Troubleshooting

**Interface not appearing:**
- Restart agentX VM: `qm reboot 100`
- Or wait a few seconds for interface to initialize

**No IP assigned:**
- Check DHCP is active on VLAN 215
- Manually request: `sudo dhclient <interface_name>`
- Check interface is up: `ip link set <interface_name> up`

**Cannot ping 192.168.215.78:**
- Verify original Proxmox is on 192.168.215.78
- Check VLAN 215 is configured correctly on network switch
- Verify bridge configuration on Proxmox host

---

*Last Updated: November 24, 2024*

