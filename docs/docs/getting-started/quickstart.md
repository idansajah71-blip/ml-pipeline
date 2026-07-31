---
sidebar_position: 2
title: Quick Start
description: Get started with ML Pipeline in 5 minutes
---

# Quick Start

Get up and running with ML Pipeline in just a few minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (recommended)

## Option 1: Docker (Recommended)

This is the fastest way to get started.

### 1. Clone the repository

```bash
git clone https://github.com/your-username/ml-pipeline.git
cd ml-pipeline
```

### 2. Setup environment

```bash
cp .env.example .env
```

### 3. Start services

```bash
docker compose up -d
```

### 4. Seed database

```bash
docker compose exec app python scripts/seed.py
```

### 5. Access the application

- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs
- **API Health**: http://localhost:8000/health

## Option 2: Local Development

### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis (using Docker)
docker compose up -d postgres redis

# Seed database
python scripts/seed.py

# Start the server
python run.py
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Default Users

| Email | Password | Role |
|-------|----------|------|
| admin@mlpipeline.com | admin123 | Admin |
| datascientist@mlpipeline.com | ds123456 | Data Scientist |
| user@mlpipeline.com | user1234 | User |

## First Steps

### 1. Login to Dashboard

1. Open http://localhost:3000
2. Login with `admin@mlpipeline.com` / `admin123`

### 2. Upload a Dataset

1. Go to **Datasets** page
2. Click **Upload Dataset**
3. Select a CSV or Excel file
4. Enter a name and target column

### 3. Create a Model

1. Go to **Models** page
2. Click **Create Model**
3. Enter model name and select algorithm
4. Click **Create**

### 4. Train the Model

1. Select a dataset from the dropdown
2. Click **Train**
3. Wait for training to complete

### 5. Make Predictions

1. Go to **Predictions** page
2. Select your trained model
3. Enter input data in JSON format
4. Click **Predict**

## API Examples

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@mlpipeline.com", "password": "admin123"}'
```

### Upload Dataset

```bash
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@data.csv" \
  -F "name=My Dataset" \
  -F "target_column=target"
```

### Train Model

```bash
curl -X POST http://localhost:8000/api/v1/models/MODEL_ID/train \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"dataset_id": "DATASET_ID", "algorithm": "random_forest"}'
```

### Make Prediction

```bash
curl -X POST http://localhost:8000/api/v1/models/MODEL_ID/predict \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"data": [{"feature1": 1.0, "feature2": 2.0}]}'
```

## Next Steps

- [Installation Guide](./installation) - Detailed installation options
- [Configuration](./configuration) - Customize your setup
- [First Model Tutorial](../tutorials/iris-classification) - Build your first ML model
