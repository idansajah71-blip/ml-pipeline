"""
Performance Monitoring — delayed ground truth comparison.

When actual labels become available for predictions, compare
production performance against the training baseline to detect
concept drift or performance degradation.

Do NOT infer model degradation from feature drift alone.
Feature drift (PSI/KS) indicates distribution shift but does not
necessarily mean the model is performing worse.
Performance monitoring directly measures prediction quality
when ground truth arrives.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def evaluate_production_performance(
    predictions: List[Dict[str, Any]],
    ground_truths: List[Any],
    problem_type: str = "classification",
) -> Dict[str, Any]:
    """
    Evaluate production predictions against ground truth.

    Args:
        predictions: List of dicts with 'prediction' and optionally 'predicted_probability'
        ground_truths: List of actual values
        problem_type: 'classification' or 'regression'

    Returns:
        Dict with production metrics and comparison to baseline
    """
    import numpy as np

    if len(predictions) != len(ground_truths):
        raise ValueError(f"Predictions ({len(predictions)}) and ground truths ({len(ground_truths)}) must match")

    y_pred = np.array([p.get("prediction", p) for p in predictions])
    y_true = np.array(ground_truths)

    # Handle string predictions
    if y_pred.dtype.kind in ("U", "S", "O"):
        y_pred = y_pred.astype(str)
        y_true = y_true.astype(str)
        problem_type = "classification"

    if problem_type == "classification":
        from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
        metrics = {
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "f1_macro": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
            "precision_macro": float(precision_score(y_true, y_pred, average="macro", zero_division=0)),
            "recall_macro": float(recall_score(y_true, y_pred, average="macro", zero_division=0)),
        }

        # Brier score if probabilities available
        probs = [p.get("predicted_probability") or p.get("probability") for p in predictions]
        if all(p is not None for p in probs):
            probs_arr = np.array(probs, dtype=float)
            # Binary case
            y_bin = (y_true == y_true[1]).astype(float) if len(np.unique(y_true)) == 2 else None
            if y_bin is not None and len(np.unique(y_true)) == 2:
                metrics["brier_score"] = float(np.mean((probs_arr - y_bin) ** 2))
    else:
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        y_pred_num = y_pred.astype(float)
        y_true_num = y_true.astype(float)
        metrics = {
            "r2": float(r2_score(y_true_num, y_pred_num)),
            "rmse": float(np.sqrt(mean_squared_error(y_true_num, y_pred_num))),
            "mae": float(mean_absolute_error(y_true_num, y_pred_num)),
        }

    return {
        "n_samples": len(y_true),
        "problem_type": problem_type,
        "production_metrics": metrics,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def compare_with_baseline(
    production_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
    problem_type: str = "classification",
    degradation_threshold: float = 0.05,
) -> Dict[str, Any]:
    """
    Compare production metrics with training baseline.
    
    Args:
        production_metrics: Metrics from evaluate_production_performance
        baseline_metrics: Metrics from training/evaluation
        problem_type: 'classification' or 'regression'
        degradation_threshold: Max allowed drop before flagging
    
    Returns:
        Dict with comparison results and degradation flag
    """
    comparisons = []
    degraded = False

    if problem_type == "classification":
        key_metrics = ["accuracy", "f1_macro"]
    else:
        key_metrics = ["r2", "rmse"]

    for metric in key_metrics:
        baseline_val = baseline_metrics.get(metric)
        prod_val = production_metrics.get(metric)

        if baseline_val is None or prod_val is None:
            continue

        if metric in ("rmse", "mae"):
            # Lower is better
            change = (prod_val - baseline_val) / max(abs(baseline_val), 1e-8)
            is_degraded = change > degradation_threshold
        else:
            # Higher is better
            change = (baseline_val - prod_val) / max(abs(baseline_val), 1e-8)
            is_degraded = change > degradation_threshold

        if is_degraded:
            degraded = True

        comparisons.append({
            "metric": metric,
            "baseline": round(baseline_val, 4),
            "production": round(prod_val, 4),
            "change_pct": round(change * 100, 2),
            "degraded": is_degraded,
        })

    return {
        "degraded": degraded,
        "comparisons": comparisons,
        "recommendation": (
            "Performance degradation detected — consider retraining or investigation."
            if degraded
            else "Production performance within acceptable range."
        ),
    }
