import pytest
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression, Ridge

from app.ml.hyperparameter_tuner import HyperparameterTuner, tune_hyperparameters


@pytest.fixture
def classifier_data():
    np.random.seed(42)
    X = np.random.randn(100, 4)
    y = (X[:, 0] + X[:, 1] > 0).astype(int)
    return X, y


@pytest.fixture
def regressor_data():
    np.random.seed(42)
    X = np.random.randn(100, 4)
    y = X[:, 0] * 2 + X[:, 1] * 0.5 + np.random.randn(100) * 0.1
    return X, y


class TestHyperparameterTuner:
    def test_grid_search_classification(self, classifier_data):
        X, y = classifier_data
        tuner = HyperparameterTuner()
        model = RandomForestClassifier(random_state=42)
        best_model, results = tuner.tune(
            model, X, y,
            algorithm='random_forest',
            problem_type='classification',
            method='grid',
            cv=3,
        )
        assert 'best_params' in results
        assert 'best_score' in results
        assert results['best_score'] > 0
        assert best_model is not None

    def test_random_search_classification(self, classifier_data):
        X, y = classifier_data
        tuner = HyperparameterTuner()
        model = RandomForestClassifier(random_state=42)
        best_model, results = tuner.tune(
            model, X, y,
            algorithm='random_forest',
            problem_type='classification',
            method='random',
            cv=3,
            n_iter=5,
        )
        assert 'best_params' in results
        assert results['method'] == 'random'

    def test_regression_tuning(self, regressor_data):
        X, y = regressor_data
        tuner = HyperparameterTuner()
        model = Ridge()
        best_model, results = tuner.tune(
            model, X, y,
            algorithm='ridge',
            problem_type='regression',
            method='grid',
            cv=3,
        )
        assert 'best_params' in results
        assert 'best_score' in results

    def test_no_grid_returns_original(self):
        tuner = HyperparameterTuner()
        model = LogisticRegression()
        X = np.random.randn(50, 3)
        y = np.random.choice([0, 1], 50)
        best_model, results = tuner.tune(
            model, X, y,
            algorithm='nonexistent_algo',
            problem_type='classification',
        )
        assert results.get('message') == 'No tuning grid available'
        assert best_model is model

    def test_search_space_summary(self):
        tuner = HyperparameterTuner()
        summary = tuner.get_search_space_summary('random_forest', 'classification')
        assert 'total_combinations' in summary
        assert summary['total_combinations'] > 0
        assert summary['algorithm'] == 'random_forest'

    def test_search_space_summary_no_grid(self):
        tuner = HyperparameterTuner()
        summary = tuner.get_search_space_summary('nonexistent', 'classification')
        assert 'message' in summary

    def test_tuning_history_recorded(self, classifier_data):
        X, y = classifier_data
        tuner = HyperparameterTuner()
        model = RandomForestClassifier(random_state=42)
        tuner.tune(model, X, y, algorithm='random_forest', cv=3)
        assert len(tuner.tuning_history) == 1
        assert 'best_params' in tuner.tuning_history[0]

    def test_convenience_function(self, classifier_data):
        X, y = classifier_data
        model = RandomForestClassifier(random_state=42)
        best_model, results = tune_hyperparameters(
            model, X, y,
            algorithm='random_forest',
            problem_type='classification',
            method='grid',
            cv=3,
        )
        assert 'best_params' in results
        assert best_model is not None
