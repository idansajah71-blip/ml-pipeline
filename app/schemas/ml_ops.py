from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class DataQualityConfig(BaseModel):
    model_config = {"protected_namespaces": ()}

    missing_threshold: float = Field(default=5.0, ge=0, le=100)
    z_threshold: float = Field(default=3.0, gt=0)
    expected_types: Optional[dict] = None
    value_ranges: Optional[dict] = None
    unique_columns: Optional[list] = None


class DataQualityCheckResponse(BaseModel):
    name: str
    status: str
    message: str
    details: dict = {}


class DataQualityReportResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    status: str
    total_checks: int
    passed_checks: int
    failed_checks: int
    score: float
    checks: List[DataQualityCheckResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class BatchJobCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str = Field(..., max_length=255)
    model_id: UUID
    input_file_path: str


class BatchJobResponse(BaseModel):
    id: UUID
    name: str
    model_id: UUID
    status: str
    input_file_path: Optional[str] = None
    output_file_path: Optional[str] = None
    total_rows: int = 0
    processed_rows: int = 0
    failed_rows: int = 0
    avg_latency_ms: float = 0
    results_summary: dict = {}
    error_message: Optional[str] = None
    task_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class BatchJobListResponse(BaseModel):
    total: int
    items: List[BatchJobResponse]


class BenchmarkResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_rps: float
    accuracy: Optional[float] = None
    f1: Optional[float] = None


class PruneResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    total_features: int
    kept_features: int
    pruned_features: int
    importance_threshold: float
    feature_importances: dict = {}
    kept: List[str] = []
    pruned: List[str] = []


class ExportResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    format: str
    path: str
    size_bytes: int


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: Optional[UUID] = None
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    details: dict = {}
    ip_address: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogListResponse(BaseModel):
    total: int
    items: List[AuditLogResponse]


class StatisticalResult(BaseModel):
    model_config = {"protected_namespaces": ()}

    test_name: str
    statistic: float
    p_value: float
    significant: bool
    confidence_level: float
    model_a_value: float
    model_b_value: float
    winner: Optional[str] = None


class ABTestMetricsResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    test_id: UUID
    model_a_requests: int
    model_b_requests: int
    model_a_accuracy: float
    model_b_accuracy: float
    statistical_test: Optional[StatisticalResult] = None
    confidence_level: float = 0.95
    duration_hours: Optional[float] = None
