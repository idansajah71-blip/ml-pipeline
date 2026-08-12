import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow_naive


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id = Column(UUID(as_uuid=True), ForeignKey("datasets.id"), nullable=False)
    status = Column(String(20), default="passed")
    total_rows = Column(Float, default=0)
    total_checks = Column(Float, default=0)
    passed_checks = Column(Float, default=0)
    failed_checks = Column(Float, default=0)
    score = Column(Float, default=100.0)
    checks = Column(JSON, default=list)
    summary = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow_naive)

    dataset = relationship("Dataset")
