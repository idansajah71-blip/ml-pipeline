"""Add scrape config tables - templates, schedules, webhooks, proxies, cache

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-08-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ScrapeTemplate
    op.create_table(
        'scrape_templates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, default=''),
        sa.Column('url_pattern', sa.String(2000), default=''),
        sa.Column('config', JSON, nullable=False, default=dict),
        sa.Column('scrape_type', sa.String(50), default='single'),
        sa.Column('tags', JSON, default=list),
        sa.Column('use_count', sa.Integer, default=0),
        sa.Column('is_public', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ScrapeSchedule
    op.create_table(
        'scrape_schedules',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('template_id', UUID(as_uuid=True), sa.ForeignKey('scrape_templates.id'), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('url', sa.String(2000), nullable=False),
        sa.Column('config', JSON, default=dict),
        sa.Column('cron_expression', sa.String(100), default='0 2 * * *'),
        sa.Column('interval_minutes', sa.Integer, default=1440),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('last_run_at', sa.DateTime, nullable=True),
        sa.Column('next_run_at', sa.DateTime, nullable=True),
        sa.Column('run_count', sa.Integer, default=0),
        sa.Column('last_status', sa.String(50), default='pending'),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ScrapeWebhookConfig
    op.create_table(
        'scrape_webhook_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('url', sa.String(2000), nullable=False),
        sa.Column('webhook_type', sa.String(50), default='generic'),
        sa.Column('events', JSON, default=lambda: ['scrape.complete', 'scrape.error']),
        sa.Column('headers', JSON, default=dict),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('secret', sa.String(200), nullable=True),
        sa.Column('last_triggered_at', sa.DateTime, nullable=True),
        sa.Column('last_status', sa.Integer, nullable=True),
        sa.Column('trigger_count', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ScrapeProxyConfig
    op.create_table(
        'scrape_proxy_configs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('proxy_url', sa.String(2000), nullable=False),
        sa.Column('proxy_type', sa.String(50), default='http'),
        sa.Column('username', sa.String(200), nullable=True),
        sa.Column('password_encrypted', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_healthy', sa.Boolean, default=True),
        sa.Column('last_checked_at', sa.DateTime, nullable=True),
        sa.Column('avg_response_ms', sa.Float, default=0.0),
        sa.Column('total_requests', sa.Integer, default=0),
        sa.Column('failed_requests', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    # ScrapeCache
    op.create_table(
        'scrape_cache',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('url', sa.String(2000), nullable=False, index=True),
        sa.Column('content_hash', sa.String(64), nullable=False, index=True),
        sa.Column('title', sa.String(500), default=''),
        sa.Column('cached_data', JSON, default=dict),
        sa.Column('row_count', sa.Integer, default=0),
        sa.Column('hit_count', sa.Integer, default=0),
        sa.Column('expires_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index('ix_scrape_cache_url_hash', 'scrape_cache', ['url', 'content_hash'])


def downgrade() -> None:
    op.drop_table('scrape_cache')
    op.drop_table('scrape_proxy_configs')
    op.drop_table('scrape_webhook_configs')
    op.drop_table('scrape_schedules')
    op.drop_table('scrape_templates')
