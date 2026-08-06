from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import get_settings
from app.core.error_utils import sanitize_error_message, log_error
from app.core.safe_joblib import safe_load
from app.models.user import User
from app.models.model import MLModel
from app.models.dataset import Dataset
from app.ml.mlflow_tracker import get_mlflow_tracker

settings = get_settings()
router = APIRouter(prefix="/mlflow", tags=["MLflow Experiment Tracking"])
logger = logging.getLogger(__name__)


class MLflowConfigRequest(BaseModel):
    tracking_uri: Optional[str] = None
    experiment_name: str = "ml-pipeline"


class MLflowRunLogRequest(BaseModel):
    model_id: UUID
    parameters: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}
    tags: Dict[str, str] = {}


@router.get("/status")
async def mlflow_status(current_user: User = Depends(get_current_active_user)):
    tracker = get_mlflow_tracker(
        tracking_uri=settings.MLFLOW_TRACKING_URI if hasattr(settings, 'MLFLOW_TRACKING_URI') else None,
    )
    return {
        "available": tracker.is_available,
        "tracking_uri": tracker.tracking_uri or "default",
        "experiment_name": tracker.experiment_name,
    }


@router.get("/runs")
async def list_runs(
    max_results: int = 10,
    current_user: User = Depends(get_current_active_user),
):
    tracker = get_mlflow_tracker(
        tracking_uri=settings.MLFLOW_TRACKING_URI if hasattr(settings, 'MLFLOW_TRACKING_URI') else None,
    )
    runs = tracker.get_experiment_runs(max_results=max_results)
    return {"runs": runs, "total": len(runs)}


@router.post("/log")
async def log_training_run(
    data: MLflowRunLogRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    tracker = get_mlflow_tracker(
        tracking_uri=settings.MLFLOW_TRACKING_URI if hasattr(settings, 'MLFLOW_TRACKING_URI') else None,
    )

    if not tracker.is_available:
        raise HTTPException(
            status_code=503,
            detail="MLflow is not installed. Install with: pip install mlflow",
        )

    run_id = tracker.track_training(
        algorithm=model.algorithm,
        parameters={**model.parameters, **data.parameters},
        metrics=data.metrics or model.metrics,
        run_name=f"{model.algorithm}_v{model.version}",
        tags={**data.tags, "model_id": str(model.id), "owner_id": str(current_user.id)},
    )

    return {
        "run_id": run_id,
        "experiment_name": tracker.experiment_name,
        "status": "logged" if run_id else "failed",
    }
