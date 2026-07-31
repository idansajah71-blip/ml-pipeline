# Kubernetes Deployment

This directory contains Kubernetes manifests and Helm charts for deploying ML Pipeline.

## Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or minikube)
- kubectl configured
- Helm 3.x installed

## Quick Start

```bash
# Deploy to staging
./k8s/deploy.sh staging

# Deploy to production
./k8s/deploy.sh production
```

## Helm Chart

The Helm chart is located at `k8s/helm/ml-pipeline/`.

### Install

```bash
cd k8s/helm/ml-pipeline

# Staging
helm install ml-pipeline-staging . \
    --namespace ml-pipeline-staging \
    --create-namespace \
    --values values.yaml \
    --values values-staging.yaml

# Production
helm install ml-pipeline-production . \
    --namespace ml-pipeline-production \
    --create-namespace \
    --values values.yaml \
    --values values-production.yaml \
    --set app.secrets.JWT_SECRET_KEY=$(openssl rand -hex 32) \
    --set postgresql.auth.password=$(openssl rand -base64 32)
```

### Upgrade

```bash
helm upgrade ml-pipeline-staging . \
    --namespace ml-pipeline-staging \
    --values values.yaml \
    --values values-staging.yaml
```

### Uninstall

```bash
helm uninstall ml-pipeline-staging -n ml-pipeline-staging
kubectl delete namespace ml-pipeline-staging
```

## Environments

| Environment | Replicas | Resources | Autoscaling |
|-------------|----------|-----------|-------------|
| Development | 1 | Minimal | Disabled |
| Staging | 1 | Moderate | Disabled |
| Production | 3+ | Large | Enabled |

## Components

- **Backend**: FastAPI application
- **Frontend**: Next.js dashboard
- **PostgreSQL**: Database
- **Redis**: Cache
- **Ingress**: Nginx ingress controller

## Scaling

```bash
# Manual scaling
kubectl scale deployment/ml-pipeline-backend --replicas=5 -n ml-pipeline-production

# Check HPA
kubectl get hpa -n ml-pipeline-production
```

## Monitoring

```bash
# View pods
kubectl get pods -n ml-pipeline-production

# View logs
kubectl logs -f deployment/ml-pipeline-backend -n ml-pipeline-production

# Port forward to local
kubectl port-forward svc/ml-pipeline-backend 8000:8000 -n ml-pipeline-production
```

## Troubleshooting

```bash
# Check events
kubectl get events -n ml-pipeline-production --sort-by='.lastTimestamp'

# Describe pod
kubectl describe pod <pod-name> -n ml-pipeline-production

# Exec into pod
kubectl exec -it <pod-name> -n ml-pipeline-production -- /bin/bash
```
