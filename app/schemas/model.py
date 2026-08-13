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


class TrainingMode(str, Enum):
    SIMPLE = "simple"
    ADVANCED = "advanced"


class ProblemType(str, Enum):
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class ModelBase(BaseModel):
    model_config = {"protected_namespaces": ()}

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
    is_default: Optional[int] = 0
    owner_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ModelListResponse(BaseModel):
    total: int
    items: List[ModelResponse]


class TrainRequest(BaseModel):
    dataset_id: UUID
    algorithm: str = Field(default="random_forest")
    parameters: Dict[str, Any] = {}
    target_column: Optional[str] = None
    async_training: bool = False
    mode: TrainingMode = Field(default=TrainingMode.ADVANCED)
    problem_type: ProblemType = Field(default=ProblemType.CLASSIFICATION)
    run_benchmark: bool = True


class TrainResponse(BaseModel):
    experiment_id: UUID
    message: str
    status: str
    task_id: Optional[str] = None


class PredictionItem(BaseModel):
    id: Optional[UUID] = None
    index: Optional[int] = None
    prediction: str
    probability: Optional[float] = None
    probabilities: Optional[Dict[str, float]] = None
    prediction_interval: Optional[Dict[str, float]] = None


class PredictRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    data: List[Dict[str, Any]]
    model_id: Optional[UUID] = None


class PredictResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    predictions: List[PredictionItem]
    model_version: int
    latency_ms: int


class BatchPredictRequest(BaseModel):
    data: List[Dict[str, Any]]


class BatchPredictResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    predictions: List[Dict[str, Any]]
    model_version: int
    latency_ms: int
    total: int


class PredictionFeedbackRequest(BaseModel):
    correct: bool
    comment: Optional[str] = None


class PredictionFeedbackResponse(BaseModel):
    status: str
    prediction_id: UUID
    correct: bool


class ModelStageUpdate(BaseModel):
    stage: str = Field(..., pattern="^(development|staging|production|archived)$")


class ModelCardUpdate(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_card: Dict[str, Any]


class AutoMLRequest(BaseModel):
    dataset_id: UUID
    target_column: str
    algorithms: Optional[List[str]] = None
    problem_type: ProblemType = Field(default=ProblemType.CLASSIFICATION)


class AutoMLResponse(BaseModel):
    task_id: Optional[str] = None
    experiment_id: UUID
    message: str
    status: str


class ExplainRequest(BaseModel):
    data: List[Dict[str, Any]]
    top_k: int = Field(default=10, ge=1, le=50)
    method: str = Field(default="shap", pattern="^(shap|lime|both)$")


class ExplainResponse(BaseModel):
    explanations: List[Dict[str, Any]]
    global_importance: Dict[str, float]
    feature_names: List[str]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    result: Optional[Dict[str, Any]] = None


class BenchmarkRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    n_runs: int = Field(default=100, ge=10, le=1000)


class BenchmarkResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    algorithm: str
    problem_type: str
    metrics: Dict[str, Any]
    inference: Dict[str, Any]
    model_size_bytes: int
    model_size_mb: float
    feature_importance: Optional[Dict[str, float]] = None
    primary_metric: str
    primary_metric_value: float
    benchmark_timestamp: str


class TuningRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    n_trials: int = Field(default=50, ge=10, le=500)
    cv: int = Field(default=5, ge=2, le=10)
    scoring: Optional[str] = None
    timeout_seconds: Optional[int] = None


class TuningResponse(BaseModel):
    best_params: Dict[str, Any]
    best_score: float
    scoring_metric: str
    n_trials: int
    duration_seconds: float
    param_importances: Dict[str, float] = {}


class DataValidationRequest(BaseModel):
    dataset_id: UUID
    target_column: Optional[str] = None


class DataValidationResponse(BaseModel):
    dataset_name: str
    row_count: int
    column_count: int
    checks: List[Dict[str, Any]]
    passed: bool
    summary: Dict[str, Any]


class DriftDetectionRequest(BaseModel):
    reference_dataset_id: UUID
    current_dataset_id: UUID
    column_mapping: Optional[Dict[str, Any]] = None


class DriftDetectionResponse(BaseModel):
    drift_detected: bool
    drift_details: List[Dict[str, Any]]
    n_drifted_columns: int
    method: str


class MLflowRunResponse(BaseModel):
    run_id: Optional[str] = None
    experiment_name: str
    status: str


class AlgorithmsResponse(BaseModel):
    classification: Dict[str, Any]
    regression: Dict[str, Any]
