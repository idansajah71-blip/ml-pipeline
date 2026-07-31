---
sidebar_position: 4
title: Predictions
---

# Predictions API

Make real-time predictions using your trained and deployed models.

## Make Prediction

```http
POST /api/v1/models/{model_id}/predict
```

### Request Body

```json
{
  "data": [
    {"feature1": 1.0, "feature2": 2.0, "feature3": 3.0}
  ]
}
```

### Response

```json
{
  "predictions": [
    {
      "prediction": "class_a",
      "probability": 0.95,
      "probabilities": {
        "class_a": 0.95,
        "class_b": 0.05
      },
      "index": 0
    }
  ],
  "latency_ms": 12
}
```

### Batch Predictions

Send multiple data points in a single request:

```json
{
  "data": [
    {"feature1": 1.0, "feature2": 2.0, "feature3": 3.0},
    {"feature1": 4.0, "feature2": 5.0, "feature3": 6.0}
  ]
}
```

## Error Responses

| Status | Description |
|--------|-------------|
| 400 | Invalid input data |
| 404 | Model not found or not deployed |
| 422 | Validation error |

## Example Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/models/{model_id}/predict",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "data": [
            {"sepal_length": 5.1, "sepal_width": 3.5, "petal_length": 1.4, "petal_width": 0.2}
        ]
    }
)

result = response.json()
print(result["predictions"][0]["prediction"])
```

## Rate Limits

Predictions are subject to rate limiting:
- **Standard users**: 60 requests/minute
- **Data scientists**: 120 requests/minute
- **Admins**: Unlimited
