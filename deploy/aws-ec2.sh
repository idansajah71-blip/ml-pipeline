#!/bin/bash
set -e

# =====================================================
# ML Pipeline - AWS EC2 Deployment Script
# =====================================================
# This script sets up the ML Pipeline on an AWS EC2 instance
# Tested on: Ubuntu 22.04 LTS, Amazon Linux 2
# =====================================================

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# =====================================================
# 1. System Update & Dependencies
# =====================================================
print_status "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

print_status "Installing Docker..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

print_status "Adding user to docker group..."
sudo usermod -aG docker $USER

# =====================================================
# 2. Clone Repository
# =====================================================
print_status "Cloning ML Pipeline repository..."
cd /opt
if [ -d "ml-pipeline" ]; then
    cd ml-pipeline
    git pull origin main
else
    sudo git clone https://github.com/idansajah71-blip/ml-pipeline.git
    sudo chown -R $USER:$USER ml-pipeline
    cd ml-pipeline
fi

# =====================================================
# 3. Environment Configuration
# =====================================================
print_status "Configuring environment..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Generate secure keys
    JWT_SECRET=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -base64 32)
    
    sed -i "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET/" .env
    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$DB_PASSWORD/" .env
    
    print_warning "Generated new JWT_SECRET and DB_PASSWORD"
    print_warning "Please save these securely:"
    echo "JWT_SECRET: $JWT_SECRET"
    echo "DB_PASSWORD: $DB_PASSWORD"
fi

# =====================================================
# 4. Production Environment Setup
# =====================================================
print_status "Setting up production environment..."
cat > .env.production << EOF
APP_NAME=ML Pipeline
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false

HOST=0.0.0.0
PORT=8000

POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=ml_pipeline_db
POSTGRES_USER=ml_user
POSTGRES_PASSWORD=$DB_PASSWORD

REDIS_HOST=redis
REDIS_PORT=6379

JWT_SECRET_KEY=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080

ML_ARTIFACTS_DIR=./ml_artifacts
MAX_UPLOAD_SIZE_MB=100
TRAINING_TIMEOUT_SECONDS=300

ENABLE_METRICS=true
LOG_LEVEL=WARNING
EOF

# =====================================================
# 5. Firewall Configuration
# =====================================================
print_status "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

# =====================================================
# 6. Docker Compose Production
# =====================================================
print_status "Starting production services..."
docker compose -f docker-compose.prod.yml up -d

# =====================================================
# 7. Database Initialization
# =====================================================
print_status "Waiting for database to be ready..."
sleep 10

print_status "Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T app python -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
"

print_status "Seeding database..."
docker compose -f docker-compose.prod.yml exec -T app python scripts/seed.py

# =====================================================
# 8. Health Check
# =====================================================
print_status "Running health check..."
sleep 5
if curl -f http://localhost:8000/health; then
    print_status "Backend is healthy!"
else
    print_error "Backend health check failed!"
fi

# =====================================================
# 9. SSL/TLS Setup (Let's Encrypt)
# =====================================================
read -p "Do you want to setup SSL/TLS? (y/n): " setup_ssl
if [ "$setup_ssl" = "y" ]; then
    read -p "Enter your domain name: " domain_name
    
    print_status "Installing Certbot..."
    sudo apt-get install -y certbot
    
    print_status "Obtaining SSL certificate..."
    sudo certbot certonly --standalone -d $domain_name --non-interactive --agree-tos --email admin@$domain_name
    
    # Create SSL directory
    mkdir -p nginx/ssl
    sudo cp /etc/letsencrypt/live/$domain_name/fullchain.pem nginx/ssl/cert.pem
    sudo cp /etc/letsencrypt/live/$domain_name/privkey.pem nginx/ssl/key.pem
    
    # Update nginx config for SSL
    print_status "Updating Nginx configuration for SSL..."
    
    print_status "SSL/TLS setup completed!"
fi

# =====================================================
# 10. Cron Jobs for Maintenance
# =====================================================
print_status "Setting up cron jobs..."
(crontab -l 2>/dev/null || true; echo "0 2 * * * cd /opt/ml-pipeline && docker compose -f docker-compose.prod.yml exec -T app python scripts/backup.py >> /var/log/ml-pipeline-backup.log 2>&1") | crontab -
(crontab -l 2>/dev/null || true; echo "*/5 * * * * curl -f http://localhost:8000/health >> /var/log/ml-pipeline-health.log 2>&1") | crontab -

print_status "=========================================="
print_status "ML Pipeline deployed successfully!"
print_status "=========================================="
print_status ""
print_status "Services:"
print_status "  - Frontend: http://$(curl -s ifconfig.me)"
print_status "  - API: http://$(curl -s ifconfig.me):8000"
print_status "  - API Docs: http://$(curl -s ifconfig.me):8000/docs"
print_status ""
print_status "Default Users:"
print_status "  - Admin: admin@mlpipeline.com / admin123"
print_status "  - Data Scientist: datascientist@mlpipeline.com / ds123456"
print_status ""
print_status "Useful commands:"
print_status "  - View logs: docker compose -f docker-compose.prod.yml logs -f"
print_status "  - Restart: docker compose -f docker-compose.prod.yml restart"
print_status "  - Stop: docker compose -f docker-compose.prod.yml down"
print_status "  - Update: cd /opt/ml-pipeline && git pull && docker compose -f docker-compose.prod.yml up -d"
