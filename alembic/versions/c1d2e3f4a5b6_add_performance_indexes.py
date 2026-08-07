"""add performance indexes

Revision ID: c1d2e3f4a5b6
Revises: bd04ec4aa0be
Create Date: 2026-08-05 10:00:00.000000

NOTE: All indexes originally in this migration have been moved to the
initial migration (bd04ec4aa0be). This migration is now a no-op kept
only to preserve the revision chain integrity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'bd04ec4aa0be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All indexes were consolidated into the initial migration.
    pass


def downgrade() -> None:
    # Corresponding no-op.
    pass
