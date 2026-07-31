#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Restore Script
# =====================================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[RESTORE]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_timestamp>"
    echo "Example: $0 20240101_120000"
    exit 1
fi

BACKUP_DIR="/opt/ml-pipeline/backups"
TIMESTAMP=$1
BACKUP_NAME="ml-pipeline-backup-$TIMESTAMP"

# Check if backup exists
if [ ! -f "$BACKUP_DIR/$BACKUP_NAME-db.sql" ]; then
    print_error "Backup not found: $BACKUP_NAME"
    exit 1
fi

print_warning "This will restore from backup: $BACKUP_NAME"
read -p "Are you sure? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    print_error "Restore cancelled."
    exit 1
fi

# =====================================================
# 1. Stop services
# =====================================================
print_status "Stopping services..."
cd /opt/ml-pipeline
docker compose -f docker-compose.prod.yml down

# =====================================================
# 2. Restore Database
# =====================================================
print_status "Restoring PostgreSQL database..."
docker compose -f docker-compose.prod.yml up -d postgres
sleep 10
docker compose -f docker-compose.prod.yml exec -T postgres psql -U ml_user < "$BACKUP_DIR/$BACKUP_NAME-db.sql"

# =====================================================
# 3. Restore ML Artifacts
# =====================================================
print_status "Restoring ML artifacts..."
tar -xzf "$BACKUP_DIR/$BACKUP_NAME-artifacts.tar.gz" -C /opt/ml-pipeline/

# =====================================================
# 4. Restore Configuration
# =====================================================
print_status "Restoring configuration..."
tar -xzf "$BACKUP_DIR/$BACKUP_NAME-config.tar.gz" -C /opt/ml-pipeline/

# =====================================================
# 5. Start all services
# =====================================================
print_status "Starting all services..."
docker compose -f docker-compose.prod.yml up -d

# =====================================================
# 6. Health Check
# =====================================================
print_status "Running health check..."
sleep 10
if curl -f http://localhost:8000/health; then
    print_status "Restore completed successfully!"
else
    print_error "Health check failed after restore!"
fi
