from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentResponse, ExperimentListResponse

router = APIRouter(prefix="/experiments", tags=["Experiments"])


class ExperimentCompareRequest(BaseModel):
    experiment_ids: List[UUID]


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    skip: int = 0,
    limit: int = 100,
    algorithm: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Experiment).where(Experiment.owner_id == current_user.id)

    if status:
        query = query.where(Experiment.status == status)

    if algorithm:
        query = query.where(Experiment.parameters["algorithm"].as_string() == algorithm)

    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        query.order_by(Experiment.created_at.desc()).offset(skip).limit(limit)
    )
    experiments = list(result.scalars().all())
    return ExperimentListResponse(
        total=total,
        items=[ExperimentResponse.model_validate(e) for e in experiments],
    )


@router.get("/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(
    experiment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experiment).where(
            Experiment.id == experiment_id,
            Experiment.owner_id == current_user.id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse.model_validate(experiment)


@router.get("/{experiment_id}/metrics")
async def get_experiment_metrics(
    experiment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experiment).where(
            Experiment.id == experiment_id,
            Experiment.owner_id == current_user.id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    results = experiment.results or {}
    return {
        "experiment_id": str(experiment.id),
        "status": experiment.status.value,
        "metrics": results.get("metrics", {}),
        "parameters": experiment.parameters,
        "duration_seconds": experiment.duration_seconds,
        "feature_importance": results.get("feature_importance", {}),
    }


@router.post("/compare")
async def compare_experiments(
    compare_request: ExperimentCompareRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if len(compare_request.experiment_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 experiments required")

    result = await db.execute(
        select(Experiment).where(
            Experiment.id.in_(compare_request.experiment_ids),
            Experiment.owner_id == current_user.id,
        )
    )
    experiments = list(result.scalars().all())

    found_ids = {str(exp.id) for exp in experiments}
    missing = [str(eid) for eid in compare_request.experiment_ids if str(eid) not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail=f"Experiments not found: {', '.join(missing)}")

    comparison = []
    for exp in experiments:
        results = exp.results or {}
        comparison.append({
            "experiment_id": str(exp.id),
            "name": exp.name,
            "status": exp.status.value,
            "algorithm": exp.parameters.get("algorithm", "unknown"),
            "metrics": results.get("metrics", {}),
            "parameters": exp.parameters,
            "duration_seconds": exp.duration_seconds,
            "created_at": exp.created_at.isoformat(),
        })

    best_f1 = max(
        comparison,
        key=lambda x: x.get("metrics", {}).get("f1_macro", 0),
        default=None,
    )

    return {
        "experiments": comparison,
        "best_experiment": best_f1["experiment_id"] if best_f1 else None,
        "summary": {
            "total_experiments": len(comparison),
            "algorithms_used": list(set(c["algorithm"] for c in comparison)),
            "best_f1_score": best_f1.get("metrics", {}).get("f1_macro", 0) if best_f1 else 0,
        },
    }


@router.get("/{experiment_id}/logs")
async def get_experiment_logs(
    experiment_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experiment).where(
            Experiment.id == experiment_id,
            Experiment.owner_id == current_user.id,
        )
    )
    experiment = result.scalar_one_or_none()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    results = experiment.results or {}
    return {
        "experiment_id": str(experiment.id),
        "logs": experiment.logs or "",
        "error": results.get("error"),
        "status": experiment.status.value,
        "duration_seconds": experiment.duration_seconds,
    }
