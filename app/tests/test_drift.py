import pytest
import pandas as pd
import numpy as np
import io
from app.ml.drift import DriftDetector


@pytest.fixture
def detector():
    return DriftDetector()


@pytest.fixture
def reference_csv():
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "feature1": np.random.normal(0, 1, n),
        "feature2": np.random.normal(5, 2, n),
        "feature3": np.random.uniform(0, 10, n),
    })
    return df.to_csv(index=False).encode()


@pytest.fixture
def current_csv_same():
    np.random.seed(43)
    n = 100
    df = pd.DataFrame({
        "feature1": np.random.normal(0, 1, n),
        "feature2": np.random.normal(5, 2, n),
        "feature3": np.random.uniform(0, 10, n),
    })
    return df.to_csv(index=False).encode()


@pytest.fixture
def current_csv_drifted():
    np.random.seed(44)
    n = 100
    df = pd.DataFrame({
        "feature1": np.random.normal(5, 1, n),
        "feature2": np.random.normal(0, 2, n),
        "feature3": np.random.uniform(10, 20, n),
    })
    return df.to_csv(index=False).encode()


class TestDriftDetector:
    def test_detect_no_drift(self, detector, reference_csv, current_csv_same):
        result = detector.detect(reference_csv, current_csv_same, "test.csv")
        assert result["drift_detected"] is False
        assert result["severity"] == "low"
        assert result["summary"]["drifted_features"] == 0

    def test_detect_drift(self, detector, reference_csv, current_csv_drifted):
        result = detector.detect(reference_csv, current_csv_drifted, "test.csv")
        assert result["drift_detected"] is True
        assert result["severity"] in ("medium", "high")
        assert result["summary"]["drifted_features"] > 0

    def test_psi_calculation(self, detector, reference_csv, current_csv_drifted):
        result = detector.detect(reference_csv, current_csv_drifted, "test.csv")
        assert "psi" in result
        assert "feature1" in result["psi"]
        assert "psi" in result["psi"]["feature1"]
        assert isinstance(result["psi"]["feature1"]["psi"], float)

    def test_ks_test(self, detector, reference_csv, current_csv_drifted):
        result = detector.detect(reference_csv, current_csv_drifted, "test.csv")
        assert "ks_test" in result
        assert "feature1" in result["ks_test"]
        assert "statistic" in result["ks_test"]["feature1"]
        assert "p_value" in result["ks_test"]["feature1"]

    def test_distribution_shift(self, detector, reference_csv, current_csv_drifted):
        result = detector.detect(reference_csv, current_csv_drifted, "test.csv")
        assert "distribution_shift" in result
        assert "feature1" in result["distribution_shift"]
        shift = result["distribution_shift"]["feature1"]
        assert "ref_mean" in shift
        assert "curr_mean" in shift
        assert "mean_shift" in shift

    def test_custom_thresholds(self, detector, reference_csv, current_csv_drifted):
        result = detector.detect(
            reference_csv, current_csv_drifted, "test.csv",
            threshold_psi=0.01, threshold_ks=0.1
        )
        assert result["thresholds"]["psi"] == 0.01
        assert result["thresholds"]["ks"] == 0.1

    def test_severity_levels(self, detector, reference_csv, current_csv_same):
        result = detector.detect(reference_csv, current_csv_same, "test.csv")
        assert result["severity"] == "low"

    def test_unsupported_format(self, detector):
        with pytest.raises(ValueError, match="Unsupported file format"):
            detector.detect(b"data", b"data", "test.txt")

    def test_drifted_features_list(self, detector, reference_csv, current_csv_drifted):
        result = detector.detect(reference_csv, current_csv_drifted, "test.csv")
        assert "drifted_features" in result
        assert isinstance(result["drifted_features"], list)
        if result["drifted_features"]:
            feat = result["drifted_features"][0]
            assert "feature" in feat
            assert "metric" in feat
            assert "value" in feat


class TestCategoricalDrift:
    def test_categorical_drift_detected(self):
        detector = DriftDetector()
        np.random.seed(42)
        n = 200
        ref_df = pd.DataFrame({
            "cat_col": np.random.choice(["A", "B", "C"], n, p=[0.5, 0.3, 0.2]),
            "num_col": np.random.randn(n),
        })
        curr_df = pd.DataFrame({
            "cat_col": np.random.choice(["A", "B", "C", "D"], n, p=[0.1, 0.1, 0.1, 0.7]),
            "num_col": np.random.randn(n),
        })
        ref_bytes = ref_df.to_csv(index=False).encode()
        curr_bytes = curr_df.to_csv(index=False).encode()
        result = detector.detect(ref_bytes, curr_bytes, "test.csv")
        assert "categorical_psi" in result
        assert "cat_col" in result["categorical_psi"]
        assert result["categorical_psi"]["cat_col"]["psi"] > 0

    def test_categorical_no_drift(self):
        detector = DriftDetector()
        np.random.seed(42)
        n = 200
        df = pd.DataFrame({
            "cat_col": np.random.choice(["A", "B", "C"], n),
            "num_col": np.random.randn(n),
        })
        ref_bytes = df.to_csv(index=False).encode()
        result = detector.detect(ref_bytes, ref_bytes, "test.csv")
        assert result["categorical_psi"]["cat_col"]["drifted"] == False


class TestMissingnessDrift:
    def test_missingness_drift(self):
        detector = DriftDetector()
        np.random.seed(42)
        n = 200
        ref_df = pd.DataFrame({
            "f1": np.random.randn(n),
            "f2": np.random.randn(n),
        })
        curr_df = pd.DataFrame({
            "f1": np.where(np.random.rand(n) > 0.5, np.nan, np.random.randn(n)),
            "f2": np.random.randn(n),
        })
        ref_bytes = ref_df.to_csv(index=False).encode()
        curr_bytes = curr_df.to_csv(index=False).encode()
        result = detector.detect(ref_bytes, curr_bytes, "test.csv")
        assert "missingness" in result
        assert result["missingness"]["f1"]["drifted"] is True
        assert result["missingness"]["f2"]["drifted"] is False


class TestSchemaDrift:
    def test_schema_drift_adds_columns(self):
        detector = DriftDetector()
        np.random.seed(42)
        n = 100
        ref_df = pd.DataFrame({"f1": np.random.randn(n), "f2": np.random.randn(n)})
        curr_df = pd.DataFrame({"f1": np.random.randn(n), "f2": np.random.randn(n), "f3": np.random.randn(n)})
        ref_bytes = ref_df.to_csv(index=False).encode()
        curr_bytes = curr_df.to_csv(index=False).encode()
        result = detector.detect(ref_bytes, curr_bytes, "test.csv")
        assert result["schema_drift"]["drifted"] is True
        assert "f3" in result["schema_drift"]["added_columns"]

    def test_schema_drift_removes_columns(self):
        detector = DriftDetector()
        np.random.seed(42)
        n = 100
        ref_df = pd.DataFrame({"f1": np.random.randn(n), "f2": np.random.randn(n)})
        curr_df = pd.DataFrame({"f1": np.random.randn(n)})
        ref_bytes = ref_df.to_csv(index=False).encode()
        curr_bytes = curr_df.to_csv(index=False).encode()
        result = detector.detect(ref_bytes, curr_bytes, "test.csv")
        assert result["schema_drift"]["drifted"] is True
        assert "f2" in result["schema_drift"]["removed_columns"]


class TestPredictionDrift:
    def test_prediction_drift_detected(self):
        detector = DriftDetector()
        ref_preds = list(np.random.rand(200) * 0.3 + 0.1)
        curr_preds = list(np.random.rand(200) * 0.3 + 0.6)
        result = detector.detect_prediction_drift(ref_preds, curr_preds)
        assert result["drift_detected"] is True

    def test_prediction_no_drift(self):
        detector = DriftDetector()
        np.random.seed(42)
        preds = list(np.random.rand(200))
        result = detector.detect_prediction_drift(preds, preds)
        assert result["drift_detected"] is False
        assert result["psi"]["psi"] < 0.01


class TestImmutableBaseline:
    def test_freeze_baseline(self):
        detector = DriftDetector()
        np.random.seed(42)
        n = 200
        df = pd.DataFrame({
            "f1": np.random.randn(n),
            "f2": np.random.randn(n),
            "cat": np.random.choice(["A", "B"], n),
        })
        ref_bytes = df.to_csv(index=False).encode()
        baseline = detector.freeze_baseline(ref_bytes, "test.csv")
        assert baseline.is_frozen is True
        assert baseline.get("n_samples") == 200
        assert "f1" in baseline.get("bin_edges")

    def test_cannot_freeze_twice(self):
        detector = DriftDetector()
        np.random.seed(42)
        df = pd.DataFrame({"f1": np.random.randn(100)})
        ref_bytes = df.to_csv(index=False).encode()
        detector.freeze_baseline(ref_bytes, "test.csv")
        with pytest.raises(RuntimeError, match="already frozen"):
            detector.freeze_baseline(ref_bytes, "test.csv")

    def test_baseline_serialization(self):
        detector = DriftDetector()
        np.random.seed(42)
        df = pd.DataFrame({"f1": np.random.randn(100), "cat": np.random.choice(["A", "B"], 100)})
        ref_bytes = df.to_csv(index=False).encode()
        detector.freeze_baseline(ref_bytes, "test.csv")

        state = detector.baseline.to_dict()
        restored = detector.baseline.__class__.from_dict(state)
        assert restored.is_frozen is True
        assert restored.get("n_samples") == 100


class TestDelayedLabelMonitoring:
    def test_classification_monitoring(self):
        detector = DriftDetector()
        y_true = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 0])
        y_pred = np.array([0, 1, 0, 0, 1, 1, 0, 1, 1, 0])
        result = detector.monitor_delayed_labels(y_true, y_pred, 'classification')
        assert result['status'] == 'ok'
        assert 0 <= result['accuracy'] <= 1
        assert 0 <= result['f1_weighted'] <= 1
        assert result['n_samples'] == 10

    def test_regression_monitoring(self):
        detector = DriftDetector()
        y_true = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y_pred = np.array([1.1, 2.2, 2.8, 4.1, 4.9])
        result = detector.monitor_delayed_labels(y_true, y_pred, 'regression')
        assert result['status'] == 'ok'
        assert result['rmse'] < 1.0
        assert result['r2'] > 0.9
        assert result['n_samples'] == 5

    def test_empty_data(self):
        detector = DriftDetector()
        result = detector.monitor_delayed_labels(np.array([]), np.array([]))
        assert result['status'] == 'insufficient_data'
