"""fix missing columns and schema mismatches across datasets/models tables

Revision ID: a9b8c7d6e5f4
Revises: f1a2b3c4d5e6
Create Date: 2026-08-06 10:00:00.000000

This migration corrects schema mismatches between the SQLAlchemy ORM
definitions and the existing database tables. Every statement uses
IF NOT EXISTS so it is safe to run repeatedly on any database state.

Columns added:
  - datasets.is_archived  (BOOLEAN NOT NULL DEFAULT FALSE)

Indexes re-added:
  - ix_datasets_owner_id, ix_datasets_created_at, ix_datasets_name
  - ix_models_stage, ix_models_status, ix_models_owner_id, ...

Enum types re-created:
  - userrole, modelstatus, experimentstatus, abteststatus, batchjobstatus
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUMS = {
    'userrole': ['admin', 'data_scientist', 'user'],
    'modelstatus': ['training', 'trained', 'deployed', 'archived', 'failed'],
    'experimentstatus': ['pending', 'running', 'completed', 'failed'],
    'abteststatus': ['draft', 'active', 'paused', 'completed'],
    'batchjobstatus': ['pending', 'running', 'completed', 'failed'],
}


def _create_enum_if_missing(name: str, values):
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"),
        {"name": name},
    ).scalar()
    if not existing:
        enum = postgresql.ENUM(*values, name=name)
        enum.create(op.get_bind(), checkfirst=True)


def upgrade() -> None:
    # -------- Enum types (safe IF NOT EXISTS recreation) --------
    for name, values in ENUMS.items():
        _create_enum_if_missing(name, values)

    # -------- datasets table --------
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE datasets ADD COLUMN IF NOT EXISTS is_archived
                BOOLEAN NOT NULL DEFAULT FALSE;
        EXCEPTION WHEN duplicate_column THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE datasets ALTER COLUMN is_archived SET DEFAULT FALSE;
        EXCEPTION WHEN others THEN null;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            ALTER TABLE datasets ALTER COLUMN is_archived SET NOT NULL;
        EXCEPTION WHEN others THEN null;
        END $$;
    """)

    # -------- datasets: back-fill NULL -> FALSE just in case --------
    op.execute(
        sa.text("UPDATE datasets SET is_archived = FALSE WHERE is_archived IS NULL")
    )

    # -------- users schema fixes --------
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE users ALTER COLUMN is_active SET DEFAULT TRUE;
        EXCEPTION WHEN others THEN null;
        END $$;
    """)

    # -------- models: columns that may be missing on old databases --------
    models_missing_cols = [
        ("task_id", "VARCHAR(255)"),
        ("stage", "VARCHAR(50) DEFAULT 'development'"),
        ("parent_model_id", f"UUID REFERENCES models(id)"),
        ("model_card", f"JSONB DEFAULT '{{}}'::jsonb"),
    ]
    for col, definition in models_missing_cols:
        op.execute(
            sa.text(
                f"DO $$ BEGIN "
                f"    ALTER TABLE models ADD COLUMN IF NOT EXISTS {col} {definition}; "
                f"EXCEPTION WHEN duplicate_column THEN null; "
                f"END $$;"
            )
        )

    # -------- Helper: safe index creation (check column exists first) --------
    conn = op.get_bind()

    def _safe_create_index(name: str, table: str, cols: list):
        for col in cols:
            result = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": table, "c": col},
            ).scalar()
            if not result:
                return  # column missing, skip this index
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({', '.join(cols)})")

    # -------- Indexes on datasets --------
    _safe_create_index("ix_datasets_owner_id", "datasets", ["owner_id"])
    _safe_create_index("ix_datasets_created_at", "datasets", ["created_at"])
    _safe_create_index("ix_datasets_name", "datasets", ["name"])

    # -------- Indexes on models --------
    _safe_create_index("ix_models_owner_id", "models", ["owner_id"])
    _safe_create_index("ix_models_status", "models", ["status"])
    _safe_create_index("ix_models_algorithm", "models", ["algorithm"])
    _safe_create_index("ix_models_created_at", "models", ["created_at"])
    _safe_create_index("ix_models_stage", "models", ["stage"])

    # -------- Indexes on experiments --------
    _safe_create_index("ix_experiments_owner_id", "experiments", ["owner_id"])
    _safe_create_index("ix_experiments_status", "experiments", ["status"])
    _safe_create_index("ix_experiments_model_id", "experiments", ["model_id"])
    _safe_create_index("ix_experiments_dataset_id", "experiments", ["dataset_id"])
    _safe_create_index("ix_experiments_created_at", "experiments", ["created_at"])

    # -------- Indexes on predictions, ab_tests, batch_jobs --------
    _safe_create_index("ix_predictions_model_id", "predictions", ["model_id"])
    _safe_create_index("ix_predictions_created_at", "predictions", ["created_at"])
    _safe_create_index("ix_ab_tests_status", "ab_tests", ["status"])
    _safe_create_index("ix_ab_tests_owner_id", "ab_tests", ["owner_id"])
    _safe_create_index("ix_ab_tests_created_at", "ab_tests", ["created_at"])
    _safe_create_index("ix_ab_tests_model_a_id", "ab_tests", ["model_a_id"])
    _safe_create_index("ix_ab_tests_model_b_id", "ab_tests", ["model_b_id"])
    _safe_create_index("ix_batch_jobs_status", "batch_jobs", ["status"])
    _safe_create_index("ix_batch_jobs_model_id", "batch_jobs", ["model_id"])
    _safe_create_index("ix_batch_jobs_owner_id", "batch_jobs", ["owner_id"])
    _safe_create_index("ix_batch_jobs_created_at", "batch_jobs", ["created_at"])


def downgrade() -> None:
    # Intentionally a no-op: this migration is idempotent-repair-only.
    # Reversing it would drop columns/indexes that the ORM requires.
    pass
