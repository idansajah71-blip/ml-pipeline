"""add model_shares lifecycle columns, model_feedback, model_reports tables

Revision ID: b1c2d3e4f5a6
Revises: a9b8c7d6e5f4
Create Date: 2026-08-08 12:00:00.000000

Adds missing columns to model_shares and creates model_feedback/model_reports
tables that are defined in ORM but may not exist in the database.
All statements use IF NOT EXISTS for idempotent safety.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── model_shares: add missing lifecycle columns ──────────────────────
    lifecycle_cols = [
        ("lifecycle_stage", "VARCHAR(50) DEFAULT 'active'"),
        ("deprecation_note", "TEXT"),
        ("deprecated_at", "TIMESTAMP"),
        ("last_trained_at", "TIMESTAMP"),
    ]
    for col, definition in lifecycle_cols:
        op.execute(
            sa.text(
                f"DO $$ BEGIN "
                f"    ALTER TABLE model_shares ADD COLUMN IF NOT EXISTS {col} {definition}; "
                f"EXCEPTION WHEN duplicate_column THEN null; "
                f"END $$;"
            )
        )

    # ── model_shares: add missing rich-publish columns (Phase 70) ───────
    rich_cols = [
        ("use_case", "TEXT"),
        ("limitations", "TEXT"),
        ("example_inputs", "JSONB DEFAULT '[]'::jsonb"),
        ("training_data_summary", "JSONB DEFAULT '{}'::jsonb"),
        ("status", "VARCHAR(50) DEFAULT 'pending'"),
        ("review_note", "TEXT"),
    ]
    for col, definition in rich_cols:
        op.execute(
            sa.text(
                f"DO $$ BEGIN "
                f"    ALTER TABLE model_shares ADD COLUMN IF NOT EXISTS {col} {definition}; "
                f"EXCEPTION WHEN duplicate_column THEN null; "
                f"END $$;"
            )
        )

    # ── model_shares: indexes ───────────────────────────────────────────
    share_indexes = [
        ("ix_model_shares_model_id", "model_shares", ["model_id"]),
        ("ix_model_shares_shared_by", "model_shares", ["shared_by"]),
        ("ix_model_shares_is_public", "model_shares", ["is_public"]),
    ]
    for name, table, cols in share_indexes:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({', '.join(cols)})")

    # ── model_feedback table ────────────────────────────────────────────
    op.execute("""
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
            created_at TIMESTAMP DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_feedback_model_id ON model_feedback (model_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_feedback_user_id ON model_feedback (user_id)")

    # ── model_reports table ─────────────────────────────────────────────
    op.execute("""
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
            created_at TIMESTAMP DEFAULT now(),
            reviewed_at TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_reports_share_id ON model_reports (share_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_reports_status ON model_reports (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_reports_reported_by ON model_reports (reported_by)")


def downgrade() -> None:
    # ── Drop indexes ──
    for name in [
        "ix_model_reports_reported_by",
        "ix_model_reports_status",
        "ix_model_reports_share_id",
        "ix_model_feedback_user_id",
        "ix_model_feedback_model_id",
    ]:
        op.execute(f"DROP INDEX IF EXISTS {name}")

    # ── Drop tables ──
    op.execute("DROP TABLE IF EXISTS model_reports")
    op.execute("DROP TABLE IF EXISTS model_feedback")

    # ── Drop columns from model_shares ──
    for col in [
        "status", "review_note", "training_data_summary",
        "example_inputs", "limitations", "use_case",
        "lifecycle_stage", "deprecation_note", "deprecated_at", "last_trained_at",
    ]:
        op.execute(
            sa.text(
                f"DO $$ BEGIN "
                f"    ALTER TABLE model_shares DROP COLUMN IF EXISTS {col}; "
                f"EXCEPTION WHEN undefined_column THEN null; "
                f"END $$;"
            )
        )
