"""
Prediction Intervals — conformal prediction for regression.

Provides valid prediction intervals that have guaranteed coverage.
Uses split conformal prediction: a held-out calibration set is used
to compute nonconformity scores, then prediction intervals are
constructed by adding/subtracting the (1-alpha) quantile of those scores.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def conformal_prediction_interval(
    y_cal: np.ndarray,
    y_cal_pred: np.ndarray,
    y_pred: float,
    alpha: float = 0.1,
) -> Dict[str, float]:
    """
    Split conformal prediction interval.

    Args:
        y_cal: Ground truth on calibration set
        y_cal_pred: Model predictions on calibration set
        y_pred: Point prediction for new sample
        alpha: Significance level (e.g. 0.1 for 90% interval)

    Returns:
        Dict with 'lower', 'upper', 'coverage_target'
    """
    n = len(y_cal)
    residuals = np.abs(y_cal - y_cal_pred)
    quantile_level = np.ceil((1 - alpha) * (n + 1)) / n
    quantile_level = min(quantile_level, 1.0)
    q_hat = np.quantile(residuals, quantile_level)

    return {
        "lower": float(y_pred - q_hat),
        "upper": float(y_pred + q_hat),
        "coverage_target": float(1 - alpha),
        "nonconformity_score": float(q_hat),
        "calibration_set_size": n,
    }


def bootstrap_prediction_interval(
    model,
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_new: np.ndarray,
    n_bootstrap: int = 100,
    alpha: float = 0.1,
) -> Dict[str, Any]:
    """
    Bootstrap prediction interval for regression.

    Fits multiple bootstrap resamples of the training data,
    collects predictions, and takes percentile-based intervals.

    Args:
        model: sklearn-compatible model
        X_train: Training features
        y_train: Training targets
        X_new: New samples to predict
        n_bootstrap: Number of bootstrap resamples
        alpha: Significance level

    Returns:
        Dict with 'lower', 'upper', 'point_prediction', 'std_bootstrap'
    """
    from sklearn.utils import resample

    bootstrap_preds = []
    for _ in range(n_bootstrap):
        X_boot, y_boot = resample(X_train, y_train, random_state=None)
        model_clone = type(model)(**model.get_params())
        model_clone.fit(X_boot, y_boot)
        bootstrap_preds.append(model_clone.predict(X_new))

    bootstrap_preds = np.array(bootstrap_preds)
    lower = np.percentile(bootstrap_preds, 100 * alpha / 2, axis=0)
    upper = np.percentile(bootstrap_preds, 100 * (1 - alpha / 2), axis=0)
    point = np.mean(bootstrap_preds, axis=0)
    std = np.std(bootstrap_preds, axis=0)

    return {
        "lower": lower.tolist(),
        "upper": upper.tolist(),
        "point_prediction": point.tolist(),
        "std_bootstrap": std.tolist(),
        "coverage_target": 1 - alpha,
        "n_bootstrap": n_bootstrap,
    }


def compute_empirical_coverage(
    y_true: np.ndarray, lower: np.ndarray, upper: np.ndarray
) -> Dict[str, float]:
    """Compute empirical coverage and average interval width."""
    in_interval = (y_true >= lower) & (y_true <= upper)
    coverage = float(np.mean(in_interval))
    avg_width = float(np.mean(upper - lower))
    return {
        "empirical_coverage": coverage,
        "avg_interval_width": avg_width,
        "n_samples": len(y_true),
    }
