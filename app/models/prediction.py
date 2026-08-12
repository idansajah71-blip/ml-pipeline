import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow_naive


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_data = Column(JSON, nullable=False)
    prediction = Column(String(255), nullable=False)
    probability = Column(Float)
    confidence = Column(Float)
    latency_ms = Column(Integer)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    feedback_correct = Column(Boolean, nullable=True)
    feedback_comment = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)

    model = relationship("MLModel", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_model_id", "model_id"),
        Index("ix_predictions_created_at", "created_at"),
    )
