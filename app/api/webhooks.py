from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import httpx
import hashlib
import hmac
import json

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.webhook import Webhook, WebhookLog

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str]
    secret: Optional[str] = None
    headers: dict = {}


class WebhookResponse(BaseModel):
    id: UUID
    name: str
    url: str
    events: list
    is_active: int
    last_triggered_at: Optional[str]
    last_status_code: Optional[int]
    created_at: str
    model_config = {"from_attributes": True}


class WebhookLogResponse(BaseModel):
    id: UUID
    webhook_id: UUID
    event: str
    payload: dict
    response_status: Optional[int]
    success: int
    duration_ms: int
    created_at: str
    model_config = {"from_attributes": True}


@router.post("", response_model=WebhookResponse, status_code=201)
async def create_webhook(
    data: WebhookCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    webhook = Webhook(
        name=data.name,
        url=data.url,
        events=data.events,
        secret=data.secret,
        headers=data.headers,
        owner_id=current_user.id,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return WebhookResponse.model_validate(webhook)


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Webhook).where(Webhook.owner_id == current_user.id)
    )
    webhooks = list(result.scalars().all())
    return [WebhookResponse.model_validate(w) for w in webhooks]


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Webhook).where(Webhook.id == webhook_id, Webhook.owner_id == current_user.id)
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    await db.delete(webhook)
    return {"status": "deleted"}


@router.get("/{webhook_id}/logs", response_model=List[WebhookLogResponse])
async def list_webhook_logs(
    webhook_id: UUID,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WebhookLog)
        .where(WebhookLog.webhook_id == webhook_id)
        .order_by(WebhookLog.created_at.desc())
        .offset(skip).limit(limit)
    )
    logs = list(result.scalars().all())
    return [WebhookLogResponse.model_validate(l) for l in logs]


async def trigger_webhooks(db, event: str, payload: dict):
    result = await db.execute(
        select(Webhook).where(Webhook.is_active == 1)
    )
    webhooks = list(result.scalars().all())

    for webhook in webhooks:
        if event not in webhook.events and "*" not in webhook.events:
            continue

        headers = {**webhook.headers, "Content-Type": "application/json"}
        if webhook.secret:
            body = json.dumps(payload, default=str)
            signature = hmac.new(webhook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = signature

        log = WebhookLog(
            webhook_id=webhook.id,
            event=event,
            payload=payload,
        )

        try:
            import time
            start = time.perf_counter()
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(webhook.url, json=payload, headers=headers)
                duration = int((time.perf_counter() - start) * 1000)

            log.response_status = response.status_code
            log.success = 1 if response.status_code < 400 else 0
            log.duration_ms = duration
            webhook.last_triggered_at = datetime.utcnow()
            webhook.last_status_code = response.status_code

        except Exception as e:
            log.response_status = 0
            log.success = 0
            log.duration_ms = 0
            log.response_body = str(e)

        db.add(log)

    await db.flush()
