"""add model task_id stage parent_model_id model_card

Revision ID: e5f6a7b8c9d0
Revises: c1d2e3f4a5b6
Create Date: 2026-08-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'c1d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('models', sa.Column('task_id', sa.String(255), nullable=True))
    op.add_column('models', sa.Column('stage', sa.String(50), server_default='development'))
    op.add_column('models', sa.Column('parent_model_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=True))
    op.add_column('models', sa.Column('model_card', sa.JSON, server_default='{}'))
    op.create_index('ix_models_stage', 'models', ['stage'])


def downgrade() -> None:
    op.drop_index('ix_models_stage', 'models')
    op.drop_column('models', 'model_card')
    op.drop_column('models', 'parent_model_id')
    op.drop_column('models', 'stage')
    op.drop_column('models', 'task_id')
