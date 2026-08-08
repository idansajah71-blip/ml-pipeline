"""add advanced tables: dataset_versions, ensemble_models, compute_costs, model_shares

Revision ID: f1a2b3c4d5e6
Revises: e5f6a7b8c9d0
Create Date: 2026-08-06 09:20:00.000000

Adds 4 tables from app/models/advanced.py that were never included
in any previous migration despite being defined in the ORM.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table_name):
    return conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {"t": table_name},
    ).scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # --- dataset_versions ---
    if not _table_exists(conn, 'dataset_versions'):
        op.create_table(
            'dataset_versions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('version_number', sa.Integer(), nullable=False),
            sa.Column('file_path', sa.String(500), nullable=True),
            sa.Column('rows_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('columns_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('schema_snapshot', sa.JSON(), nullable=True),
            sa.Column('stats_snapshot', sa.JSON(), nullable=True),
            sa.Column('changelog', sa.Text(), nullable=True),
            sa.Column('checksum', sa.String(64), nullable=True),
            sa.Column('size_bytes', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # --- ensemble_models ---
    if not _table_exists(conn, 'ensemble_models'):
        op.create_table(
            'ensemble_models',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('strategy', sa.String(50), nullable=True, server_default='voting'),
            sa.Column('model_ids', sa.JSON(), nullable=True),
            sa.Column('weights', sa.JSON(), nullable=True),
            sa.Column('metrics', sa.JSON(), nullable=True),
            sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )

    # --- compute_costs ---
    if not _table_exists(conn, 'compute_costs'):
        op.create_table(
            'compute_costs',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('resource_type', sa.String(50), nullable=False),
            sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('cost_usd', sa.Float(), nullable=False),
            sa.Column('usage_hours', sa.Float(), nullable=True, server_default='0'),
            sa.Column('gpu_hours', sa.Float(), nullable=True, server_default='0'),
            sa.Column('details', sa.JSON(), nullable=True),
            sa.Column('recorded_at', sa.DateTime(), nullable=True),
        )

    # --- model_shares ---
    if not _table_exists(conn, 'model_shares'):
        op.create_table(
            'model_shares',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('shared_by', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('shared_with_org', sa.String(255), nullable=True),
            sa.Column('permission', sa.String(50), nullable=True, server_default='read'),
            sa.Column('is_public', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('downloads', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('rating', sa.Float(), nullable=True, server_default='0'),
            sa.Column('tags', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
        )

    # Indexes (all IF NOT EXISTS)
    for name, table, cols in [
        ('ix_dataset_versions_dataset_id', 'dataset_versions', ['dataset_id']),
        ('ix_dataset_versions_owner_id', 'dataset_versions', ['owner_id']),
        ('ix_compute_costs_user_id', 'compute_costs', ['user_id']),
        ('ix_model_shares_model_id', 'model_shares', ['model_id']),
    ]:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({', '.join(cols)})")


def downgrade() -> None:
    op.drop_index('ix_model_shares_model_id', 'model_shares')
    op.drop_index('ix_compute_costs_user_id', 'compute_costs')
    op.drop_index('ix_dataset_versions_owner_id', 'dataset_versions')
    op.drop_index('ix_dataset_versions_dataset_id', 'dataset_versions')

    op.drop_table('model_shares')
    op.drop_table('compute_costs')
    op.drop_table('ensemble_models')
    op.drop_table('dataset_versions')
