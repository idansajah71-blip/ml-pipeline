"""Shared utilities for Celery tasks — progress publishing and sync DB sessions."""
import json
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

_engine = None


def publish_progress(channel: str, data: dict, prefix: str = ""):
    """Publish a progress message to a Redis channel.

    If prefix is provided, the channel becomes ``f"{prefix}:{channel}"``.
    """
    full_channel = f"{prefix}:{channel}" if prefix else channel
    try:
        import redis as sync_redis
        r = sync_redis.from_url(_settings.REDIS_URL, decode_responses=True)
        r.publish(full_channel, json.dumps(data, default=str))
        r.close()
    except Exception as exc:
        logger.debug("publish_progress to %s failed: %s", full_channel, exc)


def get_sync_session():
    """Create a synchronous SQLAlchemy session using a shared engine."""
    global _engine
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    if _engine is None:
        _engine = create_engine(_settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=_engine)()
