from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.error_utils import log_error
from app.models.user import User
from app.schemas.dataset import DatasetResponse, DatasetCreate, DatasetUpdate, DatasetPreview, DatasetProfileResponse
from app.services.dataset_service import DatasetService
from app.ml.data_utils import validate_magic_bytes

router = APIRouter(prefix="/datasets", tags=["Datasets"])
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = ('.csv', '.tsv', '.xls', '.xlsx', '.json', '.ods')


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
    if not file.filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    content = await file.read()
    magic_error = validate_magic_bytes(file.filename, content)
    if magic_error:
        raise HTTPException(status_code=400, detail=magic_error)

    await file.seek(0)

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


@router.get("/trash", response_model=List[DatasetResponse])
async def list_trash_datasets(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    datasets = await service.get_archived_datasets(current_user.id, skip=skip, limit=limit)
    return [DatasetResponse.model_validate(d) for d in datasets]


@router.post("/{dataset_id}/restore")
async def restore_dataset(
    dataset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    restored = await service.restore_dataset(dataset_id, current_user.id)
    if not restored:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return {"message": "Dataset restored successfully"}


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


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: UUID,
    update_data: DatasetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = DatasetService(db)
    dataset = await service.update_dataset(
        dataset_id,
        update_data.model_dump(exclude_unset=True),
        current_user.id,
    )
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return DatasetResponse.model_validate(dataset)


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
    return {"message": "Dataset archived successfully"}


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
        log_error(e, context=f"Profiling failed for dataset {dataset_id}")
        raise HTTPException(status_code=500, detail="Failed to generate dataset profile. The file may be corrupted.")


@router.post("/import/google-sheet", response_model=DatasetResponse, status_code=201)
async def import_google_sheet(
    url: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    target_column: Optional[str] = Form(None),
    tags: Optional[str] = Form(""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Import a dataset from a public Google Sheets URL."""
    from app.ml.data_utils import load_google_sheet

    try:
        df = load_google_sheet(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    csv_bytes = df.to_csv(index=False).encode('utf-8')
    filename = f"{name}.csv"

    service = DatasetService(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []

    dataset_data = DatasetCreate(
        name=name,
        description=description,
        target_column=target_column,
        tags=tag_list,
    )

    import uuid, os
    file_id = str(uuid.uuid4())
    file_path = os.path.join(service.upload_dir, f"{file_id}.csv")

    with open(file_path, "wb") as f:
        f.write(csv_bytes)

    data_info = service.processor.get_data_info(df)

    target_col = dataset_data.target_column
    if target_col and target_col not in df.columns:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Target column '{target_col}' not found")

    from app.models.dataset import Dataset
    dataset = Dataset(
        name=dataset_data.name,
        description=dataset_data.description,
        file_path=file_path,
        file_size=len(csv_bytes),
        rows_count=data_info['shape'][0],
        columns_count=data_info['shape'][1],
        column_names=data_info['columns'],
        column_types=data_info['dtypes'],
        target_column=target_col,
        tags=dataset_data.tags,
        owner_id=current_user.id,
    )

    db.add(dataset)
    await db.flush()
    await db.refresh(dataset)
    return DatasetResponse.model_validate(dataset)
