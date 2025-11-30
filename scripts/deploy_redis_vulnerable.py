#!/usr/bin/env python3
"""
Deploy Redis 8.2.1 Vulnerable Server (CVE-2025-49844 - RediShell)
Creates an Ubuntu VM on Proxmox with Redis 8.2.1 configured for evaluation
"""
import asyncio
import logging
import sys
import time
from pathlib import Path
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from glassdome.core.security import ensure_security_context, get_secure_settings
ensure_security_context()

from glassdome.agents.ubuntu_installer import UbuntuInstallerAgent
from glassdome.platforms.proxmox_client import ProxmoxClient
import paramiko
from typing import Optional

# Use centralized logging
try:
    from glassdome.core.logging import setup_logging_from_settings
    setup_logging_from_settings()
except ImportError:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def deploy_redis_vulnerable():
    """Deploy Redis 8.2.1 vulnerable server"""
    
    # Load session-aware settings
    settings = get_secure_settings()
    
    if not settings.proxmox_host:
        logger.error("Proxmox credentials not configured. Check .env file.")
        return
    
    # Initialize Proxmox client
    proxmox = ProxmoxClient(
        host=settings.proxmox_host,
        user=settings.proxmox_user or "root@pam",
        password=settings.proxmox_password,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
        default_node=settings.proxmox_node or "pve"
    )
    
    # Initialize Ubuntu installer agent
    agent = UbuntuInstallerAgent(
        agent_id="redis-vuln-deployer",
        platform_client=proxmox
    )
    
    # DHCP is enabled, no need for static IP allocation
    logger.info("📡 Using DHCP for network configuration")
    
    # Read SSH public key (REQUIRED: cloud-init template doesn't allow password login)
    ssh_key_path = Path("/tmp/glassdome_key")
    ssh_pub_key_path = Path("/tmp/glassdome_key.pub")
    
    if not ssh_key_path.exists():
        logger.error("❌ SSH key not found at /tmp/glassdome_key - REQUIRED for cloud-init")
        return None
    
    if not ssh_pub_key_path.exists():
        # Generate public key from private key
        import subprocess
        try:
            result = subprocess.run(
                ["ssh-keygen", "-y", "-f", str(ssh_key_path)],
                capture_output=True,
                text=True,
                check=True
            )
            ssh_pub_key_path.write_text(result.stdout.strip())
            logger.info("✅ Generated public key from private key")
        except Exception as e:
            logger.error(f"❌ Failed to generate public key: {e}")
            return None
    
    ssh_key_path_str = str(ssh_key_path)
    logger.info("✅ SSH key found and ready")
    
    # VM configuration
    vm_config = {
        "element_type": "ubuntu_vm",
        "config": {
            "name": "redis-vuln-8.2.1",
            "ubuntu_version": "22.04",
            "cores": 2,
            "memory": 4096,  # 4GB RAM for Redis
            "disk_size": 20,
            "network": "vmbr0",
            "vlan_tag": 2,  # For 192.168.3.x network
            # No static IP - using DHCP
            "ssh_user": "ubuntu",
            "password": "glassdome123",  # Password for cloud-init (template now has password enabled)
            "ssh_key_path": ssh_key_path_str,  # SSH key also configured
            "packages": [
                "openssh-server",
                "qemu-guest-agent",
                "curl",
                "wget",
                "build-essential",
                "tcl"
            ]
        }
    }
    
    logger.info("🚀 Deploying Redis 8.2.1 vulnerable server...")
    logger.info(f"   Name: {vm_config['config']['name']}")
    logger.info(f"   Version: Redis 8.2.1 (CVE-2025-49844)")
    
    try:
        # Deploy VM
        result = await agent.execute(vm_config)
        
        if not result.get("success"):
            logger.error(f"❌ Deployment failed: {result.get('error', 'Unknown error')}")
            return None
        
        # Extract VM ID from result (could be in different places)
        vm_id = (result.get("resource_id") or 
                 result.get("vm_id") or 
                 result.get("details", {}).get("vm_id") or
                 result.get("details", {}).get("platform_specific", {}).get("vmid"))
        
        if not vm_id:
            logger.error(f"❌ Deployment failed: No VM ID returned")
            logger.error(f"   Result: {result}")
            return None
        
        # Check if VM is running, start if needed
        status = result.get("status") or result.get("details", {}).get("status")
        if status == "stopped":
            logger.info(f"🔄 VM {vm_id} is stopped, starting...")
            await proxmox.start_vm(str(vm_id))
            await asyncio.sleep(10)
        
        # Get IP address from VM (DHCP assigned)
        logger.info(f"✅ VM {vm_id} deployed, waiting for DHCP IP assignment...")
        
        # Wait for IP via guest agent
        ip_address = None
        for i in range(30):  # Wait up to 2.5 minutes
            ip_address = await proxmox.get_vm_ip(str(vm_id), timeout=10)
            if ip_address:
                logger.info(f"✅ VM {vm_id} got IP: {ip_address}")
                break
            await asyncio.sleep(5)
        
        if not ip_address:
            logger.warning(f"⚠️  Could not get IP for VM {vm_id}, will try SSH with hostname")
            # Try to use VM name or wait longer
            ip_address = "unknown"
        
        logger.info("✅ VM deployed successfully!")
        logger.info(f"   VM ID: {vm_id}")
        if ip_address and ip_address != "unknown":
            logger.info(f"   IP Address: {ip_address}")
        else:
            logger.info(f"   IP Address: DHCP - waiting for assignment...")
        if not ip_address or ip_address == "unknown":
            logger.warning("⚠️  IP address not yet available, trying to get it via guest agent...")
            # Try one more time to get IP
            for i in range(10):
                ip_address = await proxmox.get_vm_ip(str(vm_id), timeout=10)
                if ip_address:
                    logger.info(f"✅ Got IP address: {ip_address}")
                    break
                await asyncio.sleep(5)
            
            if not ip_address or ip_address == "unknown":
                logger.error("❌ Cannot proceed without IP address")
                logger.info("   VM may still be booting. Check Proxmox console for status.")
                return None
        
        logger.info("")
        logger.info("⏳ Waiting for VM to boot and SSH to be ready...")
        
        # Wait for SSH to be ready (using SSH key, not password)
        max_wait = 180  # 3 minutes for cloud-init
        ssh_ready = False
        for i in range(max_wait // 5):
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                # Try SSH key first, fallback to password
                try:
                    ssh.connect(
                        ip_address,
                        username="ubuntu",
                        key_filename="/tmp/glassdome_key",
                        timeout=5
                    )
                except:
                    # Fallback to password
                    ssh.connect(
                        ip_address,
                        username="ubuntu",
                        password="glassdome123",
                        timeout=5
                    )
                ssh.close()
                ssh_ready = True
                logger.info(f"✅ SSH is ready after {i * 5} seconds")
                break
            except Exception as e:
                if i < (max_wait // 5) - 1:
                    await asyncio.sleep(5)
                else:
                    logger.warning(f"⚠️  SSH not ready after {max_wait} seconds: {e}")
        
        if not ssh_ready:
            logger.error("❌ SSH not available, cannot configure Redis")
            return None
        
        # Configure Redis via SSH
        logger.info("🔧 Configuring Redis 8.2.1...")
        await configure_redis(ip_address, "ubuntu", None)  # No password, use SSH key
        
        logger.info("")
        logger.info("✅ Redis vulnerable server setup complete!")
        logger.info("")
        logger.info("📋 Connection Details:")
        logger.info(f"   Host: {ip_address}")
        logger.info("   Port: 6379")
        logger.info("   Password: glassdome123")
        logger.info("")
        logger.info("🧪 Test Commands:")
        logger.info(f"   redis-cli -h {ip_address} -p 6379 -a glassdome123 PING")
        logger.info(f"   redis-cli -h {ip_address} -p 6379 -a glassdome123 EVAL \"return 1\" 0")
        logger.info(f"   redis-cli -h {ip_address} -p 6379 -a glassdome123 INFO server | grep redis_version")
        logger.info("")
        logger.info("⚠️  WARNING: This server is intentionally vulnerable for evaluation only!")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Deployment error: {e}", exc_info=True)
        return None


async def configure_redis(ip_address: str, username: str, password: Optional[str] = None):
    """Configure Redis 8.2.1 on the deployed VM via SSH"""
    
    # Connect via SSH key (password not used for cloud-init template)
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # Try SSH key first, fallback to password
        try:
            ssh.connect(
                ip_address,
                username=username,
                key_filename="/tmp/glassdome_key",
                timeout=10
            )
        except:
            # Fallback to password
            ssh.connect(
                ip_address,
                username=username,
                password="glassdome123",
                timeout=10
            )
        logger.info("✅ SSH connection established with key")
    except Exception as e:
        logger.error(f"❌ Failed to connect via SSH: {e}")
        return
    
    # Redis installation script
    redis_setup_script = """#!/bin/bash
set -e

echo "📦 Installing Redis 8.2.1..."

# Update system
sudo apt-get update
sudo apt-get install -y wget build-essential tcl

# Download and compile Redis 8.2.1 (vulnerable version)
cd /tmp
wget -q https://download.redis.io/releases/redis-8.2.1.tar.gz
tar xzf redis-8.2.1.tar.gz
cd redis-8.2.1
make -j$(nproc)
sudo make install

# Create redis user
sudo useradd -r -s /bin/false redis 2>/dev/null || true

# Create Redis directories
sudo mkdir -p /etc/redis
sudo mkdir -p /var/lib/redis
sudo mkdir -p /var/log/redis
sudo chown redis:redis /var/lib/redis
sudo chown redis:redis /var/log/redis

# Create Redis configuration
sudo tee /etc/redis/redis.conf > /dev/null << 'REDISCONF'
# Redis 8.2.1 Configuration for CVE-2025-49844 (RediShell) Evaluation
port 6379
bind 0.0.0.0
protected-mode no
requirepass glassdome123

# Enable Lua scripting (required for vulnerability)
lua-time-limit 5000

# Logging
logfile /var/log/redis/redis-server.log
loglevel notice

# Persistence (optional, can disable for testing)
save ""
appendonly no

# ACL - Allow scripting for default user
user default on >glassdome123 ~* &* +@all
REDISCONF

# Set permissions
sudo chown redis:redis /etc/redis/redis.conf
sudo chmod 640 /etc/redis/redis.conf

# Create systemd service
sudo tee /etc/systemd/system/redis-server.service > /dev/null << 'SYSTEMD'
[Unit]
Description=Redis In-Memory Data Store
After=network.target

[Service]
User=redis
Group=redis
ExecStart=/usr/local/bin/redis-server /etc/redis/redis.conf
ExecStop=/usr/local/bin/redis-cli -a glassdome123 shutdown
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

# Enable and start Redis
sudo systemctl daemon-reload
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Wait for Redis to start
sleep 3

# Verify Redis is running
if sudo systemctl is-active --quiet redis-server; then
    echo "✅ Redis 8.2.1 started successfully"
    /usr/local/bin/redis-cli -a glassdome123 INFO server | grep redis_version
    /usr/local/bin/redis-cli -a glassdome123 EVAL "return 'Lua scripting enabled'" 0
    echo "✅ Lua scripting verified"
else
    echo "❌ Redis failed to start"
    sudo systemctl status redis-server
    exit 1
fi

# Create evaluation info file
cat > /home/ubuntu/redis-vuln-info.txt << 'INFO'
Redis 8.2.1 Vulnerable Server (CVE-2025-49844 - RediShell)
===========================================================

Vulnerability: Use-after-free in Redis embedded Lua parser
Affected: Redis <= 8.2.1
Fixed: Redis 8.2.2

Connection Details:
- Host: This VM's IP address
- Port: 6379
- Password: glassdome123
- User: default (has @scripting permissions)

Test Connection:
  redis-cli -h <VM_IP> -p 6379 -a glassdome123 PING

Test Lua Scripting (required for exploit):
  redis-cli -h <VM_IP> -p 6379 -a glassdome123 EVAL "return 1" 0

Verify Version:
  redis-cli -h <VM_IP> -p 6379 -a glassdome123 INFO server | grep redis_version

ACL Check:
  redis-cli -h <VM_IP> -p 6379 -a glassdome123 ACL LIST

⚠️  WARNING: This server is intentionally vulnerable for evaluation purposes only.
    Do not expose to untrusted networks.
INFO

echo "✅ Redis vulnerable server setup complete"
echo "📋 See /home/ubuntu/redis-vuln-info.txt for connection details"
"""
    
    try:
        # Execute script
        stdin, stdout, stderr = ssh.exec_command(redis_setup_script)
        
        # Stream output
        for line in iter(stdout.readline, ""):
            if line:
                logger.info(f"   {line.strip()}")
        
        # Check exit status
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            error_output = stderr.read().decode()
            logger.error(f"❌ Redis setup failed: {error_output}")
        else:
            logger.info("✅ Redis 8.2.1 configured successfully")
        
        ssh.close()
        
    except Exception as e:
        logger.error(f"❌ Failed to configure Redis: {e}", exc_info=True)
        ssh.close()


if __name__ == "__main__":
    asyncio.run(deploy_redis_vulnerable())
