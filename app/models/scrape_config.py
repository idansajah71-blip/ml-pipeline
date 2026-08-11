"""Scrape Configuration Models — Persistent storage for templates, schedules, webhooks, proxies."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ScrapeTemplate(Base):
    """Reusable scrape configuration templates."""
    __tablename__ = "scrape_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    url_pattern = Column(String(2000), default="")
    config = Column(JSON, default=dict, nullable=False)
    scrape_type = Column(String(50), default="single")
    tags = Column(JSON, default=list)
    use_count = Column(Integer, default=0)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "description": self.description,
            "url_pattern": self.url_pattern,
            "config": self.config,
            "scrape_type": self.scrape_type,
            "tags": self.tags or [],
            "use_count": self.use_count,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ScrapeSchedule(Base):
    """Periodic scraping schedules."""
    __tablename__ = "scrape_schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("scrape_templates.id"), nullable=True)
    name = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False)
    config = Column(JSON, default=dict)
    cron_expression = Column(String(100), default="0 2 * * *")
    interval_minutes = Column(Integer, default=1440)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    run_count = Column(Integer, default=0)
    last_status = Column(String(50), default="pending")
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "template_id": str(self.template_id) if self.template_id else None,
            "name": self.name,
            "url": self.url,
            "config": self.config,
            "cron_expression": self.cron_expression,
            "interval_minutes": self.interval_minutes,
            "is_active": self.is_active,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "run_count": self.run_count,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScrapeWebhookConfig(Base):
    """Webhook configurations for scrape notifications."""
    __tablename__ = "scrape_webhook_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False)
    webhook_type = Column(String(50), default="generic")
    events = Column(JSON, default=lambda: ["scrape.complete", "scrape.error"])
    headers = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    secret = Column(String(200), nullable=True)
    last_triggered_at = Column(DateTime, nullable=True)
    last_status = Column(Integer, nullable=True)
    trigger_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "url": self.url,
            "webhook_type": self.webhook_type,
            "events": self.events or [],
            "is_active": self.is_active,
            "last_triggered_at": self.last_triggered_at.isoformat() if self.last_triggered_at else None,
            "last_status": self.last_status,
            "trigger_count": self.trigger_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScrapeProxyConfig(Base):
    """Proxy configurations for scraping."""
    __tablename__ = "scrape_proxy_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    proxy_url = Column(String(2000), nullable=False)
    proxy_type = Column(String(50), default="http")
    username = Column(String(200), nullable=True)
    password_encrypted = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    is_healthy = Column(Boolean, default=True)
    last_checked_at = Column(DateTime, nullable=True)
    avg_response_ms = Column(Float, default=0.0)
    total_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "name": self.name,
            "proxy_url": self.proxy_url,
            "proxy_type": self.proxy_type,
            "is_active": self.is_active,
            "is_healthy": self.is_healthy,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "avg_response_ms": self.avg_response_ms,
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ScrapeCache(Base):
    """Content cache for deduplication."""
    __tablename__ = "scrape_cache"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(2000), nullable=False, index=True)
    content_hash = Column(String(64), nullable=False, index=True)
    title = Column(String(500), default="")
    cached_data = Column(JSON, default=dict)
    row_count = Column(Integer, default=0)
    hit_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "url": self.url,
            "content_hash": self.content_hash,
            "title": self.title,
            "row_count": self.row_count,
            "hit_count": self.hit_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
