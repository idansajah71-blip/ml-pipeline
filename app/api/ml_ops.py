from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime
import pandas as pd
import numpy as np
import io
import os
import tempfile

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.model import MLModel
from app.models.dataset import Dataset
from app.models.data_quality import DataQualityReport
from app.models.batch_job import BatchJob, BatchJobStatus
from app.models.audit_log import AuditLog
from app.ml.data_quality import DataQualityChecker
from app.ml.data_utils import load_dataframe_from_path
from app.services.audit_service import AuditService
from app.schemas.ml_ops import (
    DataQualityConfig, DataQualityReportResponse,
    BatchJobCreate, BatchJobResponse, BatchJobListResponse,
    AuditLogResponse, AuditLogListResponse,
)

router = APIRouter(prefix="/ml-ops", tags=["MLOps"])


@router.post("/datasets/{dataset_id}/validate", response_model=DataQualityReportResponse)
async def validate_dataset(
    dataset_id: UUID,
    config: Optional[DataQualityConfig] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if not dataset.file_path or not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=400, detail="Dataset file not found on disk")

    df = load_dataframe_from_path(dataset.file_path)
    checker = DataQualityChecker(df)
    check_result = checker.run_all(config.model_dump() if config else None)

    report = DataQualityReport(
        dataset_id=dataset_id,
        status=check_result["status"],
        total_rows=len(df),
        total_checks=check_result["total_checks"],
        passed_checks=check_result["passed_checks"],
        failed_checks=check_result["failed_checks"],
        score=check_result["score"],
        checks=check_result["checks"],
        summary={
            "rows": len(df),
            "columns": len(df.columns),
            "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        },
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    audit = AuditService(db)
    await audit.log(
        action="validate_dataset",
        resource_type="dataset",
        resource_id=dataset_id,
        details={"score": check_result["score"], "failed_checks": check_result["failed_checks"]},
        user_id=current_user.id,
    )

    return DataQualityReportResponse.model_validate(report)


@router.get("/datasets/{dataset_id}/quality", response_model=DataQualityReportResponse)
async def get_latest_quality_report(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DataQualityReport)
        .where(DataQualityReport.dataset_id == dataset_id)
        .order_by(DataQualityReport.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="No quality reports found")
    return DataQualityReportResponse.model_validate(report)


@router.post("/batch-jobs", response_model=BatchJobResponse, status_code=201)
async def create_batch_job(
    job_data: BatchJobCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    model_result = await db.execute(select(MLModel).where(MLModel.id == job_data.model_id))
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    job = BatchJob(
        name=job_data.name,
        model_id=job_data.model_id,
        input_file_path=job_data.input_file_path,
        owner_id=current_user.id,
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    from app.ml.batch_tasks import batch_predict_task
    task = batch_predict_task.delay(
        job_id=str(job.id),
        model_id=str(model.id),
        input_file_path=job_data.input_file_path,
        output_dir=os.path.join(settings.ML_ARTIFACTS_DIR, "batch_outputs"),
        owner_id=str(current_user.id),
    )
    job.task_id = task.id
    await db.flush()

    audit = AuditService(db)
    await audit.log(
        action="create_batch_job",
        resource_type="batch_job",
        resource_id=job.id,
        details={"model_id": str(model.id), "name": job.name},
        user_id=current_user.id,
        request=request,
    )

    return BatchJobResponse.model_validate(job)


@router.get("/batch-jobs", response_model=BatchJobListResponse)
async def list_batch_jobs(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BatchJob).order_by(BatchJob.created_at.desc()).offset(skip).limit(limit)
    )
    jobs = list(result.scalars().all())
    return BatchJobListResponse(
        total=len(jobs),
        items=[BatchJobResponse.model_validate(j) for j in jobs],
    )


@router.get("/batch-jobs/{job_id}", response_model=BatchJobResponse)
async def get_batch_job(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BatchJob).where(BatchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    return BatchJobResponse.model_validate(job)


@router.get("/batch-jobs/{job_id}/download")
async def download_batch_results(
    job_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BatchJob).where(BatchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Batch job not found")
    if not job.output_file_path or not os.path.exists(job.output_file_path):
        raise HTTPException(status_code=404, detail="Output file not found")

    from fastapi.responses import FileResponse
    return FileResponse(
        job.output_file_path,
        media_type="text/csv",
        filename=f"predictions_{job.name}.csv",
    )


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = list(result.scalars().all())
    return AuditLogListResponse(
        total=len(logs),
        items=[AuditLogResponse.model_validate(l) for l in logs],
    )
