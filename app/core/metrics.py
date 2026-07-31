from prometheus_client import Counter, Histogram, Gauge, Summary
from typing import Optional

# Request metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ML metrics
PREDICTION_COUNT = Counter(
    "ml_predictions_total",
    "Total ML predictions",
    ["model_id", "success"],
)

PREDICTION_LATENCY = Histogram(
    "ml_prediction_duration_seconds",
    "ML prediction latency in seconds",
    ["model_id"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

TRAINING_COUNT = Counter(
    "ml_trainings_total",
    "Total ML trainings",
    ["algorithm", "status"],
)

TRAINING_LATENCY = Histogram(
    "ml_training_duration_seconds",
    "ML training duration in seconds",
    ["algorithm"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

# Database metrics
DB_POOL_SIZE = Gauge(
    "db_pool_connections",
    "Database connection pool size",
    ["state"],
)

# Model metrics
MODEL_VERSION = Gauge(
    "ml_model_version",
    "Current model version",
    ["model_id", "model_name"],
)

MODEL_STATUS = Gauge(
    "ml_model_status",
    "Model status (1=active, 0=inactive)",
    ["model_id", "status"],
)

# System metrics
ACTIVE_REQUESTS = Gauge(
    "active_requests",
    "Number of active requests",
)

QUEUE_SIZE = Gauge(
    "queue_size",
    "Size of processing queue",
)


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        method = scope["method"]
        path = scope["path"]

        ACTIVE_REQUESTS.inc()

        import time
        start_time = time.time()

        try:
            response = await self.app(scope, receive, send)
            return response
        finally:
            ACTIVE_REQUESTS.dec()
            duration = time.time() - start_time
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)


def record_prediction(model_id: str, success: bool, latency: float):
    PREDICTION_COUNT.labels(model_id=str(model_id), success=str(success)).inc()
    PREDICTION_LATENCY.labels(model_id=str(model_id)).observe(latency)


def record_training(algorithm: str, success: bool, duration: float):
    status = "success" if success else "failed"
    TRAINING_COUNT.labels(algorithm=algorithm, status=status).inc()
    TRAINING_LATENCY.labels(algorithm=algorithm).observe(duration)


def record_request(method: str, endpoint: str, status_code: int, duration: float):
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)


def update_model_status(model_id: str, model_name: str, version: int, status: str):
    MODEL_VERSION.labels(model_id=str(model_id), model_name=model_name).set(version)
    for s in ["training", "trained", "deployed", "archived", "failed"]:
        MODEL_STATUS.labels(model_id=str(model_id), status=s).set(1 if s == status else 0)
