"""Webhook Notifier — Send notifications via webhook/Slack/Discord/Email (DB-backed)."""
import json
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import httpx

from app.models.scrape_config import ScrapeWebhookConfig

logger = logging.getLogger(__name__)


class WebhookNotifier:

    def __init__(self, db: AsyncSession = None):
        self._db = db

    def _set_db(self, db: AsyncSession):
        self._db = db

    async def configure(
        self,
        user_id: str,
        name: str,
        url: str,
        webhook_type: str = "generic",
        events: List[str] = None,
        headers: Dict = None,
        is_active: bool = True,
        secret: str = None,
    ) -> Dict:
        config = ScrapeWebhookConfig(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if len(user_id) == 36 else user_id,
            name=name,
            url=url,
            webhook_type=webhook_type,
            events=events or ["scrape.complete", "scrape.error"],
            headers=headers or {},
            is_active=is_active,
            secret=secret,
        )
        self._db.add(config)
        await self._db.commit()
        await self._db.refresh(config)
        return config.to_dict()

    async def list_user_webhooks(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Dict]:
        result = await self._db.execute(
            select(ScrapeWebhookConfig)
            .where(ScrapeWebhookConfig.user_id == user_id)
            .order_by(ScrapeWebhookConfig.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [w.to_dict() for w in result.scalars().all()]

    async def get_webhook(self, webhook_id: str) -> Optional[Dict]:
        result = await self._db.execute(
            select(ScrapeWebhookConfig).where(ScrapeWebhookConfig.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        return webhook.to_dict() if webhook else None

    async def update_webhook(self, webhook_id: str, **kwargs) -> Optional[Dict]:
        result = await self._db.execute(
            select(ScrapeWebhookConfig).where(ScrapeWebhookConfig.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            return None
        for key, value in kwargs.items():
            if hasattr(webhook, key) and key not in ("id", "user_id", "created_at"):
                setattr(webhook, key, value)
        await self._db.commit()
        await self._db.refresh(webhook)
        return webhook.to_dict()

    async def delete_webhook(self, webhook_id: str) -> bool:
        result = await self._db.execute(
            select(ScrapeWebhookConfig).where(ScrapeWebhookConfig.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            return False
        await self._db.delete(webhook)
        await self._db.commit()
        return True

    async def test_webhook(self, webhook_id: str) -> Dict:
        webhook = await self.get_webhook(webhook_id)
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        test_payload = {
            "event": "test",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Test webhook from ML Pipeline"},
        }

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(webhook["url"], json=test_payload)
                return {
                    "success": resp.status_code < 300,
                    "status_code": resp.status_code,
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def notify(self, event: str, data: dict, user_id: str = None) -> Dict:
        """Send notification to all matching webhooks for a user."""
        result = {"sent": 0, "failed": 0, "errors": []}

        query = select(ScrapeWebhookConfig).where(ScrapeWebhookConfig.is_active == True)
        if user_id:
            query = query.where(ScrapeWebhookConfig.user_id == user_id)

        db_result = await self._db.execute(query)
        webhooks = db_result.scalars().all()

        for wh in webhooks:
            if event not in (wh.events or []):
                continue

            payload = {
                "event": event,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data,
            }

            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    headers = wh.headers or {}
                    if wh.secret:
                        import hashlib
                        import hmac
                        sig = hmac.new(wh.secret.encode(), json.dumps(payload).encode(), hashlib.sha256).hexdigest()
                        headers["X-Webhook-Signature"] = f"sha256={sig}"

                    resp = await client.post(wh.url, json=payload, headers=headers)
                    wh.last_triggered_at = datetime.utcnow()
                    wh.last_status = resp.status_code

                    if resp.status_code < 300:
                        result["sent"] += 1
                        wh.trigger_count = (wh.trigger_count or 0) + 1
                    else:
                        result["failed"] += 1
                        result["errors"].append(f"{wh.name}: HTTP {resp.status_code}")
            except Exception as e:
                result["failed"] += 1
                result["errors"].append(f"{wh.name}: {str(e)}")

        await self._db.commit()
        return result
