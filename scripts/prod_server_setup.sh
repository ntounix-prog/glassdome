#!/bin/bash
#
# Glassdome Production Server Setup Script
# Run this on the production VM after first boot
#
# Usage: curl -sSL https://raw.githubusercontent.com/ntounix-prog/glassdome/main/scripts/prod_server_setup.sh | bash
#        OR copy/paste into the console
#

set -e

echo "========================================"
echo "Glassdome Production Server Setup"
echo "========================================"

# Update and install prerequisites
echo "[1/6] Installing system packages..."
sudo apt-get update
sudo apt-get install -y qemu-guest-agent git python3 python3-pip python3-venv nginx curl

# Enable and start QEMU guest agent
echo "[2/6] Enabling QEMU guest agent..."
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent

# Check network - configure ens19 if not configured
echo "[3/6] Checking network configuration..."
if ! ip addr show ens19 2>/dev/null | grep -q "192.168.3.6"; then
    echo "Configuring ens19 with static IP..."
    
    # Create netplan config for the second interface
    sudo tee /etc/netplan/60-prod-network.yaml > /dev/null << 'EOF'
network:
  version: 2
  ethernets:
    ens19:
      addresses:
        - 192.168.3.6/24
      routes:
        - to: default
          via: 192.168.3.1
      nameservers:
        addresses:
          - 192.168.3.1
EOF
    
    sudo netplan apply
    echo "Network configured!"
else
    echo "ens19 already configured with 192.168.3.6"
fi

# Show network status
echo ""
echo "Current network configuration:"
ip addr show | grep -E "inet |^[0-9]"

# Create glassdome user and directory
echo ""
echo "[4/6] Setting up Glassdome directory..."
sudo mkdir -p /opt/glassdome
sudo chown $USER:$USER /opt/glassdome

# Clone repository
echo "[5/6] Cloning Glassdome repository..."
cd /opt/glassdome
if [ -d ".git" ]; then
    git fetch --all
    git checkout main
    git pull origin main
else
    git clone https://github.com/ntounix-prog/glassdome.git .
    git checkout main
fi

# Set up Python environment
echo "[6/6] Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "========================================"
echo "Basic Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Copy .env file from dev server"
echo "  2. Run: cd /opt/glassdome && source venv/bin/activate"
echo "  3. Build frontend: cd frontend && npm install && npm run build"
echo "  4. Configure nginx and systemd (see docs/DEPLOYMENT.md)"
echo ""
echo "Quick test:"
echo "  python -m glassdome.server"
echo ""

