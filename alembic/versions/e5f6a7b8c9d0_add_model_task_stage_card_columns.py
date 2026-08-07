"""add model task_id stage parent_model_id model_card

Revision ID: e5f6a7b8c9d0
Revises: c1d2e3f4a5b6
Create Date: 2026-08-05 20:00:00.000000

NOTE: Columns task_id, stage, parent_model_id, model_card and index ix_models_stage
have been consolidated into the initial migration (bd04ec4aa0be).
This migration is now a no-op kept only to preserve the revision chain integrity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All columns and indexes were consolidated into the initial migration.
    pass


def downgrade() -> None:
    # Corresponding no-op.
    pass
