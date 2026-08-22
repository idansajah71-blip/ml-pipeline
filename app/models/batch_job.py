import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Integer, Float, Enum, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.core.utils import utcnow_naive


class BatchJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BatchJob(Base):
    __tablename__ = "batch_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    status = Column(Enum(BatchJobStatus), default=BatchJobStatus.PENDING)
    input_file_path = Column(String(500))
    output_file_path = Column(String(500))
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    avg_latency_ms = Column(Float, default=0)
    results_summary = Column(JSON, default=dict)
    error_message = Column(Text)
    task_id = Column(String(255))
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=utcnow_naive)

    model = relationship("MLModel")
    owner = relationship("User")

    __table_args__ = (
        Index("ix_batch_jobs_status", "status"),
        Index("ix_batch_jobs_model_id", "model_id"),
        Index("ix_batch_jobs_owner_id", "owner_id"),
        Index("ix_batch_jobs_created_at", "created_at"),
    )
