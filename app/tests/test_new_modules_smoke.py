import numpy as np
import pandas as pd
from unittest.mock import patch


class TestMLflowTracker:
    """Smoke tests for MLflow experiment tracking module."""

    def test_import(self):
        from app.ml.mlflow_tracker import MLflowTracker
        assert MLflowTracker is not None

    def test_tracker_init_without_mlflow(self):
        from app.ml.mlflow_tracker import MLflowTracker
        with patch.dict('sys.modules', {'mlflow': None}):
            tracker = MLflowTracker()
            assert tracker.is_available is False

    def test_tracker_methods_graceful_without_mlflow(self):
        from app.ml.mlflow_tracker import MLflowTracker
        tracker = MLflowTracker()
        tracker.is_available = False

        assert tracker.start_run() is None
        tracker.log_params({"key": "value"})
        tracker.log_metrics({"accuracy": 0.95})
        tracker.log_model(None)
        tracker.end_run()

    def test_get_mlflow_tracker_factory(self):
        from app.ml.mlflow_tracker import get_mlflow_tracker
        tracker = get_mlflow_tracker(experiment_name="test")
        assert tracker is not None
        assert tracker.experiment_name == "test"

    def test_track_training_without_mlflow(self):
        from app.ml.mlflow_tracker import MLflowTracker
        tracker = MLflowTracker()
        tracker.is_available = False

        result = tracker.track_training(
            algorithm="random_forest",
            parameters={"n_estimators": 100},
            metrics={"accuracy": 0.9},
        )
        assert result is None


class TestLIMEExplainer:
    """Smoke tests for LIME explainability module."""

    def test_import(self):
        from app.ml.lime_explainer import LIMEExplainer
        assert LIMEExplainer is not None

    def test_explainer_init(self):
        from app.ml.lime_explainer import LIMEExplainer
        explainer = LIMEExplainer()
        assert explainer.is_available in (True, False)

    def test_explain_with_lime_function(self):
        from app.ml.lime_explainer import explain_with_lime
        from sklearn.ensemble import RandomForestClassifier

        X_train = np.random.randn(50, 4)
        y_train = np.random.choice([0, 1], size=50)
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)

        result = explain_with_lime(
            model=model,
            X_train=X_train,
            X_instance=X_train[0],
            feature_names=["f1", "f2", "f3", "f4"],
            problem_type="classification",
            num_features=3,
        )
        assert "method" in result
        assert result["method"] == "lime"

    def test_explainer_global_without_lime(self):
        from app.ml.lime_explainer import LIMEExplainer
        explainer = LIMEExplainer()
        explainer.is_available = False

        result = explainer.explain_global(
            None, np.random.randn(10, 4), ["f1", "f2", "f3", "f4"]
        )
        assert "error" in result


class TestModelMonitor:
    """Smoke tests for Evidently AI model monitoring module."""

    def test_import(self):
        from app.ml.model_monitor import ModelMonitor
        assert ModelMonitor is not None

    def test_monitor_init(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        assert monitor.is_available in (True, False)

    def test_fallback_drift_detection(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        ref_df = pd.DataFrame({"a": np.random.randn(100), "b": np.random.randn(100)})
        cur_df = pd.DataFrame({"a": np.random.randn(100) + 5, "b": np.random.randn(100)})

        result = monitor.detect_data_drift(ref_df, cur_df)
        assert "drift_detected" in result
        assert "method" in result

    def test_fallback_quality_check(self):
        from app.ml.model_monitor import ModelMonitor
        monitor = ModelMonitor()
        monitor.is_available = False

        df = pd.DataFrame({"a": [1, 2, None, 4], "b": [5, 6, 7, 8]})
        result = monitor.check_data_quality(df)
        assert "quality_issues" in result

    def test_detect_drift_function(self):
        from app.ml.model_monitor import detect_drift
        ref_df = pd.DataFrame({"x": np.random.randn(100)})
        cur_df = pd.DataFrame({"x": np.random.randn(100)})
        result = detect_drift(ref_df, cur_df)
        assert "drift_detected" in result

    def test_check_quality_function(self):
        from app.ml.model_monitor import check_quality
        df = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
        result = check_quality(df)
        assert "quality_issues" in result


class TestDataValidation:
    """Smoke tests for Great Expectations data validation module."""

    def test_import(self):
        from app.ml.data_validation import DataValidator
        assert DataValidator is not None

    def test_validator_init(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()
        assert validator.is_available in (True, False)

    def test_auto_checks_generation(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5],
            "b": ["x", "y", "z", "x", "y"],
            "c": [1.0, 2.0, 3.0, 4.0, 5.0],
        })

        checks = validator._auto_generate_checks(df)
        assert isinstance(checks, list)
        assert len(checks) > 0

    def test_validate_dataset(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({
            "feature1": range(20),
            "feature2": range(20),
            "target": [0, 1] * 10,
        })

        result = validator.validate_dataset(df, dataset_name="test_data")
        assert "checks" in result
        assert "summary" in result
        assert "passed" in result

    def test_validate_for_training(self):
        from app.ml.data_validation import DataValidator
        validator = DataValidator()

        df = pd.DataFrame({
            "feature1": range(20),
            "feature2": range(20),
            "target": [0, 1] * 10,
        })

        result = validator.validate_for_training(df, target_column="target")
        assert "checks" in result or "error" in result

    def test_validate_data_function(self):
        from app.ml.data_validation import validate_data
        df = pd.DataFrame({"x": range(10), "y": range(10)})
        result = validate_data(df)
        assert "checks" in result


class TestModelBenchmark:
    """Smoke tests for model benchmark functionality (in trainer)."""

    def test_trainer_has_benchmark_method(self):
        from app.ml.trainer import ModelTrainer
        trainer = ModelTrainer()
        assert hasattr(trainer, 'benchmark')

    def test_benchmark_classification(self):
        from app.ml.trainer import ModelTrainer

        X_train = np.random.randn(100, 4)
        y_train = np.random.choice([0, 1, 2], size=100)
        X_test = np.random.randn(20, 4)
        y_test = np.random.choice([0, 1, 2], size=20)

        trainer = ModelTrainer()
        trainer.train(X_train, y_train, algorithm="random_forest", problem_type="classification")

        result = trainer.benchmark(X_test, y_test, feature_names=["f1", "f2", "f3", "f4"])

        assert "algorithm" in result
        assert "metrics" in result
        assert "inference" in result
        assert "model_size_mb" in result
        assert "primary_metric" in result
        assert result["problem_type"] == "classification"

    def test_benchmark_regression(self):
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
        assert "mean_latency_ms" in result["inference"]
