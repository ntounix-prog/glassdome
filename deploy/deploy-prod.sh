#!/bin/bash
# Glassdome Production Deployment Script
# Run on production server: bash deploy/deploy-prod.sh

set -e

echo "=== Glassdome Production Deployment ==="

cd /opt/glassdome

# Pull latest code
echo "Pulling latest from main..."
git fetch origin
git checkout main
git pull origin main

# Show version
echo ""
echo "Version: $(git describe --tags 2>/dev/null || git rev-parse --short HEAD)"

# Python dependencies
echo ""
echo "Installing Python dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

# Run database migrations
echo ""
echo "Running database migrations..."
alembic upgrade head

# Build frontend
echo ""
echo "Building frontend..."
cd frontend
npm install --silent 2>/dev/null
npm run build
cd ..

# Update nginx config if changed
echo ""
echo "Checking nginx config..."
if ! diff -q deploy/nginx-glassdome.conf /etc/nginx/sites-enabled/glassdome > /dev/null 2>&1; then
    echo "Updating nginx config..."
    sudo cp deploy/nginx-glassdome.conf /etc/nginx/sites-enabled/glassdome
    sudo nginx -t && sudo systemctl reload nginx
else
    echo "Nginx config unchanged"
fi

# Restart backend
echo ""
echo "Restarting backend..."
sudo systemctl restart glassdome

# Verify
sleep 3
echo ""
echo "=== Verification ==="
curl -s http://localhost/api/health

echo ""
echo "=== Deployment Complete ==="

