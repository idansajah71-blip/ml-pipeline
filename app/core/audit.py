import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Column, String, DateTime, JSON, Text
from sqlalchemy.dialects.postgresql import UUID
import json

from app.core.database import Base
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(100), nullable=False)
    user_id = Column(String(100))
    user_email = Column(String(255))
    user_role = Column(String(50))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    request_method = Column(String(10))
    request_path = Column(String(500))
    response_status = Column(String(10))
    duration_ms = Column(String(20))


class AuditEventType:
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_REGISTER = "auth.register"
    AUTH_FAILED = "auth.failed"
    AUTH_PASSWORD_CHANGE = "auth.password_change"

    DATASET_UPLOAD = "dataset.upload"
    DATASET_DELETE = "dataset.delete"
    DATASET_ACCESS = "dataset.access"

    MODEL_CREATE = "model.create"
    MODEL_TRAIN = "model.train"
    MODEL_DEPLOY = "model.deploy"
    MODEL_DELETE = "model.delete"
    MODEL_PREDICT = "model.predict"

    EXPERIMENT_START = "experiment.start"
    EXPERIMENT_COMPLETE = "experiment.complete"
    EXPERIMENT_FAIL = "experiment.fail"

    AB_TEST_CREATE = "ab_test.create"
    AB_TEST_START = "ab_test.start"
    AB_TEST_STOP = "ab_test.stop"

    API_KEY_CREATE = "api_key.create"
    API_KEY_REVOKE = "api_key.revoke"

    SYSTEM_ERROR = "system.error"
    SECURITY_VIOLATION = "security.violation"


class AuditLogger:
    def __init__(self):
        self.logger = logger

    async def log(
        self,
        db: AsyncSession,
        event_type: str,
        action: str,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_method: Optional[str] = None,
        request_path: Optional[str] = None,
        response_status: Optional[str] = None,
        duration_ms: Optional[str] = None,
    ):
        audit_entry = AuditLog(
            event_type=event_type,
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request_method=request_method,
            request_path=request_path,
            response_status=response_status,
            duration_ms=duration_ms,
        )

        db.add(audit_entry)

        self.logger.info(
            f"Audit: {event_type} - {action}",
            event_type=event_type,
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
        )

    async def log_auth_event(
        self,
        db: AsyncSession,
        event_type: str,
        user_id: str,
        user_email: str,
        user_role: str,
        ip_address: Optional[str] = None,
        success: bool = True,
        details: Optional[Dict] = None,
    ):
        await self.log(
            db=db,
            event_type=event_type,
            action=event_type.split(".")[-1],
            user_id=user_id,
            user_email=user_email,
            user_role=user_role,
            ip_address=ip_address,
            details=details or {"success": success},
        )

    async def log_model_event(
        self,
        db: AsyncSession,
        event_type: str,
        user_id: str,
        model_id: str,
        model_name: str,
        details: Optional[Dict] = None,
    ):
        await self.log(
            db=db,
            event_type=event_type,
            action=event_type.split(".")[-1],
            user_id=user_id,
            resource_type="model",
            resource_id=model_id,
            details=details or {"model_name": model_name},
        )

    async def log_dataset_event(
        self,
        db: AsyncSession,
        event_type: str,
        user_id: str,
        dataset_id: str,
        dataset_name: str,
        details: Optional[Dict] = None,
    ):
        await self.log(
            db=db,
            event_type=event_type,
            action=event_type.split(".")[-1],
            user_id=user_id,
            resource_type="dataset",
            resource_id=dataset_id,
            details=details or {"dataset_name": dataset_name},
        )

    async def log_security_event(
        self,
        db: AsyncSession,
        action: str,
        ip_address: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        await self.log(
            db=db,
            event_type=AuditEventType.SECURITY_VIOLATION,
            action=action,
            ip_address=ip_address,
            details=details,
        )


audit_logger = AuditLogger()
