import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Float, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    url = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="pending")

    raw_row_count = Column(Integer, default=0)
    clean_row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)

    tables_data = Column(JSON, default=list)
    lists_data = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)

    processed_data = Column(JSON, default=list)
    columns_typed = Column(JSON, default=dict)
    columns_renamed = Column(JSON, default=dict)
    quality_score = Column(Float, default=0.0)
    quality_issues = Column(JSON, default=list)
    clusters = Column(JSON, default=dict)

    ml_processing_applied = Column(JSON, default=list)

    advanced_analysis = Column(JSON, default=dict)
    sentiment_analysis = Column(JSON, default=dict)
    pattern_analysis = Column(JSON, default=dict)
    scrape_metadata = Column(JSON, default=dict)

    content_hash = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)

    scrape_type = Column(String(30), default="single")
    batch_results = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    scraped_at = Column(DateTime, nullable=True)
    processed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_scrape_jobs_user_id", "user_id"),
        Index("ix_scrape_jobs_status", "status"),
        Index("ix_scrape_jobs_created_at", "created_at"),
        Index("ix_scrape_jobs_scrape_type", "scrape_type"),
    )
