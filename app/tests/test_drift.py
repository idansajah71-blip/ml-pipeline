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
