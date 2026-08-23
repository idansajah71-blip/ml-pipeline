import pytest
from app.ml.profiler import DatasetProfiler


@pytest.fixture
def profiler():
    return DatasetProfiler()


@pytest.fixture
def sample_csv_bytes():
    csv_content = """feature1,feature2,feature3,target
1.0,2.0,3.0,class_a
4.0,5.0,6.0,class_b
7.0,8.0,9.0,class_a
10.0,11.0,12.0,class_b
13.0,14.0,15.0,class_a
16.0,17.0,18.0,class_b
19.0,20.0,21.0,class_a
22.0,23.0,24.0,class_b
25.0,26.0,27.0,class_a
28.0,29.0,30.0,class_b
"""
    return csv_content.encode()


@pytest.fixture
def csv_with_missing():
    csv_content = """feature1,feature2,feature3,target
1.0,2.0,3.0,class_a
4.0,,6.0,class_b
7.0,8.0,,class_a
10.0,11.0,12.0,class_b
,14.0,15.0,class_a
16.0,17.0,18.0,class_b
19.0,20.0,21.0,class_a
22.0,23.0,24.0,class_b
"""
    return csv_content.encode()


@pytest.fixture
def csv_imbalanced():
    csv_content = """feature1,feature2,target
1.0,2.0,class_a
4.0,5.0,class_a
7.0,8.0,class_a
10.0,11.0,class_a
13.0,14.0,class_a
16.0,17.0,class_a
19.0,20.0,class_a
22.0,23.0,class_b
25.0,26.0,class_c
"""
    return csv_content.encode()


class TestDatasetProfiler:
    def test_profile_basic(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        assert "summary" in result
        assert "column_profiles" in result
        assert "missing_values" in result
        assert "outliers" in result
        assert "correlations" in result
        assert "class_distribution" in result

    def test_profile_summary(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        summary = result["summary"]
        assert summary["rows"] == 10
        assert summary["columns"] == 4
        assert summary["numeric_columns"] == 3
        assert summary["categorical_columns"] == 1
        assert summary["duplicated_rows"] == 0

    def test_profile_column_profiles(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        profiles = result["column_profiles"]
        assert "feature1" in profiles
        assert "target" in profiles
        assert profiles["feature1"]["dtype"] in ("float64", "int64")
        assert profiles["target"]["unique_count"] == 2

    def test_profile_missing_values(self, profiler, csv_with_missing):
        result = profiler.profile(csv_with_missing, "test.csv", "target")
        missing = result["missing_values"]
        assert missing["total_missing"] > 0
        assert len(missing["columns_with_missing"]) > 0
        assert missing["complete_rows"] < missing["total_cells"]

    def test_profile_no_missing(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        missing = result["missing_values"]
        assert missing["total_missing"] == 0
        assert len(missing["columns_with_missing"]) == 0

    def test_profile_outliers(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        outliers = result["outliers"]
        assert "feature1" in outliers
        assert "iqr" in outliers["feature1"]
        assert "outlier_count" in outliers["feature1"]

    def test_profile_correlations(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        correlations = result["correlations"]
        assert "matrix" in correlations
        assert "strong_correlations" in correlations
        assert "feature1" in correlations["matrix"]

    def test_profile_class_distribution(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        dist = result["class_distribution"]
        assert dist["column"] == "target"
        assert dist["num_classes"] == 2
        assert "class_a" in dist["distribution"]
        assert "class_b" in dist["distribution"]
        assert dist["imbalance_ratio"] == 1.0

    def test_profile_imbalanced_classes(self, profiler, csv_imbalanced):
        result = profiler.profile(csv_imbalanced, "test.csv", "target")
        dist = result["class_distribution"]
        assert dist["is_imbalanced"] is True
        assert dist["imbalance_ratio"] > 3

    def test_profile_no_target_column(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv")
        assert "class_distribution" not in result

    def test_profile_unsupported_format(self, profiler):
        with pytest.raises(ValueError, match="Unsupported file format"):
            profiler.profile(b"data", "test.txt")

    def test_profile_numeric_statistics(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        stats = result["column_profiles"]["feature1"]["statistics"]
        assert "mean" in stats
        assert "std" in stats
        assert "min" in stats
        assert "max" in stats
        assert "skewness" in stats
        assert "kurtosis" in stats

    def test_profile_categorical_statistics(self, profiler, sample_csv_bytes):
        result = profiler.profile(sample_csv_bytes, "test.csv", "target")
        stats = result["column_profiles"]["target"]["statistics"]
        assert "top_values" in stats
        assert "mode" in stats
