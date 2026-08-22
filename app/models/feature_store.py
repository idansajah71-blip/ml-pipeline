import uuid
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow_naive


class FeatureGroup(Base):
    __tablename__ = "feature_groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    tags = Column(JSON, default=list)
    schema_definition = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    features = relationship("Feature", back_populates="feature_group")


class Feature(Base):
    __tablename__ = "features"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    feature_group_id = Column(UUID(as_uuid=True), ForeignKey("feature_groups.id"), nullable=False)
    data_type = Column(String(50), nullable=False)
    description = Column(Text)
    is_required = Column(Boolean, default=False)
    default_value = Column(String(500))
    validation_rules = Column(JSON, default=dict)
    transformation = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    feature_group = relationship("FeatureGroup", back_populates="features")


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    feature_group_id = Column(UUID(as_uuid=True), nullable=False)
    row_key = Column(String(255), nullable=False)
    features = Column(JSON, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=utcnow_naive)
