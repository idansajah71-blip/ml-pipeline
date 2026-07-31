---
sidebar_position: 5
title: Experiments
---

# Experiments API

View and manage model training experiments.

## List Experiments

```http
GET /api/v1/experiments
```

### Response

```json
{
  "total": 10,
  "items": [
    {
      "id": "uuid",
      "name": "Experiment #1",
      "description": "Random Forest on Iris dataset",
      "status": "completed",
      "parameters": {"n_estimators": 100, "random_state": 42},
      "results": {"accuracy": 0.96, "f1_macro": 0.95},
      "duration_seconds": "12.5",
      "dataset_id": "uuid",
      "model_id": "uuid",
      "owner_id": "uuid",
      "created_at": "2024-01-15T10:30:00Z",
      "completed_at": "2024-01-15T10:30:12Z"
    }
  ]
}
```

## Get Experiment Details

```http
GET /api/v1/experiments/{id}
```

### Response

Returns the full experiment object with parameters, results, and logs.

## Experiment Statuses

| Status | Description |
|--------|-------------|
| `pending` | Queued for execution |
| `running` | Currently training |
| `completed` | Training finished successfully |
| `failed` | Training failed with error |

## Experiment Results Structure

```json
{
  "accuracy": 0.96,
  "precision_macro": 0.95,
  "recall_macro": 0.94,
  "f1_macro": 0.95,
  "confusion_matrix": [[14, 1], [0, 15]],
  "cross_validation": {
    "accuracy": {"mean": 0.953, "std": 0.02}
  }
}
```
