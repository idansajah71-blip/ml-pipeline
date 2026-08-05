import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Webhook(Base):
    __tablename__ = "webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    secret = Column(String(255))
    events = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    headers = Column(JSON, default=dict)
    owner_id = Column(UUID(as_uuid=True), nullable=False)
    last_triggered_at = Column(DateTime)
    last_status_code = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class WebhookLog(Base):
    __tablename__ = "webhook_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    webhook_id = Column(UUID(as_uuid=True), nullable=False)
    event = Column(String(100), nullable=False)
    payload = Column(JSON, default=dict)
    response_status = Column(Integer)
    response_body = Column(Text)
    success = Column(Boolean, default=False)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
