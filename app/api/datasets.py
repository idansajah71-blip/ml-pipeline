from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.dataset import DatasetResponse, DatasetCreate, DatasetPreview, DatasetProfileResponse
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    target_column: Optional[str] = Form(None),
    tags: Optional[str] = Form(""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename.endswith(('.csv', '.xls', '.xlsx')):
        raise HTTPException(status_code=400, detail="Only CSV and Excel files are supported")

    service = DatasetService(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    dataset_data = DatasetCreate(
        name=name,
        description=description,
        target_column=target_column,
        tags=tag_list,
    )

    dataset = await service.create_dataset(file, dataset_data, current_user.id)
    return DatasetResponse.model_validate(dataset)


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    datasets = await service.get_user_datasets(current_user.id, skip=skip, limit=limit)
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.get("/all", response_model=List[DatasetResponse])
async def list_all_datasets(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    datasets = await service.get_all_datasets(skip=skip, limit=limit)
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetResponse.model_validate(dataset)


@router.get("/{dataset_id}/preview", response_model=DatasetPreview)
async def preview_dataset(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    preview = await service.get_dataset_preview(dataset_id)
    return preview


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    deleted = await service.delete_dataset(dataset_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset deleted successfully"}


@router.get("/{dataset_id}/profile", response_model=DatasetProfileResponse)
async def profile_dataset(
    dataset_id: UUID,
    target_column: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    try:
        with open(dataset.file_path, "rb") as f:
            file_content = f.read()

        from app.ml.profiler import DatasetProfiler
        profiler = DatasetProfiler()
        profile = profiler.profile(
            file_content=file_content,
            filename=dataset.file_path.split("/")[-1],
            target_column=target_column or dataset.target_column,
        )
        return DatasetProfileResponse(**profile)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profiling failed: {str(e)}")
