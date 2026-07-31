---
sidebar_position: 1
title: Your First Model
description: Build your first ML model
---

# Your First Model

This guide walks you through building your first machine learning model with ML Pipeline.

## Overview

We'll build an Iris flower classifier using the classic Iris dataset.

### What You'll Learn

1. Upload a dataset
2. Create a model
3. Train the model
4. Make predictions

## Prerequisites

- ML Pipeline running (see [Quick Start](../getting-started/quickstart))
- A user account with `data_scientist` role

## Step 1: Upload Dataset

### Using Dashboard

1. Go to **Datasets** page
2. Click **Upload Dataset**
3. Fill in:
   - Name: `Iris Dataset`
   - File: Select `iris.csv`
   - Target Column: `species`
4. Click **Upload**

### Using API

```bash
# First, get your token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "datascientist@mlpipeline.com", "password": "ds123456"}' \
  | jq -r '.access_token')

# Upload dataset
curl -X POST http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@iris.csv" \
  -F "name=Iris Dataset" \
  -F "target_column=species"
```

## Step 2: Create Model

### Using Dashboard

1. Go to **Models** page
2. Click **Create Model**
3. Fill in:
   - Name: `Iris Classifier`
   - Algorithm: `random_forest`
   - Target Column: `species`
4. Click **Create**

### Using API

```bash
curl -X POST http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Iris Classifier",
    "algorithm": "random_forest",
    "target_column": "species"
  }'
```

## Step 3: Train Model

### Using Dashboard

1. Go to **Models** page
2. Find your model
3. Select `Iris Dataset` from dropdown
4. Click **Train**

### Using API

```bash
# Get model ID
MODEL_ID=$(curl -s http://localhost:8000/api/v1/models \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.items[0].id')

# Get dataset ID
DATASET_ID=$(curl -s http://localhost:8000/api/v1/datasets \
  -H "Authorization: Bearer $TOKEN" \
  | jq -r '.[0].id')

# Train model
curl -X POST "http://localhost:8000/api/v1/models/$MODEL_ID/train" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\": \"$DATASET_ID\", \"algorithm\": \"random_forest\"}"
```

## Step 4: Make Predictions

### Using Dashboard

1. Go to **Predictions** page
2. Select `Iris Classifier`
3. Enter input data:

```json
{
  "sepal length (cm)": 5.1,
  "sepal width (cm)": 3.5,
  "petal length (cm)": 1.4,
  "petal width (cm)": 0.2
}
```

4. Click **Predict**

### Using API

```bash
curl -X POST "http://localhost:8000/api/v1/models/$MODEL_ID/predict" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [{
      "sepal length (cm)": 5.1,
      "sepal width (cm)": 3.5,
      "petal length (cm)": 1.4,
      "petal width (cm)": 0.2
    }]
  }'
```

**Response:**

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
      }
    }
  ],
  "latency_ms": 15
}
```

## Step 5: Deploy Model (Optional)

Make your model available for production use:

### Using Dashboard

1. Go to **Models** page
2. Click **Deploy** on your model

### Using API

```bash
curl -X POST "http://localhost:8000/api/v1/models/$MODEL_ID/deploy" \
  -H "Authorization: Bearer $TOKEN"
```

## Complete Example

Here's a complete Python script:

```python
import requests

BASE_URL = "http://localhost:8000"

# Login
login_response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
    "email": "datascientist@mlpipeline.com",
    "password": "ds123456"
})
token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Upload dataset
with open("iris.csv", "rb") as f:
    upload_response = requests.post(
        f"{BASE_URL}/api/v1/datasets",
        headers=headers,
        files={"file": f},
        data={"name": "Iris Dataset", "target_column": "species"}
    )
dataset_id = upload_response.json()["id"]

# Create model
model_response = requests.post(
    f"{BASE_URL}/api/v1/models",
    headers=headers,
    json={
        "name": "Iris Classifier",
        "algorithm": "random_forest",
        "target_column": "species"
    }
)
model_id = model_response.json()["id"]

# Train model
train_response = requests.post(
    f"{BASE_URL}/api/v1/models/{model_id}/train",
    headers=headers,
    json={"dataset_id": dataset_id, "algorithm": "random_forest"}
)
print(f"Training status: {train_response.json()['status']}")

# Make prediction
predict_response = requests.post(
    f"{BASE_URL}/api/v1/models/{model_id}/predict",
    headers=headers,
    json={
        "data": [{
            "sepal length (cm)": 5.1,
            "sepal width (cm)": 3.5,
            "petal length (cm)": 1.4,
            "petal width (cm)": 0.2
        }]
    }
)
print(f"Prediction: {predict_response.json()['predictions'][0]['prediction']}")
```

## Next Steps

- [Data Preprocessing](./data-preprocessing) - Learn about data preprocessing
- [Model Training](./model-training) - Advanced training techniques
- [Deployment](./deployment) - Deploy to production
