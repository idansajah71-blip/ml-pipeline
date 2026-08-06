import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    rows_count = Column(Integer)
    columns_count = Column(Integer)
    column_names = Column(JSON)
    column_types = Column(JSON)
    target_column = Column(String(255))
    tags = Column(JSON, default=list)
    is_archived = Column(Boolean, default=False, nullable=False)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="datasets")
    experiments = relationship("Experiment", back_populates="dataset")

    __table_args__ = (
        Index("ix_datasets_owner_id", "owner_id"),
        Index("ix_datasets_created_at", "created_at"),
        Index("ix_datasets_name", "name"),
    )
