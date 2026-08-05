from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.dataset import Dataset

router = APIRouter(prefix="/data-versions", tags=["Data Versioning"])


class DatasetVersionCreate(BaseModel):
    dataset_id: UUID
    changelog: Optional[str] = None


class DatasetVersionResponse(BaseModel):
    id: str
    dataset_id: str
    version_number: int
    rows_count: int
    columns_count: int
    changelog: Optional[str]
    checksum: Optional[str]
    size_bytes: int
    created_at: str


dataset_versions = []


@router.post("", response_model=DatasetVersionResponse, status_code=201)
async def create_dataset_version(
    data: DatasetVersionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Dataset).where(Dataset.id == data.dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    existing = [v for v in dataset_versions if v["dataset_id"] == str(data.dataset_id)]
    next_version = len(existing) + 1

    import hashlib
    checksum = ""
    if dataset.file_path:
        try:
            with open(dataset.file_path, "rb") as f:
                checksum = hashlib.md5(f.read()).hexdigest()
        except Exception:
            pass

    version = {
        "id": str(UUID(int=len(dataset_versions) + 1)),
        "dataset_id": str(data.dataset_id),
        "version_number": next_version,
        "rows_count": dataset.rows_count or 0,
        "columns_count": dataset.columns_count or 0,
        "changelog": data.changelog,
        "checksum": checksum,
        "size_bytes": dataset.file_size or 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    dataset_versions.append(version)

    return DatasetVersionResponse(**version)


@router.get("/dataset/{dataset_id}", response_model=List[DatasetVersionResponse])
async def list_dataset_versions(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
):
    versions = [v for v in dataset_versions if v["dataset_id"] == str(dataset_id)]
    versions.sort(key=lambda x: x["version_number"], reverse=True)
    return [DatasetVersionResponse(**v) for v in versions]


@router.get("/{version_id}", response_model=DatasetVersionResponse)
async def get_dataset_version(
    version_id: str,
    current_user: User = Depends(get_current_active_user),
):
    version = next((v for v in dataset_versions if v["id"] == version_id), None)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return DatasetVersionResponse(**version)


@router.post("/{version_id}/diff")
async def diff_versions(
    version_id: str,
    other_version_id: str,
    current_user: User = Depends(get_current_active_user),
):
    v1 = next((v for v in dataset_versions if v["id"] == version_id), None)
    v2 = next((v for v in dataset_versions if v["id"] == other_version_id), None)
    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Version not found")

    return {
        "version_1": v1,
        "version_2": v2,
        "rows_diff": v2["rows_count"] - v1["rows_count"],
        "columns_diff": v2["columns_count"] - v1["columns_count"],
        "checksum_changed": v1.get("checksum") != v2.get("checksum"),
        "schema_changed": v1.get("columns_count") != v2.get("columns_count"),
    }
