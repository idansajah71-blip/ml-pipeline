import pandas as pd
import numpy as np

from app.ml.data_quality import DataQualityChecker


class TestDataQualityChecker:
    def test_all_checks_pass(self):
        np.random.seed(42)
        df = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
        })
        checker = DataQualityChecker(df)
        result = checker.run_all()
        assert result['status'] == 'passed'
        assert result['failed_checks'] == 0

    def test_missing_values_detected(self):
        df = pd.DataFrame({
            'f1': [1, 2, None] * 10,
            'f2': [1, 2, 3] * 10,
        })
        checker = DataQualityChecker(df)
        checker.check_missing_values(threshold=5.0)
        failed = [c for c in checker.checks if c['status'] == 'failed']
        assert len(failed) > 0
        assert 'f1' in failed[0]['name']

    def test_duplicates_detected(self):
        df = pd.DataFrame({
            'f1': [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3],
            'f2': [10, 20, 30] * 10,
        })
        checker = DataQualityChecker(df)
        checker.check_duplicates()
        failed = [c for c in checker.checks if c['status'] == 'failed']
        assert len(failed) > 0
        assert 'duplicates' in failed[0]['name']

    def test_outliers_detected(self):
        normal = np.random.randn(100)
        for i in range(6):
            normal[i] = 100 + i
        df = pd.DataFrame({'f1': normal})
        checker = DataQualityChecker(df)
        checker.check_outliers(z_threshold=3.0)
        failed = [c for c in checker.checks if c['status'] == 'failed']
        assert len(failed) > 0

    def test_value_range_violation(self):
        df = pd.DataFrame({'score': [1, 2, 3, 11, 12, 13, 4, 5, 6, 7]})
        checker = DataQualityChecker(df)
        checker.check_value_ranges({'score': (0, 10)})
        failed = [c for c in checker.checks if c['status'] == 'failed']
        assert len(failed) > 0
        assert 'range_score' in failed[0]['name']

    def test_uniqueness_check(self):
        df = pd.DataFrame({'id': [1, 1, 2, 3, 4, 5]})
        checker = DataQualityChecker(df)
        checker.check_uniqueness(['id'])
        failed = [c for c in checker.checks if c['status'] == 'failed']
        assert len(failed) > 0
        assert 'unique_id' in failed[0]['name']

    def test_score_calculation(self):
        df = pd.DataFrame({'f1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]})
        checker = DataQualityChecker(df)
        checker.run_all()
        assert checker.passed > 0
        score = (checker.passed / (checker.passed + checker.failed)) * 100
        assert 0 <= score <= 100
