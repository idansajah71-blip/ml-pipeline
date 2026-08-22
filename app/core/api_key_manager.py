import secrets
import hashlib
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import HTTPException

from app.models.user import User
from app.core.logging import get_logger

logger = get_logger(__name__)


class APIKeyManager:
    def __init__(self):
        self.key_prefix = "mlp_"
        self.key_length = 48

    def generate_api_key(self) -> tuple[str, str]:
        raw_key = secrets.token_urlsafe(self.key_length)
        api_key = f"{self.key_prefix}{raw_key}"
        key_hash = self._hash_key(api_key)
        return api_key, key_hash

    def _hash_key(self, api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    def validate_key_format(self, api_key: str) -> bool:
        if not api_key.startswith(self.key_prefix):
            return False
        if len(api_key) < 50:
            return False
        return True

    async def create_api_key(self, db: AsyncSession, user_id: UUID) -> str:
        user = await self._get_user(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        api_key, key_hash = self.generate_api_key()

        user.api_key = key_hash
        await db.flush()

        logger.info(
            f"API key created for user {user_id}",
            user_id=str(user_id),
        )

        return api_key

    async def revoke_api_key(self, db: AsyncSession, user_id: UUID) -> bool:
        user = await self._get_user(db, user_id)
        if not user:
            return False

        user.api_key = None
        await db.flush()

        logger.info(
            f"API key revoked for user {user_id}",
            user_id=str(user_id),
        )

        return True

    async def validate_api_key(self, db: AsyncSession, api_key: str) -> Optional[User]:
        if not self.validate_key_format(api_key):
            return None

        key_hash = self._hash_key(api_key)

        result = await db.execute(
            select(User).where(
                and_(
                    User.api_key == key_hash,
                    User.is_active == True,
                )
            )
        )
        user = result.scalar_one_or_none()

        if user:
            logger.info(
                f"API key validated for user {user.id}",
                user_id=str(user.id),
            )

        return user

    async def rotate_api_key(self, db: AsyncSession, user_id: UUID) -> str:
        await self.revoke_api_key(db, user_id)
        new_key = await self.create_api_key(db, user_id)

        logger.info(
            f"API key rotated for user {user_id}",
            user_id=str(user_id),
        )

        return new_key

    async def _get_user(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()


api_key_manager = APIKeyManager()
