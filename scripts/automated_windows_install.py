#!/usr/bin/env python3
"""
Fully Automated Windows Installation via VNC Console Automation
Uses PyAutoGUI to control the Proxmox VNC console
"""
import time
import subprocess
import sys

def automate_windows_setup(proxmox_host, vmid, vnc_port=5900):
    """
    Automate Windows Setup via VNC console
    
    This sends keyboard commands to navigate Windows Setup:
    - Select language
    - Accept license
    - Custom install
    - Select disk
    - Set administrator password
    - Complete setup
    """
    try:
        # Connect to VNC (Proxmox VNC is at port 5900 + display number)
        print(f"Connecting to Proxmox VNC console for VM {vmid}...")
        
        # Get VNC display info from Proxmox
        vnc_cmd = f"qm vncproxy {vmid}"
        result = subprocess.run(
            f"sshpass -p 'xisxxisx' ssh root@{proxmox_host} '{vnc_cmd}'",
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(f"VNC Info: {result.stdout}")
        
        # Install vncdotool for VNC automation
        print("Installing vncdotool for VNC automation...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "vncdotool"], check=True)
        
        from vncdotool import api
        
        # Parse VNC port from Proxmox response
        # Format: TICKET:port
        vnc_info = result.stdout.strip().split(':')
        if len(vnc_info) >= 2:
            vnc_display = vnc_info[1]
            vnc_full_port = 5900 + int(vnc_display)
        else:
            print(f"Could not parse VNC info, using default port {vnc_port + vmid}")
            vnc_full_port = vnc_port + vmid
        
        print(f"Connecting to VNC at {proxmox_host}:{vnc_full_port}...")
        
        # Connect to VNC
        client = api.connect(f"{proxmox_host}::{vnc_full_port}")
        
        # Wait for Windows Setup to boot
        print("Waiting for Windows Setup to start (30s)...")
        time.sleep(30)
        
        # Windows Setup automation sequence
        print("🤖 Starting automated Windows Setup...")
        
        # Step 1: Language selection screen - press Enter
        print("  → Selecting language...")
        client.keyPress('enter')
        time.sleep(2)
        
        # Step 2: "Install Now" button
        print("  → Clicking Install Now...")
        client.keyPress('enter')
        time.sleep(5)
        
        # Step 3: Product key screen - skip
        print("  → Skipping product key...")
        client.keyPress('tab')
        time.sleep(0.5)
        client.keyPress('enter')
        time.sleep(3)
        
        # Step 4: Select Windows edition (Standard with Desktop Experience)
        print("  → Selecting Windows Server 2022 Standard (Desktop Experience)...")
        client.keyPress('down')  # Navigate to Standard Desktop
        time.sleep(0.5)
        client.keyPress('enter')
        time.sleep(2)
        
        # Step 5: Accept license
        print("  → Accepting license...")
        client.keyPress('tab')
        time.sleep(0.5)
        client.keyPress('space')  # Check "I accept"
        time.sleep(0.5)
        client.keyPress('enter')
        time.sleep(3)
        
        # Step 6: Custom install
        print("  → Selecting Custom install...")
        client.keyPress('tab')
        time.sleep(0.5)
        client.keyPress('enter')
        time.sleep(3)
        
        # Step 7: Select disk and install
        print("  → Installing to disk...")
        client.keyPress('enter')  # Disk should already be selected
        time.sleep(5)
        
        print("✅ Windows installation started!")
        print("⏱️  Installation will take 10-15 minutes")
        print("   The VM will reboot automatically")
        print("")
        print("Next: After installation, run the sysprep script to create a template")
        
        client.disconnect()
        return True
        
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        print("\nFallback: Access Proxmox console manually:")
        print(f"  https://192.168.3.2:8006")
        print(f"  VM: {vmid} → Console")
        return False

if __name__ == "__main__":
    automate_windows_setup("192.168.3.2", 113)
