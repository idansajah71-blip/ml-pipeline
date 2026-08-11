"""Scrape Template — Save and reuse scrape configurations (DB-backed)."""
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.scrape_config import ScrapeTemplate as ScrapeTemplateModel


class TemplateManager:

    def __init__(self, db: AsyncSession = None):
        self._db = db

    def _set_db(self, db: AsyncSession):
        self._db = db

    async def create(
        self,
        user_id: str,
        name: str,
        description: str = "",
        scrape_type: str = "single",
        config: Dict = None,
        tags: List[str] = None,
        is_public: bool = False,
    ) -> Dict:
        template = ScrapeTemplateModel(
            id=uuid.uuid4(),
            user_id=uuid.UUID(user_id) if len(user_id) == 36 else user_id,
            name=name,
            description=description,
            scrape_type=scrape_type,
            config=config or {},
            tags=tags or [],
            is_public=is_public,
        )
        self._db.add(template)
        await self._db.commit()
        await self._db.refresh(template)
        return template.to_dict()

    async def get(self, template_id: str) -> Optional[Dict]:
        result = await self._db.execute(
            select(ScrapeTemplateModel).where(ScrapeTemplateModel.id == template_id)
        )
        template = result.scalar_one_or_none()
        return template.to_dict() if template else None

    async def list_user(self, user_id: str, skip: int = 0, limit: int = 50) -> List[Dict]:
        result = await self._db.execute(
            select(ScrapeTemplateModel)
            .where(ScrapeTemplateModel.user_id == user_id)
            .order_by(ScrapeTemplateModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return [t.to_dict() for t in result.scalars().all()]

    async def list_public(self, skip: int = 0, limit: int = 50) -> List[Dict]:
        result = await self._db.execute(
            select(ScrapeTemplateModel)
            .where(ScrapeTemplateModel.is_public == True)
            .order_by(ScrapeTemplateModel.use_count.desc())
            .offset(skip)
            .limit(limit)
        )
        return [t.to_dict() for t in result.scalars().all()]

    async def update(self, template_id: str, **kwargs) -> Optional[Dict]:
        result = await self._db.execute(
            select(ScrapeTemplateModel).where(ScrapeTemplateModel.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            return None
        for key, value in kwargs.items():
            if hasattr(template, key) and key not in ("id", "user_id", "created_at"):
                setattr(template, key, value)
        template.updated_at = datetime.utcnow()
        await self._db.commit()
        await self._db.refresh(template)
        return template.to_dict()

    async def delete(self, template_id: str) -> bool:
        result = await self._db.execute(
            select(ScrapeTemplateModel).where(ScrapeTemplateModel.id == template_id)
        )
        template = result.scalar_one_or_none()
        if not template:
            return False
        await self._db.delete(template)
        await self._db.commit()
        return True

    async def record_usage(self, template_id: str) -> None:
        result = await self._db.execute(
            select(ScrapeTemplateModel).where(ScrapeTemplateModel.id == template_id)
        )
        template = result.scalar_one_or_none()
        if template:
            template.use_count = (template.use_count or 0) + 1
            await self._db.commit()

    async def clone(self, template_id: str, new_name: str = None) -> Optional[Dict]:
        original = await self.get(template_id)
        if not original:
            return None
        return await self.create(
            user_id=original["user_id"],
            name=new_name or f"{original['name']} (copy)",
            description=original.get("description", ""),
            scrape_type=original.get("scrape_type", "single"),
            config=original.get("config", {}),
            tags=original.get("tags", []),
            is_public=False,
        )

    async def search(self, query: str, user_id: str = None, limit: int = 20) -> List[Dict]:
        q = f"%{query}%"
        sql = text("""
            SELECT * FROM scrape_templates
            WHERE (name ILIKE :q OR description ILIKE :q)
            AND (:user_id IS NULL OR user_id = :user_id OR is_public = true)
            ORDER BY use_count DESC
            LIMIT :limit
        """)
        result = await self._db.execute(sql, {"q": q, "user_id": user_id, "limit": limit})
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    async def get_popular(self, limit: int = 10) -> List[Dict]:
        result = await self._db.execute(
            select(ScrapeTemplateModel)
            .order_by(ScrapeTemplateModel.use_count.desc())
            .limit(limit)
        )
        return [t.to_dict() for t in result.scalars().all()]

    async def get_recent(self, limit: int = 10) -> List[Dict]:
        result = await self._db.execute(
            select(ScrapeTemplateModel)
            .order_by(ScrapeTemplateModel.created_at.desc())
            .limit(limit)
        )
        return [t.to_dict() for t in result.scalars().all()]

    async def get_tags(self) -> List[Dict]:
        sql = text("""
            SELECT jsonb_array_elements_text(tags) as tag, COUNT(*) as count
            FROM scrape_templates
            GROUP BY tag
            ORDER BY count DESC
        """)
        result = await self._db.execute(sql)
        return [{"tag": row["tag"], "count": row["count"]} for row in result.mappings().all()]
