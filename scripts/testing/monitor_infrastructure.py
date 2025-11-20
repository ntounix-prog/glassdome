#!/usr/bin/env python3
"""
Infrastructure Monitoring Script
Continuously monitors deployed VMs and alerts on issues
"""
import asyncio
import sys
import os

sys.path.insert(0, '/home/nomad/glassdome')

from glassdome.agents.overseer import OverseerAgent
from glassdome.platforms.proxmox_client import ProxmoxClient


async def main():
    print("\n" + "=" * 70)
    print("INFRASTRUCTURE MONITORING - Overseer Agent")
    print("=" * 70)
    print()
    
    # Create Proxmox client
    proxmox = ProxmoxClient(
        host="192.168.3.2",
        user="apex@pve",
        token_name="glassdome-token",
        token_value="44fa1891-0b3f-487a-b1ea-0800284f79d9",
        verify_ssl=False
    )
    
    # Connect
    print("Connecting to Proxmox...")
    connected = await proxmox.test_connection()
    
    if not connected:
        print("❌ Failed to connect to Proxmox")
        return
    
    print("✅ Connected to Proxmox")
    print()
    
    # Create Overseer
    overseer = OverseerAgent("overseer-001", proxmox)
    print(f"✅ Overseer Agent initialized: {overseer.agent_id}")
    print()
    
    # Initial check
    print("=" * 70)
    print("Performing initial infrastructure check...")
    print("=" * 70)
    print()
    
    report = await overseer.check_node("pve01")
    
    print(f"Node: {report['node']}")
    print(f"  Total VMs: {report['total_vms']}")
    print(f"  Running: {report['running']}")
    print(f"  Stopped: {report['stopped']}")
    print(f"  Issues: {len(report['issues'])}")
    print()
    
    # Show VM details
    if report['vms']:
        print("VMs:")
        print("-" * 70)
        for vm in report['vms']:
            status_icon = "✅" if vm['status'] == 'running' else "⏸️"
            print(f"{status_icon} VM {vm['vmid']}: {vm['name']}")
            print(f"   Status: {vm['status']}")
            print(f"   Uptime: {vm['uptime']}s")
            print(f"   Memory: {vm['memory_mb']}/{vm['memory_max_mb']} MB ({vm.get('memory_percent', 0):.1f}%)")
            
            if vm.get('ip_address'):
                print(f"   IP: {vm['ip_address']}")
            
            if vm['issues']:
                print(f"   ⚠️  Issues: {len(vm['issues'])}")
                for issue in vm['issues']:
                    print(f"      - {issue}")
            
            print()
    
    # Show alerts
    if overseer.alerts:
        print("Alerts:")
        print("-" * 70)
        for alert in overseer.alerts:
            print(f"[{alert['severity'].upper()}] {alert['message']}")
        print()
    
    # Generate report
    print("=" * 70)
    print("INFRASTRUCTURE REPORT")
    print("=" * 70)
    print()
    
    full_report = await overseer.generate_report()
    print(full_report)
    
    # Ask if user wants continuous monitoring
    print()
    print("=" * 70)
    print("Continuous monitoring available")
    print("=" * 70)
    print()
    print("The Overseer can continuously monitor infrastructure and:")
    print("  • Detect when VMs stop/crash")
    print("  • Alert on high resource usage")
    print("  • Track uptime and availability")
    print("  • Auto-restart failed VMs")
    print("  • Generate periodic reports")
    print()
    print("To enable continuous monitoring:")
    print("  1. Via API: POST /api/overseer/start-monitoring")
    print("  2. Via Python: await overseer.start_monitoring(['pve01'], interval=60)")
    print()
    print("Current check complete!")


if __name__ == "__main__":
    asyncio.run(main())

