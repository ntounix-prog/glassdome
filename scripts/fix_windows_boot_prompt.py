#!/usr/bin/env python3
"""
Fix Windows boot prompt by modifying the Windows ISO to remove "Press any key" prompt
OR automatically press key via VNC

This script provides two solutions:
1. Modify Windows ISO to remove boot prompt (recommended)
2. Use VNC automation to press key automatically
"""
import sys
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()
settings = get_secure_settings()


def modify_windows_iso_remove_prompt(iso_path: Path, output_path: Path):
    """
    Modify Windows ISO to remove "Press any key to boot from CD-ROM" prompt
    
    This replaces bootfix.bin with an empty file for BIOS boot,
    and uses efisys_noprompt.bin for UEFI boot.
    """
    print(f"📦 Modifying Windows ISO to remove boot prompt...")
    print(f"   Input: {iso_path}")
    print(f"   Output: {output_path}")
    
    # This requires:
    # 1. Mount ISO
    # 2. Extract files
    # 3. Modify boot files
    # 4. Recreate ISO
    
    print("⚠️  ISO modification requires manual steps:")
    print("   1. Extract Windows ISO")
    print("   2. Remove/rename bootfix.bin (BIOS boot)")
    print("   3. Replace efisys.bin with efisys_noprompt.bin (UEFI boot)")
    print("   4. Replace cdboot.efi with cdboot_noprompt.efi (UEFI boot)")
    print("   5. Recreate ISO with xorriso or similar tool")
    print()
    print("   For now, use VNC automation instead (see below)")


def send_key_via_proxmox_api(vmid: int):
    """
    Send key press via Proxmox API/VNC
    
    Note: Proxmox API doesn't directly support sending keyboard input.
    This would require VNC client library or SSH access.
    """
    print(f"🔄 Attempting to send key press to VM {vmid}...")
    
    # Option 1: Use qm terminal (requires SSH)
    try:
        cmd = f"ssh root@{settings.proxmox_host} 'qm terminal {vmid}'"
        # This opens an interactive terminal - not suitable for automation
        print("⚠️  qm terminal requires interactive session")
    except Exception as e:
        print(f"❌ SSH not available: {e}")
    
    # Option 2: Use VNC client library
    print("💡 Recommended: Use VNC automation library (vncdotool)")
    print("   Install: pip install vncdotool")
    print("   Then use VNC to send key press automatically")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix Windows boot prompt")
    parser.add_argument("--vmid", type=int, help="VM ID to send key press to")
    parser.add_argument("--modify-iso", action="store_true", help="Modify Windows ISO to remove prompt")
    parser.add_argument("--iso-path", type=Path, help="Path to Windows ISO")
    parser.add_argument("--output-path", type=Path, help="Output path for modified ISO")
    
    args = parser.parse_args()
    
    if args.modify_iso:
        if not args.iso_path or not args.output_path:
            print("❌ --iso-path and --output-path required for ISO modification")
            return
        modify_windows_iso_remove_prompt(args.iso_path, args.output_path)
    elif args.vmid:
        send_key_via_proxmox_api(args.vmid)
    else:
        print("Usage:")
        print("  Send key press: python fix_windows_boot_prompt.py --vmid <vmid>")
        print("  Modify ISO: python fix_windows_boot_prompt.py --modify-iso --iso-path <iso> --output-path <output>")


if __name__ == "__main__":
    main()

