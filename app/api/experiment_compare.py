from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.experiment import Experiment

router = APIRouter(prefix="/experiment-compare", tags=["Experiment Comparison"])


class ExperimentSummary(BaseModel):
    id: str
    name: str
    status: str
    algorithm: str
    metrics: dict
    duration_seconds: Optional[float]
    created_at: str


class ComparisonResult(BaseModel):
    experiments: List[ExperimentSummary]
    best_by_metric: dict
    metric_comparison: dict


@router.post("", response_model=ComparisonResult)
async def compare_experiments(
    experiment_ids: List[UUID],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if len(experiment_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 experiments required")
    if len(experiment_ids) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 experiments")

    result = await db.execute(
        select(Experiment).where(
            Experiment.id.in_(experiment_ids),
            Experiment.owner_id == current_user.id,
        )
    )
    experiments = list(result.scalars().all())

    if len(experiments) != len(experiment_ids):
        raise HTTPException(status_code=404, detail="Some experiments not found")

    summaries = []
    all_metrics = {}
    for exp in experiments:
        metrics = exp.results.get("metrics", {}) if exp.results else {}
        algo = exp.results.get("algorithm", exp.parameters.get("algorithm", "unknown")) if exp.results else "unknown"
        summary = ExperimentSummary(
            id=str(exp.id),
            name=exp.name,
            status=exp.status.value if hasattr(exp.status, 'value') else exp.status,
            algorithm=algo,
            metrics=metrics,
            duration_seconds=float(exp.duration_seconds) if exp.duration_seconds else None,
            created_at=exp.created_at.isoformat() if exp.created_at else "",
        )
        summaries.append(summary)
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                if k not in all_metrics:
                    all_metrics[k] = []
                all_metrics[k].append({"experiment_id": str(exp.id), "value": v})

    best_by_metric = {}
    for metric, values in all_metrics.items():
        if values:
            best = max(values, key=lambda x: x["value"])
            best_by_metric[metric] = {
                "experiment_id": best["experiment_id"],
                "value": best["value"],
            }

    metric_comparison = {}
    for metric, values in all_metrics.items():
        vals = [v["value"] for v in values]
        metric_comparison[metric] = {
            "min": min(vals),
            "max": max(vals),
            "mean": sum(vals) / len(vals),
            "spread": max(vals) - min(vals),
        }

    return ComparisonResult(
        experiments=summaries,
        best_by_metric=best_by_metric,
        metric_comparison=metric_comparison,
    )


@router.get("/leaderboard")
async def get_leaderboard(
    algorithm: Optional[str] = None,
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Experiment).where(
        Experiment.status == "completed",
        Experiment.owner_id == current_user.id,
    )
    if algorithm:
        query = query.where(Experiment.parameters["algorithm"].as_string() == algorithm)
    query = query.order_by(Experiment.created_at.desc()).limit(100)

    result = await db.execute(query)
    experiments = list(result.scalars().all())

    leaderboard = []
    for exp in experiments:
        metrics = exp.results.get("metrics", {}) if exp.results else {}
        if not metrics:
            continue
        algo = exp.results.get("algorithm", "unknown") if exp.results else "unknown"
        leaderboard.append({
            "experiment_id": str(exp.id),
            "name": exp.name,
            "algorithm": algo,
            "accuracy": metrics.get("accuracy", 0),
            "f1_macro": metrics.get("f1_macro", 0),
            "created_at": exp.created_at.isoformat() if exp.created_at else "",
        })

    leaderboard.sort(key=lambda x: x.get("f1_macro", 0), reverse=True)
    return {"leaderboard": leaderboard[:limit]}
