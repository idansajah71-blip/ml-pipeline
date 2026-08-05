from typing import Dict, Any, Optional, Tuple
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    RandomForestRegressor,
    GradientBoostingRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

CLASSIFICATION_GRIDS = {
    'random_forest': {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
    },
    'gradient_boosting': {
        'n_estimators': [50, 100, 200],
        'learning_rate': [0.01, 0.1, 0.2],
        'max_depth': [3, 5, 7],
        'min_samples_split': [2, 5],
    },
    'logistic_regression': {
        'C': [0.01, 0.1, 1.0, 10.0],
        'penalty': ['l2'],
        'solver': ['lbfgs', 'liblinear'],
    },
    'svm': {
        'C': [0.1, 1.0, 10.0],
        'kernel': ['rbf', 'linear'],
        'gamma': ['scale', 'auto'],
    },
    'knn': {
        'n_neighbors': [3, 5, 7, 11],
        'weights': ['uniform', 'distance'],
        'metric': ['euclidean', 'manhattan'],
    },
    'decision_tree': {
        'max_depth': [None, 5, 10, 20],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
    },
}

REGRESSION_GRIDS = {
    'random_forest': {
        'n_estimators': [50, 100, 200],
        'max_depth': [None, 10, 20, 30],
        'min_samples_split': [2, 5, 10],
        'min_samples_leaf': [1, 2, 4],
    },
    'gradient_boosting': {
        'n_estimators': [50, 100, 200],
        'learning_rate': [0.01, 0.1, 0.2],
        'max_depth': [3, 5, 7],
        'min_samples_split': [2, 5],
    },
    'ridge': {
        'alpha': [0.01, 0.1, 1.0, 10.0, 100.0],
    },
}

CLASSIFICATION_MODELS = {
    'random_forest': RandomForestClassifier,
    'gradient_boosting': GradientBoostingClassifier,
    'logistic_regression': LogisticRegression,
    'svm': SVC,
    'knn': KNeighborsClassifier,
    'decision_tree': DecisionTreeClassifier,
}

REGRESSION_MODELS = {
    'random_forest': RandomForestRegressor,
    'gradient_boosting': GradientBoostingRegressor,
    'ridge': Ridge,
}


class HyperparameterTuner:
    """
    Hyperparameter tuning using GridSearchCV or RandomizedSearchCV.
    
    Supports both classification and regression tasks with
    predefined search spaces for common algorithms.
    """

    def __init__(self):
        self.best_params = None
        self.best_score = None
        self.best_model = None
        self.tuning_history = []

    def tune(
        self,
        model,
        X_train,
        y_train,
        algorithm: str,
        problem_type: str = 'classification',
        method: str = 'grid',
        cv: int = 5,
        n_iter: int = 50,
        scoring: Optional[str] = None,
        n_jobs: int = -1,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Perform hyperparameter tuning.
        
        Args:
            model: Base model to tune
            X_train: Training features
            y_train: Training labels
            algorithm: Algorithm name
            problem_type: 'classification' or 'regression'
            method: 'grid' for GridSearchCV, 'random' for RandomizedSearchCV
            cv: Number of cross-validation folds
            n_iter: Number of iterations for RandomizedSearchCV
            scoring: Scoring metric (auto-selected if None)
            n_jobs: Number of parallel jobs
            
        Returns:
            Tuple of (best_model, tuning_results)
        """
        if problem_type == 'classification':
            param_grid = CLASSIFICATION_GRIDS.get(algorithm, {})
        else:
            param_grid = REGRESSION_GRIDS.get(algorithm, {})

        if not param_grid:
            logger.warning(f"No parameter grid found for {algorithm}. Using default parameters.")
            return model, {'message': 'No tuning grid available', 'params': {}}

        if scoring is None:
            if problem_type == 'classification':
                scoring = 'f1_weighted'
            else:
                scoring = 'r2'

        start_time = datetime.now()

        try:
            if method == 'grid':
                searcher = GridSearchCV(
                    model,
                    param_grid,
                    cv=cv,
                    scoring=scoring,
                    n_jobs=n_jobs,
                    refit=True,
                    return_train_score=False,
                )
            else:
                searcher = RandomizedSearchCV(
                    model,
                    param_grid,
                    n_iter=min(n_iter, self._count_combinations(param_grid)),
                    cv=cv,
                    scoring=scoring,
                    n_jobs=n_jobs,
                    refit=True,
                    return_train_score=False,
                    random_state=42,
                )

            searcher.fit(X_train, y_train)

            duration = (datetime.now() - start_time).total_seconds()

            self.best_params = searcher.best_params_
            self.best_score = searcher.best_score_
            self.best_model = searcher.best_estimator_

            results = {
                'best_params': searcher.best_params_,
                'best_score': float(searcher.best_score_),
                'scoring_metric': scoring,
                'method': method,
                'cv_folds': cv,
                'duration_seconds': round(duration, 2),
                'n_candidates': len(searcher.cv_results_['params']),
                'completed_at': datetime.utcnow().isoformat(),
            }

            self.tuning_history.append(results)

            return self.best_model, results

        except Exception as e:
            logger.error(f"Hyperparameter tuning failed: {e}", exc_info=True)
            return model, {
                'error': str(e),
                'message': 'Tuning failed, using original model',
                'params': {},
            }

    def _count_combinations(self, param_grid: Dict) -> int:
        """Count total parameter combinations."""
        count = 1
        for values in param_grid.values():
            count *= len(values)
        return count

    def get_search_space_summary(self, algorithm: str, problem_type: str = 'classification') -> Dict[str, Any]:
        """Get summary of search space for an algorithm."""
        if problem_type == 'classification':
            grid = CLASSIFICATION_GRIDS.get(algorithm, {})
        else:
            grid = REGRESSION_GRIDS.get(algorithm, {})

        if not grid:
            return {'algorithm': algorithm, 'message': 'No tuning grid available'}

        total_combinations = self._count_combinations(grid)

        return {
            'algorithm': algorithm,
            'problem_type': problem_type,
            'parameters': {k: v if len(v) <= 5 else f"[{len(v)} options]" for k, v in grid.items()},
            'total_combinations': total_combinations,
        }


def tune_hyperparameters(
    model,
    X_train,
    y_train,
    algorithm: str,
    problem_type: str = 'classification',
    method: str = 'grid',
    cv: int = 5,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Convenience function for hyperparameter tuning.
    
    Args:
        model: Base model to tune
        X_train: Training features
        y_train: Training labels
        algorithm: Algorithm name
        problem_type: 'classification' or 'regression'
        method: 'grid' or 'random'
        cv: Number of CV folds
        
    Returns:
        Tuple of (tuned_model, tuning_results)
    """
    tuner = HyperparameterTuner()
    return tuner.tune(
        model, X_train, y_train,
        algorithm=algorithm,
        problem_type=problem_type,
        method=method,
        cv=cv,
    )
