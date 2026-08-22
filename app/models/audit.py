from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.core.database import Base
from app.core.utils import utcnow_naive


class AuditLog(Base):
    __tablename__ = "audit_logs_secondary"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    status_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=utcnow_naive, index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id} on {self.resource_type}>"
