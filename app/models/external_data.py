import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow_naive


class ExternalDataSource(Base):
    """Registered external data source (whitelist-only)."""
    __tablename__ = "external_data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True)
    base_url = Column(String(500), nullable=False)
    source_type = Column(String(20), nullable=False, default="api")  # api / scrape
    license = Column(String(255), nullable=True)
    license_url = Column(String(500), nullable=True)
    rate_limit_per_min = Column(Integer, default=60)
    requires_api_key = Column(Boolean, default=False)
    api_key_env_var = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)

    caches = relationship("ExternalDatasetCache", back_populates="source")
    search_logs = relationship("ExternalDataSearchLog", back_populates="source")

    __table_args__ = (
        Index("ix_external_data_sources_slug", "slug"),
        Index("ix_external_data_sources_is_active", "is_active"),
    )


class ExternalDatasetCache(Base):
    """Cached result from an external data source fetch."""
    __tablename__ = "external_dataset_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("external_data_sources.id"), nullable=False)
    query_hash = Column(String(64), nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    preview_data = Column(JSON, default=list)  # first 5-10 rows for preview
    full_data_path = Column(String(500), nullable=True)  # path to cached CSV/parquet
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    columns = Column(JSON, default=list)  # column names + types
    source_url = Column(String(500), nullable=True)
    license_note = Column(Text, nullable=True)
    fetched_at = Column(DateTime, default=utcnow_naive)
    expires_at = Column(DateTime, nullable=True)

    source = relationship("ExternalDataSource", back_populates="caches")

    __table_args__ = (
        Index("ix_external_dataset_cache_source_id", "source_id"),
        Index("ix_external_dataset_cache_query_hash", "query_hash"),
        Index("ix_external_dataset_cache_expires_at", "expires_at"),
    )


class ExternalDataSearchLog(Base):
    """Audit log for external data searches and imports."""
    __tablename__ = "external_data_search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    query_text = Column(String(500), nullable=False)
    matched_source_id = Column(UUID(as_uuid=True), ForeignKey("external_data_sources.id"), nullable=True)
    selected_result_id = Column(UUID(as_uuid=True), ForeignKey("external_dataset_cache.id"), nullable=True)
    imported = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow_naive)

    source = relationship("ExternalDataSource", back_populates="search_logs")

    __table_args__ = (
        Index("ix_external_data_search_logs_user_id", "user_id"),
        Index("ix_external_data_search_logs_created_at", "created_at"),
    )
