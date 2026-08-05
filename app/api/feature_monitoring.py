from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.notifications import send_alert_email
from app.models.user import User
from app.models.feature_monitoring import FeatureDriftAlert, FeatureStats

router = APIRouter(prefix="/feature-monitoring", tags=["Feature Monitoring"])


class DriftAlertResponse(BaseModel):
    id: UUID
    feature_name: str
    model_id: Optional[UUID]
    drift_type: str
    severity: str
    current_value: Optional[float]
    baseline_value: Optional[float]
    drift_score: Optional[float]
    details: dict
    acknowledged: int
    created_at: str
    model_config = {"from_attributes": True}


class FeatureStatsResponse(BaseModel):
    id: UUID
    feature_name: str
    mean_value: Optional[float]
    std_value: Optional[float]
    min_value: Optional[float]
    max_value: Optional[float]
    null_rate: Optional[float]
    unique_count: Optional[int]
    sample_count: Optional[int]
    histogram: dict
    window_start: Optional[str]
    window_end: Optional[str]
    created_at: str
    model_config = {"from_attributes": True}


@router.get("/alerts", response_model=List[DriftAlertResponse])
async def list_drift_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(FeatureDriftAlert)
    if severity:
        query = query.where(FeatureDriftAlert.severity == severity)
    if acknowledged is not None:
        query = query.where(FeatureDriftAlert.acknowledged == acknowledged)
    query = query.order_by(FeatureDriftAlert.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    alerts = list(result.scalars().all())
    return [DriftAlertResponse.model_validate(a) for a in alerts]


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeatureDriftAlert).where(FeatureDriftAlert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.acknowledged = 1
    await db.flush()
    return {"status": "acknowledged"}


@router.get("/stats/{feature_name}", response_model=List[FeatureStatsResponse])
async def get_feature_stats(
    feature_name: str,
    hours: int = 24,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(FeatureStats)
        .where(FeatureStats.feature_name == feature_name)
        .where(FeatureStats.created_at >= cutoff)
        .order_by(FeatureStats.created_at.desc())
    )
    stats = list(result.scalars().all())
    return [FeatureStatsResponse.model_validate(s) for s in stats]


@router.post("/check")
async def check_feature_drift(
    feature_name: str,
    current_value: float,
    baseline_mean: float,
    baseline_std: float,
    model_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    z_score = abs(current_value - baseline_mean) / baseline_std if baseline_std > 0 else 0

    if z_score > 3:
        severity = "critical"
    elif z_score > 2:
        severity = "warning"
    elif z_score > 1.5:
        severity = "info"
    else:
        severity = "none"

    if severity != "none":
        alert = FeatureDriftAlert(
            feature_name=feature_name,
            model_id=model_id,
            drift_type="distribution_shift",
            severity=severity,
            current_value=current_value,
            baseline_value=baseline_mean,
            drift_score=z_score,
            details={"z_score": z_score, "baseline_std": baseline_std},
        )
        db.add(alert)
        await db.flush()

        if severity in ("critical", "warning"):
            send_alert_email(
                subject=f"Drift Alert: {feature_name}",
                body=(
                    f"Feature: {feature_name}\n"
                    f"Severity: {severity}\n"
                    f"Z-Score: {z_score:.4f}\n"
                    f"Current: {current_value}\n"
                    f"Baseline Mean: {baseline_mean}\n"
                    f"Baseline Std: {baseline_std}\n"
                ),
                alert_type=severity,
            )

    return {
        "feature": feature_name,
        "z_score": round(z_score, 4),
        "severity": severity,
        "drift_detected": severity in ("warning", "critical"),
    }
