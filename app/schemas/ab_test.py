from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class ABTestStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ABTestBase(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    traffic_split: int = Field(default=50, ge=0, le=100)


class ABTestCreate(ABTestBase):
    model_config = {"protected_namespaces": ()}

    model_a_id: UUID
    model_b_id: UUID


class ABTestUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ABTestStatus] = None
    traffic_split: Optional[int] = None


class ABTestResponse(ABTestBase):
    id: UUID
    status: ABTestStatus
    model_a_id: UUID
    model_b_id: UUID
    model_a_requests: int
    model_b_requests: int
    model_a_accuracy: int
    model_b_accuracy: int
    results: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ABTestListResponse(BaseModel):
    total: int
    items: List[ABTestResponse]
