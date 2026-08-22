import uuid
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utils import utcnow_naive


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    status = Column(String(50), default="created")
    file_path = Column(String(500))
    metrics = Column(JSON, default=dict)
    parameters = Column(JSON, default=dict)
    changelog = Column(Text)
    artifact_size_bytes = Column(Integer, default=0)
    parent_version_id = Column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utcnow_naive)

    model = relationship("MLModel")
    owner = relationship("User")
    parent_version = relationship("ModelVersion", remote_side=[id])


class ModelLineage(Base):
    __tablename__ = "model_lineage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    parent_model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=True)
    relationship_type = Column(String(50), nullable=False)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow_naive)

    model = relationship("MLModel", foreign_keys=[model_id])
    parent_model = relationship("MLModel", foreign_keys=[parent_model_id])


class ModelArtifact(Base):
    __tablename__ = "model_artifacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("models.id"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True)
    name = Column(String(255), nullable=False)
    artifact_type = Column(String(50), nullable=False)
    file_path = Column(String(500))
    size_bytes = Column(Integer, default=0)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utcnow_naive)

    model = relationship("MLModel")
    version = relationship("ModelVersion")
