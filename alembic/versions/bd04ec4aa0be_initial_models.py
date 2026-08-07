"""initial models

Revision ID: bd04ec4aa0be
Revises: 
Create Date: 2026-07-31 08:33:04.040821

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'bd04ec4aa0be'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all initial tables."""

    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', sa.Enum('admin', 'data_scientist', 'user', name='userrole'), nullable=False, server_default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column('api_key', sa.String(255), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- datasets ---
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('rows_count', sa.Integer(), nullable=True),
        sa.Column('columns_count', sa.Integer(), nullable=True),
        sa.Column('column_names', sa.JSON(), nullable=True),
        sa.Column('column_types', sa.JSON(), nullable=True),
        sa.Column('target_column', sa.String(255), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- models ---
    op.create_table(
        'models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('algorithm', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('status', sa.Enum('training', 'trained', 'deployed', 'archived', 'failed', name='modelstatus'), nullable=True, server_default='trained'),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('feature_names', sa.JSON(), nullable=True),
        sa.Column('target_column', sa.String(255), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('is_default', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('stage', sa.String(50), nullable=True, server_default='development'),
        sa.Column('parent_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=True),
        sa.Column('model_card', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- experiments ---
    op.create_table(
        'experiments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='experimentstatus'), nullable=True, server_default='pending'),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('logs', sa.Text(), nullable=True),
        sa.Column('duration_seconds', sa.String(50), nullable=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id'), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # --- predictions ---
    op.create_table(
        'predictions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('input_data', sa.JSON(), nullable=False),
        sa.Column('prediction', sa.String(255), nullable=False),
        sa.Column('probability', sa.Float(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- ab_tests ---
    op.create_table(
        'ab_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('draft', 'active', 'paused', 'completed', name='abteststatus'), nullable=True, server_default='draft'),
        sa.Column('traffic_split', sa.Integer(), nullable=True, server_default='50'),
        sa.Column('model_a_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('model_b_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('model_a_requests', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('model_b_requests', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('model_a_accuracy', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('model_b_accuracy', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
    )

    # --- data_quality_reports ---
    op.create_table(
        'data_quality_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('datasets.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=True, server_default='passed'),
        sa.Column('total_rows', sa.Float(), nullable=True, server_default='0'),
        sa.Column('total_checks', sa.Float(), nullable=True, server_default='0'),
        sa.Column('passed_checks', sa.Float(), nullable=True, server_default='0'),
        sa.Column('failed_checks', sa.Float(), nullable=True, server_default='0'),
        sa.Column('score', sa.Float(), nullable=True, server_default='100.0'),
        sa.Column('checks', sa.JSON(), nullable=True),
        sa.Column('summary', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- batch_jobs ---
    op.create_table(
        'batch_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='batchjobstatus'), nullable=True, server_default='pending'),
        sa.Column('input_file_path', sa.String(500), nullable=True),
        sa.Column('output_file_path', sa.String(500), nullable=True),
        sa.Column('total_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('processed_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('failed_rows', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True, server_default='0'),
        sa.Column('results_summary', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('task_id', sa.String(255), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- audit_logs ---
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('status_code', sa.String(10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True, server_default=sa.func.now()),
    )

    # --- organizations ---
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('plan', sa.String(50), nullable=True, server_default='free'),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- org_members ---
    op.create_table(
        'org_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('role', sa.String(50), nullable=True, server_default='member'),
        sa.Column('joined_at', sa.DateTime(), nullable=True),
    )

    # --- api_quotas ---
    op.create_table(
        'api_quotas',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False, unique=True),
        sa.Column('tier', sa.String(50), nullable=True, server_default='free'),
        sa.Column('rpm_limit', sa.Integer(), nullable=True, server_default='60'),
        sa.Column('daily_limit', sa.Integer(), nullable=True, server_default='10000'),
        sa.Column('monthly_limit', sa.Integer(), nullable=True, server_default='300000'),
        sa.Column('current_rpm', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('current_daily', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('current_monthly', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('rpm_reset_at', sa.DateTime(), nullable=True),
        sa.Column('daily_reset_at', sa.DateTime(), nullable=True),
        sa.Column('monthly_reset_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- api_usage_logs ---
    op.create_table(
        'api_usage_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- feature_groups ---
    op.create_table(
        'feature_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('schema_definition', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- features ---
    op.create_table(
        'features',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('feature_group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('feature_groups.id'), nullable=False),
        sa.Column('data_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('default_value', sa.String(500), nullable=True),
        sa.Column('validation_rules', sa.JSON(), nullable=True),
        sa.Column('transformation', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- feature_snapshots ---
    op.create_table(
        'feature_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('feature_group_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('row_key', sa.String(255), nullable=False),
        sa.Column('features', sa.JSON(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- serving_endpoints ---
    op.create_table(
        'serving_endpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('max_batch_size', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('cache_ttl_seconds', sa.Integer(), nullable=True, server_default='300'),
        sa.Column('rate_limit_rpm', sa.Integer(), nullable=True, server_default='1000'),
        sa.Column('is_active', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- serving_logs ---
    op.create_table(
        'serving_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('endpoint_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('prediction', sa.JSON(), nullable=True),
        sa.Column('latency_ms', sa.Float(), nullable=True),
        sa.Column('cache_hit', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('status', sa.String(20), nullable=True, server_default='success'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- model_versions ---
    op.create_table(
        'model_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=True, server_default='created'),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('changelog', sa.Text(), nullable=True),
        sa.Column('artifact_size_bytes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('parent_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id'), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- model_lineage ---
    op.create_table(
        'model_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('parent_model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=True),
        sa.Column('relationship_type', sa.String(50), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- model_artifacts ---
    op.create_table(
        'model_artifacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('models.id'), nullable=False),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('model_versions.id'), nullable=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- feature_drift_alerts ---
    op.create_table(
        'feature_drift_alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('feature_name', sa.String(255), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('drift_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('current_value', sa.Float(), nullable=True),
        sa.Column('baseline_value', sa.Float(), nullable=True),
        sa.Column('drift_score', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('acknowledged', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- feature_stats ---
    op.create_table(
        'feature_stats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('feature_name', sa.String(255), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('mean_value', sa.Float(), nullable=True),
        sa.Column('std_value', sa.Float(), nullable=True),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('null_rate', sa.Float(), nullable=True),
        sa.Column('unique_count', sa.Integer(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=True),
        sa.Column('histogram', sa.JSON(), nullable=True),
        sa.Column('window_start', sa.DateTime(), nullable=True),
        sa.Column('window_end', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- webhooks ---
    op.create_table(
        'webhooks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('secret', sa.String(255), nullable=True),
        sa.Column('events', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.true()),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('last_triggered_at', sa.DateTime(), nullable=True),
        sa.Column('last_status_code', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- webhook_logs ---
    op.create_table(
        'webhook_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('webhook_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event', sa.String(100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True, server_default=sa.false()),
        sa.Column('duration_ms', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- data_lineage ---
    op.create_table(
        'data_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_type', sa.String(50), nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transformation', sa.String(255), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    # --- custom_metrics ---
    op.create_table(
        'custom_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('metric_type', sa.String(50), nullable=False),
        sa.Column('query_or_formula', sa.Text(), nullable=False),
        sa.Column('model_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dashboard_config', sa.JSON(), nullable=True),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # --- metric_data_points ---
    op.create_table(
        'metric_data_points',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('metric_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('labels', sa.JSON(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(), nullable=True),
    )

    # ======== INDEXES ========

    # users
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'])
    op.create_index('ix_users_is_active', 'users', ['is_active'])

    # datasets
    op.create_index('ix_datasets_owner_id', 'datasets', ['owner_id'])
    op.create_index('ix_datasets_created_at', 'datasets', ['created_at'])
    op.create_index('ix_datasets_name', 'datasets', ['name'])

    # models
    op.create_index('ix_models_owner_id', 'models', ['owner_id'])
    op.create_index('ix_models_status', 'models', ['status'])
    op.create_index('ix_models_algorithm', 'models', ['algorithm'])
    op.create_index('ix_models_created_at', 'models', ['created_at'])
    op.create_index('ix_models_stage', 'models', ['stage'])

    # experiments
    op.create_index('ix_experiments_owner_id', 'experiments', ['owner_id'])
    op.create_index('ix_experiments_status', 'experiments', ['status'])
    op.create_index('ix_experiments_model_id', 'experiments', ['model_id'])
    op.create_index('ix_experiments_dataset_id', 'experiments', ['dataset_id'])
    op.create_index('ix_experiments_created_at', 'experiments', ['created_at'])

    # ab_tests
    op.create_index('ix_ab_tests_status', 'ab_tests', ['status'])
    op.create_index('ix_ab_tests_owner_id', 'ab_tests', ['owner_id'])
    op.create_index('ix_ab_tests_created_at', 'ab_tests', ['created_at'])
    op.create_index('ix_ab_tests_model_a_id', 'ab_tests', ['model_a_id'])
    op.create_index('ix_ab_tests_model_b_id', 'ab_tests', ['model_b_id'])

    # predictions
    op.create_index('ix_predictions_model_id', 'predictions', ['model_id'])
    op.create_index('ix_predictions_created_at', 'predictions', ['created_at'])

    # batch_jobs
    op.create_index('ix_batch_jobs_status', 'batch_jobs', ['status'])
    op.create_index('ix_batch_jobs_model_id', 'batch_jobs', ['model_id'])
    op.create_index('ix_batch_jobs_owner_id', 'batch_jobs', ['owner_id'])
    op.create_index('ix_batch_jobs_created_at', 'batch_jobs', ['created_at'])

    # audit_logs
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])
    op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])

    # serving
    op.create_index('ix_serving_endpoints_model_id', 'serving_endpoints', ['model_id'])
    op.create_index('ix_serving_endpoints_owner_id', 'serving_endpoints', ['owner_id'])
    op.create_index('ix_serving_endpoints_name', 'serving_endpoints', ['name'])
    op.create_index('ix_serving_logs_endpoint_id', 'serving_logs', ['endpoint_id'])
    op.create_index('ix_serving_logs_created_at', 'serving_logs', ['created_at'])
    op.create_index('ix_serving_logs_status', 'serving_logs', ['status'])

    # feature monitoring
    op.create_index('ix_drift_alerts_severity', 'feature_drift_alerts', ['severity'])
    op.create_index('ix_drift_alerts_feature_name', 'feature_drift_alerts', ['feature_name'])
    op.create_index('ix_drift_alerts_created_at', 'feature_drift_alerts', ['created_at'])
    op.create_index('ix_drift_alerts_acknowledged', 'feature_drift_alerts', ['acknowledged'])
    op.create_index('ix_feature_stats_feature_name', 'feature_stats', ['feature_name'])
    op.create_index('ix_feature_stats_created_at', 'feature_stats', ['created_at'])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""

    # indexes first (non-table-specific)
    op.drop_index('ix_feature_stats_created_at', 'feature_stats')
    op.drop_index('ix_feature_stats_feature_name', 'feature_stats')
    op.drop_index('ix_drift_alerts_acknowledged', 'feature_drift_alerts')
    op.drop_index('ix_drift_alerts_created_at', 'feature_drift_alerts')
    op.drop_index('ix_drift_alerts_feature_name', 'feature_drift_alerts')
    op.drop_index('ix_drift_alerts_severity', 'feature_drift_alerts')
    op.drop_index('ix_serving_logs_status', 'serving_logs')
    op.drop_index('ix_serving_logs_created_at', 'serving_logs')
    op.drop_index('ix_serving_logs_endpoint_id', 'serving_logs')
    op.drop_index('ix_serving_endpoints_name', 'serving_endpoints')
    op.drop_index('ix_serving_endpoints_owner_id', 'serving_endpoints')
    op.drop_index('ix_serving_endpoints_model_id', 'serving_endpoints')
    op.drop_index('ix_audit_logs_created_at', 'audit_logs')
    op.drop_index('ix_audit_logs_resource_type', 'audit_logs')
    op.drop_index('ix_audit_logs_action', 'audit_logs')
    op.drop_index('ix_batch_jobs_created_at', 'batch_jobs')
    op.drop_index('ix_batch_jobs_owner_id', 'batch_jobs')
    op.drop_index('ix_batch_jobs_model_id', 'batch_jobs')
    op.drop_index('ix_batch_jobs_status', 'batch_jobs')
    op.drop_index('ix_predictions_created_at', 'predictions')
    op.drop_index('ix_predictions_model_id', 'predictions')
    op.drop_index('ix_ab_tests_model_b_id', 'ab_tests')
    op.drop_index('ix_ab_tests_model_a_id', 'ab_tests')
    op.drop_index('ix_ab_tests_created_at', 'ab_tests')
    op.drop_index('ix_ab_tests_owner_id', 'ab_tests')
    op.drop_index('ix_ab_tests_status', 'ab_tests')
    op.drop_index('ix_experiments_created_at', 'experiments')
    op.drop_index('ix_experiments_dataset_id', 'experiments')
    op.drop_index('ix_experiments_model_id', 'experiments')
    op.drop_index('ix_experiments_status', 'experiments')
    op.drop_index('ix_experiments_owner_id', 'experiments')
    op.drop_index('ix_models_stage', 'models')
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

    # tables in reverse FK dependency order
    op.drop_table('metric_data_points')
    op.drop_table('custom_metrics')
    op.drop_table('data_lineage')
    op.drop_table('webhook_logs')
    op.drop_table('webhooks')
    op.drop_table('feature_stats')
    op.drop_table('feature_drift_alerts')
    op.drop_table('model_artifacts')
    op.drop_table('model_lineage')
    op.drop_table('model_versions')
    op.drop_table('serving_logs')
    op.drop_table('serving_endpoints')
    op.drop_table('feature_snapshots')
    op.drop_table('features')
    op.drop_table('feature_groups')
    op.drop_table('api_usage_logs')
    op.drop_table('api_quotas')
    op.drop_table('org_members')
    op.drop_table('organizations')
    op.drop_table('audit_logs')
    op.drop_table('batch_jobs')
    op.drop_table('data_quality_reports')
    op.drop_table('ab_tests')
    op.drop_table('predictions')
    op.drop_table('experiments')
    op.drop_table('models')
    op.drop_table('datasets')
    op.drop_table('users')

    # drop enums
    op.execute("DROP TYPE IF EXISTS userrole")
    op.execute("DROP TYPE IF EXISTS modelstatus")
    op.execute("DROP TYPE IF EXISTS experimentstatus")
    op.execute("DROP TYPE IF EXISTS abteststatus")
    op.execute("DROP TYPE IF EXISTS batchjobstatus")
