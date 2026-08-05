from typing import Dict, Any, Tuple
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    AdaBoostClassifier,
    BaggingClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import cross_val_score
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
import joblib
import numpy as np
from datetime import datetime
from app.core.safe_joblib import safe_load


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

    def __init__(self):
        self.model = None
        self.algorithm = None

    def train(
        self,
        X_train,
        y_train,
        algorithm: str = 'random_forest',
        parameters: Dict[str, Any] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"Unknown algorithm: {algorithm}. Available: {list(self.ALGORITHMS.keys())}")

        self.algorithm = algorithm
        ModelClass = self.ALGORITHMS[algorithm]

        params = self.DEFAULT_PARAMS.get(algorithm, {}).copy()
        if parameters:
            params.update(parameters)

        self.model = ModelClass(**params)
        self.model.fit(X_train, y_train)

        training_info = {
            'algorithm': algorithm,
            'parameters': params,
            'trained_at': datetime.utcnow().isoformat(),
            'n_samples': len(X_train),
            'n_features': X_train.shape[1] if hasattr(X_train, 'shape') else 0,
        }

        return self.model, training_info

    def evaluate(self, X_test, y_test) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("Model not trained yet")

        y_pred = self.model.predict(X_test)

        metrics = {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'precision_macro': float(precision_score(y_test, y_pred, average='macro', zero_division=0)),
            'recall_macro': float(recall_score(y_test, y_pred, average='macro', zero_division=0)),
            'f1_macro': float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True),
        }

        return metrics

    def cross_validate(self, X, y, cv: int = 5) -> Dict[str, Any]:
        if self.model is None:
            raise ValueError("Model not trained yet")

        scoring_metrics = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro']
        cv_results = {}

        for metric in scoring_metrics:
            scores = cross_val_score(self.model, X, y, cv=cv, scoring=metric)
            cv_results[metric] = {
                'mean': float(scores.mean()),
                'std': float(scores.std()),
                'scores': scores.tolist(),
            }

        return cv_results

    def save_model(self, filepath: str) -> None:
        if self.model is None:
            raise ValueError("No model to save")

        model_data = {
            'model': self.model,
            'algorithm': self.algorithm,
        }
        joblib.dump(model_data, filepath)

    def load_model(self, filepath: str) -> Any:
        model_data = safe_load(filepath)
        self.model = model_data['model']
        self.algorithm = model_data['algorithm']
        return self.model

    def get_feature_importance(self, feature_names: list) -> Dict[str, float] | None:
        if self.model is None:
            return None

        if hasattr(self.model, 'feature_importances_'):
            importance = self.model.feature_importances_
            return dict(zip(feature_names, importance.tolist()))
        elif hasattr(self.model, 'coef_'):
            importance = np.abs(self.model.coef_).mean(axis=0)
            return dict(zip(feature_names, importance.tolist()))

        return None
