import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class FeatureDriftAlert(Base):
    __tablename__ = "feature_drift_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_name = Column(String(255), nullable=False)
    model_id = Column(UUID(as_uuid=True), nullable=True)
    drift_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    current_value = Column(Float)
    baseline_value = Column(Float)
    drift_score = Column(Float)
    details = Column(JSON, default=dict)
    acknowledged = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class FeatureStats(Base):
    __tablename__ = "feature_stats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_name = Column(String(255), nullable=False)
    model_id = Column(UUID(as_uuid=True), nullable=True)
    mean_value = Column(Float)
    std_value = Column(Float)
    min_value = Column(Float)
    max_value = Column(Float)
    null_rate = Column(Float)
    unique_count = Column(Integer)
    sample_count = Column(Integer)
    histogram = Column(JSON, default=dict)
    window_start = Column(DateTime)
    window_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
