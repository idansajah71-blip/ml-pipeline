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
        # Stage 1: Readiness scoring columns
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS readiness_score INTEGER DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS readiness_label VARCHAR(50)"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS readiness_details JSONB DEFAULT '{}'::jsonb"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS training_samples INTEGER DEFAULT 0"
        ))
        await conn.execute(text(
            "ALTER TABLE models ADD COLUMN IF NOT EXISTS cv_scores JSONB DEFAULT '[]'::jsonb"
        ))
        # Stage 2+3: model_shares table with rich metadata
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS model_shares (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_id UUID NOT NULL REFERENCES models(id),
                shared_by UUID NOT NULL REFERENCES users(id),
                shared_with_org VARCHAR(255),
                permission VARCHAR(50) DEFAULT 'read',
                is_public INTEGER DEFAULT 0,
                downloads INTEGER DEFAULT 0,
                rating FLOAT DEFAULT 0.0,
                rating_count INTEGER DEFAULT 0,
                tags JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT NOW(),
                use_case TEXT,
                limitations TEXT,
                example_inputs JSONB DEFAULT '[]'::jsonb,
                training_data_summary JSONB DEFAULT '{}'::jsonb,
                status VARCHAR(50) DEFAULT 'pending',
                review_note TEXT,
                lifecycle_stage VARCHAR(50) DEFAULT 'active',
                deprecation_note TEXT,
                deprecated_at TIMESTAMP,
                last_trained_at TIMESTAMP
            )
        """))
        # Stage 7 lifecycle columns (may be missing on older databases)
        for col_def in [
            "ALTER TABLE model_shares ADD COLUMN IF NOT EXISTS lifecycle_stage VARCHAR(50) DEFAULT 'active'",
            "ALTER TABLE model_shares ADD COLUMN IF NOT EXISTS deprecation_note TEXT",
            "ALTER TABLE model_shares ADD COLUMN IF NOT EXISTS deprecated_at TIMESTAMP",
            "ALTER TABLE model_shares ADD COLUMN IF NOT EXISTS last_trained_at TIMESTAMP",
        ]:
            await conn.execute(text(col_def))
        # model_reports table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS model_reports (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                share_id UUID NOT NULL,
                model_id UUID NOT NULL REFERENCES models(id),
                reported_by UUID NOT NULL REFERENCES users(id),
                reason VARCHAR(100) NOT NULL,
                description TEXT,
                status VARCHAR(50) DEFAULT 'pending',
                admin_note TEXT,
                reviewed_by UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT NOW(),
                reviewed_at TIMESTAMP
            )
        """))
        # Stage 5: model_feedback table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS model_feedback (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                model_id UUID NOT NULL REFERENCES models(id),
                share_id UUID,
                user_id UUID NOT NULL REFERENCES users(id),
                prediction_id UUID,
                rating INTEGER NOT NULL,
                comment TEXT,
                is_accurate BOOLEAN,
                actual_value VARCHAR(500),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_shares_model_id ON model_shares (model_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_shares_shared_by ON model_shares (shared_by)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_feedback_model_id ON model_feedback (model_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_feedback_user_id ON model_feedback (user_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_reports_share_id ON model_reports (share_id)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_reports_status ON model_reports (status)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_reports_reported_by ON model_reports (reported_by)"
        ))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_model_shares_is_public ON model_shares (is_public)"
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
