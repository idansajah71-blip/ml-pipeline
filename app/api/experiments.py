from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.experiment import Experiment
from app.schemas.experiment import ExperimentResponse, ExperimentListResponse

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.get("", response_model=ExperimentListResponse)
async def list_experiments(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Experiment)
        .where(Experiment.owner_id == current_user.id)
        .order_by(Experiment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    experiments = list(result.scalars().all())
    return ExperimentListResponse(
        total=len(experiments),
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
