---
sidebar_position: 3
title: Installation
description: Detailed installation guide
---

# Installation

Choose the installation method that best fits your needs.

## System Requirements

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Storage | 20 GB | 50+ GB |
| OS | Ubuntu 20.04, macOS 12, Windows 10 | Latest versions |

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| PostgreSQL | 14+ | Database |
| Redis | 7+ | Cache |
| Docker | 24+ | Containerization (optional) |

## Installation Methods

### Method 1: Docker (Recommended)

The easiest way to install ML Pipeline.

```bash
# Clone repository
git clone https://github.com/your-username/ml-pipeline.git
cd ml-pipeline

# Setup environment
cp .env.example .env

# Start all services
docker compose up -d

# Seed database
docker compose exec app python scripts/seed.py
```

### Method 2: Manual Installation

#### 1. Install Python

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# macOS (using Homebrew)
brew install python@3.11

# Windows
# Download from https://www.python.org/downloads/
```

#### 2. Install Node.js

```bash
# Using nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

#### 3. Install PostgreSQL

```bash
# Ubuntu/Debian
sudo apt install postgresql postgresql-contrib

# macOS
brew install postgresql@16

# Windows
# Download from https://www.postgresql.org/download/windows/
```

#### 4. Install Redis

```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis

# Windows
# Download from https://redis.io/download
```

#### 5. Setup Backend

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure database
createdb ml_pipeline_db

# Update .env file
cp .env.example .env
# Edit .env with your database credentials

# Seed database
python scripts/seed.py
```

#### 6. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Method 3: Kubernetes

For production deployments.

```bash
# Using Helm
cd k8s/helm/ml-pipeline

helm install ml-pipeline . \
  --namespace ml-pipeline \
  --create-namespace \
  --values values.yaml \
  --values values-production.yaml
```

See [Kubernetes Deployment](../deployment/kubernetes) for details.

## Verifying Installation

### 1. Check Backend

```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

### 2. Check Frontend

Open http://localhost:3000 in your browser.

### 3. Run Tests

```bash
# Backend tests
pytest app/tests/ -v

# Frontend build
cd frontend && npm run build
```

## Troubleshooting

### Common Issues

#### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

#### Database Connection Error

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check database exists
psql -U ml_user -d ml_pipeline_db
```

#### Redis Connection Error

```bash
# Check Redis is running
sudo systemctl status redis-server

# Test connection
redis-cli ping
```

## Next Steps

- [Configuration](./configuration) - Customize your setup
- [Quick Start](./quickstart) - Get started quickly
- [Deployment](../deployment/docker) - Deploy to production
