from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum


class ModelStatus(str, Enum):
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"
    FAILED = "failed"


class ModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    algorithm: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = []


class ModelCreate(ModelBase):
    target_column: str


class ModelUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ModelStatus] = None
    tags: Optional[List[str]] = None
    is_default: Optional[int] = None


class ModelResponse(ModelBase):
    id: UUID
    version: int
    status: ModelStatus
    file_path: Optional[str] = None
    metrics: Dict[str, Any] = {}
    parameters: Dict[str, Any] = {}
    feature_names: List[str] = []
    target_column: Optional[str] = None
    is_default: int
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    total: int
    items: List[ModelResponse]


class TrainRequest(BaseModel):
    dataset_id: UUID
    algorithm: str = Field(default="random_forest")
    parameters: Dict[str, Any] = {}
    target_column: Optional[str] = None


class TrainResponse(BaseModel):
    experiment_id: UUID
    message: str
    status: str


class PredictRequest(BaseModel):
    data: List[Dict[str, Any]]
    model_id: Optional[UUID] = None


class PredictResponse(BaseModel):
    predictions: List[Dict[str, Any]]
    model_version: int
    latency_ms: int


class BatchPredictRequest(BaseModel):
    data: List[Dict[str, Any]]


class BatchPredictResponse(BaseModel):
    predictions: List[Dict[str, Any]]
    model_version: int
    latency_ms: int
    total: int
