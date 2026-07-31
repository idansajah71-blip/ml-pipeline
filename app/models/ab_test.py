import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ABTestStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ABTest(Base):
    __tablename__ = "ab_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    status = Column(Enum(ABTestStatus), default=ABTestStatus.DRAFT)
    traffic_split = Column(Integer, default=50)
    model_a_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    model_b_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    model_a_requests = Column(Integer, default=0)
    model_b_requests = Column(Integer, default=0)
    model_a_accuracy = Column(Integer, default=0)
    model_b_accuracy = Column(Integer, default=0)
    results = Column(JSON, default=dict)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    model_a = relationship("MLModel", foreign_keys=[model_a_id])
    model_b = relationship("MLModel", foreign_keys=[model_b_id])
