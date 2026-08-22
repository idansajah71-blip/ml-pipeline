from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import Dict, Optional, List
from uuid import UUID
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import json

from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.core.redis import cache_get, cache_set
from app.models.user import User
from app.models.model import MLModel, ModelStatus
from app.models.dataset import Dataset
from app.models.experiment import Experiment, ExperimentStatus
from app.models.prediction import Prediction

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    cached = await cache_get("monitoring:stats")
    if cached:
        return json.loads(cached)

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

    result = {
        "total_models": models_count.scalar(),
        "total_datasets": datasets_count.scalar(),
        "total_experiments": experiments_count.scalar(),
        "total_predictions": predictions_count.scalar(),
        "active_models": active_models.scalar(),
        "training_experiments": training_experiments.scalar(),
    }

    await cache_set("monitoring:stats", json.dumps(result, default=str), expire=60)

    return result


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


@router.get("/model/{model_id}/performance")
async def get_model_performance(
    model_id: UUID,
    hours: int = 24,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    preds_result = await db.execute(
        select(Prediction)
        .where(
            Prediction.model_id == model_id,
            Prediction.created_at >= cutoff,
        )
        .order_by(Prediction.created_at)
    )
    predictions = list(preds_result.scalars().all())

    if not predictions:
        return {
            "model_id": str(model_id),
            "period_hours": hours,
            "total_predictions": 0,
            "metrics": {},
            "hourly_breakdown": [],
        }

    hourly: Dict[str, List] = {}
    for pred in predictions:
        hour_key = pred.created_at.strftime("%Y-%m-%d %H:00")
        if hour_key not in hourly:
            hourly[hour_key] = []
        hourly[hour_key].append(pred)

    hourly_breakdown = []
    for hour, preds in sorted(hourly.items()):
        confidences = [p.confidence or 0 for p in preds if p.confidence is not None]
        latencies = [p.latency_ms or 0 for p in preds if p.latency_ms is not None]
        hourly_breakdown.append({
            "hour": hour,
            "count": len(preds),
            "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "min_confidence": round(min(confidences), 4) if confidences else 0,
            "max_confidence": round(max(confidences), 4) if confidences else 0,
        })

    all_confidences = [p.confidence or 0 for p in predictions if p.confidence is not None]
    all_latencies = [p.latency_ms or 0 for p in predictions if p.latency_ms is not None]

    return {
        "model_id": str(model_id),
        "model_name": model.name,
        "period_hours": hours,
        "total_predictions": len(predictions),
        "metrics": {
            "avg_confidence": round(sum(all_confidences) / len(all_confidences), 4) if all_confidences else 0,
            "min_confidence": round(min(all_confidences), 4) if all_confidences else 0,
            "max_confidence": round(max(all_confidences), 4) if all_confidences else 0,
            "avg_latency_ms": round(sum(all_latencies) / len(all_latencies), 2) if all_latencies else 0,
            "p95_latency_ms": round(sorted(all_latencies)[int(len(all_latencies) * 0.95)] if all_latencies else 0, 2),
            "p99_latency_ms": round(sorted(all_latencies)[int(len(all_latencies) * 0.99)] if all_latencies else 0, 2),
        },
        "hourly_breakdown": hourly_breakdown,
    }


class PredictionHistoryQuery(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: Optional[UUID] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    prediction_value: Optional[str] = None
    min_confidence: Optional[float] = None
    skip: int = 0
    limit: int = 100


@router.post("/predictions/history")
async def get_prediction_history(
    query: PredictionHistoryQuery,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Prediction)

    if query.model_id:
        stmt = stmt.where(Prediction.model_id == query.model_id)

    if query.start_date:
        try:
            start = datetime.fromisoformat(query.start_date)
            stmt = stmt.where(Prediction.created_at >= start)
        except ValueError:
            pass

    if query.end_date:
        try:
            end = datetime.fromisoformat(query.end_date)
            stmt = stmt.where(Prediction.created_at <= end)
        except ValueError:
            pass

    if query.prediction_value:
        stmt = stmt.where(Prediction.prediction == query.prediction_value)

    if query.min_confidence is not None:
        stmt = stmt.where(Prediction.confidence >= query.min_confidence)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(desc(Prediction.created_at)).offset(query.skip).limit(query.limit)
    result = await db.execute(stmt)
    predictions = list(result.scalars().all())

    return {
        "total": total,
        "items": [
            {
                "id": str(p.id),
                "input_data": p.input_data,
                "prediction": p.prediction,
                "probability": p.probability,
                "confidence": p.confidence,
                "latency_ms": p.latency_ms,
                "model_id": str(p.model_id),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in predictions
        ],
    }


@router.get("/predictions/stats")
async def get_prediction_stats(
    model_id: Optional[UUID] = None,
    hours: int = 24,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = select(Prediction).where(Prediction.created_at >= cutoff)

    if model_id:
        stmt = stmt.where(Prediction.model_id == model_id)

    result = await db.execute(stmt)
    predictions = list(result.scalars().all())

    if not predictions:
        return {
            "total": 0,
            "period_hours": hours,
            "by_prediction": {},
            "avg_confidence": 0,
            "avg_latency_ms": 0,
        }

    by_prediction: Dict[str, int] = {}
    for p in predictions:
        by_prediction[p.prediction] = by_prediction.get(p.prediction, 0) + 1

    confidences = [p.confidence or 0 for p in predictions if p.confidence is not None]
    latencies = [p.latency_ms or 0 for p in predictions if p.latency_ms is not None]

    return {
        "total": len(predictions),
        "period_hours": hours,
        "by_prediction": by_prediction,
        "avg_confidence": round(sum(confidences) / len(confidences), 4) if confidences else 0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
    }


@router.get("/alerts")
async def get_model_alerts(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MLModel).where(MLModel.status == ModelStatus.DEPLOYED)
    )
    deployed_models = list(result.scalars().all())

    if not deployed_models:
        return {"total_alerts": 0, "alerts": [], "checked_at": datetime.now(timezone.utc).isoformat()}

    model_ids = [m.id for m in deployed_models]
    model_names = {m.id: m.name for m in deployed_models}
    cutoff_24h = datetime.now(timezone.utc) - timedelta(hours=24)

    stats_result = await db.execute(
        select(
            Prediction.model_id,
            func.count(Prediction.id).label("pred_count"),
            func.avg(Prediction.confidence).label("avg_conf"),
            func.avg(Prediction.latency_ms).label("avg_lat"),
        ).where(
            Prediction.model_id.in_(model_ids),
            Prediction.created_at >= cutoff_24h,
        ).group_by(Prediction.model_id)
    )
    model_stats = {row.model_id: row for row in stats_result.all()}

    alerts = []
    for model_id in model_ids:
        stats = model_stats.get(model_id)
        name = model_names[model_id]

        if stats is None or stats.pred_count == 0:
            alerts.append({
                "model_id": str(model_id),
                "model_name": name,
                "alert_type": "no_predictions",
                "severity": "warning",
                "message": f"No predictions in last 24h for {name}",
            })
            continue

        avg_conf = stats.avg_conf or 0
        if avg_conf < 0.5:
            alerts.append({
                "model_id": str(model_id),
                "model_name": name,
                "alert_type": "low_confidence",
                "severity": "critical",
                "message": f"Low avg confidence ({avg_conf:.2%}) for {name}",
            })

        avg_lat = stats.avg_lat or 0
        if avg_lat > 1000:
            alerts.append({
                "model_id": str(model_id),
                "model_name": name,
                "alert_type": "high_latency",
                "severity": "warning",
                "message": f"High avg latency ({avg_lat:.0f}ms) for {name}",
            })

    return {
        "total_alerts": len(alerts),
        "alerts": alerts,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/retrain/{model_id}")
async def trigger_retrain(
    model_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    from app.ml.tasks import retrain_model_task
    task = retrain_model_task.delay(str(model_id), str(current_user.id))

    return {
        "message": f"Retraining started for {model.name}",
        "task_id": task.id,
        "model_id": str(model_id),
    }


class LatencySLARequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    sla_threshold_ms: float = 500.0
    window_hours: int = 24


@router.post("/latency-sla")
async def check_latency_sla(
    req: LatencySLARequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == req.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    cutoff = datetime.now(timezone.utc) - timedelta(hours=req.window_hours)

    avg_result = await db.execute(
        select(func.avg(Prediction.latency_ms)).where(
            Prediction.model_id == req.model_id,
            Prediction.created_at >= cutoff,
        )
    )
    avg_latency = float(avg_result.scalar() or 0)

    p95_result = await db.execute(
        select(Prediction.latency_ms).where(
            Prediction.model_id == req.model_id,
            Prediction.created_at >= cutoff,
        ).order_by(Prediction.latency_ms)
    )
    all_latencies = [r[0] for r in p95_result.all() if r[0] is not None]
    p95 = all_latencies[int(len(all_latencies) * 0.95)] if all_latencies else 0
    p99 = all_latencies[int(len(all_latencies) * 0.99)] if all_latencies else 0

    violations = len([l for l in all_latencies if l > req.sla_threshold_ms])
    violation_pct = (violations / len(all_latencies) * 100) if all_latencies else 0

    return {
        "model_id": str(req.model_id),
        "model_name": model.name,
        "window_hours": req.window_hours,
        "sla_threshold_ms": req.sla_threshold_ms,
        "metrics": {
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95, 2),
            "p99_latency_ms": round(p99, 2),
            "total_predictions": len(all_latencies),
            "violations": violations,
            "violation_percentage": round(violation_pct, 2),
        },
        "sla_met": violation_pct < 5.0,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
