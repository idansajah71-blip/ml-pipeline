from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import pandas as pd
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.error_utils import sanitize_error_message, log_error
from app.models.user import User
from app.models.dataset import Dataset

router = APIRouter(prefix="/data-validation", tags=["Data Validation"])
logger = logging.getLogger(__name__)


@router.post("/{dataset_id}/validate")
async def validate_dataset(
    dataset_id: UUID,
    target_column: str = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        from app.ml.data_validation import DataValidator

        df = pd.read_csv(dataset.file_path)

        validator = DataValidator()

        if target_column:
            validation_result = validator.validate_for_training(df, target_column)
        else:
            validation_result = validator.validate_dataset(df, dataset_name=dataset.name)

        return validation_result

    except Exception as e:
        log_error(e, context=f"Data validation failed for dataset {dataset_id}")
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.post("/drift-detect")
async def detect_drift(
    reference_dataset_id: UUID,
    current_dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    ref_result = await db.execute(select(Dataset).where(Dataset.id == reference_dataset_id))
    ref_dataset = ref_result.scalar_one_or_none()
    if not ref_dataset:
        raise HTTPException(status_code=404, detail="Reference dataset not found")

    cur_result = await db.execute(select(Dataset).where(Dataset.id == current_dataset_id))
    cur_dataset = cur_result.scalar_one_or_none()
    if not cur_dataset:
        raise HTTPException(status_code=404, detail="Current dataset not found")

    try:
        ref_df = pd.read_csv(ref_dataset.file_path)
        cur_df = pd.read_csv(cur_dataset.file_path)

        from app.ml.model_monitor import detect_drift
        drift_result = detect_drift(ref_df, cur_df)

        return drift_result

    except Exception as e:
        log_error(e, context="Drift detection failed")
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))


@router.post("/{dataset_id}/quality")
async def check_data_quality(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        df = pd.read_csv(dataset.file_path)

        from app.ml.model_monitor import check_quality
        quality_result = check_quality(df)

        return quality_result

    except Exception as e:
        log_error(e, context=f"Quality check failed for dataset {dataset_id}")
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))
