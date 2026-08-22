import uuid
from sqlalchemy import Column, String, Enum, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base
from app.core.utils import utcnow_naive


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    DATA_SCIENTIST = "data_scientist"
    USER = "user"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    role = Column(Enum(UserRole, values_callable=lambda x: [e.value for e in x]), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    api_key = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, default=utcnow_naive)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    datasets = relationship("Dataset", back_populates="owner")
    models = relationship("MLModel", back_populates="owner")
    experiments = relationship("Experiment", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")
