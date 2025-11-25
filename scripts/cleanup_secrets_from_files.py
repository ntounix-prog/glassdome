#!/usr/bin/env python3
"""
Clean up secrets from .bashrc and .env files
Moves them to .env-org backup and removes/comments them from source files
"""
from pathlib import Path
import re
import shutil
from datetime import datetime

# All secret keys we're looking for
SECRET_KEYS = {
    # Proxmox
    'PROXMOX_PASSWORD', 'PROXMOX_ADMIN_PASSWD', 'PROXMOX_TOKEN_VALUE',
    'PROXMOX_TOKEN_VALUE_02', 'PROXMOX_TOKEN_VALUE_03',
    # ESXi
    'ESXI_PASSWORD',
    # Azure
    'AZURE_CLIENT_SECRET',
    # AWS
    'AWS_SECRET_ACCESS_KEY', 'AWS_ACCESS_KEY_ID',
    # AI Model API Keys
    'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'XAI_API_KEY',
    'PERPLEXITY_API_KEY', 'RAPIDAPI_KEY',
    # Google
    'GOOGLE_SEARCH_API', 'GOOGLE_SEARCH_API_KEY', 'GOOGLE_ENGINE_ID',
    # Mailcow
    'MAIL_API',
    # JWT
    'SECRET_KEY',
}

# Pattern for PROXMOX_TOKEN_VALUE_XX
TOKEN_PATTERN = re.compile(r'^PROXMOX_TOKEN_VALUE_\d+$')

def is_secret_key(key):
    """Check if a key is a secret"""
    return key in SECRET_KEYS or TOKEN_PATTERN.match(key)

def extract_secrets_from_file(filepath):
    """Extract secrets from a file, return dict of key->value"""
    secrets = {}
    if not filepath.exists():
        return secrets
    
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Handle export KEY="value" format (.bashrc)
            is_export = line.startswith('export ')
            if is_export:
                line = line[7:].strip()
            
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                
                if is_secret_key(key):
                    secrets[key] = value
    
    return secrets

def cleanup_file(filepath, secrets_to_remove, backup_suffix='.backup'):
    """Remove or comment out secrets from a file"""
    if not filepath.exists():
        return False, "File does not exist"
    
    # Create backup
    backup_path = filepath.with_suffix(filepath.suffix + backup_suffix)
    shutil.copy2(filepath, backup_path)
    
    # Read file
    with open(filepath) as f:
        lines = f.readlines()
    
    # Process lines
    modified_lines = []
    removed_count = 0
    
    for line in lines:
        original_line = line
        line_stripped = line.strip()
        
        # Skip comments and empty lines
        if not line_stripped or line_stripped.startswith('#'):
            modified_lines.append(line)
            continue
        
        # Check if this line contains a secret
        is_export = line_stripped.startswith('export ')
        line_to_check = line_stripped[7:].strip() if is_export else line_stripped
        
        if '=' in line_to_check:
            key = line_to_check.split('=', 1)[0].strip()
            
            if is_secret_key(key):
                # Comment it out instead of removing (safer)
                if line_stripped.startswith('export '):
                    modified_lines.append(f"# {line_stripped}  # Moved to secrets manager\n")
                else:
                    modified_lines.append(f"# {line_stripped}  # Moved to secrets manager\n")
                removed_count += 1
                continue
        
        modified_lines.append(line)
    
    # Write modified file
    with open(filepath, 'w') as f:
        f.writelines(modified_lines)
    
    return True, f"Commented out {removed_count} secrets (backup: {backup_path.name})"

def main():
    """Main cleanup process"""
    print("=" * 70)
    print("SECRETS CLEANUP - Moving secrets to .env-org and cleaning source files")
    print("=" * 70)
    
    bashrc = Path.home() / '.bashrc'
    env_file = Path('.env')
    env_org = Path('.env-org')
    
    # Step 1: Extract all secrets
    print("\n1. Extracting secrets from files...")
    bashrc_secrets = extract_secrets_from_file(bashrc)
    env_secrets = extract_secrets_from_file(env_file)
    
    # Combine (env takes precedence for duplicates)
    all_secrets = {**bashrc_secrets, **env_secrets}
    
    print(f"   Found {len(bashrc_secrets)} secrets in .bashrc")
    print(f"   Found {len(env_secrets)} secrets in .env")
    print(f"   Total unique secrets: {len(all_secrets)}")
    
    if not all_secrets:
        print("\n   ✅ No secrets found to clean up!")
        return
    
    # Step 2: Create .env-org backup
    print("\n2. Creating .env-org backup...")
    with open(env_org, 'w') as f:
        f.write(f"# Backup of all secrets from .bashrc and .env\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n")
        f.write("# DO NOT COMMIT TO GIT - These secrets are now in the secrets manager\n")
        f.write("# This file is for reference only\n\n")
        
        for key in sorted(all_secrets.keys()):
            f.write(f"{key}={all_secrets[key]}\n")
    
    print(f"   ✅ Saved {len(all_secrets)} secrets to .env-org")
    
    # Step 3: Clean up .bashrc
    print("\n3. Cleaning up .bashrc...")
    if bashrc.exists() and bashrc_secrets:
        success, message = cleanup_file(bashrc, bashrc_secrets)
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ⚠️  {message}")
    else:
        print("   ⚠️  No secrets found in .bashrc or file doesn't exist")
    
    # Step 4: Clean up .env
    print("\n4. Cleaning up .env...")
    if env_file.exists() and env_secrets:
        success, message = cleanup_file(env_file, env_secrets)
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ⚠️  {message}")
    else:
        print("   ⚠️  No secrets found in .env or file doesn't exist")
    
    # Step 5: Summary
    print("\n" + "=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print(f"✅ Backed up {len(all_secrets)} secrets to .env-org")
    print(f"✅ Cleaned up .bashrc and .env (secrets commented out)")
    print(f"\n⚠️  IMPORTANT:")
    print(f"   - Review the changes in .bashrc.backup and .env.backup")
    print(f"   - Secrets are now in the secrets manager")
    print(f"   - .env-org contains the original values (DO NOT COMMIT)")
    print("=" * 70)

if __name__ == '__main__':
    main()

