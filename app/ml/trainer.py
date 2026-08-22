from typing import Dict, Any, Tuple
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    AdaBoostClassifier,
    BaggingClassifier,
    RandomForestRegressor,
    GradientBoostingRegressor,
    AdaBoostRegressor,
    BaggingRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge, Lasso, ElasticNet
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    log_loss,
    matthews_corrcoef,
)
import joblib
import numpy as np
import logging
from datetime import datetime, timezone
from app.core.safe_joblib import safe_load

logger = logging.getLogger(__name__)


def _get_xgboost():
    try:
        from xgboost import XGBClassifier, XGBRegressor
        return XGBClassifier, XGBRegressor
    except ImportError:
        return None, None


def _get_lightgbm():
    try:
        from lightgbm import LGBMClassifier, LGBMRegressor
        return LGBMClassifier, LGBMRegressor
    except ImportError:
        return None, None


def _get_catboost():
    try:
        from catboost import CatBoostClassifier, CatBoostRegressor
        return CatBoostClassifier, CatBoostRegressor
    except ImportError:
        return None, None


XGBClassifier, XGBRegressor = _get_xgboost()
LGBMClassifier, LGBMRegressor = _get_lightgbm()
CatBoostClassifier, CatBoostRegressor = _get_catboost()


class ModelTrainer:
    ALGORITHMS = {
        'random_forest': RandomForestClassifier,
        'gradient_boosting': GradientBoostingClassifier,
        'logistic_regression': LogisticRegression,
        'svm': SVC,
        'knn': KNeighborsClassifier,
        'decision_tree': DecisionTreeClassifier,
        'adaboost': AdaBoostClassifier,
        'bagging': BaggingClassifier,
        'mlp': MLPClassifier,
    }

    REGRESSION_ALGORITHMS = {
        'random_forest': RandomForestRegressor,
        'gradient_boosting': GradientBoostingRegressor,
        'ridge': Ridge,
        'lasso': Lasso,
        'elastic_net': ElasticNet,
        'svr': SVR,
        'knn': KNeighborsRegressor,
        'decision_tree': DecisionTreeRegressor,
        'adaboost': AdaBoostRegressor,
        'bagging': BaggingRegressor,
        'mlp': MLPRegressor,
    }

    DEFAULT_PARAMS = {
        'random_forest': {'n_estimators': 100, 'random_state': 42},
        'gradient_boosting': {'n_estimators': 100, 'random_state': 42},
        'logistic_regression': {'max_iter': 1000, 'random_state': 42},
        'svm': {'kernel': 'rbf', 'probability': True},
        'knn': {'n_neighbors': 5},
        'decision_tree': {'random_state': 42},
        'adaboost': {'n_estimators': 100, 'random_state': 42},
        'bagging': {'n_estimators': 10, 'random_state': 42},
        'mlp': {'hidden_layer_sizes': (100, 50), 'max_iter': 500, 'random_state': 42},
    }

    REGRESSION_DEFAULT_PARAMS = {
        'random_forest': {'n_estimators': 100, 'random_state': 42},
        'gradient_boosting': {'n_estimators': 100, 'random_state': 42},
        'ridge': {'alpha': 1.0},
        'lasso': {'alpha': 1.0},
        'elastic_net': {'alpha': 1.0, 'l1_ratio': 0.5},
        'svr': {'kernel': 'rbf'},
        'knn': {'n_neighbors': 5},
        'decision_tree': {'random_state': 42},
        'adaboost': {'n_estimators': 100, 'random_state': 42},
        'bagging': {'n_estimators': 10, 'random_state': 42},
        'mlp': {'hidden_layer_sizes': (100, 50), 'max_iter': 500, 'random_state': 42},
    }

    def __init__(self):
        self.model = None
        self.algorithm = None
        self.problem_type = 'classification'

        if XGBClassifier is not None:
            self.ALGORITHMS['xgboost'] = XGBClassifier
            self.REGRESSION_ALGORITHMS['xgboost'] = XGBRegressor
            self.DEFAULT_PARAMS['xgboost'] = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 6,
                'random_state': 42,
                'eval_metric': 'logloss',
                'use_label_encoder': False,
            }
            self.REGRESSION_DEFAULT_PARAMS['xgboost'] = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'max_depth': 6,
                'random_state': 42,
            }

        if LGBMClassifier is not None:
            self.ALGORITHMS['lightgbm'] = LGBMClassifier
            self.REGRESSION_ALGORITHMS['lightgbm'] = LGBMRegressor
            self.DEFAULT_PARAMS['lightgbm'] = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'num_leaves': 31,
                'random_state': 42,
                'verbose': -1,
            }
            self.REGRESSION_DEFAULT_PARAMS['lightgbm'] = {
                'n_estimators': 100,
                'learning_rate': 0.1,
                'num_leaves': 31,
                'random_state': 42,
                'verbose': -1,
            }

        if CatBoostClassifier is not None:
            self.ALGORITHMS['catboost'] = CatBoostClassifier
            self.REGRESSION_ALGORITHMS['catboost'] = CatBoostRegressor
            self.DEFAULT_PARAMS['catboost'] = {
                'iterations': 100,
                'learning_rate': 0.1,
                'depth': 6,
                'random_state': 42,
                'verbose': 0,
            }
            self.REGRESSION_DEFAULT_PARAMS['catboost'] = {
                'iterations': 100,
                'learning_rate': 0.1,
                'depth': 6,
                'random_state': 42,
                'verbose': 0,
            }

    def get_algorithms(self, problem_type: str = 'classification') -> Dict[str, Any]:
        if problem_type == 'regression':
            return {
                'algorithms': list(self.REGRESSION_ALGORITHMS.keys()),
                'default_params': self.REGRESSION_DEFAULT_PARAMS,
            }
        return {
            'algorithms': list(self.ALGORITHMS.keys()),
            'default_params': self.DEFAULT_PARAMS,
        }

    def train(
        self,
        X_train,
        y_train,
        algorithm: str = 'random_forest',
        parameters: Dict[str, Any] = None,
        problem_type: str = 'classification',
    ) -> Tuple[Any, Dict[str, Any]]:
        self.problem_type = problem_type

        if problem_type == 'regression':
            algos = self.REGRESSION_ALGORITHMS
            defaults = self.REGRESSION_DEFAULT_PARAMS
        else:
            algos = self.ALGORITHMS
            defaults = self.DEFAULT_PARAMS

        if algorithm not in algos:
            raise ValueError(f"Unknown algorithm: {algorithm}. Available: {list(algos.keys())}")

        self.algorithm = algorithm
        ModelClass = algos[algorithm]

        params = defaults.get(algorithm, {}).copy()
        if parameters:
            params.update(parameters)

        self.model = ModelClass(**params)
        self.model.fit(X_train, y_train)

        training_info = {
            'algorithm': algorithm,
            'parameters': params,
            'problem_type': problem_type,
            'trained_at': datetime.now(timezone.utc).isoformat(),
            'n_samples': len(X_train),
            'n_features': X_train.shape[1] if hasattr(X_train, 'shape') else 0,
        }

        return self.model, training_info

    def evaluate(self, X_test, y_test) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("Model not trained yet")

        y_pred = self.model.predict(X_test)

        if self.problem_type == 'regression':
            metrics = self._evaluate_regression(y_test, y_pred, X_test)
        else:
            metrics = self._evaluate_classification(y_test, y_pred, X_test)

        return metrics

    def _evaluate_classification(self, y_test, y_pred, X_test) -> Dict[str, Any]:
        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision_macro': float(precision_score(y_test, y_pred, average='macro', zero_division=0)),
            'recall_macro': float(recall_score(y_test, y_pred, average='macro', zero_division=0)),
            'f1_macro': float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
            'precision_weighted': float(precision_score(y_test, y_pred, average='weighted', zero_division=0)),
            'recall_weighted': float(recall_score(y_test, y_pred, average='weighted', zero_division=0)),
            'f1_weighted': float(f1_score(y_test, y_pred, average='weighted', zero_division=0)),
            'matthews_corrcoef': float(matthews_corrcoef(y_test, y_pred)),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
        }

        if hasattr(self.model, 'predict_proba'):
            try:
                y_proba = self.model.predict_proba(X_test)
                n_classes = len(np.unique(y_test))
                if n_classes == 2:
                    metrics['roc_auc'] = float(roc_auc_score(y_test, y_proba[:, 1]))
                    metrics['brier_score'] = float(np.mean((y_proba[:, 1] - y_test.astype(float)) ** 2))
                elif n_classes > 2:
                    metrics['roc_auc_ovr'] = float(roc_auc_score(y_test, y_proba, multi_class='ovr', average='macro'))
                    # Brier score for multiclass
                    from sklearn.preprocessing import label_binarize
                    classes = sorted(np.unique(y_test))
                    y_bin = label_binarize(y_test, classes=classes)
                    if y_bin.shape[1] == 1:
                        y_bin = np.hstack([1 - y_bin, y_bin])
                    metrics['brier_score'] = float(np.mean(np.sum((y_proba - y_bin) ** 2, axis=1)))

                metrics['log_loss'] = float(log_loss(y_test, y_proba))

                # Calibration via binned calibration (Expected Calibration Error)
                try:
                    from sklearn.calibration import calibration_curve
                    if n_classes == 2:
                        fraction_of_positives, mean_predicted_value = calibration_curve(
                            y_test, y_proba[:, 1], n_bins=10, strategy='uniform'
                        )
                        ece = float(np.mean(np.abs(fraction_of_positives - mean_predicted_value)))
                        metrics['expected_calibration_error'] = ece
                        metrics['calibration_curve'] = {
                            'fraction_of_positives': fraction_of_positives.tolist(),
                            'mean_predicted_value': mean_predicted_value.tolist(),
                        }
                except Exception:
                    pass
            except Exception as e:
                logger.warning(f"Probability-based metrics failed: {e}")

        return metrics

    def _evaluate_regression(self, y_test, y_pred, X_test) -> Dict[str, Any]:
        mse = float(mean_squared_error(y_test, y_pred))
        rmse = float(np.sqrt(mse))
        mae = float(mean_absolute_error(y_test, y_pred))
        r2 = float(r2_score(y_test, y_pred))

        ss_res = np.sum((np.array(y_test) - np.array(y_pred)) ** 2)
        ss_tot = np.sum((np.array(y_test) - np.mean(np.array(y_test))) ** 2)
        adjusted_r2 = float(1 - (1 - r2) * (len(y_test) - 1) / max(len(y_test) - X_test.shape[1] - 1, 1)) if X_test.shape[1] > 0 else r2

        mape = float(np.mean(np.abs((np.array(y_test) - np.array(y_pred)) / np.maximum(np.abs(np.array(y_test)), 1e-8))) * 100)

        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'adjusted_r2': adjusted_r2,
            'mape': mape,
            'max_error': float(np.max(np.abs(np.array(y_test) - np.array(y_pred)))),
            'median_absolute_error': float(np.median(np.abs(np.array(y_test) - np.array(y_pred)))),
        }

    def cross_validate(self, X, y, cv: int = 5) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("Model not trained yet")

        if self.problem_type == 'regression':
            scoring_metrics = ['r2', 'neg_mean_squared_error', 'neg_mean_absolute_error']
        else:
            scoring_metrics = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']

        cv_results = {}
        for metric in scoring_metrics:
            try:
                scores = cross_val_score(self.model, X, y, cv=cv, scoring=metric)
                cv_results[metric] = {
                    'mean': float(scores.mean()),
                    'std': float(scores.std()),
                    'scores': scores.tolist(),
                }
            except Exception as e:
                cv_results[metric] = {'error': str(e)}

        return cv_results

    def benchmark(self, X_test, y_test, feature_names: list = None) -> Dict[str, Any]:
        import time

        if self.model is None:
            raise ValueError("Model not trained yet")

        metrics = self.evaluate(X_test, y_test)

        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            self.model.predict(X_test[:1])
            latencies.append((time.perf_counter() - start) * 1000)

        inference_stats = {
            'mean_latency_ms': round(float(np.mean(latencies)), 3),
            'std_latency_ms': round(float(np.std(latencies)), 3),
            'min_latency_ms': round(float(np.min(latencies)), 3),
            'max_latency_ms': round(float(np.max(latencies)), 3),
            'p50_latency_ms': round(float(np.percentile(latencies, 50)), 3),
            'p95_latency_ms': round(float(np.percentile(latencies, 95)), 3),
            'p99_latency_ms': round(float(np.percentile(latencies, 99)), 3),
            'samples_benchmarked': 100,
        }

        import sys
        model_size_bytes = sys.getsizeof(self.model)
        try:
            import tempfile, os, joblib as jl
            with tempfile.NamedTemporaryFile(suffix='.joblib', delete=False) as f:
                jl.dump(self.model, f.name)
                model_size_bytes = os.path.getsize(f.name)
                os.unlink(f.name)
        except Exception:
            pass

        feature_importance = None
        if feature_names:
            feature_importance = self.get_feature_importance(feature_names)

        problem_type = self.problem_type

        if problem_type == 'classification':
            primary_metric = metrics.get('f1_weighted', metrics.get('accuracy', 0))
            primary_metric_name = 'f1_weighted'
        else:
            primary_metric = metrics.get('r2', 0)
            primary_metric_name = 'r2'

        return {
            'algorithm': self.algorithm,
            'problem_type': problem_type,
            'metrics': metrics,
            'inference': inference_stats,
            'model_size_bytes': model_size_bytes,
            'model_size_mb': round(model_size_bytes / (1024 * 1024), 4),
            'feature_importance': feature_importance,
            'primary_metric': primary_metric_name,
            'primary_metric_value': primary_metric,
            'benchmark_timestamp': datetime.now(timezone.utc).isoformat(),
        }

    def save_model(self, filepath: str) -> None:
        if self.model is None:
            raise ValueError("No model to save")

        model_data = {
            'model': self.model,
            'algorithm': self.algorithm,
            'problem_type': self.problem_type,
        }
        joblib.dump(model_data, filepath)

    def load_model(self, filepath: str) -> Any:
        model_data = safe_load(filepath)
        self.model = model_data['model']
        self.algorithm = model_data.get('algorithm', 'unknown')
        self.problem_type = model_data.get('problem_type', 'classification')
        return self.model

    def get_feature_importance(self, feature_names: list) -> Dict[str, float] | None:
        if self.model is None:
            return None

        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            return dict(sorted(
                zip(feature_names, importance.tolist()),
                key=lambda x: x[1],
                reverse=True,
            ))
        elif hasattr(self.model, 'coef_'):
            importance = np.abs(self.model.coef_).mean(axis=0) if self.model.coef_.ndim > 1 else np.abs(self.model.coef_)
            return dict(sorted(
                zip(feature_names, importance.tolist()),
                key=lambda x: x[1],
                reverse=True,
            ))

        return None
