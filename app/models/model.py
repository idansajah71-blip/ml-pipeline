import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Float, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ModelStatus(str, enum.Enum):
    TRAINING = "training"
    TRAINED = "trained"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"
    FAILED = "failed"


class MLModel(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    algorithm = Column(String(100), nullable=False)
    version = Column(Integer, default=1)
    status = Column(Enum(ModelStatus), default=ModelStatus.TRAINED)
    file_path = Column(String(500))
    metrics = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)
    feature_names = Column(JSON, default=list)
    target_column = Column(String(255))
    tags = Column(JSON, default=list)
    is_default = Column(Integer, default=0)
    task_id = Column(String(255), nullable=True)
    stage = Column(String(50), default="development")
    parent_model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=True)
    model_card = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="models")
    experiments = relationship("Experiment", back_populates="model")
    predictions = relationship("Prediction", back_populates="model")
    ab_tests = relationship("ABTest", back_populates="model_a", foreign_keys="ABTest.model_a_id")

    __table_args__ = (
        Index("ix_models_status", "status"),
        Index("ix_models_owner_id", "owner_id"),
        Index("ix_models_algorithm", "algorithm"),
        Index("ix_models_stage", "stage"),
        Index("ix_models_created_at", "created_at"),
    )
