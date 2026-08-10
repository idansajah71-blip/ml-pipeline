"""In-app notification API endpoints + helper utility for creating notifications."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.notification import Notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/in-app-notifications", tags=["In-App Notifications"])


# ── Helper: create notification (used by tasks, services, etc.) ──────────────

async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    notification_type: str,
    title: str,
    message: str,
    link: Optional[str] = None,
) -> Notification:
    """Create an in-app notification for a user. Called from training tasks, feedback, etc."""
    notif = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        link=link,
    )
    db.add(notif)
    await db.flush()
    return notif


def create_notification_sync(
    session,
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    link: Optional[str] = None,
) -> None:
    """Create notification using a synchronous session (for Celery tasks)."""
    from app.models.notification import Notification as NotifModel
    from uuid import UUID as _UUID
    notif = NotifModel(
        user_id=_UUID(user_id) if isinstance(user_id, str) else user_id,
        type=notification_type,
        title=title,
        message=message,
        link=link,
    )
    session.add(notif)
    session.commit()


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    message: str
    is_read: bool
    link: Optional[str] = None
    created_at: str


class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    skip: int = 0,
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user with unread count."""
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)
    stmt = stmt.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    # Total unread count
    count_stmt = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    )
    unread_result = await db.execute(count_stmt)
    unread_count = unread_result.scalar() or 0

    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id),
                type=n.type,
                title=n.title,
                message=n.message,
                is_read=n.is_read,
                link=n.link,
                created_at=n.created_at.isoformat() if n.created_at else "",
            )
            for n in notifications
        ],
        total=len(notifications),
        unread_count=unread_count,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the count of unread notifications (lightweight, for polling)."""
    stmt = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    )
    result = await db.execute(stmt)
    count = result.scalar() or 0
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    stmt = select(Notification).where(
        Notification.id == UUID(notification_id),
        Notification.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan")

    notif.is_read = True
    await db.flush()
    return {"status": "ok", "notification_id": notification_id}


@router.put("/read-all")
async def mark_all_as_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    stmt = update(Notification).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).values(is_read=True)
    await db.execute(stmt)
    await db.flush()
    return {"status": "ok", "message": "Semua notifikasi ditandai sudah dibaca"}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification."""
    stmt = select(Notification).where(
        Notification.id == UUID(notification_id),
        Notification.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notifikasi tidak ditemukan")

    await db.delete(notif)
    await db.flush()
    return {"status": "ok", "notification_id": notification_id}
