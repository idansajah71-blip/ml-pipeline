---
sidebar_position: 1
title: Docker Deployment
description: Deploy with Docker
---

# Docker Deployment

Deploy ML Pipeline using Docker Compose.

## Prerequisites

- Docker 24+
- Docker Compose v2+

## Quick Start

```bash
# Clone repository
git clone https://github.com/your-username/ml-pipeline.git
cd ml-pipeline

# Setup environment
cp .env.example .env

# Start services
docker compose up -d

# Seed database
docker compose exec app python scripts/seed.py
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| app | 8000 | FastAPI backend |
| frontend | 3000 | Next.js dashboard |
| postgres | 5432 | PostgreSQL database |
| redis | 6379 | Redis cache |

## Configuration

### Environment Variables

Edit `.env` file:

```bash
# Database
POSTGRES_PASSWORD=your_secure_password

# Authentication
JWT_SECRET_KEY=your_jwt_secret_key

# Application
ENVIRONMENT=production
DEBUG=false
```

### Docker Compose Files

| File | Environment |
|------|-------------|
| docker-compose.yml | Development |
| docker-compose.prod.yml | Production |
| docker-compose.logging.yml | Logging stack |

## Production Deployment

### 1. Configure Production Environment

```bash
# Create production env file
cat > .env.production << EOF
ENVIRONMENT=production
DEBUG=false
POSTGRES_PASSWORD=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)
EOF
```

### 2. Start Production Services

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 3. Setup SSL/TLS

```bash
# Install Certbot
sudo apt install certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
mkdir -p nginx/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## Commands

### Service Management

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Restart services
docker compose restart

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f app
```

### Database Operations

```bash
# Access PostgreSQL
docker compose exec postgres psql -U ml_user -d ml_pipeline_db

# Backup database
docker compose exec postgres pg_dumpall -U ml_user > backup.sql

# Restore database
docker compose exec -T postgres psql -U ml_user < backup.sql
```

### Scaling

```bash
# Scale backend
docker compose up -d --scale app=3
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/health
```

### View Metrics

```bash
# With logging stack
docker compose -f docker-compose.logging.yml up -d

# Access Grafana: http://localhost:3001
# Access Prometheus: http://localhost:9090
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs app

# Check status
docker compose ps
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker compose ps postgres

# Test connection
docker compose exec postgres pg_isready -U ml_user
```

### Out of Memory

```bash
# Check resource usage
docker stats

# Increase memory limit in docker-compose.yml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 2G
```

## Next Steps

- [Kubernetes Deployment](./kubernetes)
- [AWS Deployment](./aws)
- [Monitoring Guide](../guides/monitoring)
