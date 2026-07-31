#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Update Script
# =====================================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[UPDATE]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cd /opt/ml-pipeline

# =====================================================
# 1. Create backup before update
# =====================================================
print_status "Creating pre-update backup..."
./deploy/backup.sh

# =====================================================
# 2. Pull latest changes
# =====================================================
print_status "Pulling latest changes..."
git pull origin main

# =====================================================
# 3. Rebuild Docker images
# =====================================================
print_status "Rebuilding Docker images..."
docker compose -f docker-compose.prod.yml build --no-cache

# =====================================================
# 4. Restart services
# =====================================================
print_status "Restarting services..."
docker compose -f docker-compose.prod.yml up -d

# =====================================================
# 5. Run migrations (if any)
# =====================================================
print_status "Running migrations..."
sleep 10
docker compose -f docker-compose.prod.yml exec -T app python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
" || true

# =====================================================
# 6. Health Check
# =====================================================
print_status "Running health check..."
sleep 5
if curl -f http://localhost:8000/health; then
    print_status "Update completed successfully!"
else
    print_warning "Health check failed. Check logs with: docker compose -f docker-compose.prod.yml logs -f"
fi
