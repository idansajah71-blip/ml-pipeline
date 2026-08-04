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

## Docker

```bash
cp .env.example .env

docker-compose up -d

docker-compose exec app python scripts/seed.py
```

Application

```
Dashboard
http://localhost:3000

API Documentation
http://localhost:8000/docs
```

---

## Local Development

### Backend

```bash
pip install -r requirements.txt

docker-compose up -d postgres redis

python scripts/seed.py

python run.py
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

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

# Default Accounts

| Email | Password | Role |
|---------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

---

# Project Structure

```text
backend/
├── api/
├── core/
├── models/
├── services/
├── ml/
├── scripts/

frontend/
├── app/
├── components/
├── lib/

docker-compose.yml
README.md
```

---

# Contributing

Contributions are welcome.

Please read **CONTRIBUTING.md** before opening an issue or submitting a pull request.

---

# License

Distributed under the **MIT License**.
