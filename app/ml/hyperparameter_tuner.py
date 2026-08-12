from typing import Dict, Any, Optional, Tuple, List
import numpy as np
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _get_optuna():
    try:
        import optuna
        optuna.logging.set_verbosity(optuna.logging.WARNING)
        return optuna
    except ImportError:
        return None


optuna = _get_optuna()


def _suggest_xgboost_params(trial, problem_type):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'random_state': 42,
    }
    if problem_type == 'classification':
        params['eval_metric'] = 'logloss'
        params['use_label_encoder'] = False
    return params


def _suggest_lightgbm_params(trial, problem_type):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 500),
        'num_leaves': trial.suggest_int('num_leaves', 20, 150),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 1.0),
        'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 1.0),
        'bagging_freq': trial.suggest_int('bagging_freq', 1, 7),
        'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10.0, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10.0, log=True),
        'random_state': 42,
        'verbose': -1,
    }
    return params


def _suggest_catboost_params(trial, problem_type):
    params = {
        'iterations': trial.suggest_int('iterations', 50, 500),
        'depth': trial.suggest_int('depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'l2_leaf_reg': trial.suggest_float('l2_leaf_reg', 1e-8, 10.0, log=True),
        'random_strength': trial.suggest_float('random_strength', 0.0, 10.0),
        'bagging_temperature': trial.suggest_float('bagging_temperature', 0.0, 10.0),
        'random_state': 42,
        'verbose': 0,
    }
    return params


def _suggest_random_forest_params(trial, problem_type):
    return {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 30) if trial.suggest_categorical('use_max_depth', [True, False]) else None,
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
        'random_state': 42,
    }


def _suggest_gradient_boosting_params(trial, problem_type):
    return {
        'n_estimators': trial.suggest_int('n_estimators', 50, 300),
        'max_depth': trial.suggest_int('max_depth', 3, 10),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'random_state': 42,
    }


def _suggest_svm_params(trial, problem_type):
    return {
        'C': trial.suggest_float('C', 0.01, 100.0, log=True),
        'kernel': trial.suggest_categorical('kernel', ['rbf', 'linear', 'poly']),
        'gamma': trial.suggest_categorical('gamma', ['scale', 'auto']),
        'probability': True,
    }


def _suggest_knn_params(trial, problem_type):
    return {
        'n_neighbors': trial.suggest_int('n_neighbors', 1, 20),
        'weights': trial.suggest_categorical('weights', ['uniform', 'distance']),
        'metric': trial.suggest_categorical('metric', ['euclidean', 'manhattan', 'minkowski']),
        'p': trial.suggest_int('p', 1, 5),
    }


def _suggest_logistic_regression_params(trial, problem_type):
    return {
        'C': trial.suggest_float('C', 0.01, 100.0, log=True),
        'penalty': trial.suggest_categorical('penalty', ['l1', 'l2']),
        'solver': trial.suggest_categorical('solver', ['lbfgs', 'liblinear', 'saga']),
        'max_iter': 1000,
        'random_state': 42,
    }


def _suggest_decision_tree_params(trial, problem_type):
    return {
        'max_depth': trial.suggest_int('max_depth', 3, 20) if trial.suggest_categorical('use_max_depth', [True, False]) else None,
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'criterion': trial.suggest_categorical('criterion', ['gini', 'entropy']),
        'random_state': 42,
    }


PARAM_SUGGESTERS = {
    'xgboost': _suggest_xgboost_params,
    'lightgbm': _suggest_lightgbm_params,
    'catboost': _suggest_catboost_params,
    'random_forest': _suggest_random_forest_params,
    'gradient_boosting': _suggest_gradient_boosting_params,
    'svm': _suggest_svm_params,
    'knn': _suggest_knn_params,
    'logistic_regression': _suggest_logistic_regression_params,
    'decision_tree': _suggest_decision_tree_params,
}


class HyperparameterTuner:
    """
    Hyperparameter tuning using Optuna with TPE sampler.
    
    Supports Bayesian optimization with pruning for efficient search
    across classification and regression tasks.
    """

    def __init__(self):
        self.best_params = None
        self.best_score = None
        self.best_model = None
        self.tuning_history = []
        self.study = None

    def tune(
        self,
        model_class,
        X_train,
        y_train,
        algorithm: str,
        problem_type: str = 'classification',
        n_trials: int = 50,
        cv: int = 5,
        scoring: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        n_jobs: int = 1,
    ) -> Tuple[Any, Dict[str, Any]]:
        suggest_fn = PARAM_SUGGESTERS.get(algorithm)
        if suggest_fn is None:
            logger.warning(f"No search space for {algorithm}. Using default params.")
            return model_class, {'message': f'No search space for {algorithm}', 'best_params': {}}

        if optuna is None:
            logger.warning("Optuna not installed. Falling back to default parameters.")
            return model_class, {
                'message': 'Optuna not installed. Using default parameters.',
                'best_params': {},
            }

        if scoring is None:
            scoring = 'f1_weighted' if problem_type == 'classification' else 'r2'

        from sklearn.model_selection import cross_val_score

        def objective(trial):
            params = suggest_fn(trial, problem_type)

            try:
                model_instance = model_class(**params)
                scores = cross_val_score(
                    model_instance, X_train, y_train,
                    cv=cv, scoring=scoring, n_jobs=1,
                )
                return float(scores.mean())
            except Exception as e:
                logger.warning(f"Trial failed: {e}")
                return float('-inf')

        start_time = datetime.now(timezone.utc)

        try:
            study = optuna.create_study(
                direction='maximize',
                sampler=optuna.samplers.TPESampler(seed=42),
                pruner=optuna.pruners.MedianPruner(n_warmup_steps=5),
            )
            study.optimize(
                objective,
                n_trials=n_trials,
                timeout=timeout_seconds,
                n_jobs=n_jobs,
                show_progress_bar=False,
            )

            self.study = study
            self.best_params = study.best_params
            self.best_score = study.best_value

            best_model = model_class(**self.best_params, random_state=42)
            best_model.fit(X_train, y_train)
            self.best_model = best_model

            duration = (datetime.now(timezone.utc) - start_time).total_seconds()

            results = {
                'best_params': study.best_params,
                'optimization_score': float(study.best_value),
                'scoring_metric': scoring,
                'method': 'optuna_tpe',
                'cv_folds': cv,
                'n_trials': len(study.trials),
                'duration_seconds': round(duration, 2),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'note': 'optimization_score is the CV score used during search. '
                        'It is optimistically biased. Always evaluate on a held-out test set '
                        'for the final generalization estimate.',
                'optimization_history': [
                    {
                        'trial': t.number,
                        'value': float(t.value) if t.value is not None else None,
                        'params': t.params,
                        'state': str(t.state),
                    }
                    for t in study.trials[-10:]
                ],
                'param_importances': self._get_param_importances(study),
            }

            self.tuning_history.append(results)
            return self.best_model, results

        except Exception as e:
            logger.error(f"Optuna tuning failed: {e}", exc_info=True)
            return model_class, {
                'error': str(e),
                'message': 'Tuning failed, using default model',
                'best_params': {},
            }

    def _get_param_importances(self, study) -> Dict[str, float]:
        try:
            import optuna
            importances = optuna.importance.get_param_importances(study)
            return {k: round(float(v), 6) for k, v in importances.items()}
        except Exception:
            return {}

    def get_search_space_summary(self, algorithm: str, problem_type: str = 'classification') -> Dict[str, Any]:
        suggest_fn = PARAM_SUGGESTERS.get(algorithm)
        if suggest_fn is None:
            return {'algorithm': algorithm, 'message': 'No tuning space available'}

        return {
            'algorithm': algorithm,
            'problem_type': problem_type,
            'method': 'optuna_tpe',
            'has_search_space': True,
        }


def tune_hyperparameters(
    model_class,
    X_train,
    y_train,
    algorithm: str,
    problem_type: str = 'classification',
    n_trials: int = 50,
    cv: int = 5,
    scoring: Optional[str] = None,
) -> Tuple[Any, Dict[str, Any]]:
    tuner = HyperparameterTuner()
    return tuner.tune(
        model_class, X_train, y_train,
        algorithm=algorithm,
        problem_type=problem_type,
        n_trials=n_trials,
        cv=cv,
        scoring=scoring,
    )
