from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
import logging
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db
from app.core.error_utils import sanitize_error_message, log_error
from app.api import auth, datasets, models, experiments, monitoring, ab_testing, notifications
from app.api import ml_ops, ab_testing_enhanced, model_optimization
from app.api import feature_store, serving, organizations, quota
from app.api import model_versions, experiment_compare, feature_monitoring, webhooks, lineage_metrics
from app.api import explainability_dashboard, ensemble, data_versioning, marketplace, cost_tracking
from app.api import mlflow_tracking, model_benchmark, data_validation_api, recommendations
from app.api import analytics, external_data, scraping, scraping_advanced, scraping_ultra
from app.api import system_health, in_app_notifications
from app.core.security_middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    InputSanitizationMiddleware,
    UploadSizeLimitMiddleware,
    TrainingQuotaMiddleware,
)

settings = get_settings()
logger = logging.getLogger(__name__)


def validate_production_config():
    """Validate critical configuration for production environment."""
    if settings.ENVIRONMENT == "production":
        if not settings.JWT_SECRET_KEY:
            raise ValueError(
                "FATAL: JWT_SECRET_KEY is not set. "
                "Application cannot start in production without a secure JWT secret. "
                "Set the JWT_SECRET_KEY environment variable."
            )
        if settings.JWT_SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError(
                "FATAL: JWT_SECRET_KEY is using the default dev value. "
                "Application cannot start in production with the default secret. "
                "Set a secure random string via the JWT_SECRET_KEY environment variable."
            )
        logger.info("Production configuration validated successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_config()

    if settings.ENVIRONMENT == "development":
        await init_db()

    from app.core.websocket import manager
    await manager.start_redis_listener()
    yield
    await manager.stop_redis_listener()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-ready ML Pipeline API with FastAPI, scikit-learn, and PostgreSQL",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

cors_origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, default_limit=100, default_window=60)
app.add_middleware(UploadSizeLimitMiddleware, default_max_mb=100)
app.add_middleware(TrainingQuotaMiddleware)
app.add_middleware(InputSanitizationMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join(str(x) for x in err.get("loc", []))
        errors.append(f"[{loc}] {err.get('msg', err)}")
    detail = "Validation failed: " + "; ".join(errors) if errors else "Validation failed"
    log_error(exc, context=f"Validation error on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={
            "detail": detail,
            "errors": [err.get("msg", str(err)) for err in exc.errors()],
            "locations": [list(err.get("loc", [])) for err in exc.errors()],
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from app.core.error_utils import humanize_http_detail

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": humanize_http_detail(exc.detail, exc.status_code)},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(exc, context=f"Unhandled exception on {request.method} {request.url.path}")

    if settings.DEBUG:
        detail = str(exc)
    else:
        detail = sanitize_error_message(exc)

    return JSONResponse(
        status_code=500,
        content={"detail": detail, "error_code": "INTERNAL_ERROR"},
    )


app.include_router(auth.router, prefix="/api/v1")
app.include_router(datasets.router, prefix="/api/v1")
app.include_router(models.router, prefix="/api/v1")
app.include_router(experiments.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1")
app.include_router(ab_testing.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(ml_ops.router, prefix="/api/v1")
app.include_router(ab_testing_enhanced.router, prefix="/api/v1")
app.include_router(model_optimization.router, prefix="/api/v1")
app.include_router(feature_store.router, prefix="/api/v1")
app.include_router(serving.router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(quota.router, prefix="/api/v1")
app.include_router(model_versions.router, prefix="/api/v1")
app.include_router(experiment_compare.router, prefix="/api/v1")
app.include_router(feature_monitoring.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(lineage_metrics.router, prefix="/api/v1")
app.include_router(explainability_dashboard.router, prefix="/api/v1")
app.include_router(ensemble.router, prefix="/api/v1")
app.include_router(data_versioning.router, prefix="/api/v1")
app.include_router(marketplace.router, prefix="/api/v1")
app.include_router(cost_tracking.router, prefix="/api/v1")
app.include_router(mlflow_tracking.router, prefix="/api/v1")
app.include_router(model_benchmark.router, prefix="/api/v1")
app.include_router(data_validation_api.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(external_data.router, prefix="/api/v1")
app.include_router(scraping.router, prefix="/api/v1")
app.include_router(scraping_advanced.router, prefix="/api/v1")
app.include_router(scraping_ultra.router, prefix="/api/v1")
app.include_router(system_health.router, prefix="/api/v1")
app.include_router(in_app_notifications.router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    checks = {}

    try:
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        log_error(e, context="Health check: database")
        checks["database"] = "error"

    try:
        from app.core.redis import get_redis
        client = await get_redis()
        if client:
            await client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as e:
        log_error(e, context="Health check: redis")
        checks["redis"] = "error"

    healthy = all(v == "ok" or v == "unavailable" for v in checks.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/api/v1/algorithms")
async def list_algorithms():
    from app.ml.trainer import ModelTrainer
    trainer = ModelTrainer()
    return {
        "classification": trainer.get_algorithms("classification"),
        "regression": trainer.get_algorithms("regression"),
        "available_count": {
            "classification": len(trainer.ALGORITHMS),
            "regression": len(trainer.REGRESSION_ALGORITHMS),
        },
    }


@app.websocket("/ws/training/{experiment_id}")
async def websocket_training(websocket: WebSocket, experiment_id: str):
    from app.core.websocket import manager

    channel = f"training:{experiment_id}"
    await manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
