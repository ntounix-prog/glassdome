#!/bin/bash
#
# Replicate Glassdome Database from Dev to Prod
# Run this from the dev server (agentx)
#
# This script:
# 1. Dumps the dev database (schema + data)
# 2. Loads it into the prod database
#

set -e

echo "========================================"
echo "Database Replication: Dev → Prod"
echo "========================================"

# Configuration
DEV_HOST="192.168.3.26"
DEV_DB="glassdome"
DEV_USER="glassdome"

PROD_HOST="192.168.3.7"
PROD_DB="glassdome"
PROD_USER="glassdome"
PROD_PASS="glassdome"

DUMP_FILE="/tmp/glassdome_dev_dump.sql"

echo ""
echo "Source (Dev):  $DEV_USER@$DEV_HOST/$DEV_DB"
echo "Target (Prod): $PROD_USER@$PROD_HOST/$PROD_DB"
echo ""

# Check prod connectivity first
echo "[1/4] Testing prod database connectivity..."
if PGPASSWORD=$PROD_PASS psql -h "$PROD_HOST" -U "$PROD_USER" -d "$PROD_DB" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "  ✓ Connected to prod database"
else
    echo "  ✗ Cannot connect to prod database"
    echo "  Make sure PostgreSQL is running on $PROD_HOST"
    echo "  and the glassdome database exists."
    exit 1
fi

# Dump dev database
echo ""
echo "[2/4] Dumping dev database..."
PGPASSWORD=$PROD_PASS pg_dump -h "$DEV_HOST" -U "$DEV_USER" -d "$DEV_DB" \
    --clean --if-exists \
    --no-owner --no-acl \
    -f "$DUMP_FILE"
echo "  ✓ Dump created: $DUMP_FILE ($(du -h $DUMP_FILE | cut -f1))"

# Load into prod (with warning)
echo ""
echo "[3/4] Loading into prod database..."
echo ""
echo "  ⚠️  WARNING: This will REPLACE all data in the prod database!"
echo ""
read -p "  Continue? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "  Aborted."
    rm -f "$DUMP_FILE"
    exit 0
fi

PGPASSWORD=$PROD_PASS psql -h "$PROD_HOST" -U "$PROD_USER" -d "$PROD_DB" -f "$DUMP_FILE" > /dev/null 2>&1
echo "  ✓ Data loaded into prod"

# Verify
echo ""
echo "[4/4] Verifying replication..."
DEV_TABLES=$(PGPASSWORD=$PROD_PASS psql -h "$DEV_HOST" -U "$DEV_USER" -d "$DEV_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")
PROD_TABLES=$(PGPASSWORD=$PROD_PASS psql -h "$PROD_HOST" -U "$PROD_USER" -d "$PROD_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';")

echo "  Dev tables:  $DEV_TABLES"
echo "  Prod tables: $PROD_TABLES"

# Cleanup
rm -f "$DUMP_FILE"

echo ""
echo "========================================"
echo "Database Replication Complete!"
echo "========================================"
echo ""
echo "Prod database is now a copy of dev."
echo ""
echo "IMPORTANT - Future Updates:"
echo "  - Schema changes: Use 'alembic upgrade head'"
echo "  - NEVER run this script again (would overwrite prod data)"
echo ""

