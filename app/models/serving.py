import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ServingEndpoint(Base):
    __tablename__ = "serving_endpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    description = Column(Text)
    max_batch_size = Column(Integer, default=1)
    cache_ttl_seconds = Column(Integer, default=300)
    rate_limit_rpm = Column(Integer, default=1000)
    is_active = Column(Integer, default=1)
    metrics = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    model = relationship("MLModel")
    owner = relationship("User")

    __table_args__ = (
        Index("ix_serving_endpoints_model_id", "model_id"),
        Index("ix_serving_endpoints_owner_id", "owner_id"),
        Index("ix_serving_endpoints_name", "name"),
    )


class ServingLog(Base):
    __tablename__ = "serving_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    endpoint_id = Column(UUID(as_uuid=True), nullable=False)
    input_data = Column(JSON)
    prediction = Column(JSON)
    latency_ms = Column(Float)
    cache_hit = Column(Integer, default=0)
    status = Column(String(20), default="success")
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_serving_logs_endpoint_id", "endpoint_id"),
        Index("ix_serving_logs_created_at", "created_at"),
        Index("ix_serving_logs_status", "status"),
    )
