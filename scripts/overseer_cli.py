#!/usr/bin/env python3
"""
Overseer CLI - Command-line interface to interact with Overseer

Usage:
    ./overseer_cli.py status              # Get Overseer status
    ./overseer_cli.py vms                 # List all VMs
    ./overseer_cli.py vm <vm_id>          # Get VM details
    ./overseer_cli.py deploy <platform> <os>  # Request VM deployment
    ./overseer_cli.py destroy <vm_id>     # Request VM destruction
    ./overseer_cli.py requests            # List pending requests
"""

import sys
import asyncio
import argparse
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.overseer import OverseerEntity
from glassdome.overseer.state import SystemState, VM, VMStatus
from glassdome.core.config import Settings


def print_json(data):
    """Pretty print JSON"""
    print(json.dumps(data, indent=2, default=str))


async def cmd_status(args):
    """Get Overseer status"""
    state = SystemState()
    summary = state.get_summary()
    
    print("\n" + "="*70)
    print("🧠 GLASSDOME OVERSEER - STATUS")
    print("="*70)
    print(f"Total VMs:        {summary['total_vms']}")
    print(f"Running VMs:      {summary['running_vms']}")
    print(f"Production VMs:   {summary['production_vms']}")
    print(f"Total Hosts:      {summary['total_hosts']}")
    print(f"Healthy Hosts:    {summary['healthy_hosts']}")
    print(f"Services:         {summary['total_services']}")
    print(f"Pending Requests: {summary['pending_requests']}")
    print("="*70 + "\n")


async def cmd_vms(args):
    """List all VMs"""
    state = SystemState()
    
    if not state.vms:
        print("No VMs in state")
        return
    
    print("\n" + "="*100)
    print(f"{'VM ID':<15} {'Name':<25} {'Platform':<12} {'Status':<12} {'IP':<15} {'Prod':<5}")
    print("="*100)
    
    for vm in state.vms.values():
        print(f"{vm.id:<15} {vm.name:<25} {vm.platform:<12} {vm.status.value:<12} {vm.ip or 'N/A':<15} {'YES' if vm.is_production else 'NO':<5}")
    
    print("="*100 + "\n")


async def cmd_vm(args):
    """Get VM details"""
    state = SystemState()
    vm = state.get_vm(args.vm_id)
    
    if not vm:
        print(f"❌ VM {args.vm_id} not found")
        return
    
    print("\n" + "="*70)
    print(f"VM: {vm.name} ({vm.id})")
    print("="*70)
    print(f"Platform:     {vm.platform}")
    print(f"Status:       {vm.status.value}")
    print(f"IP:           {vm.ip or 'N/A'}")
    print(f"Production:   {'YES' if vm.is_production else 'NO'}")
    print(f"Deployed:     {vm.deployed_at or 'N/A'}")
    print(f"Deployed By:  {vm.deployed_by or 'N/A'}")
    print(f"\nSpecs:")
    print_json(vm.specs or {})
    print(f"\nServices:     {', '.join(vm.services) if vm.services else 'None'}")
    print("="*70 + "\n")


async def cmd_deploy(args):
    """Request VM deployment"""
    overseer = OverseerEntity(Settings())
    
    result = await overseer.receive_request(
        action='deploy_vm',
        params={
            'platform': args.platform,
            'os': args.os,
            'specs': {}
        },
        user=args.user or 'cli-user'
    )
    
    if result['approved']:
        print(f"✅ Request APPROVED")
        print(f"   Request ID: {result['request_id']}")
        print(f"   Queue Position: {result['queue_position']}")
    else:
        print(f"❌ Request DENIED")
        print(f"   Reason: {result['reason']}")


async def cmd_destroy(args):
    """Request VM destruction"""
    overseer = OverseerEntity(Settings())
    
    result = await overseer.receive_request(
        action='destroy_vm',
        params={
            'vm_id': args.vm_id,
            'force_production': args.force
        },
        user=args.user or 'cli-user'
    )
    
    if result['approved']:
        print(f"✅ Request APPROVED")
        print(f"   Request ID: {result['request_id']}")
    else:
        print(f"❌ Request DENIED")
        print(f"   Reason: {result['reason']}")


async def cmd_requests(args):
    """List pending requests"""
    state = SystemState()
    pending = state.get_pending_requests()
    approved = state.get_approved_requests()
    
    print("\n" + "="*100)
    print(f"{'Request ID':<15} {'Action':<20} {'User':<15} {'Status':<12} {'Submitted':<20}")
    print("="*100)
    
    for req in pending + approved:
        print(f"{req.request_id:<15} {req.action:<20} {req.user:<15} {req.status:<12} {req.submitted_at:<20}")
    
    print("="*100 + "\n")


async def cmd_hosts(args):
    """List all hosts"""
    state = SystemState()
    
    if not state.hosts:
        print("No hosts in state")
        return
    
    print("\n" + "="*90)
    print(f"{'Platform':<12} {'Identifier':<20} {'Status':<12} {'VMs':<6}")
    print("="*90)
    
    for host in state.hosts.values():
        print(f"{host.platform:<12} {host.identifier:<20} {host.status.value:<12} {len(host.vms):<6}")
    
    print("="*90 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Glassdome Overseer CLI")
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Status
    subparsers.add_parser('status', help='Get Overseer status')
    
    # VMs
    subparsers.add_parser('vms', help='List all VMs')
    
    vm_parser = subparsers.add_parser('vm', help='Get VM details')
    vm_parser.add_argument('vm_id', help='VM ID')
    
    # Deploy
    deploy_parser = subparsers.add_parser('deploy', help='Request VM deployment')
    deploy_parser.add_argument('platform', choices=['proxmox', 'esxi', 'aws', 'azure'])
    deploy_parser.add_argument('os', choices=['ubuntu', 'windows'])
    deploy_parser.add_argument('--user', help='User making request')
    
    # Destroy
    destroy_parser = subparsers.add_parser('destroy', help='Request VM destruction')
    destroy_parser.add_argument('vm_id', help='VM ID')
    destroy_parser.add_argument('--force', action='store_true', help='Force production VM destruction')
    destroy_parser.add_argument('--user', help='User making request')
    
    # Requests
    subparsers.add_parser('requests', help='List pending requests')
    
    # Hosts
    subparsers.add_parser('hosts', help='List all hosts')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Route to command
    commands = {
        'status': cmd_status,
        'vms': cmd_vms,
        'vm': cmd_vm,
        'deploy': cmd_deploy,
        'destroy': cmd_destroy,
        'requests': cmd_requests,
        'hosts': cmd_hosts
    }
    
    if args.command in commands:
        asyncio.run(commands[args.command](args))
    else:
        print(f"Unknown command: {args.command}")
        parser.print_help()


if __name__ == "__main__":
    main()

