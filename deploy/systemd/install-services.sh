#!/bin/bash
# Install Glassdome systemd services
# Run with: sudo ./install-services.sh

set -e

echo "=== Installing Glassdome Services ==="

# Create log directory
mkdir -p /var/log/glassdome
chown nomad:nomad /var/log/glassdome

# Copy service files
cp /home/nomad/glassdome/deploy/systemd/glassdome-backend.service /etc/systemd/system/
cp /home/nomad/glassdome/deploy/systemd/glassdome-frontend.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable services (start on boot)
systemctl enable glassdome-backend
systemctl enable glassdome-frontend

# Stop any running instances first
pkill -f "uvicorn glassdome" 2>/dev/null || true
pkill -f "vite --host" 2>/dev/null || true
sleep 2

# Start services
systemctl start glassdome-backend
sleep 3
systemctl start glassdome-frontend

echo ""
echo "=== Services Installed ==="
echo ""
systemctl status glassdome-backend --no-pager -l | head -15
echo ""
systemctl status glassdome-frontend --no-pager -l | head -15
echo ""
echo "Commands:"
echo "  sudo systemctl status glassdome-backend"
echo "  sudo systemctl status glassdome-frontend"
echo "  sudo journalctl -u glassdome-backend -f"
echo "  sudo journalctl -u glassdome-frontend -f"
echo "  sudo systemctl restart glassdome-backend"
echo "  sudo systemctl restart glassdome-frontend"

