from typing import Optional
from uuid import UUID
from fastapi import Request


class AuditService:
    def __init__(self, session):
        self.session = session

    async def log(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        user_id: Optional[UUID] = None,
        request: Optional[Request] = None,
    ):
        from app.models.audit_log import AuditLog

        ip_address = None
        user_agent = None
        if request:
            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")

        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry
