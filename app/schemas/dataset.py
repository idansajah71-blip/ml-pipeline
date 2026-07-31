from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    target_column: Optional[str] = None
    tags: List[str] = []


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    target_column: Optional[str] = None
    tags: Optional[List[str]] = None


class DatasetResponse(DatasetBase):
    id: UUID
    file_path: str
    file_size: Optional[int] = None
    rows_count: Optional[int] = None
    columns_count: Optional[int] = None
    column_names: Optional[List[str]] = None
    column_types: Optional[Dict[str, str]] = None
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetPreview(BaseModel):
    columns: List[str]
    dtypes: Dict[str, str]
    head: List[Dict[str, Any]]
    shape: tuple[int, int]
    statistics: Dict[str, Any]
