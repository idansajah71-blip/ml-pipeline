import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    input_data = Column(JSON, nullable=False)
    prediction = Column(String(255), nullable=False)
    probability = Column(Float)
    confidence = Column(Float)
    latency_ms = Column(Integer)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    model = relationship("MLModel", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_model_id", "model_id"),
        Index("ix_predictions_created_at", "created_at"),
    )
