from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.models.user import User
from app.services.system_health import check_system_health

router = APIRouter(prefix="/admin", tags=["System Health"])


@router.get("/system-health")
async def system_health(
    current_user: User = Depends(require_admin),
):
    """Internal admin dashboard: real-time status of Celery, Redis, DB, storage."""
    return await check_system_health()
