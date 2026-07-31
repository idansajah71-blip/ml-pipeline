#!/bin/bash

# =====================================================
# ML Pipeline - Health Check Script
# =====================================================

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_ok() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

echo "=========================================="
echo "ML Pipeline Health Check"
echo "=========================================="
echo ""

# 1. Check Docker containers
echo "Docker Containers:"
if docker compose -f docker-compose.prod.yml ps | grep -q "running"; then
    print_ok "Containers are running"
else
    print_fail "Some containers are not running"
fi

# 2. Check Backend API
echo ""
echo "Backend API:"
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    print_ok "API is responding"
else
    print_fail "API is not responding"
fi

# 3. Check Database
echo ""
echo "Database:"
if docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U ml_user > /dev/null 2>&1; then
    print_ok "PostgreSQL is ready"
else
    print_fail "PostgreSQL is not ready"
fi

# 4. Check Redis
echo ""
echo "Redis:"
if docker compose -f docker-compose.prod.yml exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_ok "Redis is responding"
else
    print_fail "Redis is not responding"
fi

# 5. Check Frontend (if running)
echo ""
echo "Frontend:"
if curl -f http://localhost:3000 > /dev/null 2>&1; then
    print_ok "Frontend is responding"
else
    print_fail "Frontend is not responding"
fi

# 6. Check disk space
echo ""
echo "Disk Space:"
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    print_ok "Disk usage: ${DISK_USAGE}%"
else
    print_fail "Disk usage critical: ${DISK_USAGE}%"
fi

# 7. Check memory
echo ""
echo "Memory:"
MEM_USAGE=$(free | awk 'NR==2 {printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -lt 80 ]; then
    print_ok "Memory usage: ${MEM_USAGE}%"
else
    print_fail "Memory usage high: ${MEM_USAGE}%"
fi

echo ""
echo "=========================================="
echo "Health check completed at: $(date)"
echo "=========================================="
