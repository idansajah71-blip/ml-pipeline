---
sidebar_position: 5
title: Monitoring
---

# Monitoring Guide

Monitor your ML pipeline and system health.

## Dashboard

The monitoring dashboard shows:

- **Pipeline Stats** - Total models, datasets, experiments, predictions
- **System Resources** - CPU, Memory, Disk usage
- **Model Performance** - Accuracy, latency, prediction counts

## System Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| CPU Usage | Processor utilization | > 80% |
| Memory Usage | RAM utilization | > 80% |
| Disk Usage | Storage utilization | > 80% |

## Model Metrics

Track per-model metrics:
- **Accuracy** - Prediction accuracy over time
- **Latency** - Response time per prediction
- **Request Count** - Total predictions served
- **Error Rate** - Failed predictions percentage

## Setting Up Monitoring

### Prometheus

```yaml
scrape_configs:
  - job_name: 'ml-pipeline'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
```

### Grafana Dashboard

Import the pre-built dashboard from `logging/grafana/dashboards/`.

### Alert Rules

Alert rules are configured in `logging/prometheus/alert_rules.yml`:
- High CPU usage
- High memory usage
- Low model accuracy
- High error rate

## Logs

Logs are structured JSON format. View with:

```bash
# Docker
docker compose logs -f app

# Kubernetes
kubectl logs -f deployment/ml-pipeline
```

## Health Check

```http
GET /health
```

Returns service health status.
