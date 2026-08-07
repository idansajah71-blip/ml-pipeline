from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Repair old databases missing fields required by current ORM definitions.
        await conn.execute(text(
            "ALTER TABLE datasets ADD COLUMN IF NOT EXISTS is_archived BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS task_id VARCHAR(255)"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS stage VARCHAR(50) DEFAULT 'development'"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS parent_model_id UUID REFERENCES models(id)"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS model_card JSONB DEFAULT '{}'::jsonb"
        ))
        await conn.execute(text(
            "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS feedback_correct BOOLEAN"
        ))
        await conn.execute(text(
            "ALTER TABLE predictions ADD COLUMN IF NOT EXISTS feedback_comment VARCHAR(500)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_datasets_owner_id ON datasets (owner_id)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_datasets_created_at ON datasets (created_at)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_datasets_name ON datasets (name)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_models_stage ON models (stage)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_models_status ON models (status)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_models_owner_id ON models (owner_id)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_models_algorithm ON models (algorithm)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_models_created_at ON models (created_at)"))
