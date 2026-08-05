import pytest
import pandas as pd
import numpy as np

from app.ml.data_validator import DataValidator, validate_training_data


@pytest.fixture
def validator():
    return DataValidator()


class TestDataValidator:
    def test_valid_dataset(self, validator):
        np.random.seed(42)
        df = pd.DataFrame({
            'f1': np.random.randn(100),
            'f2': np.random.randn(100),
            'target': np.random.choice(['a', 'b'], 100),
        })
        result = validator.validate_dataset(df, 'target')
        assert result.is_valid
        assert result.quality_score > 80

    def test_target_not_found(self, validator):
        df = pd.DataFrame({'f1': [1, 2, 3], 'target': ['a', 'b', 'c']})
        result = validator.validate_dataset(df, 'missing_col')
        assert not result.is_valid
        assert result.quality_score == 0.0
        assert any('not found' in e for e in result.errors)

    def test_too_few_samples_error(self, validator):
        df = pd.DataFrame({'f1': [1, 2, 3, 4, 5, 6, 7, 8, 9], 't': ['a'] * 9})
        result = validator.validate_dataset(df, 't')
        assert not result.is_valid
        assert any('10 samples' in e for e in result.errors)

    def test_small_dataset_warning(self, validator):
        df = pd.DataFrame({'f1': range(20), 't': ['a', 'b'] * 10})
        result = validator.validate_dataset(df, 't')
        assert result.is_valid
        assert len(result.warnings) > 0
        assert any('samples' in w for w in result.warnings)

    def test_constant_columns_detected(self, validator):
        df = pd.DataFrame({
            'const': [5] * 100,
            'f1': np.random.randn(100),
            'target': np.random.choice(['a', 'b'], 100),
        })
        result = validator.validate_dataset(df, 'target')
        assert any('one unique value' in w for w in result.warnings)
        assert any('const' in w for w in result.warnings)

    def test_high_cardinality_detected(self, validator):
        df = pd.DataFrame({
            'id_col': [f'id_{i}' for i in range(100)],
            'f1': np.random.randn(100),
            'target': np.random.choice(['a', 'b'], 100),
        })
        result = validator.validate_dataset(df, 'target')
        assert any('high cardinality' in w for w in result.warnings)

    def test_imbalanced_target(self, validator):
        df = pd.DataFrame({
            'f1': np.random.randn(100),
            'target': ['a'] * 95 + ['b'] * 5,
        })
        result = validator.validate_dataset(df, 'target')
        assert any('imbalanced' in w.lower() for w in result.warnings)

    def test_convenience_function(self):
        np.random.seed(42)
        df = pd.DataFrame({
            'f1': np.random.randn(100),
            'target': np.random.choice(['a', 'b'], 100),
        })
        result = validate_training_data(df, 'target')
        assert result.is_valid
        assert result.quality_score > 0

    def test_quality_score_decreases_with_issues(self, validator):
        np.random.seed(42)
        clean_df = pd.DataFrame({
            'f1': np.random.randn(100),
            'target': np.random.choice(['a', 'b'], 100),
        })
        clean_result = validator.validate_dataset(clean_df, 'target')

        dirty_df = pd.DataFrame({
            'const': [1] * 100,
            'f1': np.random.randn(100),
            'target': np.random.choice(['a', 'b'], 100),
        })
        dirty_result = validator.validate_dataset(dirty_df, 'target')
        assert dirty_result.quality_score <= clean_result.quality_score
