# ML Pipeline

A production-ready Machine Learning platform built with **FastAPI**, **scikit-learn**, and **Next.js**.

The project provides a complete workflow for managing datasets, training machine learning models, deploying them through REST APIs, and monitoring production performance from a modern web dashboard.

---

## Overview

ML Pipeline combines modern backend development, machine learning workflows, and deployment best practices into a single platform.

The system enables users to:

- Upload and manage datasets
- Train multiple machine learning algorithms
- Track experiments and model versions
- Deploy production-ready models
- Serve real-time predictions
- Run A/B testing
- Monitor system performance

---

# Architecture

```text
                        ┌───────────────────────┐
                        │     Next.js 14        │
                        │    Dashboard (UI)     │
                        └──────────┬────────────┘
                                   │
                              REST API
                                   │
                        ┌──────────▼────────────┐
                        │       FastAPI         │
                        │ Authentication        │
                        │ Dataset Management    │
                        │ ML Training           │
                        │ Prediction Service    │
                        └──────┬─────────┬──────┘
                               │         │
                    ┌──────────▼───┐   ┌─▼──────────┐
                    │ PostgreSQL   │   │   Redis    │
                    │ Application  │   │ Cache      │
                    │ Data         │   │ Sessions   │
                    └──────────────┘   └────────────┘

                            Model Artifacts
                                   │
                           File Storage / Registry
```

---

# Data Flow

```
Dataset Upload
        │
        ▼
Validation
        │
        ▼
PostgreSQL + Redis
        │
        ▼
Model Training
        │
        ▼
Model Registry
        │
        ▼
Deployment
        │
        ▼
Prediction API
        │
        ▼
Monitoring
```

---

# Features

## Backend

- FastAPI asynchronous REST API
- scikit-learn training pipeline
- PostgreSQL database
- Redis caching and session management
- JWT Authentication
- Role-Based Access Control (RBAC)
- Model Registry
- Experiment Tracking
- A/B Testing
- Monitoring endpoints

---

## Frontend

- Next.js 14 App Router
- Tailwind CSS
- Responsive dashboard
- Dataset explorer
- Model management
- Interactive charts with Recharts
- Real-time monitoring

---

## Machine Learning

Supported algorithms:

- Random Forest
- Gradient Boosting
- Logistic Regression
- Decision Tree
- Support Vector Machine
- K-Nearest Neighbors
- AdaBoost
- Bagging
- Multi-layer Perceptron

---

## Technology Stack

| Layer | Technology |
|--------|------------|
| Frontend | Next.js 14, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Machine Learning | scikit-learn, pandas, numpy |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| Authentication | JWT, API Key |
| Deployment | Docker, Nginx |
| CI/CD | GitHub Actions |

---

# Quick Start

## Jalur A — Coba cepat (Docker, 3 menit)

```bash
cp .env.example .env
# isi JWT_SECRET_KEY di .env dulu
docker-compose up -d
docker-compose exec app python scripts/seed.py
# Buka http://localhost:3000
```

## Jalur B — Development lokal (tanpa Docker penuh)

```bash
pip install -r requirements.txt
docker-compose up -d postgres redis
python scripts/seed.py
python run.py
# Di terminal lain:
cd frontend && npm install && npm run dev
```

**[OPSIONAL] Jalur C — AutoML & Celery:**
```bash
celery -A app.core.celery_app worker --loglevel=info
```

**[OPSIONAL] Jalur D — Data eksternal BPS/World Bank:**
```bash
# Daftar API key di https://webapi.bps.go.id/developer/register
# Tambahkan BPS_API_KEY=xxx di .env
python -m alembic upgrade head
```

---

## Dashboard

- Dashboard: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

# Dashboard Modules

| Module | Description |
|---------|-------------|
| Dashboard | Overview statistics |
| Datasets | Upload and preview datasets |
| Models | Create and train ML models |
| Experiments | View training history |
| Predictions | Real-time inference |
| A/B Testing | Compare deployed models |
| Monitoring | CPU, RAM, Disk metrics |

> **[OPSIONAL]**: MLflow, Feature Store, Web Scraping, Webhooks, Marketplace — fitur lanjutan, tidak diperlukan untuk penggunaan dasar.

---

# REST API

## Authentication

| Method | Endpoint |
|---------|----------|
| POST | `/api/v1/auth/register` |
| POST | `/api/v1/auth/login` |
| GET | `/api/v1/auth/me` |

### Datasets

| Method | Endpoint |
|---------|----------|
| POST | `/api/v1/datasets` |
| GET | `/api/v1/datasets` |
| GET | `/api/v1/datasets/{id}/preview` |

### Models

| Method | Endpoint |
|---------|----------|
| POST | `/api/v1/models` |
| POST | `/api/v1/models/{id}/train` |
| POST | `/api/v1/models/{id}/predict` |
| POST | `/api/v1/models/{id}/deploy` |

### Experiments

| Method | Endpoint |
|---------|----------|
| GET | `/api/v1/experiments` |
| GET | `/api/v1/experiments/{id}` |

### A/B Testing

| Method | Endpoint |
|---------|----------|
| POST | `/api/v1/ab-tests` |
| POST | `/api/v1/ab-tests/{id}/route` |

### Monitoring

| Method | Endpoint |
|---------|----------|
| GET | `/api/v1/monitoring/stats` |
| GET | `/api/v1/monitoring/system` |

---

# Setup Akun Admin Pertama

Setelah database siap, buat akun admin pertama dengan menjalankan seed script:

```bash
python scripts/seed.py
```

Akun default untuk development:

| Email | Password | Role |
|---------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

> **Warning**: Ganti password sebelum deployment produksi. Jangan commit password ke repository.

---

# Project Structure

```text
app/
├── api/         # 39+ endpoint modules
├── core/        # config, database, auth
├── models/      # SQLAlchemy models
├── services/    # business logic
├── ml/          # training pipeline
└── tests/

frontend/
├── src/app/     # Next.js pages (41+ halaman)
├── src/components/

docs/
├── beefest-use-case.md
├── beefest-presentation.md
└── beefest-demo-curl.md

scripts/
├── seed.py      # Database seeder (idempotent)
└── ci_quality_gates.py
```

---

# Contributing

Contributions are welcome.

Please read **CONTRIBUTING.md** before opening an issue or submitting a pull request.

---

# License

Distributed under the **MIT License**.
