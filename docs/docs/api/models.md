---
sidebar_position: 3
title: Models
description: Model management API
---

# Models API

Create, train, and manage ML models.

## Create Model

```bash
POST /api/v1/models
```

**Request Body:**

```json
{
  "name": "My Classifier",
  "algorithm": "random_forest",
  "target_column": "species",
  "description": "Random Forest classifier",
  "tags": ["classification", "iris"]
}
```

**Algorithms:**

| Algorithm | Key |
|-----------|-----|
| Random Forest | `random_forest` |
| Gradient Boosting | `gradient_boosting` |
| Logistic Regression | `logistic_regression` |
| SVM | `svm` |
| KNN | `knn` |
| Decision Tree | `decision_tree` |
| AdaBoost | `adaboost` |
| Bagging | `bagging` |
| MLP Neural Network | `mlp` |

**Response (201):**

```json
{
  "id": "uuid",
  "name": "My Classifier",
  "algorithm": "random_forest",
  "version": 1,
  "status": "trained",
  "target_column": "species",
  "parameters": {},
  "metrics": {},
  "feature_names": [],
  "tags": ["classification", "iris"],
  "is_default": 0,
  "owner_id": "uuid",
  "created_at": "2024-01-01T00:00:00"
}
```

## List Models

```bash
GET /api/v1/models
```

**Response (200):**

```json
{
  "total": 5,
  "items": [
    {
      "id": "uuid",
      "name": "Model 1",
      "algorithm": "random_forest",
      "status": "deployed"
    }
  ]
}
```

## Get Model

```bash
GET /api/v1/models/{model_id}
```

## Train Model

```bash
POST /api/v1/models/{model_id}/train
```

**Request Body:**

```json
{
  "dataset_id": "uuid",
  "algorithm": "random_forest",
  "parameters": {
    "n_estimators": 100,
    "random_state": 42
  }
}
```

**Response (200):**

```json
{
  "experiment_id": "uuid",
  "message": "Training completed successfully",
  "status": "completed"
}
```

### Training Response Fields

| Field | Type | Description |
|-------|------|-------------|
| experiment_id | string | Experiment ID |
| message | string | Status message |
| status | string | Training status |

### Training Status

| Status | Description |
|--------|-------------|
| completed | Training finished successfully |
| failed | Training failed |
| running | Training in progress |

## Make Prediction

```bash
POST /api/v1/models/{model_id}/predict
```

**Request Body:**

```json
{
  "data": [
    {
      "sepal length (cm)": 5.1,
      "sepal width (cm)": 3.5,
      "petal length (cm)": 1.4,
      "petal width (cm)": 0.2
    }
  ]
}
```

**Response (200):**

```json
{
  "predictions": [
    {
      "prediction": "setosa",
      "probability": 0.98,
      "probabilities": {
        "setosa": 0.98,
        "versicolor": 0.01,
        "virginica": 0.01
      },
      "index": 0
    }
  ],
  "latency_ms": 15
}
```

## Deploy Model

```bash
POST /api/v1/models/{model_id}/deploy
```

**Response (200):**

```json
{
  "message": "Model My Classifier v1 deployed successfully"
}
```

## Delete Model

```bash
DELETE /api/v1/models/{model_id}
```

## Model Status

| Status | Description |
|--------|-------------|
| `training` | Model is being trained |
| `trained` | Model is trained and ready |
| `deployed` | Model is deployed and serving predictions |
| `archived` | Model is archived |
| `failed` | Training failed |

## Model Metrics

After training, metrics are stored in `model.metrics`:

```json
{
  "accuracy": 0.95,
  "precision_macro": 0.94,
  "recall_macro": 0.93,
  "f1_macro": 0.93,
  "confusion_matrix": [[14, 0, 0], [0, 13, 1], [0, 0, 15]]
}
```

## Next Steps

- [Predictions API](./predictions)
- [Experiments API](./experiments)
- [Model Training Guide](../guides/model-training)
