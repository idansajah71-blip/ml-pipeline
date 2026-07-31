---
sidebar_position: 6
title: A/B Testing
---

# A/B Testing API

Compare model performance with A/B testing.

## Create A/B Test

```http
POST /api/v1/ab-tests
```

### Request Body

```json
{
  "name": "Model Comparison Test",
  "model_a_id": "uuid-model-a",
  "model_b_id": "uuid-model-b",
  "traffic_split": 50
}
```

### Response

```json
{
  "id": "uuid",
  "name": "Model Comparison Test",
  "status": "draft",
  "traffic_split": 50,
  "model_a_id": "uuid-model-a",
  "model_b_id": "uuid-model-b",
  "model_a_requests": 0,
  "model_b_requests": 0,
  "model_a_accuracy": 0,
  "model_b_accuracy": 0
}
```

## List A/B Tests

```http
GET /api/v1/ab-tests
```

## Update A/B Test Status

```http
PUT /api/v1/ab-tests/{id}
```

```json
{
  "status": "active"
}
```

## Route Prediction

```http
POST /api/v1/ab-tests/{id}/route
```

Routes a prediction request to either Model A or Model B based on the traffic split.

### Response

```json
{
  "model_id": "uuid-model-a",
  "model_version": "a",
  "prediction": {"prediction": "class_a", "probability": 0.92}
}
```

## A/B Test Statuses

| Status | Description |
|--------|-------------|
| `draft` | Created but not started |
| `active` | Currently routing traffic |
| `paused` | Temporarily paused |
| `completed` | Test finished |

## Traffic Split

The `traffic_split` parameter (0-100) determines the percentage of traffic routed to Model B. For example:
- `traffic_split: 50` - 50% to Model A, 50% to Model B
- `traffic_split: 80` - 20% to Model A, 80% to Model B
