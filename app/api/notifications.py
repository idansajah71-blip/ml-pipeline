from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import httpx

from app.core.database import get_db
from app.core.security import get_current_active_user, require_data_scientist
from app.core.redis import cache_get, cache_set
from app.models.user import User
from app.models.model import MLModel
from app.models.prediction import Prediction

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class WebhookCreate(BaseModel):
    url: HttpUrl
    events: List[str] = ["training.completed", "training.failed"]
    secret: Optional[str] = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    is_active: bool
    created_at: str


class NotificationResponse(BaseModel):
    message: str
    notification_id: str


webhooks_db: Dict[str, Dict] = {}


async def send_webhook(url: str, event: str, payload: Dict[str, Any], secret: Optional[str] = None):
    try:
        headers = {"Content-Type": "application/json"}
        if secret:
            import hmac
            import hashlib
            import json
            signature = hmac.new(
                secret.encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Secret"] = signature

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=headers, timeout=10)
            return response.status_code == 200
    except Exception as e:
        print(f"Webhook delivery failed: {e}")
        return False


@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    webhook: WebhookCreate,
    current_user: User = Depends(require_data_scientist),
):
    import secrets
    webhook_id = str(secrets.token_urlsafe(16))

    webhooks_db[webhook_id] = {
        "id": webhook_id,
        "url": str(webhook.url),
        "events": webhook.events,
        "secret": webhook.secret,
        "user_id": str(current_user.id),
        "is_active": True,
        "created_at": datetime.utcnow().isoformat(),
    }

    return WebhookResponse(
        id=webhook_id,
        url=str(webhook.url),
        events=webhook.events,
        is_active=True,
        created_at=datetime.utcnow().isoformat(),
    )


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    current_user: User = Depends(require_data_scientist),
):
    user_webhooks = [
        wh for wh in webhooks_db.values()
        if wh["user_id"] == str(current_user.id)
    ]
    return [
        WebhookResponse(
            id=wh["id"],
            url=wh["url"],
            events=wh["events"],
            is_active=wh["is_active"],
            created_at=wh["created_at"],
        )
        for wh in user_webhooks
    ]


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: User = Depends(require_data_scientist),
):
    if webhook_id not in webhooks_db:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if webhooks_db[webhook_id]["user_id"] != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    del webhooks_db[webhook_id]
    return {"message": "Webhook deleted successfully"}


@router.post("/trigger/{event}")
async def trigger_notification(
    event: str,
    payload: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_data_scientist),
):
    matching_webhooks = [
        wh for wh in webhooks_db.values()
        if wh["user_id"] == str(current_user.id)
        and event in wh["events"]
        and wh["is_active"]
    ]

    sent_count = 0
    for wh in matching_webhooks:
        background_tasks.add_task(
            send_webhook,
            url=wh["url"],
            event=event,
            payload=payload,
            secret=wh.get("secret"),
        )
        sent_count += 1

    return {
        "message": f"Notification triggered for event: {event}",
        "webhooks_notified": sent_count,
    }


class DriftCheckRequest(BaseModel):
    model_id: UUID
    reference_window: int = 100
    current_window: int = 50
    threshold: float = 0.1


class DriftCheckResponse(BaseModel):
    model_id: str
    drift_detected: bool
    drift_score: float
    reference_mean_confidence: float
    current_mean_confidence: float
    details: Dict[str, Any]


@router.post("/drift-check", response_model=DriftCheckResponse)
async def check_concept_drift(
    request: DriftCheckRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func
    from sqlalchemy import desc

    model_result = await db.execute(
        select(MLModel).where(MLModel.id == request.model_id)
    )
    model = model_result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    ref_result = await db.execute(
        select(Prediction)
        .where(Prediction.model_id == request.model_id)
        .order_by(desc(Prediction.created_at))
        .offset(request.current_window)
        .limit(request.reference_window)
    )
    reference_predictions = list(ref_result.scalars().all())

    curr_result = await db.execute(
        select(Prediction)
        .where(Prediction.model_id == request.model_id)
        .order_by(desc(Prediction.created_at))
        .limit(request.current_window)
    )
    current_predictions = list(curr_result.scalars().all())

    if not reference_predictions or not current_predictions:
        return DriftCheckResponse(
            model_id=str(request.model_id),
            drift_detected=False,
            drift_score=0.0,
            reference_mean_confidence=0.0,
            current_mean_confidence=0.0,
            details={"message": "Insufficient prediction data"},
        )

    ref_confidences = [p.confidence or 0 for p in reference_predictions if p.confidence is not None]
    curr_confidences = [p.confidence or 0 for p in current_predictions if p.confidence is not None]

    ref_mean = sum(ref_confidences) / len(ref_confidences) if ref_confidences else 0
    curr_mean = sum(curr_confidences) / len(curr_confidences) if curr_confidences else 0

    drift_score = abs(ref_mean - curr_mean)
    drift_detected = drift_score > request.threshold

    return DriftCheckResponse(
        model_id=str(request.model_id),
        drift_detected=drift_detected,
        drift_score=round(drift_score, 4),
        reference_mean_confidence=round(ref_mean, 4),
        current_mean_confidence=round(curr_mean, 4),
        details={
            "reference_samples": len(reference_predictions),
            "current_samples": len(current_predictions),
            "threshold": request.threshold,
            "recommendation": "Consider retraining the model" if drift_detected else "Model performance stable",
        },
    )
