---
sidebar_position: 4
title: Deployment
---

# Deployment Guide

Deploy trained models to production.

## Deploy via API

```http
POST /api/v1/models/{model_id}/deploy
```

### Requirements

- Model must have status `trained`
- Model must have valid metrics

## Deploy via Python

```python
from app.ml.pipeline import MLPipeline

pipeline = MLPipeline()

# Save artifacts
paths = pipeline.save_artifacts("/path/to/deploy")

# Later, load and predict
pipeline.load_artifacts("/path/to/deploy")
result = pipeline.predict(data, feature_names)
```

## Deployment Architecture

```
Client → FastAPI → Model Registry → Prediction Service
                ↓
           PostgreSQL (metadata)
           Redis (cache)
           File System (models)
```

## Model States

| State | Description |
|-------|-------------|
| `training` | Currently being trained |
| `trained` | Ready for deployment |
| `deployed` | Serving predictions |
| `archived` | No longer active |
| `failed` | Training failed |

## Production Considerations

- Monitor prediction latency
- Set up alerts for accuracy drops
- Use A/B testing for model comparison
- Keep model versions for rollback
