import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Float, Enum, Index, Boolean
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
    status = Column(Enum(ModelStatus, values_callable=lambda x: [e.value for e in x]), default=ModelStatus.TRAINED)
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

    # ── Stage 1: Readiness scoring ────────────────────────────────────────
    readiness_score = Column(Integer, default=0)
    readiness_label = Column(String(50), nullable=True)
    readiness_details = Column(JSON, default=dict)
    training_samples = Column(Integer, default=0)
    cv_scores = Column(JSON, default=list)

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


class ModelShare(Base):
    """A model published to the marketplace by its owner."""
    __tablename__ = "model_shares"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    shared_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    shared_with_org = Column(String(255), nullable=True)
    permission = Column(String(50), default="read")
    is_public = Column(Integer, default=0)
    downloads = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    # ── Stage 2: Rich publish metadata ────────────────────────────────────
    use_case = Column(Text, nullable=True)
    limitations = Column(Text, nullable=True)
    example_inputs = Column(JSON, default=list)
    training_data_summary = Column(JSON, default=dict)
    status = Column(String(50), default="pending")  # pending / approved / rejected
    review_note = Column(Text, nullable=True)

    model = relationship("MLModel", foreign_keys=[model_id])
    user = relationship("User", foreign_keys=[shared_by])

    __table_args__ = (
        Index("ix_model_shares_model_id", "model_id"),
        Index("ix_model_shares_shared_by", "shared_by"),
        Index("ix_model_shares_is_public", "is_public"),
    )


class ModelFeedback(Base):
    """Stage 5: User feedback on marketplace model predictions."""
    __tablename__ = "model_feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    share_id = Column(UUID(as_uuid=True), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    prediction_id = Column(UUID(as_uuid=True), ForeignKey("predictions.id"), nullable=True)
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    is_accurate = Column(Boolean, nullable=True)
    actual_value = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("MLModel", foreign_keys=[model_id])
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_model_feedback_model_id", "model_id"),
        Index("ix_model_feedback_user_id", "user_id"),
    )
