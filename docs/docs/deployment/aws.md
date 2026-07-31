---
sidebar_position: 3
title: AWS
---

# AWS Deployment

Deploy ML Pipeline to AWS EC2.

## Quick Deploy

```bash
./deploy/aws-ec2.sh
```

## Prerequisites

- AWS CLI configured
- EC2 instance (t3.medium or larger)
- SSH access to instance

## Architecture

```
Internet → ALB → EC2 (Docker) → RDS (PostgreSQL)
                              → ElastiCache (Redis)
```

## Step 1: Launch EC2 Instance

```bash
# Using AWS CLI
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxx \
  --subnet-id subnet-xxxxx
```

## Step 2: SSH into Instance

```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

## Step 3: Install Dependencies

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
```

## Step 4: Clone and Deploy

```bash
git clone https://github.com/your-org/ml-pipeline.git
cd ml-pipeline

# Setup environment
cp .env.example .env
nano .env  # Configure secrets

# Start services
docker compose -f docker-compose.prod.yml up -d

# Seed database
docker compose exec app python scripts/seed.py
```

## Step 5: Configure Security Group

Open ports:
- **80** (HTTP)
- **443** (HTTPS)
- **22** (SSH - restricted)

## Step 6: Setup SSL

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d api.yourdomain.com
```

## Environment Variables

```bash
JWT_SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)
CORS_ORIGINS=https://yourdomain.com
```

## Backup

```bash
# Database backup
./deploy/backup.sh

# Restore
./deploy/restore.sh backup-file.sql
```

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| EC2 t3.medium | ~$30 |
| RDS db.t3.micro | ~$15 |
| ElastiCache | ~$15 |
| ALB | ~$20 |
| **Total** | **~$80** |
