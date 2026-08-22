import uuid
from sqlalchemy import Column, String, DateTime, JSON, Text, Float, Integer
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.utils import utcnow_naive


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String(500))
    rows_count = Column(Integer, default=0)
    columns_count = Column(Integer, default=0)
    schema_snapshot = Column(JSON, default=dict)
    stats_snapshot = Column(JSON, default=dict)
    changelog = Column(Text)
    checksum = Column(String(64))
    size_bytes = Column(Integer, default=0)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)


class EnsembleModel(Base):
    __tablename__ = "ensemble_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    strategy = Column(String(50), default="voting")
    model_ids = Column(JSON, default=list)
    weights = Column(JSON, default=dict)
    metrics = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)


class ComputeCost(Base):
    __tablename__ = "compute_costs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    cost_usd = Column(Float, nullable=False)
    usage_hours = Column(Float, default=0)
    gpu_hours = Column(Float, default=0)
    details = Column(JSON, default=dict)
    recorded_at = Column(DateTime, default=utcnow_naive)
