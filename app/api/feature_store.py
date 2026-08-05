from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.feature_store import FeatureGroup, Feature, FeatureSnapshot
from app.services.feature_store_service import FeatureStoreService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/feature-store", tags=["Feature Store"])


class FeatureGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    tags: List[str] = []


class FeatureGroupResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    tags: list
    created_at: str
    model_config = {"from_attributes": True}


class FeatureCreate(BaseModel):
    name: str
    data_type: str
    description: Optional[str] = None
    is_required: bool = False
    default_value: Optional[str] = None
    validation_rules: dict = {}
    transformation: dict = {}


class FeatureResponse(BaseModel):
    id: UUID
    name: str
    data_type: str
    description: Optional[str]
    is_required: bool
    created_at: str
    model_config = {"from_attributes": True}


class FeatureIngest(BaseModel):
    row_key: str
    features: dict


@router.post("/groups", response_model=FeatureGroupResponse, status_code=201)
async def create_feature_group(
    data: FeatureGroupCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = FeatureStoreService(db)
    group = await service.create_group(data.name, data.description, current_user.id, data.tags)
    audit = AuditService(db)
    await audit.log("create_feature_group", "feature_group", group.id, {"name": data.name}, current_user.id, request)
    return FeatureGroupResponse.model_validate(group)


@router.get("/groups", response_model=List[FeatureGroupResponse])
async def list_feature_groups(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FeatureGroup).order_by(FeatureGroup.created_at.desc()))
    groups = list(result.scalars().all())
    return [FeatureGroupResponse.model_validate(g) for g in groups]


@router.post("/groups/{group_id}/features", response_model=FeatureResponse, status_code=201)
async def add_feature(
    group_id: UUID,
    data: FeatureCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = FeatureStoreService(db)
    feature = await service.add_feature(
        group_id, data.name, data.data_type, current_user.id,
        description=data.description, is_required=data.is_required,
        default_value=data.default_value, validation_rules=data.validation_rules,
        transformation=data.transformation,
    )
    return FeatureResponse.model_validate(feature)


@router.get("/groups/{group_id}/features", response_model=List[FeatureResponse])
async def list_features(
    group_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Feature).where(Feature.feature_group_id == group_id)
    )
    features = list(result.scalars().all())
    return [FeatureResponse.model_validate(f) for f in features]


@router.post("/groups/{group_id}/ingest")
async def ingest_features(
    group_id: UUID,
    data: FeatureIngest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = FeatureStoreService(db)
    snapshot = await service.ingest_features(group_id, data.row_key, data.features)
    return {"status": "ok", "version": snapshot.version}


@router.get("/groups/{group_id}/get/{row_key}")
async def get_features(
    group_id: UUID,
    row_key: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = FeatureStoreService(db)
    snapshot = await service.get_features(group_id, row_key)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Features not found")
    return {"row_key": row_key, "features": snapshot.features, "version": snapshot.version}


@router.post("/groups/{group_id}/get-batch")
async def get_batch_features(
    group_id: UUID,
    row_keys: List[str],
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = FeatureStoreService(db)
    results = await service.get_batch_features(group_id, row_keys)
    return {
        "features": {
            k: {"features": v.features, "version": v.version}
            for k, v in results.items()
        }
    }
