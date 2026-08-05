from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import os
import joblib

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import get_settings
from app.models.user import User
from app.models.model import MLModel
from app.services.audit_service import AuditService
from app.schemas.ml_ops import BenchmarkResult, PruneResult, ExportResult

settings = get_settings()
router = APIRouter(prefix="/models", tags=["Model Optimization"])


@router.post("/{model_id}/benchmark", response_model=BenchmarkResult)
async def benchmark_model(
    model_id: UUID,
    n_samples: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="Model file not found on disk")

    model_data = joblib.load(model.file_path)
    if isinstance(model_data, dict):
        ml_model = model_data.get("model", model_data)
        scaler = model_data.get("scaler")
        feature_names = model_data.get("feature_names", [])
    else:
        ml_model = model_data
        scaler = None
        feature_names = []

    import numpy as np
    X_test = np.random.randn(n_samples, len(feature_names) or 10).astype(float)

    from app.ml.optimizer import ModelOptimizer
    optimizer = ModelOptimizer(ml_model, scaler, feature_names)
    metrics = optimizer.benchmark(X_test, n_samples=min(n_samples, 100))

    audit = AuditService(db)
    await audit.log(
        action="benchmark_model",
        resource_type="model",
        resource_id=model_id,
        details={"n_samples": n_samples, "avg_latency_ms": metrics["avg_latency_ms"]},
        user_id=current_user.id,
    )

    return BenchmarkResult(**metrics)


@router.post("/{model_id}/prune", response_model=PruneResult)
async def prune_model_features(
    model_id: UUID,
    importance_threshold: float = 0.01,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="Model file not found on disk")

    model_data = joblib.load(model.file_path)
    if isinstance(model_data, dict):
        ml_model = model_data.get("model", model_data)
        feature_names = model_data.get("feature_names", [])
    else:
        ml_model = model_data
        feature_names = []

    from app.ml.optimizer import ModelOptimizer
    optimizer = ModelOptimizer(ml_model, feature_names=feature_names)
    result = optimizer.prune_features(importance_threshold)

    audit = AuditService(db)
    await audit.log(
        action="prune_model",
        resource_type="model",
        resource_id=model_id,
        details={"threshold": importance_threshold, "kept": result.get("kept_features", 0)},
        user_id=current_user.id,
    )

    return PruneResult(**result)


@router.post("/{model_id}/export", response_model=ExportResult)
async def export_model(
    model_id: UUID,
    format: str = "joblib",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if not model.file_path or not os.path.exists(model.file_path):
        raise HTTPException(status_code=400, detail="Model file not found on disk")

    model_data = joblib.load(model.file_path)
    if isinstance(model_data, dict):
        ml_model = model_data.get("model", model_data)
        scaler = model_data.get("scaler")
        feature_names = model_data.get("feature_names", [])
    else:
        ml_model = model_data
        scaler = None
        feature_names = []

    export_dir = os.path.join(settings.ML_ARTIFACTS_DIR, "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, f"model_{model_id}")

    from app.ml.optimizer import ModelOptimizer
    optimizer = ModelOptimizer(ml_model, scaler, feature_names)
    export_result = optimizer.export_model(export_path, format)

    if export_result["status"] == "failed":
        raise HTTPException(status_code=500, detail=export_result["error"])

    audit = AuditService(db)
    await audit.log(
        action="export_model",
        resource_type="model",
        resource_id=model_id,
        details={"format": format, "path": export_result["path"]},
        user_id=current_user.id,
    )

    return ExportResult(**export_result)
