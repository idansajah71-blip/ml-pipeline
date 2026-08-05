import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class DataLineage(Base):
    __tablename__ = "data_lineage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_type = Column(String(50), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(UUID(as_uuid=True), nullable=False)
    transformation = Column(String(255))
    metadata_json = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CustomMetric(Base):
    __tablename__ = "custom_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    metric_type = Column(String(50), nullable=False)
    query_or_formula = Column(Text, nullable=False)
    model_id = Column(UUID(as_uuid=True), nullable=True)
    dashboard_config = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MetricDataPoint(Base):
    __tablename__ = "metric_data_points"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_id = Column(UUID(as_uuid=True), nullable=False)
    value = Column(Float, nullable=False)
    labels = Column(JSON, default=dict)
    recorded_at = Column(DateTime, default=datetime.utcnow)
