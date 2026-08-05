from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.model import MLModel

router = APIRouter(prefix="/marketplace", tags=["Model Marketplace"])


class ShareCreate(BaseModel):
    model_id: UUID
    shared_with_org: Optional[str] = None
    permission: str = "read"
    is_public: bool = False
    tags: List[str] = []


class ShareResponse(BaseModel):
    id: str
    model_id: str
    model_name: str
    shared_by: str
    permission: str
    is_public: int
    downloads: int
    rating: float
    tags: list
    created_at: str


marketplace_store = []


@router.post("/share", response_model=ShareResponse, status_code=201)
async def share_model(
    data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    share = {
        "id": str(len(marketplace_store) + 1),
        "model_id": str(data.model_id),
        "model_name": model.name,
        "shared_by": str(current_user.id),
        "shared_with_org": data.shared_with_org,
        "permission": data.permission,
        "is_public": 1 if data.is_public else 0,
        "downloads": 0,
        "rating": 0,
        "tags": data.tags,
        "created_at": "2026-01-01T00:00:00",
    }
    marketplace_store.append(share)
    return ShareResponse(**share)


@router.get("/discover")
async def discover_models(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
):
    public = [s for s in marketplace_store if s["is_public"] == 1]
    if tag:
        public = [s for s in public if tag in s.get("tags", [])]
    if search:
        public = [s for s in public if search.lower() in s.get("model_name", "").lower()]
    return {"models": public}


@router.post("/{share_id}/download")
async def download_model(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
):
    share = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    share["downloads"] += 1
    return {"status": "downloaded", "model_id": share["model_id"]}


@router.post("/{share_id}/rate")
async def rate_model(
    share_id: str,
    rating: float,
    current_user: User = Depends(get_current_active_user),
):
    share = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    share["rating"] = round((share["rating"] + rating) / 2, 1)
    return {"status": "rated", "new_rating": share["rating"]}
