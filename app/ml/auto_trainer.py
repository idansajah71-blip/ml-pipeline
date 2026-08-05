from typing import Dict, Any, Tuple, List, Optional
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    RandomForestRegressor,
    GradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge, Lasso
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    mean_squared_error,
    mean_absolute_error,
    r2_score,
    confusion_matrix,
    classification_report,
    roc_auc_score,
)
import joblib
import numpy as np
from datetime import datetime
import logging

from app.core.safe_joblib import safe_load

logger = logging.getLogger(__name__)


class AutoTrainer:
    """
    Automated model trainer for 'simple' mode.
    Automatically selects the best model based on data characteristics.
    """

    CLASSIFICATION_MODELS = {
        'random_forest': {
            'class': RandomForestClassifier,
            'default_params': {'n_estimators': 100, 'random_state': 42, 'n_jobs': -1},
            'description': 'Good general-purpose classifier, handles mixed features well',
        },
        'gradient_boosting': {
            'class': GradientBoostingClassifier,
            'default_params': {'n_estimators': 100, 'random_state': 42},
            'description': 'High accuracy, good for structured data',
        },
        'logistic_regression': {
            'class': LogisticRegression,
            'default_params': {'max_iter': 1000, 'random_state': 42},
            'description': 'Fast, interpretable, good baseline',
        },
    }

    REGRESSION_MODELS = {
        'random_forest': {
            'class': RandomForestRegressor,
            'default_params': {'n_estimators': 100, 'random_state': 42, 'n_jobs': -1},
            'description': 'Good general-purpose regressor',
        },
        'gradient_boosting': {
            'class': GradientBoostingRegressor,
            'default_params': {'n_estimators': 100, 'random_state': 42},
            'description': 'High accuracy for regression tasks',
        },
        'ridge': {
            'class': Ridge,
            'default_params': {'alpha': 1.0},
            'description': 'Regularized linear regression',
        },
    }

    def __init__(self):
        self.model = None
        self.algorithm = None
        self.problem_type = None

    def _select_best_model(
        self,
        X_train,
        y_train,
        problem_type: str,
        n_samples: int,
        n_features: int,
    ) -> str:
        """Select the best model based on data characteristics."""
        if problem_type == 'classification':
            models = self.CLASSIFICATION_MODELS
        else:
            models = self.REGRESSION_MODELS

        if n_samples < 1000:
            candidates = ['logistic_regression', 'random_forest'] if problem_type == 'classification' else ['ridge', 'random_forest']
        elif n_samples < 10000:
            candidates = ['random_forest', 'gradient_boosting']
        else:
            candidates = ['gradient_boosting', 'random_forest']

        candidates = [c for c in candidates if c in models]

        best_score = -1
        best_model = candidates[0]

        for model_name in candidates:
            try:
                model_info = models[model_name]
                model = model_info['class'](**model_info['default_params'])

                if problem_type == 'classification':
                    scoring = 'f1_weighted' if len(np.unique(y_train)) > 2 else 'accuracy'
                else:
                    scoring = 'r2'

                scores = cross_val_score(model, X_train, y_train, cv=min(5, n_samples // 10), scoring=scoring)
                mean_score = scores.mean()

                if mean_score > best_score:
                    best_score = mean_score
                    best_model = model_name

            except Exception as e:
                logger.warning(f"Cross-validation failed for {model_name}: {e}")
                continue

        return best_model

    def auto_train(
        self,
        X_train,
        y_train,
        problem_type: str,
        n_samples: int,
        n_features: int,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Automatically select and train the best model.
        
        Returns:
            Tuple of (trained_model, training_info)
        """
        self.problem_type = problem_type

        self.algorithm = self._select_best_model(
            X_train, y_train, problem_type, n_samples, n_features
        )

        if problem_type == 'classification':
            model_info = self.CLASSIFICATION_MODELS[self.algorithm]
        else:
            model_info = self.REGRESSION_MODELS[self.algorithm]

        params = model_info['default_params'].copy()

        self.model = model_info['class'](**params)
        self.model.fit(X_train, y_train)

        training_info = {
            'algorithm': self.algorithm,
            'parameters': params,
            'problem_type': problem_type,
            'model_description': model_info['description'],
            'trained_at': datetime.utcnow().isoformat(),
            'n_samples': n_samples,
            'n_features': n_features,
            'auto_selected': True,
        }

        return self.model, training_info

    def evaluate(self, X_test, y_test, problem_type: str) -> Dict[str, Any]:
        """Evaluate the trained model with appropriate metrics."""
        if self.model is None:
            raise ValueError("Model not trained yet")

        y_pred = self.model.predict(X_test)

        if problem_type == 'classification':
            metrics = {
                'accuracy': float(accuracy_score(y_test, y_pred)),
                'precision_macro': float(precision_score(y_test, y_pred, average='macro', zero_division=0)),
                'recall_macro': float(recall_score(y_test, y_pred, average='macro', zero_division=0)),
                'f1_macro': float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
                'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
                'classification_report': classification_report(y_test, y_pred, output_dict=True),
            }

            if hasattr(self.model, 'predict_proba'):
                try:
                    y_proba = self.model.predict_proba(X_test)
                    if len(np.unique(y_test)) == 2:
                        metrics['roc_auc'] = float(roc_auc_score(y_test, y_proba[:, 1]))
                    else:
                        metrics['roc_auc'] = float(roc_auc_score(y_test, y_proba, multi_class='ovr'))
                except Exception:
                    pass
        else:
            metrics = {
                'mse': float(mean_squared_error(y_test, y_pred)),
                'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred))),
                'mae': float(mean_absolute_error(y_test, y_pred)),
                'r2': float(r2_score(y_test, y_pred)),
            }

        return metrics

    def get_feature_importance(self, feature_names: list) -> Dict[str, float] | None:
        """Get feature importance from the trained model."""
        if self.model is None:
            return None

        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            return dict(zip(feature_names, importance.tolist()))
        elif hasattr(self.model, 'coef_'):
            importance = np.abs(self.model.coef_).mean(axis=0) if len(self.model.coef_.shape) > 1 else np.abs(self.model.coef_)
            return dict(zip(feature_names, importance.tolist()))

        return None

    def save_model(self, filepath: str) -> None:
        """Save the trained model."""
        if self.model is None:
            raise ValueError("No model to save")

        model_data = {
            'model': self.model,
            'algorithm': self.algorithm,
            'problem_type': self.problem_type,
        }
        joblib.dump(model_data, filepath)

    def load_model(self, filepath: str) -> Any:
        """Load a trained model."""
        model_data = safe_load(filepath)
        self.model = model_data['model']
        self.algorithm = model_data['algorithm']
        self.problem_type = model_data.get('problem_type', 'classification')
        return self.model
