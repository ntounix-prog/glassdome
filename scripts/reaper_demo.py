#!/usr/bin/env python3
"""
Reaper System Demo

Demonstrates the event-driven vulnerability injection system.
Assumes VMs are already deployed and running.

Usage:
    python3 scripts/reaper_demo.py
"""

import sys
import threading
import time
from pathlib import Path

# Add glassdome to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.reaper.models import MissionState, HostState
from glassdome.reaper.task_queue import InMemoryTaskQueue
from glassdome.reaper.event_bus import InMemoryEventBus
from glassdome.reaper.mission_store import InMemoryMissionStore
from glassdome.reaper.planner import VulnerabilityPlanner
from glassdome.reaper.engine import MissionEngine
from glassdome.reaper.agents.linux_agent import LinuxReaperAgent
from glassdome.reaper.agents.windows_agent import WindowsReaperAgent


def main():
    print("=" * 70)
    print("REAPER VULNERABILITY INJECTION SYSTEM - DEMO")
    print("=" * 70)
    print()
    
    # Initialize infrastructure
    print("Initializing infrastructure...")
    task_queue = InMemoryTaskQueue()
    event_bus = InMemoryEventBus()
    mission_store = InMemoryMissionStore()
    planner = VulnerabilityPlanner()
    print("✓ Infrastructure initialized")
    print()
    
    # Create mission targeting already-deployed VMs
    print("Creating vulnerability injection mission...")
    mission_id = "mission-demo-001"
    lab_id = "web-security-lab-001"
    
    # Define target hosts (these would come from LabOrchestrator in production)
    hosts = {
        "web-01": HostState(
            host_id="web-01",
            os="linux",
            ip_address="192.168.3.100"
        ),
        "web-02": HostState(
            host_id="web-02",
            os="linux",
            ip_address="192.168.3.101"
        ),
        "win-01": HostState(
            host_id="win-01",
            os="windows",
            ip_address="192.168.3.200"
        ),
    }
    
    initial_state = MissionState(
        mission_id=mission_id,
        lab_id=lab_id,
        mission_type="web-security-training",
        hosts=hosts
    )
    
    print(f"✓ Mission created: {mission_id}")
    print(f"  Lab ID: {lab_id}")
    print(f"  Target hosts: {len(hosts)}")
    for host_id, host in hosts.items():
        print(f"    - {host_id} ({host.os}) @ {host.ip_address}")
    print()
    
    # Create mission engine
    print("Initializing mission engine...")
    engine = MissionEngine(
        mission_id,
        mission_store,
        task_queue,
        event_bus,
        planner
    )
    print("✓ Mission engine initialized")
    print()
    
    # Start agents in background threads
    print("Starting Reaper agents...")
    linux_agent = LinuxReaperAgent(task_queue, event_bus)
    windows_agent = WindowsReaperAgent(task_queue, event_bus)
    
    agent_threads = [
        threading.Thread(target=linux_agent.run_forever, daemon=True, name="LinuxAgent"),
        threading.Thread(target=windows_agent.run_forever, daemon=True, name="WindowsAgent"),
    ]
    
    for t in agent_threads:
        t.start()
    print(f"✓ Started {len(agent_threads)} Reaper agents")
    print()
    
    # Start mission engine event loop in background
    print("Starting mission engine event loop...")
    engine_thread = threading.Thread(
        target=engine.run_event_loop_sync,
        daemon=True,
        name="MissionEngine"
    )
    engine_thread.start()
    print("✓ Mission engine event loop started")
    print()
    
    # Start the mission!
    print("=" * 70)
    print("STARTING MISSION")
    print("=" * 70)
    print()
    engine.start_mission(initial_state)
    print()
    
    # Monitor for 30 seconds
    print("Monitoring mission progress (30 seconds)...")
    print()
    
    for i in range(30):
        time.sleep(1)
        
        # Get status every 5 seconds
        if (i + 1) % 5 == 0:
            status = engine.get_status()
            print(f"\n--- Status at t+{i+1}s ---")
            print(f"Mission Status: {status.get('status', 'unknown')}")
            print(f"Pending Tasks: {status.get('pending_tasks', 0)}")
            print(f"Completed Tasks: {status.get('completed_tasks', 0)}")
            print(f"Failed Tasks: {status.get('failed_tasks', 0)}")
            print(f"Healthy Hosts: {status.get('healthy_hosts', 0)}/{status.get('total_hosts', 0)}")
            print(f"Locked Hosts: {status.get('locked_hosts', 0)}")
            
            # Get detailed host status
            detailed = engine.get_detailed_status()
            if detailed and 'hosts' in detailed:
                print("\nHost Details:")
                for host_id, host_data in detailed['hosts'].items():
                    print(f"  {host_id}:")
                    print(f"    Status: {host_data.get('last_status', 'unknown')}")
                    print(f"    Failures: {host_data.get('failure_count', 0)}")
                    print(f"    Locked: {host_data.get('locked', False)}")
                    vulns = host_data.get('vulnerabilities_injected', [])
                    if vulns:
                        print(f"    Vulnerabilities: {', '.join(vulns)}")
    
    # Final status
    print("\n" + "=" * 70)
    print("MISSION COMPLETE")
    print("=" * 70)
    print()
    
    final_status = engine.get_detailed_status()
    print(f"Final Mission Status: {final_status.get('status', 'unknown')}")
    print(f"Total Tasks Completed: {len(final_status.get('completed_tasks', []))}")
    print(f"Total Tasks Failed: {len(final_status.get('failed_tasks', []))}")
    print()
    
    print("Host Summary:")
    for host_id, host_data in final_status.get('hosts', {}).items():
        print(f"\n{host_id}:")
        print(f"  OS: {host_data.get('os', 'unknown')}")
        print(f"  IP: {host_data.get('ip_address', 'unknown')}")
        print(f"  Final Status: {host_data.get('last_status', 'unknown')}")
        print(f"  Total Failures: {host_data.get('failure_count', 0)}")
        
        vulns = host_data.get('vulnerabilities_injected', [])
        if vulns:
            print(f"  Vulnerabilities Injected:")
            for vuln in vulns:
                print(f"    - {vuln}")
        
        facts = host_data.get('facts', {})
        if facts:
            print(f"  Discovered Facts:")
            for key, value in facts.items():
                if isinstance(value, list):
                    print(f"    {key}: {', '.join(map(str, value))}")
                else:
                    print(f"    {key}: {value}")
    
    print()
    print("=" * 70)
    print("Demo complete. In production, missions would run until all hosts are")
    print("successfully configured or locked due to failures.")
    print("=" * 70)
    
    # Stop engine
    engine.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

