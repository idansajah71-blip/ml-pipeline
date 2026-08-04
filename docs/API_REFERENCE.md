# API Reference

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

### Register
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "full_name": "Full Name"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "username": "username",
    "role": "user"
  }
}
```

### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

### Get Current User
```http
GET /auth/me
Authorization: Bearer <token>
```

---

## Datasets

### Upload Dataset
```http
POST /datasets
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: data.csv
name: My Dataset
description: Optional description
target_column: label
```

### List Datasets
```http
GET /datasets
Authorization: Bearer <token>
```

### Get Dataset
```http
GET /datasets/{id}
Authorization: Bearer <token>
```

### Preview Dataset
```http
GET /datasets/{id}/preview
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "columns": ["feature1", "feature2", "label"],
  "rows": [
    {"feature1": 1.2, "feature2": 3.4, "label": 0},
    {"feature1": 5.6, "feature2": 7.8, "label": 1}
  ],
  "total_rows": 1000
}
```

### Delete Dataset
```http
DELETE /datasets/{id}
Authorization: Bearer <token>
```

---

## Models

### Create Model
```http
POST /models
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "My Model",
  "algorithm": "random_forest",
  "target_column": "label",
  "description": "Optional description"
}
```

### List Models
```http
GET /models
Authorization: Bearer <token>
```

### Get Model
```http
GET /models/{id}
Authorization: Bearer <token>
```

### Train Model
```http
POST /models/{id}/train
Authorization: Bearer <token>
Content-Type: application/json

{
  "dataset_id": "uuid",
  "algorithm": "random_forest",
  "parameters": {
    "n_estimators": 100,
    "max_depth": 10
  }
}
```

### Make Predictions
```http
POST /models/{id}/predict
Authorization: Bearer <token>
Content-Type: application/json

{
  "data": [
    {"feature1": 1.2, "feature2": 3.4}
  ]
}
```

### Deploy Model
```http
POST /models/{id}/deploy
Authorization: Bearer <token>
```

### Delete Model
```http
DELETE /models/{id}
Authorization: Bearer <token>
```

---

## Experiments

### List Experiments
```http
GET /experiments
Authorization: Bearer <token>
```

### Get Experiment
```http
GET /experiments/{id}
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "name": "Training Run #1",
  "status": "completed",
  "parameters": {"algorithm": "random_forest", "n_estimators": 100},
  "results": {"accuracy": 0.95, "precision": 0.93, "recall": 0.97},
  "duration_seconds": "45.2",
  "created_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:45Z"
}
```

---

## A/B Testing

### Create A/B Test
```http
POST /ab-tests
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Model Comparison",
  "model_a_id": "uuid-a",
  "model_b_id": "uuid-b",
  "traffic_split": 50
}
```

### List A/B Tests
```http
GET /ab-tests
Authorization: Bearer <token>
```

### Route Prediction
```http
POST /ab-tests/{id}/route
Authorization: Bearer <token>
Content-Type: application/json

{
  "data": {"feature1": 1.2, "feature2": 3.4}
}
```

---

## Monitoring

### System Statistics
```http
GET /monitoring/stats
Authorization: Bearer <token>
```

**Response:** `200 OK`
```json
{
  "total_models": 10,
  "total_datasets": 5,
  "total_experiments": 25,
  "total_predictions": 1000,
  "active_models": 3,
  "training_experiments": 2
}
```

### System Info
```http
GET /monitoring/system
Authorization: Bearer <token>
```

---

## Health Check

```http
GET /health
```

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "app": "ML Pipeline",
  "version": "1.0.0",
  "environment": "development",
  "checks": {
    "database": "ok",
    "redis": "ok"
  }
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized - Invalid or missing token |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |
