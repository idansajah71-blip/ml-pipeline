from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/costs", tags=["Cost Tracking"])


class CostEntry(BaseModel):
    resource_type: str
    resource_id: Optional[str] = None
    cost_usd: float
    usage_hours: float = 0
    gpu_hours: float = 0
    details: dict = {}


costs_store = []


@router.post("", status_code=201)
async def record_cost(
    data: CostEntry,
    current_user: User = Depends(get_current_active_user),
):
    entry = {
        "id": str(len(costs_store) + 1),
        "user_id": str(current_user.id),
        "resource_type": data.resource_type,
        "resource_id": data.resource_id,
        "cost_usd": data.cost_usd,
        "usage_hours": data.usage_hours,
        "gpu_hours": data.gpu_hours,
        "details": data.details,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    costs_store.append(entry)
    return {"status": "recorded", "id": entry["id"]}


@router.get("/summary")
async def cost_summary(
    days: int = 30,
    current_user: User = Depends(get_current_active_user),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    user_costs = [c for c in costs_store if c["user_id"] == str(current_user.id)]

    total_cost = sum(c["cost_usd"] for c in user_costs)
    total_hours = sum(c["usage_hours"] for c in user_costs)
    total_gpu = sum(c["gpu_hours"] for c in user_costs)

    by_type = {}
    for c in user_costs:
        t = c["resource_type"]
        if t not in by_type:
            by_type[t] = {"cost": 0, "count": 0, "hours": 0}
        by_type[t]["cost"] += c["cost_usd"]
        by_type[t]["count"] += 1
        by_type[t]["hours"] += c["usage_hours"]

    daily = {}
    for c in user_costs:
        day = c["recorded_at"][:10]
        daily[day] = daily.get(day, 0) + c["cost_usd"]

    return {
        "period_days": days,
        "total_cost_usd": round(total_cost, 2),
        "total_usage_hours": round(total_hours, 2),
        "total_gpu_hours": round(total_gpu, 2),
        "by_resource_type": by_type,
        "daily_costs": daily,
        "cost_per_hour": round(total_cost / max(total_hours, 0.01), 4),
    }


@router.get("/by-model")
async def cost_by_model(
    current_user: User = Depends(get_current_active_user),
):
    user_costs = [c for c in costs_store if c["user_id"] == str(current_user.id)]
    by_model = {}
    for c in user_costs:
        mid = c.get("resource_id", "unknown")
        if mid not in by_model:
            by_model[mid] = {"cost": 0, "hours": 0, "gpu_hours": 0}
        by_model[mid]["cost"] += c["cost_usd"]
        by_model[mid]["hours"] += c["usage_hours"]
        by_model[mid]["gpu_hours"] += c["gpu_hours"]

    return {"costs_by_model": by_model}
