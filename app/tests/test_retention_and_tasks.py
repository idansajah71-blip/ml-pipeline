import pytest


def test_retention_service_imports():
    from app.services.retention_service import DataRetentionService
    assert DataRetentionService is not None


def test_batch_tasks_imports():
    from app.ml.batch_tasks import batch_predict_task
    assert batch_predict_task is not None


def test_cleanup_tasks_imports():
    from app.ml.cleanup_tasks import (
        garbage_collect_models,
        cleanup_serving_logs,
        cleanup_audit_logs,
        enforce_data_retention,
    )
    assert garbage_collect_models is not None
    assert cleanup_serving_logs is not None
    assert cleanup_audit_logs is not None
    assert enforce_data_retention is not None


def test_auto_retrain_imports():
    from app.ml.auto_retrain import run_auto_retrain_pipeline, auto_retrain_on_drift
    assert run_auto_retrain_pipeline is not None
    assert auto_retrain_on_drift is not None
