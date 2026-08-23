

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
    from app.ml.auto_retrain import (
        run_auto_retrain_pipeline,
        auto_retrain_candidate,
        RetrainingPolicy,
        promote_canary,
        reject_canary,
    )
    assert run_auto_retrain_pipeline is not None
    assert auto_retrain_candidate is not None
    assert RetrainingPolicy is not None
    assert promote_canary is not None
    assert reject_canary is not None


class TestRetrainingPolicy:
    def test_should_retrain_data_drift(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        result = policy.should_retrain('data_drift', 0.5, 200)
        assert result['retrain'] is True

    def test_should_not_retrain_low_drift(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        result = policy.should_retrain('data_drift', 0.1, 200)
        assert result['retrain'] is False

    def test_should_not_retrain_insufficient_samples(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        result = policy.should_retrain('data_drift', 0.5, 10)
        assert result['retrain'] is False
        assert 'Insufficient samples' in result['reason']

    def test_should_retrain_prediction_drift(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        result = policy.should_retrain('prediction_drift', 0.3, 200)
        assert result['retrain'] is True

    def test_should_retrain_performance_degradation(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        result = policy.should_retrain('performance_degradation', 0.1, 200)
        assert result['retrain'] is True

    def test_should_not_retrain_good_delayed_labels(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        delayed = {'status': 'ok', 'problem_type': 'classification', 'accuracy': 0.98}
        result = policy.should_retrain('data_drift', 0.5, 200, delayed)
        assert result['retrain'] is False
        assert 'accuracy' in result['reason']

    def test_should_retrain_poor_delayed_labels(self):
        from app.ml.auto_retrain import RetrainingPolicy
        policy = RetrainingPolicy()
        delayed = {'status': 'ok', 'problem_type': 'classification', 'accuracy': 0.7}
        result = policy.should_retrain('data_drift', 0.5, 200, delayed)
        assert result['retrain'] is True
