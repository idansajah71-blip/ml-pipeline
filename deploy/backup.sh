#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Backup Script
# =====================================================

BACKUP_DIR="/opt/ml-pipeline/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ml-pipeline-backup-$TIMESTAMP"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[BACKUP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create backup directory
mkdir -p $BACKUP_DIR

print_status "Starting backup: $BACKUP_NAME"

# =====================================================
# 1. Database Backup
# =====================================================
print_status "Backing up PostgreSQL database..."
docker compose -f docker-compose.prod.yml exec -T postgres pg_dumpall -U ml_user > "$BACKUP_DIR/$BACKUP_NAME-db.sql"

# =====================================================
# 2. ML Artifacts Backup
# =====================================================
print_status "Backing up ML artifacts..."
tar -czf "$BACKUP_DIR/$BACKUP_NAME-artifacts.tar.gz" -C /opt/ml-pipeline ml_artifacts/

# =====================================================
# 3. Configuration Backup
# =====================================================
print_status "Backing up configuration..."
tar -czf "$BACKUP_DIR/$BACKUP_NAME-config.tar.gz" \
    .env.production \
    docker-compose.prod.yml \
    nginx/nginx.conf

# =====================================================
# 4. Cleanup old backups (keep 7 days)
# =====================================================
print_status "Cleaning up old backups..."
find $BACKUP_DIR -name "ml-pipeline-backup-*" -mtime +7 -delete

# =====================================================
# 5. Calculate backup size
# =====================================================
BACKUP_SIZE=$(du -sh $BACKUP_DIR/$BACKUP_NAME-* | awk '{print $1}')

print_status "Backup completed!"
print_status "Files created:"
ls -lh $BACKUP_DIR/$BACKUP_NAME-*
print_status "Total size: $BACKUP_SIZE"
