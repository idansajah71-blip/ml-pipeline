import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class APIQuota(Base):
    __tablename__ = "api_quotas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    tier = Column(String(50), default="free")
    rpm_limit = Column(Integer, default=60)
    daily_limit = Column(Integer, default=10000)
    monthly_limit = Column(Integer, default=300000)
    current_rpm = Column(Integer, default=0)
    current_daily = Column(Integer, default=0)
    current_monthly = Column(Integer, default=0)
    rpm_reset_at = Column(DateTime)
    daily_reset_at = Column(DateTime)
    monthly_reset_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class APIUsageLog(Base):
    __tablename__ = "api_usage_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
