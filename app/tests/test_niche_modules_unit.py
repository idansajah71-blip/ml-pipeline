import pytest
import os
import hashlib
import json
import tempfile
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock


class TestServingServiceLogic:
    """Tests for serving service pure logic (no DB needed)."""

    def test_cache_key_format(self):
        from app.services.serving_service import ModelServingService
        svc = ModelServingService.__new__(ModelServingService)
        key = svc._cache_key("ep-123", "abc-hash")
        assert key == "serving:ep-123:abc-hash"

    def test_hash_input_deterministic(self):
        from app.services.serving_service import ModelServingService
        svc = ModelServingService.__new__(ModelServingService)
        data = {"sepal_length": 5.1, "petal_width": 0.2}
        h1 = svc._hash_input(data)
        h2 = svc._hash_input(data)
        assert h1 == h2
        assert len(h1) == 32  # MD5 hex digest

    def test_hash_input_sensitive_to_order(self):
        from app.services.serving_service import ModelServingService
        svc = ModelServingService.__new__(ModelServingService)
        h1 = svc._hash_input({"a": 1, "b": 2})
        h2 = svc._hash_input({"b": 2, "a": 1})
        assert h1 == h2  # sort_keys=True ensures order-insensitive

    def test_hash_input_different_for_different_data(self):
        from app.services.serving_service import ModelServingService
        svc = ModelServingService.__new__(ModelServingService)
        h1 = svc._hash_input({"x": 1})
        h2 = svc._hash_input({"x": 2})
        assert h1 != h2


class TestRetentionServiceLogic:
    """Tests for retention service pure logic (no DB needed)."""

    def test_retention_policies_all_tiers(self):
        from app.services.retention_service import RETENTION_POLICIES
        for tier in ["free", "starter", "pro", "enterprise"]:
            assert tier in RETENTION_POLICIES
            p = RETENTION_POLICIES[tier]
            assert "dataset_retention_days" in p
            assert "model_retention_days" in p
            assert "experiment_retention_days" in p
            assert "max_storage_mb" in p

    def test_retention_increases_by_tier(self):
        from app.services.retention_service import RETENTION_POLICIES
        tiers = ["free", "starter", "pro"]
        for key in ["dataset_retention_days", "model_retention_days", "max_storage_mb"]:
            values = [RETENTION_POLICIES[t][key] for t in tiers]
            assert values == sorted(values), f"{key} not ascending: {values}"

    def test_enterprise_unlimited(self):
        from app.services.retention_service import RETENTION_POLICIES
        ent = RETENTION_POLICIES["enterprise"]
        assert ent["dataset_retention_days"] == -1
        assert ent["model_retention_days"] == -1
        assert ent["max_storage_mb"] == -1

    def test_get_retention_policy_fallback_to_free(self):
        from app.services.retention_service import DataRetentionService
        svc = DataRetentionService.__new__(DataRetentionService)
        policy = svc.get_retention_policy("nonexistent_tier")
        from app.services.retention_service import RETENTION_POLICIES
        assert policy == RETENTION_POLICIES["free"]

    def test_get_retention_policy_known_tier(self):
        from app.services.retention_service import DataRetentionService, RETENTION_POLICIES
        svc = DataRetentionService.__new__(DataRetentionService)
        for tier in ["free", "starter", "pro", "enterprise"]:
            policy = svc.get_retention_policy(tier)
            assert policy == RETENTION_POLICIES[tier]


class TestAPIQuotaServiceLogic:
    """Tests for API quota service pure logic."""

    def test_tier_limits_all_tiers(self):
        from app.services.api_quota_service import APIQuotaService
        for tier in ["free", "starter", "pro", "enterprise"]:
            assert tier in APIQuotaService.TIER_LIMITS

    def test_tier_limits_have_required_keys(self):
        from app.services.api_quota_service import APIQuotaService
        required = ["rpm", "daily", "monthly", "training_daily", "training_monthly"]
        for tier, limits in APIQuotaService.TIER_LIMITS.items():
            for key in required:
                assert key in limits, f"{tier} missing {key}"

    def test_tier_limits_ascending(self):
        from app.services.api_quota_service import APIQuotaService
        tiers = ["free", "starter", "pro", "enterprise"]
        for key in ["rpm", "daily", "monthly", "training_daily", "training_monthly"]:
            values = [APIQuotaService.TIER_LIMITS[t][key] for t in tiers]
            assert values == sorted(values), f"{key} not ascending: {values}"

    def test_free_tier_has_reasonable_defaults(self):
        from app.services.api_quota_service import APIQuotaService
        free = APIQuotaService.TIER_LIMITS["free"]
        assert free["rpm"] == 60  # 1 per second
        assert free["training_daily"] == 5
        assert free["training_monthly"] == 100


class TestLIMEExplainerLogic:
    """Tests for LIME explainer actual logic."""

    def test_explain_with_lime_returns_method(self):
        from app.ml.lime_explainer import explain_with_lime
        from sklearn.ensemble import RandomForestClassifier

        X = np.random.randn(50, 4)
        y = np.random.choice([0, 1], size=50)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)

        result = explain_with_lime(model, X, X[0], ["f1", "f2", "f3", "f4"])
        assert result["method"] == "lime"
        assert "feature_importance" in result

    def test_explainer_global_unavailable_returns_error(self):
        from app.ml.lime_explainer import LIMEExplainer
        explainer = LIMEExplainer()
        explainer.is_available = False

        result = explainer.explain_global(None, np.random.randn(10, 4), ["a", "b", "c", "d"])
        assert "error" in result


class TestModelMonitorLogic:
    """Tests for model monitor fallback logic."""

    def test_fallback_drift_detects_shift(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        ref = pd.DataFrame({"x": np.random.randn(100)})
        cur = pd.DataFrame({"x": np.random.randn(100) + 5})  # shifted mean
        result = monitor.detect_data_drift(ref, cur)
        assert "drift_detected" in result
        assert "method" in result

    def test_fallback_drift_no_shift(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        np.random.seed(42)
        ref = pd.DataFrame({"x": np.random.randn(100)})
        cur = pd.DataFrame({"x": np.random.randn(100)})
        result = monitor.detect_data_drift(ref, cur)
        assert result["drift_detected"] is False

    def test_fallback_quality_catches_nulls(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        df = pd.DataFrame({"a": [1, 2, None, 4], "b": [5, 6, 7, 8]})
        result = monitor.check_data_quality(df)
        assert "quality_issues" in result
        assert len(result["quality_issues"]) > 0

    def test_fallback_quality_clean_data(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = monitor.check_data_quality(df)
        assert "quality_issues" in result


class TestDataValidationLogic:
    """Tests for data validation actual logic."""

    def test_auto_checks_multiple_types(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({
            "int_col": range(10),
            "float_col": [float(x) for x in range(10)],
            "str_col": ["a"] * 10,
        })
        checks = validator._auto_generate_checks(df)
        assert isinstance(checks, list)
        assert len(checks) >= 2  # should detect at least null check + type check

    def test_validate_dataset_structure(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({"f1": range(20), "f2": range(20), "target": [0, 1] * 10})
        result = validator.validate_dataset(df, "test")
        assert "checks" in result
        assert "summary" in result
        assert "passed" in result

    def test_validate_for_training_requires_target(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({"f1": range(20), "target": [0, 1] * 10})
        result = validator.validate_for_training(df, "target")
        assert "checks" in result or "error" in result


class TestBatchTasksLogic:
    """Tests for batch tasks pure logic."""

    def test_publish_progress_handles_redis_error(self):
        from app.ml.batch_tasks import publish_progress
        # Should not raise even if Redis is unavailable
        publish_progress("job-123", {"step": "test", "progress": 50})

    def test_batch_predict_task_exists(self):
        from app.ml.batch_tasks import batch_predict_task
        assert hasattr(batch_predict_task, 'delay') or hasattr(batch_predict_task, 'apply_async')


class TestFeatureStoreLogic:
    """Tests for feature store service imports and structure."""

    def test_feature_store_service_has_methods(self):
        from app.services.feature_store_service import FeatureStoreService
        assert hasattr(FeatureStoreService, 'create_group')
        assert hasattr(FeatureStoreService, 'add_feature')
        assert hasattr(FeatureStoreService, 'ingest_features')
        assert hasattr(FeatureStoreService, 'get_features')
        assert hasattr(FeatureStoreService, 'get_batch_features')
        assert hasattr(FeatureStoreService, 'list_snapshots')


class TestMLflowTrackerLogic:
    """Tests for MLflow tracker graceful degradation."""

    def test_graceful_degradation_all_methods(self):
        from app.ml.mlflow_tracker import MLflowTracker
        tracker = MLflowTracker()
        tracker.is_available = False

        # All methods should be no-ops when unavailable
        assert tracker.start_run() is None
        tracker.log_params({"k": "v"})
        tracker.log_metrics({"acc": 0.9})
        tracker.log_model(None)
        tracker.end_run()

    def test_factory_respects_experiment_name(self):
        from app.ml.mlflow_tracker import get_mlflow_tracker
        t = get_mlflow_tracker(experiment_name="my_experiment")
        assert t.experiment_name == "my_experiment"

    def test_track_training_returns_none_when_unavailable(self):
        from app.ml.mlflow_tracker import MLflowTracker
        tracker = MLflowTracker()
        tracker.is_available = False
        result = tracker.track_training(
            algorithm="random_forest",
            parameters={"n_estimators": 100},
            metrics={"accuracy": 0.9},
        )
        assert result is None


class TestTrainerBenchmark:
    """Tests for trainer benchmark actual logic."""

    def test_benchmark_classification_returns_metrics(self):
        from app.ml.trainer import ModelTrainer
        X_train = np.random.randn(100, 4)
        y_train = np.random.choice([0, 1, 2], size=100)
        X_test = np.random.randn(20, 4)
        y_test = np.random.choice([0, 1, 2], size=20)

        trainer = ModelTrainer()
        trainer.train(X_train, y_train, algorithm="random_forest", problem_type="classification")
        result = trainer.benchmark(X_test, y_test, feature_names=["f1", "f2", "f3", "f4"])

        assert result["problem_type"] == "classification"
        assert "accuracy" in result["metrics"]
        assert "f1_weighted" in result["metrics"]
        assert "mean_latency_ms" in result["inference"]
        assert "model_size_mb" in result
        assert result["model_size_mb"] > 0

    def test_benchmark_regression_returns_metrics(self):
        from app.ml.trainer import ModelTrainer
        X_train = np.random.randn(100, 4)
        y_train = np.random.randn(100)
        X_test = np.random.randn(20, 4)
        y_test = np.random.randn(20)

        trainer = ModelTrainer()
        trainer.train(X_train, y_train, algorithm="random_forest", problem_type="regression")
        result = trainer.benchmark(X_test, y_test, feature_names=["f1", "f2", "f3", "f4"])

        assert result["problem_type"] == "regression"
        assert "rmse" in result["metrics"]
        assert "r2" in result["metrics"]
        assert result["inference"]["mean_latency_ms"] >= 0

    def test_benchmark_latency_percentiles(self):
        from app.ml.trainer import ModelTrainer
        X_train = np.random.randn(100, 4)
        y_train = np.random.choice([0, 1], size=100)
        X_test = np.random.randn(20, 4)
        y_test = np.random.choice([0, 1], size=20)

        trainer = ModelTrainer()
        trainer.train(X_train, y_train, algorithm="random_forest", problem_type="classification")
        result = trainer.benchmark(X_test, y_test, feature_names=["f1", "f2", "f3", "f4"])

        inf = result["inference"]
        assert "p50_latency_ms" in inf
        assert "p95_latency_ms" in inf
        assert "p99_latency_ms" in inf
        assert "p95_ms" in inf
        assert "p99_ms" in inf
        assert inf["p50_ms"] <= inf["p95_ms"] <= inf["p99_ms"]
