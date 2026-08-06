import pytest
import os
import tempfile
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock


class TestMarketplaceService:
    """Unit tests for marketplace business logic."""

    def test_marketplace_module_imports(self):
        from app.api import marketplace
        assert hasattr(marketplace, 'router')

    def test_marketplace_router_has_endpoints(self):
        from app.api.marketplace import router
        routes = [r.path for r in router.routes]
        assert '/share' in routes or any('share' in r for r in routes)
        assert '/discover' in routes or any('discover' in r for r in routes)


class TestServingService:
    """Unit tests for serving business logic."""

    def test_serving_module_imports(self):
        from app.api import serving
        assert hasattr(serving, 'router')

    def test_serving_router_has_endpoints(self):
        from app.api.serving import router
        routes = [r.path for r in router.routes]
        assert any('endpoint' in r for r in routes)


class TestEnsembleModule:
    """Unit tests for ensemble business logic."""

    def test_ensemble_module_imports(self):
        from app.api import ensemble
        assert hasattr(ensemble, 'router')

    def test_ensemble_router_has_endpoints(self):
        from app.api.ensemble import router
        routes = [r.path for r in router.routes]
        assert len(routes) > 0


class TestExplainabilityDashboard:
    """Unit tests for explainability dashboard."""

    def test_module_imports(self):
        from app.api import explainability_dashboard
        assert hasattr(explainability_dashboard, 'router')

    def test_router_has_endpoints(self):
        from app.api.explainability_dashboard import router
        routes = [r.path for r in router.routes]
        assert any('global' in r for r in routes)
        assert any('prediction' in r for r in routes)

    def test_lime_explainer_init(self):
        from app.ml.lime_explainer import LIMEExplainer
        explainer = LIMEExplainer()
        assert explainer.is_available in (True, False)

    def test_lime_explain_with_lime(self):
        from app.ml.lime_explainer import explain_with_lime
        from sklearn.ensemble import RandomForestClassifier

        X = np.random.randn(50, 4)
        y = np.random.choice([0, 1], size=50)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X, y)

        result = explain_with_lime(model, X, X[0], ["f1", "f2", "f3", "f4"])
        assert result['method'] == 'lime'


class TestFeatureMonitoring:
    """Unit tests for feature monitoring."""

    def test_module_imports(self):
        from app.api import feature_monitoring
        assert hasattr(feature_monitoring, 'router')

    def test_model_monitor_init(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        assert monitor.is_available in (True, False)

    def test_fallback_drift(self):
        import pandas as pd
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        ref = pd.DataFrame({"x": np.random.randn(100)})
        cur = pd.DataFrame({"x": np.random.randn(100)})
        result = monitor.detect_data_drift(ref, cur)
        assert 'drift_detected' in result

    def test_fallback_quality(self):
        import pandas as pd
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = monitor.check_data_quality(df)
        assert 'quality_issues' in result


class TestCostTracking:
    """Unit tests for cost tracking."""

    def test_module_imports(self):
        from app.api import cost_tracking
        assert hasattr(cost_tracking, 'router')

    def test_router_has_endpoints(self):
        from app.api.cost_tracking import router
        routes = [r.path for r in router.routes]
        assert len(routes) > 0


class TestQuotaService:
    """Unit tests for API quota service."""

    def test_tier_limits_defined(self):
        from app.services.api_quota_service import APIQuotaService
        assert 'free' in APIQuotaService.TIER_LIMITS
        assert 'starter' in APIQuotaService.TIER_LIMITS
        assert 'pro' in APIQuotaService.TIER_LIMITS
        assert 'enterprise' in APIQuotaService.TIER_LIMITS

    def test_tier_limits_have_training(self):
        from app.services.api_quota_service import APIQuotaService
        for tier, limits in APIQuotaService.TIER_LIMITS.items():
            assert 'training_daily' in limits, f"{tier} missing training_daily"
            assert 'training_monthly' in limits, f"{tier} missing training_monthly"

    def test_tier_limits_ascending(self):
        from app.services.api_quota_service import APIQuotaService
        tiers = ['free', 'starter', 'pro', 'enterprise']
        for key in ['rpm', 'daily', 'monthly', 'training_daily', 'training_monthly']:
            values = [APIQuotaService.TIER_LIMITS[t][key] for t in tiers]
            assert values == sorted(values), f"{key} limits not ascending: {values}"


class TestRetentionService:
    """Unit tests for data retention."""

    def test_retention_module_imports(self):
        from app.services import retention_service
        assert hasattr(retention_service, 'DataRetentionService')

    def test_retention_policies_defined(self):
        from app.services.retention_service import RETENTION_POLICIES
        assert 'free' in RETENTION_POLICIES
        assert 'pro' in RETENTION_POLICIES


class TestOrganizations:
    """Unit tests for organizations."""

    def test_module_imports(self):
        from app.api import organizations
        assert hasattr(organizations, 'router')


class TestModelVersions:
    """Unit tests for model versions."""

    def test_module_imports(self):
        from app.api import model_versions
        assert hasattr(model_versions, 'router')


class TestBatchTasks:
    """Unit tests for batch prediction tasks."""

    def test_module_imports(self):
        from app.ml import batch_tasks
        assert hasattr(batch_tasks, 'batch_predict_task')


class TestFeatureStore:
    """Unit tests for feature store."""

    def test_module_imports(self):
        from app.api import feature_store
        assert hasattr(feature_store, 'router')

    def test_feature_store_service_imports(self):
        from app.services.feature_store_service import FeatureStoreService
        assert FeatureStoreService is not None


class TestDataValidationModule:
    """Unit tests for data validation."""

    def test_validator_init(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()
        assert validator.is_available in (True, False)

    def test_auto_checks(self):
        import pandas as pd
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({"a": range(10), "b": ["x"] * 10})
        checks = validator._auto_generate_checks(df)
        assert isinstance(checks, list)

    def test_validate_dataset(self):
        import pandas as pd
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({"f1": range(20), "f2": range(20), "target": [0, 1] * 10})
        result = validator.validate_dataset(df, "test")
        assert 'checks' in result
        assert 'summary' in result

    def test_validate_for_training(self):
        import pandas as pd
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({"f1": range(20), "target": [0, 1] * 10})
        result = validator.validate_for_training(df, "target")
        assert 'checks' in result or 'error' in result


class TestMLflowTrackerModule:
    """Unit tests for MLflow tracker."""

    def test_tracker_init(self):
        from app.ml.mlflow_tracker import MLflowTracker
        tracker = MLflowTracker()
        assert tracker.is_available in (True, False)

    def test_graceful_degradation(self):
        from app.ml.mlflow_tracker import MLflowTracker
        tracker = MLflowTracker()
        tracker.is_available = False

        assert tracker.start_run() is None
        tracker.log_params({"k": "v"})
        tracker.log_metrics({"acc": 0.9})
        tracker.end_run()

    def test_factory_function(self):
        from app.ml.mlflow_tracker import get_mlflow_tracker
        t = get_mlflow_tracker(experiment_name="test")
        assert t.experiment_name == "test"
