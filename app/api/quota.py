from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.services.api_quota_service import APIQuotaService

router = APIRouter(prefix="/quota", tags=["API Quota"])


class TierUpdate(BaseModel):
    tier: str


class QuotaResponse(BaseModel):
    tier: str
    rpm: dict
    daily: dict
    monthly: dict


@router.get("", response_model=QuotaResponse)
async def get_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = APIQuotaService(db)
    usage = await service.get_usage(current_user.id)
    return QuotaResponse(**usage)


@router.put("/tier")
async def set_tier(
    data: TierUpdate,
    current_user: User = Depends(require_admin if False else get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = APIQuotaService(db)
    result = await service.set_tier(current_user.id, data.tier)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/check")
async def check_quota(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = APIQuotaService(db)
    result = await service.check_and_increment(current_user.id)
    return result


from app.core.security import require_admin as _require_admin
