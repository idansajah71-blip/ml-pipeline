from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ExperimentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ExperimentBase(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = {}


class ExperimentCreate(ExperimentBase):
    dataset_id: UUID
    model_id: UUID


class ExperimentResponse(ExperimentBase):
    id: UUID
    status: ExperimentStatus
    results: Dict[str, Any] = {}
    logs: Optional[str] = None
    duration_seconds: Optional[str] = None
    dataset_id: UUID
    model_id: UUID
    owner_id: UUID
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ExperimentListResponse(BaseModel):
    total: int
    items: List[ExperimentResponse]
