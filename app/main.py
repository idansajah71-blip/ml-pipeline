from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db
from app.api import auth, datasets, models, experiments, monitoring, ab_testing, notifications
from app.api import ml_ops, ab_testing_enhanced, model_optimization
from app.api import feature_store, serving, organizations, quota
from app.api import model_versions, experiment_compare, feature_monitoring, webhooks, lineage_metrics
from app.api import explainability_dashboard, ensemble, data_versioning, marketplace, cost_tracking
from app.core.security_middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestLoggingMiddleware,
    InputSanitizationMiddleware,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.ENVIRONMENT == "development":
        await init_db()
    from app.core.websocket import manager
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
app.add_middleware(InputSanitizationMiddleware)
app.add_middleware(RateLimitMiddleware, default_limit=100, default_window=60)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    detail = str(exc) if settings.DEBUG else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
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


@app.get("/health")
async def health_check():
    checks = {}

    try:
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:100]}"

    try:
        from app.core.redis import get_redis
        client = await get_redis()
        if client:
            await client.ping()
            checks["redis"] = "ok"
        else:
            checks["redis"] = "unavailable"
    except Exception as e:
        checks["redis"] = f"error: {str(e)[:100]}"

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
    return {
        "algorithms": list(ModelTrainer.ALGORITHMS.keys()),
        "default_params": ModelTrainer.DEFAULT_PARAMS,
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
