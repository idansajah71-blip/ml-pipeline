---
sidebar_position: 4
title: GCP
---

# GCP Deployment

Deploy ML Pipeline to Google Cloud Platform.

## Quick Deploy

```bash
./deploy/gcp-compute.sh
```

## Prerequisites

- GCP account with billing enabled
- gcloud CLI configured
- Compute Engine instance

## Architecture

```
Internet → Cloud Load Balancer → Compute Engine (Docker)
                               → Cloud SQL (PostgreSQL)
                               → Memorystore (Redis)
```

## Step 1: Create GCP Project

```bash
gcloud projects create ml-pipeline-project
gcloud config set project ml-pipeline-project
```

## Step 2: Enable APIs

```bash
gcloud services enable compute.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable redis.googleapis.com
```

## Step 3: Create Compute Instance

```bash
gcloud compute instances create ml-pipeline \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud
```

## Step 4: Setup Firewall

```bash
gcloud compute firewall-rules create allow-http \
  --allow tcp:80,tcp:443 \
  --target-tags=ml-pipeline

gcloud compute firewall-rules create allow-ssh \
  --allow tcp:22 \
  --source-ranges=YOUR_IP/32
```

## Step 5: Deploy

```bash
# SSH into instance
gcloud compute ssh ml-pipeline --zone=us-central1-a

# Clone and deploy
git clone https://github.com/your-org/ml-pipeline.git
cd ml-pipeline
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d
docker compose exec app python scripts/seed.py
```

## Step 6: Setup SSL with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.yourdomain.com
```

## Cloud SQL (Optional)

For managed PostgreSQL:

```bash
gcloud sql instances create ml-pipeline-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1
```

## Cost Estimate

| Service | Monthly Cost |
|---------|-------------|
| Compute e2-medium | ~$25 |
| Cloud SQL db-f1-micro | ~$8 |
| Memorystore | ~$15 |
| Load Balancer | ~$18 |
| **Total** | **~$66** |
