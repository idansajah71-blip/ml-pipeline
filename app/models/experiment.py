import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Enum, Index, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.core.utils import utcnow_naive


class ExperimentStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(ExperimentStatus), default=ExperimentStatus.PENDING)
    parameters = Column(JSON, default=dict)
    results = Column(JSON, default=dict)
    logs = Column(Text)
    duration_seconds = Column(Float)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    completed_at = Column(DateTime)

    dataset = relationship("Dataset", back_populates="experiments")
    model = relationship("MLModel", back_populates="experiments")
    owner = relationship("User", back_populates="experiments")

    __table_args__ = (
        Index("ix_experiments_status", "status"),
        Index("ix_experiments_owner_id", "owner_id"),
        Index("ix_experiments_model_id", "model_id"),
        Index("ix_experiments_dataset_id", "dataset_id"),
        Index("ix_experiments_created_at", "created_at"),
    )
