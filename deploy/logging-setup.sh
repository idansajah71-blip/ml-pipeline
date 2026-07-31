#!/bin/bash
set -e

# =====================================================
# ML Pipeline - Logging Stack Setup
# =====================================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[LOGGING]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

cd /opt/ml-pipeline

print_status "Starting logging stack..."

# Start logging services
docker compose -f docker-compose.logging.yml up -d

print_status "Waiting for services to be ready..."
sleep 15

# Check services
print_status "Checking services..."

if curl -f http://localhost:3100/ready > /dev/null 2>&1; then
    print_status "Loki is ready!"
else
    print_warning "Loki may still be starting..."
fi

if curl -f http://localhost:3001/api/health > /dev/null 2>&1; then
    print_status "Grafana is ready!"
else
    print_warning "Grafana may still be starting..."
fi

print_status "=========================================="
print_status "Logging stack deployed!"
print_status "=========================================="
print_status ""
print_status "Services:"
print_status "  - Grafana: http://localhost:3001"
print_status "    Username: admin"
print_status "    Password: ml-pipeline"
print_status ""
print_status "  - Loki: http://localhost:3100"
print_status "  - Prometheus: http://localhost:9090"
print_status ""
print_status "Grafana dashboards:"
print_status "  - ML Pipeline Logs: http://localhost:3001/d/ml-pipeline-logs"
print_status ""
print_status "Useful commands:"
print_status "  - View logs: docker compose -f docker-compose.logging.yml logs -f"
print_status "  - Stop: docker compose -f docker-compose.logging.yml down"
print_status "  - Restart: docker compose -f docker-compose.logging.yml restart"
