# Switch Default Gateway Configuration

## Problem

The Cisco switches (Nexus 3064 and Cisco 3850) don't have a default gateway configured, so they cannot route traffic back to agentX's network (192.168.3.0/24). This causes "Destination Host Unreachable" errors when trying to reach the switches from agentX.

## Solution

Configure the default gateway on both switches to point to the UniFi gateway (192.168.2.1).

## Manual Configuration

If you need to configure manually via console or direct access:

### Nexus 3064 (NX-OS)

```bash
configure terminal
ip route 0.0.0.0/0 192.168.2.1
end
copy running-config startup-config
```

### Cisco 3850 (IOS-XE)

```bash
configure terminal
ip default-gateway 192.168.2.1
ip route 0.0.0.0 0.0.0.0 192.168.2.1
end
write memory
```

## Automated Configuration

Once you have SSH access to the switches (via console or from a device on 192.168.2.0/24), run:

```bash
cd /home/nomad/glassdome
source venv/bin/activate
python3 scripts/network_discovery/configure_switch_default_gateway.py
```

## Verification

After configuration, test connectivity from agentX:

```bash
ping -c 3 192.168.2.224  # Nexus 3064
ping -c 3 192.168.2.253  # Cisco 3850
```

Both should respond successfully.

## Next Steps

Once the switches have default gateways configured:
1. Test SSH connectivity from agentX
2. Proceed with network discovery
3. Begin VLAN cleanup and port labeling

