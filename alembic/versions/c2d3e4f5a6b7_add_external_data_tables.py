"""add external data tables: sources, cache, search logs

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-08-08 21:30:00.000000

Creates the 3 tables for external data search & import feature.
All statements use IF NOT EXISTS for idempotent safety.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c2d3e4f5a6b7'
down_revision: Union[str, Sequence[str], None] = 'b1c2d3e4f5a6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name):
    return conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    ).scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # ── external_data_sources ────────────────────────────────────────────
    if not _table_exists(conn, 'external_data_sources'):
        op.create_table(
            'external_data_sources',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False, unique=True),
            sa.Column('slug', sa.String(100), nullable=False, unique=True),
            sa.Column('base_url', sa.String(500), nullable=False),
            sa.Column('source_type', sa.String(20), nullable=False, server_default='api'),
            sa.Column('license', sa.String(255), nullable=True),
            sa.Column('license_url', sa.String(500), nullable=True),
            sa.Column('rate_limit_per_min', sa.Integer(), server_default='60'),
            sa.Column('requires_api_key', sa.Boolean(), server_default='false'),
            sa.Column('api_key_env_var', sa.String(100), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
    else:
        # Add missing columns if table exists without them
        for col, defn in [
            ("slug", "VARCHAR(100)"),
            ("source_type", "VARCHAR(20) DEFAULT 'api'"),
            ("license", "VARCHAR(255)"),
            ("license_url", "VARCHAR(500)"),
            ("rate_limit_per_min", "INTEGER DEFAULT 60"),
            ("requires_api_key", "BOOLEAN DEFAULT FALSE"),
            ("api_key_env_var", "VARCHAR(100)"),
            ("description", "TEXT"),
        ]:
            op.execute(
                sa.text(
                    f"DO $$ BEGIN "
                    f"    ALTER TABLE external_data_sources ADD COLUMN IF NOT EXISTS {col} {defn}; "
                    f"EXCEPTION WHEN duplicate_column THEN null; "
                    f"END $$;"
                )
            )

    # ── external_dataset_cache ───────────────────────────────────────────
    if not _table_exists(conn, 'external_dataset_cache'):
        op.create_table(
            'external_dataset_cache',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('source_id', postgresql.UUID(as_uuid=True),
                       sa.ForeignKey('external_data_sources.id'), nullable=False),
            sa.Column('query_hash', sa.String(64), nullable=False),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('preview_data', sa.JSON(), server_default='[]'),
            sa.Column('full_data_path', sa.String(500), nullable=True),
            sa.Column('row_count', sa.Integer(), server_default='0'),
            sa.Column('column_count', sa.Integer(), server_default='0'),
            sa.Column('columns', sa.JSON(), server_default='[]'),
            sa.Column('source_url', sa.String(500), nullable=True),
            sa.Column('license_note', sa.Text(), nullable=True),
            sa.Column('fetched_at', sa.DateTime(), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=True),
        )
    else:
        for col, defn in [
            ("query_hash", "VARCHAR(64)"),
            ("preview_data", "JSONB DEFAULT '[]'::jsonb"),
            ("full_data_path", "VARCHAR(500)"),
            ("column_count", "INTEGER DEFAULT 0"),
            ("columns", "JSONB DEFAULT '[]'::jsonb"),
            ("source_url", "VARCHAR(500)"),
            ("license_note", "TEXT"),
            ("expires_at", "TIMESTAMP"),
        ]:
            op.execute(
                sa.text(
                    f"DO $$ BEGIN "
                    f"    ALTER TABLE external_dataset_cache ADD COLUMN IF NOT EXISTS {col} {defn}; "
                    f"EXCEPTION WHEN duplicate_column THEN null; "
                    f"END $$;"
                )
            )

    # ── external_data_search_logs ────────────────────────────────────────
    if not _table_exists(conn, 'external_data_search_logs'):
        op.create_table(
            'external_data_search_logs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                       sa.ForeignKey('users.id'), nullable=False),
            sa.Column('query_text', sa.String(500), nullable=False),
            sa.Column('matched_source_id', postgresql.UUID(as_uuid=True),
                       sa.ForeignKey('external_data_sources.id'), nullable=True),
            sa.Column('selected_result_id', postgresql.UUID(as_uuid=True),
                       sa.ForeignKey('external_dataset_cache.id'), nullable=True),
            sa.Column('imported', sa.Boolean(), server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )
    else:
        for col, defn in [
            ("query_text", "VARCHAR(500)"),
            ("matched_source_id", f"UUID REFERENCES external_data_sources(id)"),
            ("selected_result_id", f"UUID REFERENCES external_dataset_cache(id)"),
            ("imported", "BOOLEAN DEFAULT FALSE"),
        ]:
            op.execute(
                sa.text(
                    f"DO $$ BEGIN "
                    f"    ALTER TABLE external_data_search_logs ADD COLUMN IF NOT EXISTS {col} {defn}; "
                    f"EXCEPTION WHEN duplicate_column THEN null; "
                    f"END $$;"
                )
            )

    # ── Indexes ──────────────────────────────────────────────────────────
    for name, table, cols in [
        ("ix_external_data_sources_slug", "external_data_sources", ["slug"]),
        ("ix_external_data_sources_is_active", "external_data_sources", ["is_active"]),
        ("ix_external_dataset_cache_source_id", "external_dataset_cache", ["source_id"]),
        ("ix_external_dataset_cache_query_hash", "external_dataset_cache", ["query_hash"]),
        ("ix_external_dataset_cache_expires_at", "external_dataset_cache", ["expires_at"]),
        ("ix_external_data_search_logs_user_id", "external_data_search_logs", ["user_id"]),
        ("ix_external_data_search_logs_created_at", "external_data_search_logs", ["created_at"]),
    ]:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({', '.join(cols)})")

    # ── Seed default sources ─────────────────────────────────────────────
    for slug, name, url, desc, lic, lic_url, needs_key, env_var, rate in [
        ("bps", "BPS - Badan Pusat Statistik", "https://webapi.bps.go.id/v1/api",
         "Data statistik resmi Indonesia", "Data publik pemerintah Indonesia",
         "https://webapi.bps.go.id/documentation", True, "BPS_API_KEY", 120),
        ("worldbank", "World Bank Open Data", "https://api.worldbank.org/v2",
         "16,000+ indikator dari 200+ negara", "CC-BY 4.0",
         "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392", False, None, 200),
    ]:
        op.execute(f"""
            INSERT INTO external_data_sources (id, name, slug, base_url, source_type,
                license, license_url, rate_limit_per_min, requires_api_key, api_key_env_var,
                is_active, description, created_at)
            SELECT gen_random_uuid(), '{name}', '{slug}', '{url}', 'api',
                '{lic}', '{lic_url}', {rate}, {str(needs_key).upper()},
                {f"'{env_var}'" if env_var else 'NULL'},
                TRUE, '{desc}', NOW()
            WHERE NOT EXISTS (SELECT 1 FROM external_data_sources WHERE slug = '{slug}')
        """)


def downgrade() -> None:
    # ── Drop indexes ──
    for name in [
        "ix_external_data_search_logs_created_at",
        "ix_external_data_search_logs_user_id",
        "ix_external_dataset_cache_expires_at",
        "ix_external_dataset_cache_query_hash",
        "ix_external_dataset_cache_source_id",
        "ix_external_data_sources_is_active",
        "ix_external_data_sources_slug",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {name}")

    # ── Drop tables (reverse dependency order) ──
    op.execute("DROP TABLE IF EXISTS external_data_search_logs")
    op.execute("DROP TABLE IF EXISTS external_dataset_cache")
    op.execute("DROP TABLE IF EXISTS external_data_sources")
