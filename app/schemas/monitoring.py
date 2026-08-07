from pydantic import BaseModel
from typing import Optional, Dict, Any


class SystemStats(BaseModel):
    total_models: int = 0
    total_datasets: int = 0
    total_experiments: int = 0
    total_predictions: int = 0
    active_models: int = 0
    training_experiments: int = 0


class CPUInfo(BaseModel):
    percent: float = 0.0
    count: int = 0


class MemoryInfo(BaseModel):
    percent: float = 0.0
    available: int = 0
    total: int = 0
    used: int = 0


class DiskInfo(BaseModel):
    percent: float = 0.0
    used: int = 0
    total: int = 0
    free: int = 0


class SystemInfo(BaseModel):
    cpu: CPUInfo
    memory: MemoryInfo
    disk: DiskInfo
    platform: str = ""
    python_version: str = ""
    uptime_seconds: float = 0.0


class ModelMetrics(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: str
    prediction_count: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    last_prediction_at: Optional[str] = None
