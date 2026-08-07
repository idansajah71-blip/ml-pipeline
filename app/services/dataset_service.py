import os
import uuid
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, UploadFile

from app.models.dataset import Dataset
from app.schemas.dataset import DatasetCreate
from app.ml.processor import DataProcessor
from app.core.config import get_settings

settings = get_settings()


class DatasetService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.processor = DataProcessor()
        self.upload_dir = os.path.join(settings.ML_ARTIFACTS_DIR, "datasets")
        os.makedirs(self.upload_dir, exist_ok=True)

    async def create_dataset(
        self,
        file: UploadFile,
        dataset_data: DatasetCreate,
        owner_id: UUID,
    ) -> Dataset:
        file_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1]
        file_path = os.path.join(self.upload_dir, f"{file_id}{file_ext}")

        content = await file.read()

        if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")

        with open(file_path, "wb") as f:
            f.write(content)

        try:
            df = self.processor.load_data(content, file.filename)
            data_info = self.processor.get_data_info(df)
        except Exception as e:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Error parsing file: {str(e)}")

        target_col = dataset_data.target_column
        if target_col and target_col not in df.columns:
            os.remove(file_path)
            raise HTTPException(status_code=400, detail=f"Target column '{target_col}' not found")

        dataset = Dataset(
            name=dataset_data.name,
            description=dataset_data.description,
            file_path=file_path,
            file_size=len(content),
            rows_count=data_info['shape'][0],
            columns_count=data_info['shape'][1],
            column_names=data_info['columns'],
            column_types=data_info['dtypes'],
            target_column=target_col,
            tags=dataset_data.tags or [],
            owner_id=owner_id,
        )

        self.db.add(dataset)
        await self.db.flush()
        await self.db.refresh(dataset)
        return dataset

    async def get_dataset(self, dataset_id: UUID) -> Optional[Dataset]:
        result = await self.db.execute(select(Dataset).where(Dataset.id == dataset_id))
        return result.scalar_one_or_none()

    async def get_user_datasets(self, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[Dataset]:
        result = await self.db.execute(
            select(Dataset)
            .where(Dataset.owner_id == owner_id, Dataset.is_archived == False)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_archived_datasets(self, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[Dataset]:
        result = await self.db.execute(
            select(Dataset)
            .where(Dataset.owner_id == owner_id, Dataset.is_archived == True)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_dataset(self, dataset_id: UUID, owner_id: UUID) -> bool:
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            return False
        if dataset.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        dataset.is_archived = True
        await self.db.flush()
        return True

    async def restore_dataset(self, dataset_id: UUID, owner_id: UUID) -> bool:
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            return False
        if dataset.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        dataset.is_archived = False
        await self.db.flush()
        return True

    async def get_dataset_preview(self, dataset_id: UUID) -> dict:
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        with open(dataset.file_path, "rb") as f:
            content = f.read()

        filename = os.path.basename(dataset.file_path)
        df = self.processor.load_data(content, filename)
        return self.processor.get_data_info(df)

    async def get_all_datasets(self, skip: int = 0, limit: int = 100) -> List[Dataset]:
        result = await self.db.execute(select(Dataset).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update_dataset(
        self,
        dataset_id: UUID,
        update_data: dict,
        owner_id: UUID,
    ) -> Optional[Dataset]:
        dataset = await self.get_dataset(dataset_id)
        if not dataset:
            return None
        if dataset.owner_id != owner_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized")

        for field, value in update_data.items():
            if value is None:
                continue
            if not hasattr(dataset, field):
                continue
            setattr(dataset, field, value)

        self.db.add(dataset)
        await self.db.flush()
        await self.db.refresh(dataset)
        return dataset
