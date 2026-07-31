---
sidebar_position: 3
title: Model Training
---

# Model Training Guide

Learn how to train ML models using the pipeline.

## Available Algorithms

| Algorithm | Key Parameters | Best For |
|-----------|---------------|----------|
| `random_forest` | n_estimators, max_depth | General purpose, robust |
| `gradient_boosting` | n_estimators, learning_rate | High accuracy needs |
| `logistic_regression` | max_iter, C | Linear boundaries |
| `svm` | kernel, C | Small-medium datasets |
| `knn` | n_neighbors | Simple classification |
| `decision_tree` | max_depth | Interpretable models |
| `adaboost` | n_estimators | Boosting weak learners |
| `bagging` | n_estimators | Reduce variance |
| `mlp` | hidden_layer_sizes | Complex patterns |

## Training via API

```http
POST /api/v1/models/{model_id}/train
```

```json
{
  "dataset_id": "uuid",
  "algorithm": "random_forest",
  "parameters": {
    "n_estimators": 200,
    "max_depth": 10
  }
}
```

## Training via Python

```python
from app.ml.pipeline import MLPipeline

pipeline = MLPipeline()

result = pipeline.run_training(
    file_content=csv_bytes,
    filename="data.csv",
    target_column="target",
    algorithm="random_forest",
    parameters={"n_estimators": 200}
)

print(result["metrics"]["accuracy"])
```

## Training Output

```json
{
  "experiment_id": "uuid",
  "algorithm": "random_forest",
  "status": "completed",
  "metrics": {
    "accuracy": 0.96,
    "precision_macro": 0.95,
    "recall_macro": 0.94,
    "f1_macro": 0.95,
    "cross_validation": {
      "accuracy": {"mean": 0.953, "std": 0.02}
    }
  },
  "feature_importance": {
    "feature1": 0.45,
    "feature2": 0.35,
    "feature3": 0.20
  },
  "duration_seconds": 2.34
}
```

## Tips

- Start with `random_forest` for baseline
- Use cross-validation for reliable estimates
- Check feature importance for insights
- Try multiple algorithms and compare
