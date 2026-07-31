---
sidebar_position: 2
title: Kubernetes
---

# Kubernetes Deployment

Deploy ML Pipeline to Kubernetes using Helm charts.

## Prerequisites

- Kubernetes cluster (1.24+)
- Helm 3.x
- kubectl configured

## Quick Deploy

```bash
./k8s/deploy.sh production
```

## Helm Chart

The Helm chart is located at `k8s/helm/ml-pipeline/`.

### Install

```bash
helm install ml-pipeline ./k8s/helm/ml-pipeline \
  --namespace ml-pipeline \
  --create-namespace \
  --values ./k8s/helm/ml-pipeline/values.yaml
```

### Upgrade

```bash
helm upgrade ml-pipeline ./k8s/helm/ml-pipeline \
  --namespace ml-pipeline \
  --values ./k8s/helm/ml-pipeline/values.yaml
```

### Uninstall

```bash
helm uninstall ml-pipeline --namespace ml-pipeline
```

## Configuration

### Environment Values

```yaml
# values.yaml
env:
  JWT_SECRET_KEY: "your-secret-key"
  POSTGRES_PASSWORD: "your-db-password"
  CORS_ORIGINS: "https://yourdomain.com"

replicaCount:
  app: 2
  worker: 1

resources:
  app:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"
```

### Ingress

```yaml
ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: api.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: ml-pipeline-tls
      hosts:
        - api.yourdomain.com
```

## Components

| Component | Replicas | Description |
|-----------|----------|-------------|
| app | 2 | FastAPI backend |
| worker | 1 | Background task processor |
| postgres | 1 | PostgreSQL database |
| redis | 1 | Cache and session store |

## Monitoring

Prometheus and Grafana are included in the Helm chart:

```bash
# Access Grafana
kubectl port-forward svc/grafana 3001:80 -n ml-pipeline

# Access Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n ml-pipeline
```
