---
sidebar_position: 7
title: Monitoring
---

# Monitoring API

System and model performance metrics.

## Get Pipeline Stats

```http
GET /api/v1/monitoring/stats
```

### Response

```json
{
  "total_models": 5,
  "total_datasets": 3,
  "total_experiments": 12,
  "total_predictions": 1500,
  "active_models": 2,
  "training_experiments": 1
}
```

## Get System Info

```http
GET /api/v1/monitoring/system
```

### Response

```json
{
  "cpu_percent": 45.2,
  "memory": {
    "total": 8589934592,
    "available": 4294967296,
    "percent": 50.0
  },
  "disk": {
    "total": 536870912000,
    "used": 214748364800,
    "percent": 40.0
  },
  "platform": "linux",
  "python_version": "3.11.0"
}
```

## Get Model Metrics

```http
GET /api/v1/monitoring/model/{model_id}/metrics
```

Returns performance metrics for a specific model, including prediction latency and accuracy over time.

## System Requirements

Monitoring endpoints require **admin** or **data_scientist** role.

## Metrics Collection

- **System metrics**: Collected every 30 seconds
- **Model metrics**: Collected on each prediction
- **Pipeline stats**: Real-time from database
