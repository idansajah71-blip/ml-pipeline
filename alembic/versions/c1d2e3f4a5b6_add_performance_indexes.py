"""add performance indexes

Revision ID: c1d2e3f4a5b6
Revises: bd04ec4aa0be
Create Date: 2026-08-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c1d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'bd04ec4aa0be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    op.create_index('ix_datasets_owner_id', 'datasets', ['owner_id'])
    op.create_index('ix_datasets_created_at', 'datasets', ['created_at'])
    op.create_index('ix_datasets_name', 'datasets', ['name'])

    op.create_index('ix_models_owner_id', 'models', ['owner_id'])
    op.create_index('ix_models_status', 'models', ['status'])
    op.create_index('ix_models_algorithm', 'models', ['algorithm'])
    op.create_index('ix_models_created_at', 'models', ['created_at'])

    op.create_index('ix_experiments_owner_id', 'experiments', ['owner_id'])
    op.create_index('ix_experiments_status', 'experiments', ['status'])
    op.create_index('ix_experiments_model_id', 'experiments', ['model_id'])
    op.create_index('ix_experiments_dataset_id', 'experiments', ['dataset_id'])
    op.create_index('ix_experiments_created_at', 'experiments', ['created_at'])

    op.create_index('ix_ab_tests_status', 'ab_tests', ['status'])
    op.create_index('ix_ab_tests_owner_id', 'ab_tests', ['owner_id'])
    op.create_index('ix_ab_tests_created_at', 'ab_tests', ['created_at'])

    op.create_index('ix_predictions_model_id', 'predictions', ['model_id'])
    op.create_index('ix_predictions_created_at', 'predictions', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_predictions_created_at', 'predictions')
    op.drop_index('ix_predictions_model_id', 'predictions')

    op.drop_index('ix_ab_tests_created_at', 'ab_tests')
    op.drop_index('ix_ab_tests_owner_id', 'ab_tests')
    op.drop_index('ix_ab_tests_status', 'ab_tests')

    op.drop_index('ix_experiments_created_at', 'experiments')
    op.drop_index('ix_experiments_dataset_id', 'experiments')
    op.drop_index('ix_experiments_model_id', 'experiments')
    op.drop_index('ix_experiments_status', 'experiments')
    op.drop_index('ix_experiments_owner_id', 'experiments')

    op.drop_index('ix_models_created_at', 'models')
    op.drop_index('ix_models_algorithm', 'models')
    op.drop_index('ix_models_status', 'models')
    op.drop_index('ix_models_owner_id', 'models')

    op.drop_index('ix_datasets_name', 'datasets')
    op.drop_index('ix_datasets_created_at', 'datasets')
    op.drop_index('ix_datasets_owner_id', 'datasets')

    op.drop_index('ix_users_is_active', 'users')
    op.drop_index('ix_users_role', 'users')
    op.drop_index('ix_users_username', 'users')
    op.drop_index('ix_users_email', 'users')
