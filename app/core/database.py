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
        # ── External Data tables ─────────────────────────────────────────
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS external_data_sources (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL UNIQUE,
                slug VARCHAR(100) NOT NULL UNIQUE,
                base_url VARCHAR(500) NOT NULL,
                source_type VARCHAR(20) NOT NULL DEFAULT 'api',
                license VARCHAR(255),
                license_url VARCHAR(500),
                rate_limit_per_min INTEGER DEFAULT 60,
                requires_api_key BOOLEAN DEFAULT FALSE,
                api_key_env_var VARCHAR(100),
                is_active BOOLEAN DEFAULT TRUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS external_dataset_cache (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source_id UUID NOT NULL REFERENCES external_data_sources(id),
                query_hash VARCHAR(64) NOT NULL,
                title VARCHAR(500) NOT NULL,
                description TEXT,
                preview_data JSONB DEFAULT '[]'::jsonb,
                full_data_path VARCHAR(500),
                row_count INTEGER DEFAULT 0,
                column_count INTEGER DEFAULT 0,
                columns JSONB DEFAULT '[]'::jsonb,
                source_url VARCHAR(500),
                license_note TEXT,
                fetched_at TIMESTAMP DEFAULT NOW(),
                expires_at TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS external_data_search_logs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL REFERENCES users(id),
                query_text VARCHAR(500) NOT NULL,
                matched_source_id UUID REFERENCES external_data_sources(id),
                selected_result_id UUID REFERENCES external_dataset_cache(id),
                imported BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_data_sources_slug ON external_data_sources (slug)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_data_sources_is_active ON external_data_sources (is_active)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_dataset_cache_source_id ON external_dataset_cache (source_id)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_dataset_cache_query_hash ON external_dataset_cache (query_hash)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_dataset_cache_expires_at ON external_dataset_cache (expires_at)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_data_search_logs_user_id ON external_data_search_logs (user_id)"))
        await conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_external_data_search_logs_created_at ON external_data_search_logs (created_at)"))
        # Scrape jobs table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scrape_jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL,
                url VARCHAR(1000) NOT NULL,
                title VARCHAR(500),
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                raw_row_count INTEGER DEFAULT 0,
                clean_row_count INTEGER DEFAULT 0,
                column_count INTEGER DEFAULT 0,
                duplicates_removed INTEGER DEFAULT 0,
                tables_data JSONB DEFAULT '[]'::jsonb,
                lists_data JSONB DEFAULT '[]'::jsonb,
                metadata JSONB DEFAULT '{}'::jsonb,
                processed_data JSONB DEFAULT '[]'::jsonb,
                columns_typed JSONB DEFAULT '{}'::jsonb,
                columns_renamed JSONB DEFAULT '{}'::jsonb,
                quality_score FLOAT DEFAULT 0.0,
                quality_issues JSONB DEFAULT '[]'::jsonb,
                clusters JSONB DEFAULT '{}'::jsonb,
                ml_processing_applied JSONB DEFAULT '[]'::jsonb,
                advanced_analysis JSONB DEFAULT '{}'::jsonb,
                sentiment_analysis JSONB DEFAULT '{}'::jsonb,
                pattern_analysis JSONB DEFAULT '{}'::jsonb,
                scrape_metadata JSONB DEFAULT '{}'::jsonb,
                content_hash VARCHAR(64),
                error_message TEXT,
                scrape_type VARCHAR(30) DEFAULT 'single',
                batch_results JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT NOW(),
                scraped_at TIMESTAMP,
                processed_at TIMESTAMP
            )
        """))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scrape_jobs_user_id ON scrape_jobs (user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scrape_jobs_status ON scrape_jobs (status)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_scrape_jobs_created_at ON scrape_jobs (created_at)"))
        # Add missing columns to existing scrape_jobs table
        for col_def in [
            "ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS advanced_analysis JSONB DEFAULT '{}'::jsonb",
            "ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS sentiment_analysis JSONB DEFAULT '{}'::jsonb",
            "ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS pattern_analysis JSONB DEFAULT '{}'::jsonb",
            "ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS scrape_metadata JSONB DEFAULT '{}'::jsonb",
            "ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS scrape_type VARCHAR(30) DEFAULT 'single'",
            "ALTER TABLE scrape_jobs ADD COLUMN IF NOT EXISTS batch_results JSONB DEFAULT '[]'::jsonb",
        ]:
            try:
                await conn.execute(text(col_def))
            except Exception:
                pass  # Column already exists
        # Seed default external data sources
        await conn.execute(text("""
            INSERT INTO external_data_sources (id, name, slug, base_url, source_type,
                license, license_url, rate_limit_per_min, requires_api_key, api_key_env_var,
                is_active, description, created_at)
            SELECT gen_random_uuid(), 'BPS - Badan Pusat Statistik', 'bps',
                'https://webapi.bps.go.id/v1/api', 'api',
                'Data publik pemerintah Indonesia', 'https://webapi.bps.go.id/documentation',
                120, TRUE, 'BPS_API_KEY', TRUE,
                'Data statistik resmi Indonesia (ekonomi, demografi, harga)', NOW()
            WHERE NOT EXISTS (SELECT 1 FROM external_data_sources WHERE slug = 'bps')
        """))
        await conn.execute(text("""
            INSERT INTO external_data_sources (id, name, slug, base_url, source_type,
                license, license_url, rate_limit_per_min, requires_api_key, api_key_env_var,
                is_active, description, created_at)
            SELECT gen_random_uuid(), 'World Bank Open Data', 'worldbank',
                'https://api.worldbank.org/v2', 'api',
                'CC-BY 4.0', 'https://datahelpdesk.worldbank.org/knowledgebase/articles/889392',
                200, FALSE, NULL, TRUE,
                '16,000+ indikator dari 200+ negara (ekonomi, pendidikan, kemiskinan)', NOW()
            WHERE NOT EXISTS (SELECT 1 FROM external_data_sources WHERE slug = 'worldbank')
        """))
        await conn.execute(text("""
            INSERT INTO external_data_sources (id, name, slug, base_url, source_type,
                license, license_url, rate_limit_per_min, requires_api_key, api_key_env_var,
                is_active, description, created_at)
            SELECT gen_random_uuid(), 'data.go.id - Satu Data Indonesia', 'datagoid',
                'https://data.go.id/api/3/action', 'api',
                'Data pemerintah Indonesia', 'https://data.go.id',
                30, FALSE, NULL, FALSE,
                'API CKAN offline (portal sedang kurasi ulang). Unduh manual di https://data.go.id/dataset', NOW()
            WHERE NOT EXISTS (SELECT 1 FROM external_data_sources WHERE slug = 'datagoid')
        """))
