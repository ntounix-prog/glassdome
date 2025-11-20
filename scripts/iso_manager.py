#!/usr/bin/env python3
"""
ISO Manager for Glassdome

Downloads and manages ISO files for Windows and other operating systems.
Stores ISOs within the Glassdome package directory.
"""
import os
import sys
import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, Any, Optional
from tqdm import tqdm


# ISO Storage Configuration (relative to glassdome root)
SCRIPT_DIR = Path(__file__).parent
GLASSDOME_ROOT = SCRIPT_DIR.parent
ISO_BASE_DIR = GLASSDOME_ROOT / "isos"
ISO_MANIFEST = ISO_BASE_DIR / "manifest.json"


# Available ISOs with download information
ISO_CATALOG = {
    "windows-server-2022": {
        "name": "Windows Server 2022 Evaluation",
        "filename": "windows-server-2022-eval.iso",
        "url": "https://go.microsoft.com/fwlink/p/?LinkID=2195280",
        "size_gb": 5.3,
        "description": "Windows Server 2022 Datacenter Evaluation (180 days)",
        "type": "windows",
        "checksum": None  # Will be calculated after download
    },
    "windows-11-enterprise": {
        "name": "Windows 11 Enterprise Evaluation",
        "filename": "windows-11-enterprise-eval.iso",
        "url": "https://www.microsoft.com/en-us/evalcenter/download-windows-11-enterprise",
        "size_gb": 5.1,
        "description": "Windows 11 Enterprise Evaluation (90 days)",
        "type": "windows",
        "manual": True,  # Requires manual download
        "note": "Visit URL manually - Microsoft requires form submission"
    },
    "virtio-win": {
        "name": "VirtIO Drivers for Windows",
        "filename": "virtio-win.iso",
        "url": "https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso",
        "size_gb": 0.6,
        "description": "Latest stable VirtIO drivers for Proxmox/KVM",
        "type": "drivers",
        "checksum": None
    },
    "ubuntu-22.04-live": {
        "name": "Ubuntu 22.04 LTS Live Server",
        "filename": "ubuntu-22.04-live-server-amd64.iso",
        "url": "https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso",
        "size_gb": 2.0,
        "description": "Ubuntu 22.04 LTS Live Server ISO",
        "type": "linux",
        "checksum": None
    }
}


def setup_iso_directory():
    """Create ISO storage directory structure"""
    print(f"Setting up ISO storage at {ISO_BASE_DIR}...")
    
    # Create base directory
    ISO_BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    (ISO_BASE_DIR / "windows").mkdir(exist_ok=True)
    (ISO_BASE_DIR / "linux").mkdir(exist_ok=True)
    (ISO_BASE_DIR / "drivers").mkdir(exist_ok=True)
    (ISO_BASE_DIR / "custom").mkdir(exist_ok=True)
    
    # Initialize manifest if it doesn't exist
    if not ISO_MANIFEST.exists():
        with open(ISO_MANIFEST, 'w') as f:
            json.dump({"isos": {}, "last_updated": None}, f, indent=2)
    
    print(f"✅ ISO directory structure created")
    print(f"   Base: {ISO_BASE_DIR}")
    print(f"   Manifest: {ISO_MANIFEST}")


def calculate_checksum(filepath: Path, algorithm: str = "sha256") -> str:
    """Calculate checksum of a file"""
    hash_obj = hashlib.new(algorithm)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def download_file(url: str, destination: Path, description: str = "File") -> bool:
    """
    Download a file with progress bar
    
    Args:
        url: Download URL
        destination: Destination file path
        description: Description for progress bar
    
    Returns:
        True if successful, False otherwise
    """
    try:
        print(f"\n→ Downloading {description}...")
        print(f"   URL: {url}")
        print(f"   Destination: {destination}")
        
        # Stream download with progress bar
        response = requests.get(url, stream=True, allow_redirects=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(destination, 'wb') as f, tqdm(
            desc=description,
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                size = f.write(chunk)
                pbar.update(size)
        
        print(f"✅ Downloaded: {destination.name}")
        return True
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        if destination.exists():
            destination.unlink()
        return False


def download_iso(iso_id: str) -> bool:
    """
    Download an ISO from the catalog
    
    Args:
        iso_id: ISO identifier from catalog
    
    Returns:
        True if successful, False otherwise
    """
    if iso_id not in ISO_CATALOG:
        print(f"❌ Unknown ISO: {iso_id}")
        print(f"Available ISOs: {', '.join(ISO_CATALOG.keys())}")
        return False
    
    iso_info = ISO_CATALOG[iso_id]
    
    # Check if manual download required
    if iso_info.get("manual"):
        print(f"\n⚠️  {iso_info['name']} requires manual download")
        print(f"   URL: {iso_info['url']}")
        print(f"   {iso_info.get('note', '')}")
        print(f"\n   Please download manually and place at:")
        print(f"   {ISO_BASE_DIR / iso_info['type'] / iso_info['filename']}")
        return False
    
    # Determine destination
    iso_type = iso_info['type']
    destination = ISO_BASE_DIR / iso_type / iso_info['filename']
    
    # Check if already exists
    if destination.exists():
        print(f"\n⚠️  ISO already exists: {destination}")
        print(f"   Size: {destination.stat().st_size / (1024**3):.2f} GB")
        response = input("   Re-download? (y/n): ").strip().lower()
        if response != 'y':
            print("   Skipping download")
            return True
        destination.unlink()
    
    # Download
    print(f"\n{'='*60}")
    print(f"  {iso_info['name']}")
    print(f"{'='*60}")
    print(f"Description: {iso_info['description']}")
    print(f"Size: ~{iso_info['size_gb']} GB")
    print(f"This may take several minutes...")
    
    success = download_file(iso_info['url'], destination, iso_info['name'])
    
    if success:
        # Calculate checksum
        print(f"\n→ Calculating checksum...")
        checksum = calculate_checksum(destination)
        print(f"   SHA256: {checksum}")
        
        # Update manifest
        update_manifest(iso_id, destination, checksum)
        
        print(f"\n✅ ISO ready: {destination}")
        return True
    
    return False


def update_manifest(iso_id: str, filepath: Path, checksum: str):
    """Update ISO manifest with download info"""
    import datetime
    
    with open(ISO_MANIFEST, 'r') as f:
        manifest = json.load(f)
    
    manifest['isos'][iso_id] = {
        'filename': filepath.name,
        'path': str(filepath),
        'checksum': checksum,
        'size_bytes': filepath.stat().st_size,
        'downloaded_at': datetime.datetime.now().isoformat()
    }
    manifest['last_updated'] = datetime.datetime.now().isoformat()
    
    with open(ISO_MANIFEST, 'w') as f:
        json.dump(manifest, f, indent=2)


def list_isos():
    """List all available and downloaded ISOs"""
    print("\n" + "="*60)
    print("  GLASSDOME ISO CATALOG")
    print("="*60)
    
    # Load manifest
    with open(ISO_MANIFEST, 'r') as f:
        manifest = json.load(f)
    
    downloaded = manifest.get('isos', {})
    
    for iso_id, info in ISO_CATALOG.items():
        status = "✅ DOWNLOADED" if iso_id in downloaded else "⬜ NOT DOWNLOADED"
        manual = " (MANUAL)" if info.get("manual") else ""
        
        print(f"\n[{iso_id}]{manual}")
        print(f"  {info['name']}")
        print(f"  {info['description']}")
        print(f"  Size: ~{info['size_gb']} GB")
        print(f"  Status: {status}")
        
        if iso_id in downloaded:
            iso_data = downloaded[iso_id]
            print(f"  Path: {iso_data['path']}")
            print(f"  Checksum: {iso_data['checksum'][:16]}...")


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Glassdome ISO Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup ISO directory
  python iso_manager.py setup
  
  # List available ISOs
  python iso_manager.py list
  
  # Download Windows Server 2022
  python iso_manager.py download windows-server-2022
  
  # Download VirtIO drivers
  python iso_manager.py download virtio-win
  
  # Download all (automated downloads only)
  python iso_manager.py download-all
        """
    )
    
    parser.add_argument('command', choices=['setup', 'list', 'download', 'download-all'],
                       help='Command to execute')
    parser.add_argument('iso_id', nargs='?', help='ISO identifier (for download command)')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        setup_iso_directory()
        print("\n✅ Setup complete!")
        print("\nNext steps:")
        print("  1. Download ISOs: sudo python iso_manager.py download windows-server-2022")
        print("  2. Or list catalog: python iso_manager.py list")
    
    elif args.command == 'list':
        if not ISO_BASE_DIR.exists():
            print("❌ ISO directory not set up. Run: sudo python iso_manager.py setup")
            sys.exit(1)
        list_isos()
    
    elif args.command == 'download':
        if not args.iso_id:
            print("❌ Please specify an ISO ID")
            print(f"Available: {', '.join(ISO_CATALOG.keys())}")
            sys.exit(1)
        
        if not ISO_BASE_DIR.exists():
            print("⚠️  ISO directory not set up. Setting up now...")
            setup_iso_directory()
        
        success = download_iso(args.iso_id)
        sys.exit(0 if success else 1)
    
    elif args.command == 'download-all':
        if not ISO_BASE_DIR.exists():
            setup_iso_directory()
        
        print("\n" + "="*60)
        print("  DOWNLOADING ALL AUTOMATED ISOs")
        print("="*60)
        
        results = {}
        for iso_id, info in ISO_CATALOG.items():
            if not info.get("manual"):
                results[iso_id] = download_iso(iso_id)
        
        print("\n" + "="*60)
        print("  DOWNLOAD SUMMARY")
        print("="*60)
        for iso_id, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{iso_id}: {status}")


if __name__ == "__main__":
    main()

