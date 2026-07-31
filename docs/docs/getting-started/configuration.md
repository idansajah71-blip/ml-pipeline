---
sidebar_position: 4
title: Configuration
description: Configure ML Pipeline
---

# Configuration

ML Pipeline can be configured through environment variables.

## Environment Variables

### Application Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | ML Pipeline | Application name |
| `APP_VERSION` | 1.0.0 | Application version |
| `ENVIRONMENT` | development | Environment (development, staging, production) |
| `DEBUG` | true | Enable debug mode |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8000 | Server port |

### Database Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | localhost | PostgreSQL host |
| `POSTGRES_PORT` | 5432 | PostgreSQL port |
| `POSTGRES_DB` | ml_pipeline_db | Database name |
| `POSTGRES_USER` | ml_user | Database user |
| `POSTGRES_PASSWORD` | - | Database password |

### Redis Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | localhost | Redis host |
| `REDIS_PORT` | 6379 | Redis port |

### Authentication Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | - | JWT secret key (required) |
| `JWT_ALGORITHM` | HS256 | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 10080 | Token expiry (7 days) |

### ML Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ML_ARTIFACTS_DIR` | ./ml_artifacts | Model artifacts directory |
| `MAX_UPLOAD_SIZE_MB` | 100 | Maximum upload size |
| `TRAINING_TIMEOUT_SECONDS` | 300 | Training timeout |

### Monitoring Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_METRICS` | true | Enable Prometheus metrics |
| `LOG_LEVEL` | INFO | Log level |

## Configuration Files

### .env

The main configuration file.

```bash
# Copy example
cp .env.example .env

# Edit with your settings
nano .env
```

### docker-compose.yml

Docker Compose configuration.

```yaml
services:
  app:
    env_file:
      - .env
```

### k8s/helm/ml-pipeline/values.yaml

Kubernetes Helm values.

```yaml
app:
  env:
    ENVIRONMENT: production
    DEBUG: "false"
```

## Advanced Configuration

### Custom Algorithms

Add custom ML algorithms in `app/ml/trainer.py`:

```python
class ModelTrainer:
    ALGORITHMS = {
        'random_forest': RandomForestClassifier,
        'your_custom_algo': YourCustomClass,
    }
```

### Custom Validators

Add custom input validators in `app/core/security_scanner.py`:

```python
class SecurityScanner:
    CUSTOM_PATTERNS = [
        r'your_pattern_here',
    ]
```

### Custom Middleware

Add custom middleware in `app/main.py`:

```python
from app.core.custom_middleware import CustomMiddleware

app.add_middleware(CustomMiddleware)
```

## Environment-Specific Configurations

### Development

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### Staging

```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
```

### Production

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
```

## Security Best Practices

1. **Never commit .env files** - Add to .gitignore
2. **Use strong secrets** - Generate with `openssl rand -hex 32`
3. **Enable HTTPS** - Use SSL/TLS in production
4. **Restrict CORS** - Configure allowed origins
5. **Use environment variables** - Don't hardcode secrets

## Next Steps

- [Docker Deployment](../deployment/docker)
- [Kubernetes Deployment](../deployment/kubernetes)
- [Security Guide](../guides/deployment)
