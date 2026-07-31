---
sidebar_position: 1
title: Development
---

# Development Guide

Set up your local development environment.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16 (or use Docker)
- Redis 7 (or use Docker)

## Quick Start

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start services
docker compose up -d postgres redis

# Setup database
python scripts/seed.py

# Run server
python run.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Project Structure

```
ml-pipeline/
├── app/                    # FastAPI backend
│   ├── core/              # Config, security, utilities
│   ├── ml/                # ML pipeline (processor, trainer)
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic
│   ├── api/               # API routes
│   └── tests/             # Tests
├── frontend/              # Next.js dashboard
│   └── src/
│       ├── app/           # Pages (App Router)
│       ├── components/    # React components
│       ├── lib/           # API client, auth, hooks
│       └── types/         # TypeScript types
├── alembic/               # Database migrations
├── docs/                  # Documentation (Docusaurus)
├── k8s/                   # Kubernetes Helm charts
├── deploy/                # Deployment scripts
└── logging/               # Loki, Grafana, Prometheus
```

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Required variables:
- `JWT_SECRET_KEY` - Generate with `openssl rand -hex 32`
- `POSTGRES_PASSWORD` - Generate with `openssl rand -base64 32`
- `CORS_ORIGINS` - Comma-separated allowed origins

## Database

### Migrations

```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Seed Data

```bash
python scripts/seed.py
```

Creates:
- 3 users (admin, data scientist, user)
- 8 categories
- 12 products
- 3 banners
- 3 delivery options
- 2 vouchers

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Git Workflow

1. Create feature branch: `git checkout -b feature/your-feature`
2. Make changes and commit
3. Push: `git push origin feature/your-feature`
4. Open Pull Request

### Commit Convention

```
feat: add new feature
fix: bug fix
docs: documentation change
test: add tests
refactor: code refactor
chore: maintenance tasks
```
