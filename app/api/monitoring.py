from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.models.user import User
from app.models.model import MLModel, ModelStatus
from app.models.dataset import Dataset
from app.models.experiment import Experiment, ExperimentStatus
from app.models.prediction import Prediction

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    models_count = await db.execute(select(func.count(MLModel.id)))
    datasets_count = await db.execute(select(func.count(Dataset.id)))
    experiments_count = await db.execute(select(func.count(Experiment.id)))
    predictions_count = await db.execute(select(func.count(Prediction.id)))

    active_models = await db.execute(
        select(func.count(MLModel.id)).where(MLModel.status == ModelStatus.DEPLOYED)
    )

    training_experiments = await db.execute(
        select(func.count(Experiment.id)).where(Experiment.status == ExperimentStatus.RUNNING)
    )

    return {
        "total_models": models_count.scalar(),
        "total_datasets": datasets_count.scalar(),
        "total_experiments": experiments_count.scalar(),
        "total_predictions": predictions_count.scalar(),
        "active_models": active_models.scalar(),
        "training_experiments": training_experiments.scalar(),
    }


@router.get("/model/{model_id}/metrics")
async def get_model_metrics(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    predictions_count = await db.execute(
        select(func.count(Prediction.id)).where(Prediction.model_id == model_id)
    )

    avg_latency = await db.execute(
        select(func.avg(Prediction.latency_ms)).where(Prediction.model_id == model_id)
    )

    return {
        "model_id": str(model.id),
        "model_name": model.name,
        "version": model.version,
        "status": model.status.value,
        "metrics": model.metrics,
        "total_predictions": predictions_count.scalar(),
        "avg_latency_ms": float(avg_latency.scalar() or 0),
    }


@router.get("/system")
async def get_system_info(
    current_user: User = Depends(require_admin),
):
    import psutil
    import platform

    return {
        "cpu_percent": psutil.cpu_percent(),
        "memory": {
            "total": psutil.virtual_memory().total,
            "available": psutil.virtual_memory().available,
            "percent": psutil.virtual_memory().percent,
        },
        "disk": {
            "total": psutil.disk_usage('/').total,
            "used": psutil.disk_usage('/').used,
            "percent": psutil.disk_usage('/').percent,
        },
        "platform": platform.platform(),
        "python_version": platform.python_version(),
    }
