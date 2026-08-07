from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime
import random

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.model import MLModel
from app.models.ab_test import ABTest, ABTestStatus
from app.services.audit_service import AuditService
from app.schemas.ml_ops import StatisticalResult, ABTestMetricsResponse

router = APIRouter(prefix="/ab-tests", tags=["A/B Testing"])


@router.post("/{test_id}/metrics", response_model=ABTestMetricsResponse)
async def get_ab_test_metrics(
    test_id: UUID,
    confidence_level: float = 0.95,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    stat_test = None
    if test.model_a_requests > 0 and test.model_b_requests > 0:
        a_acc = test.model_a_accuracy / test.model_a_requests if test.model_a_requests > 0 else 0
        b_acc = test.model_b_accuracy / test.model_b_requests if test.model_b_requests > 0 else 0

        from scipy import stats as scipy_stats
        import numpy as np

        n_a = test.model_a_requests
        n_b = test.model_b_requests
        p_a = a_acc
        p_b = b_acc

        p_pool = (test.model_a_accuracy + test.model_b_accuracy) / (n_a + n_b) if (n_a + n_b) > 0 else 0
        se = np.sqrt(p_pool * (1 - p_pool) * (1/n_a + 1/n_b)) if (n_a + n_b) > 0 and p_pool > 0 and p_pool < 1 else 1e-10

        z_stat = (p_b - p_a) / se if se > 0 else 0
        p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z_stat)))

        significant = p_value < (1 - confidence_level)
        winner = None
        if significant:
            winner = "B" if p_b > p_a else "A"

        stat_test = StatisticalResult(
            test_name="z-test proportions",
            statistic=round(z_stat, 4),
            p_value=round(p_value, 6),
            significant=significant,
            confidence_level=confidence_level,
            model_a_value=round(a_acc, 4),
            model_b_value=round(b_acc, 4),
            winner=winner,
        )

    duration_hours = None
    if test.started_at:
        end = test.ended_at or datetime.utcnow()
        duration_hours = round((end - test.started_at).total_seconds() / 3600, 2)

    return ABTestMetricsResponse(
        test_id=test.id,
        model_a_requests=test.model_a_requests,
        model_b_requests=test.model_b_requests,
        model_a_accuracy=test.model_a_accuracy,
        model_b_accuracy=test.model_b_accuracy,
        statistical_test=stat_test,
        confidence_level=confidence_level,
        duration_hours=duration_hours,
    )


@router.post("/{test_id}/record")
async def record_prediction_outcome(
    test_id: UUID,
    group: str,
    correct: bool,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ABTest).where(ABTest.id == test_id))
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    if group == "A":
        test.model_a_accuracy += 1 if correct else 0
    elif group == "B":
        test.model_b_accuracy += 1 if correct else 0
    else:
        raise HTTPException(status_code=400, detail="Invalid group, must be A or B")

    await db.flush()
    return {"status": "recorded", "group": group, "correct": correct}
