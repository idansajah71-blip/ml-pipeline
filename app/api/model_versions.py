from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.model_version import ModelVersion, ModelLineage, ModelArtifact
from app.models.model import MLModel
from app.services.audit_service import AuditService

router = APIRouter(prefix="/model-versions", tags=["Model Versioning"])


class VersionCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    changelog: Optional[str] = None


class VersionResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: UUID
    model_id: UUID
    version_number: int
    status: str
    metrics: dict
    changelog: Optional[str]
    created_at: datetime


class LineageCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    parent_model_id: Optional[UUID] = None
    relationship_type: str
    metadata_json: dict = {}


class LineageResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: UUID
    model_id: UUID
    parent_model_id: Optional[UUID]
    relationship_type: str
    metadata_json: dict
    created_at: datetime


class ArtifactResponse(BaseModel):
    model_config = {"from_attributes": True, "protected_namespaces": ()}

    id: UUID
    model_id: UUID
    name: str
    artifact_type: str
    file_path: Optional[str]
    size_bytes: int
    created_at: datetime


@router.post("", response_model=VersionResponse, status_code=201)
async def create_version(
    data: VersionCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Validate model exists
    model_check = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    if not model_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    result = await db.execute(
        select(ModelVersion)
        .where(ModelVersion.model_id == data.model_id)
        .order_by(ModelVersion.version_number.desc())
        .limit(1)
    )
    last_version = result.scalar_one_or_none()
    next_number = (last_version.version_number + 1) if last_version else 1

    version = ModelVersion(
        model_id=data.model_id,
        version_number=next_number,
        changelog=data.changelog,
        owner_id=current_user.id,
        parent_version_id=last_version.id if last_version else None,
    )
    db.add(version)
    await db.flush()
    await db.refresh(version)

    audit = AuditService(db)
    await audit.log("create_model_version", "model_version", version.id,
                     {"model_id": str(data.model_id), "version": next_number}, current_user.id, request)

    return VersionResponse.model_validate(version)


@router.get("/model/{model_id}", response_model=List[VersionResponse])
async def list_versions(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelVersion)
        .where(ModelVersion.model_id == model_id)
        .order_by(ModelVersion.version_number.desc())
    )
    versions = list(result.scalars().all())
    return [VersionResponse.model_validate(v) for v in versions]


@router.get("/{version_id}", response_model=VersionResponse)
async def get_version(
    version_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return VersionResponse.model_validate(version)


@router.put("/{version_id}/promote")
async def promote_version(
    version_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ModelVersion).where(ModelVersion.id == version_id))
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    version.status = "promoted"
    await db.flush()
    return {"status": "promoted", "version": version.version_number}


@router.post("/lineage", response_model=LineageResponse, status_code=201)
async def create_lineage(
    data: LineageCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    lineage = ModelLineage(
        model_id=data.model_id,
        parent_model_id=data.parent_model_id,
        relationship_type=data.relationship_type,
        metadata_json=data.metadata_json,
    )
    db.add(lineage)
    await db.flush()
    await db.refresh(lineage)
    return LineageResponse.model_validate(lineage)


@router.get("/lineage/{model_id}", response_model=List[LineageResponse])
async def get_lineage(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelLineage).where(
            (ModelLineage.model_id == model_id) | (ModelLineage.parent_model_id == model_id)
        )
    )
    lineage = list(result.scalars().all())
    return [LineageResponse.model_validate(l) for l in lineage]


@router.get("/artifacts/{model_id}", response_model=List[ArtifactResponse])
async def list_artifacts(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ModelArtifact).where(ModelArtifact.model_id == model_id)
    )
    artifacts = list(result.scalars().all())
    return [ArtifactResponse.model_validate(a) for a in artifacts]
