#!/bin/bash
#
# Glassdome Production Database Setup
# Run this on the prod DB server (glassdome-prod-db / 192.168.3.7)
#
# This script:
# 1. Installs PostgreSQL
# 2. Creates the glassdome database and user
# 3. Configures remote access
#

set -e

echo "========================================"
echo "Glassdome Production Database Setup"
echo "========================================"

# Configuration (match dev for simplicity)
DB_NAME="glassdome"
DB_USER="glassdome"
DB_PASS="glassdome"
ALLOWED_NETWORK="192.168.3.0/24"

# Install PostgreSQL
echo "[1/5] Installing PostgreSQL..."
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib qemu-guest-agent

# Enable and start services
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo systemctl enable qemu-guest-agent
sudo systemctl start qemu-guest-agent

# Create database and user
echo "[2/5] Creating database and user..."
sudo -u postgres psql << EOF
-- Create user if not exists
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
        CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';
    END IF;
END
\$\$;

-- Create database if not exists
SELECT 'CREATE DATABASE $DB_NAME OWNER $DB_USER'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$DB_NAME')\gexec

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "  ✓ Database '$DB_NAME' created"
echo "  ✓ User '$DB_USER' created"

# Configure PostgreSQL to listen on all interfaces
echo "[3/5] Configuring PostgreSQL for remote access..."
PG_VERSION=$(ls /etc/postgresql/)
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

# Update listen_addresses
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF"

# Add remote access rule if not exists
if ! grep -q "$ALLOWED_NETWORK" "$PG_HBA"; then
    echo "host    $DB_NAME    $DB_USER    $ALLOWED_NETWORK    scram-sha-256" | sudo tee -a "$PG_HBA"
fi

# Restart PostgreSQL
echo "[4/5] Restarting PostgreSQL..."
sudo systemctl restart postgresql

# Test connection
echo "[5/5] Testing local connection..."
PGPASSWORD=$DB_PASS psql -U $DB_USER -d $DB_NAME -c "SELECT 1 as test;" && echo "  ✓ Local connection successful"

# Configure network (if not already done)
echo ""
echo "Checking network configuration..."
if ! ip addr show | grep -q "192.168.3.7"; then
    echo "Configuring static IP..."
    sudo tee /etc/netplan/60-prod-network.yaml > /dev/null << 'NETPLAN'
network:
  version: 2
  ethernets:
    ens19:
      addresses:
        - 192.168.3.7/24
      routes:
        - to: default
          via: 192.168.3.1
      nameservers:
        addresses:
          - 192.168.3.1
NETPLAN
    sudo netplan apply
    echo "  ✓ Network configured: 192.168.3.7"
else
    echo "  ✓ Already configured: 192.168.3.7"
fi

echo ""
echo "========================================"
echo "Production Database Setup Complete!"
echo "========================================"
echo ""
echo "Connection Details:"
echo "  Host:     192.168.3.7"
echo "  Port:     5432"
echo "  Database: $DB_NAME"
echo "  User:     $DB_USER"
echo "  Password: $DB_PASS"
echo ""
echo "Connection String:"
echo "  postgresql://$DB_USER:$DB_PASS@192.168.3.7:5432/$DB_NAME"
echo ""
echo "Next Steps:"
echo "  1. From dev server, test: psql -h 192.168.3.7 -U glassdome -d glassdome"
echo "  2. Run migrations: cd /path/to/glassdome && alembic upgrade head"
echo "  3. Or load full dump: pg_dump from dev | psql on prod"
echo ""

