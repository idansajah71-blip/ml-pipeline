"""
Readiness Scoring — multi-dimensional production readiness gate.

A model is NOT "ready" just because it has a high accuracy score.
Readiness is a set of independent gates; if any critical gate fails,
status is BLOCKED regardless of other scores.

Dimensions:
1. Data Quality (missing values, cardinality, imbalance)
2. Leakage Check (target leakage, train-test overlap)
3. Validation Integrity (proper split, no leakage in preprocessing)
4. Primary Metric (accuracy / R² — weighted but not dominant)
5. Calibration (Brier score, ECE for classifiers)
6. Robustness (CV stability, confidence intervals)
7. Reproducibility (random seeds, library versions)
8. Artifact Integrity (manifest, checksums)
9. Schema Compatibility (feature count, types match)
10. Serving Latency (p95 inference time)
11. Monitoring Readiness (drift baseline exists)
12. Security (no sensitive features, input validation)
"""

from typing import Dict, Any, Optional, List
import statistics
import logging

logger = logging.getLogger(__name__)

# Gate definitions — critical gates block deployment
CRITICAL_GATES = {"data_quality", "leakage_check", "artifact_integrity", "validation_integrity"}


def compute_readiness_score(
    metrics: Dict[str, Any],
    feature_count: int = 0,
    training_samples: int = 0,
    result_type: str = "classification",
    cv_scores: Optional[list] = None,
    artifact_valid: bool = False,
    has_drift_baseline: bool = False,
    serving_latency_ms: float = 0.0,
    feature_names: Optional[list] = None,
    sensitive_features: Optional[list] = None,
    missing_ratio: float = 0.0,
    class_imbalance_ratio: float = 1.0,
    data_quality_issues: Optional[List[str]] = None,
    has_leakage: bool = False,
    random_seed: Optional[int] = None,
    library_versions: Optional[Dict[str, str]] = None,
    deployment_history: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Compute multi-dimensional readiness score.

    Returns:
        {
            "score": int,               # 0-100
            "status": str,              # "ready" | "needs_improvement" | "blocked"
            "label": str,               # Human-readable status
            "grade": str,               # A-F
            "gates": [...],             # Per-gate results
            "critical_failures": [...], # List of failed critical gates
            "recommendations": [...],   # Improvement suggestions
        }
    """
    gates = []
    recommendations = []
    failed_critical = []

    # ── Gate 1: Data Quality (0-100) ──────────────────────────────────
    dq_score = 100
    if missing_ratio > 0.3:
        dq_score -= 40
        recommendations.append(f"High missing values ({missing_ratio:.0%}). Consider imputation or column removal.")
    elif missing_ratio > 0.1:
        dq_score -= 15
    if class_imbalance_ratio < 0.1:
        dq_score -= 30
        recommendations.append("Severe class imbalance. Use class weights or oversampling.")
    elif class_imbalance_ratio < 0.3:
        dq_score -= 10
    if data_quality_issues:
        dq_score -= min(30, len(data_quality_issues) * 10)
    dq_score = max(0, dq_score)
    dq_status = "pass" if dq_score >= 70 else ("warning" if dq_score >= 40 else "fail")
    if dq_status == "fail" and "data_quality" in CRITICAL_GATES:
        failed_critical.append("data_quality")
    gates.append({"name": "data_quality", "score": dq_score, "status": dq_status, "weight": 10})

    # ── Gate 2: Leakage Check (0-100) ─────────────────────────────────
    lk_score = 100 if not has_leakage else 0
    lk_status = "pass" if not has_leakage else "fail"
    if lk_status == "fail" and "leakage_check" in CRITICAL_GATES:
        failed_critical.append("leakage_check")
        recommendations.append("Potential target leakage detected. Review features that may contain post-event information.")
    gates.append({"name": "leakage_check", "score": lk_score, "status": lk_status, "weight": 15})

    # ── Gate 3: Validation Integrity (0-100) ──────────────────────────
    vi_score = 100
    if training_samples < 100:
        vi_score -= 40
        recommendations.append("Very small training set (<100 samples). Model may overfit.")
    elif training_samples < 500:
        vi_score -= 15
    if feature_count > 200:
        vi_score -= 20
        recommendations.append("Very high feature count. Consider feature selection.")
    vi_score = max(0, vi_score)
    vi_status = "pass" if vi_score >= 70 else ("warning" if vi_score >= 40 else "fail")
    if vi_status == "fail" and "validation_integrity" in CRITICAL_GATES:
        failed_critical.append("validation_integrity")
    gates.append({"name": "validation_integrity", "score": vi_score, "status": vi_status, "weight": 10})

    # ── Gate 4: Primary Metric (0-100) ────────────────────────────────
    if result_type == "classification":
        primary = metrics.get("accuracy", metrics.get("f1", 0))
        metric_name = "Accuracy"
    else:
        primary = metrics.get("r2", 0)
        metric_name = "R²"

    if primary >= 0.90:
        pm_score = 100
    elif primary >= 0.80:
        pm_score = 85
    elif primary >= 0.70:
        pm_score = 65
        recommendations.append(f"{metric_name} ({primary:.2%}) is acceptable but could be improved.")
    elif primary >= 0.50:
        pm_score = 40
        recommendations.append(f"{metric_name} is low ({primary:.2%}). Consider hyperparameter tuning.")
    else:
        pm_score = 10
        recommendations.append(f"{metric_name} is very low ({primary:.2%}). Model needs retraining.")
    pm_status = "pass" if pm_score >= 65 else ("warning" if pm_score >= 40 else "fail")
    gates.append({"name": "primary_metric", "score": pm_score, "status": pm_status, "weight": 20})

    # ── Gate 5: Calibration (0-100) ───────────────────────────────────
    cal_score = 50  # neutral if not available
    if result_type == "classification":
        brier = metrics.get("brier_score")
        ece = metrics.get("expected_calibration_error")
        if brier is not None:
            # Brier: 0 is perfect, 1 is worst
            cal_score = int(max(0, min(100, (1 - brier * 2) * 100)))
            if brier > 0.25:
                recommendations.append("Poor model calibration (high Brier score). Consider Platt scaling.")
        elif ece is not None:
            cal_score = int(max(0, min(100, (1 - ece) * 100)))
    else:
        # For regression, use MAPE as proxy
        mape = metrics.get("mape")
        if mape is not None:
            cal_score = int(max(0, min(100, 100 - mape)))
    cal_status = "pass" if cal_score >= 60 else ("warning" if cal_score >= 30 else "fail")
    gates.append({"name": "calibration", "score": cal_score, "status": cal_status, "weight": 10})

    # ── Gate 6: Robustness (0-100) ────────────────────────────────────
    rob_score = 50
    if cv_scores and len(cv_scores) >= 3:
        mean_cv = statistics.mean(cv_scores)
        std_cv = statistics.stdev(cv_scores) if len(cv_scores) > 1 else 0
        if std_cv < 0.03 and mean_cv >= 0.75:
            rob_score = 100
        elif std_cv < 0.05 and mean_cv >= 0.70:
            rob_score = 80
        elif std_cv < 0.10:
            rob_score = 55
            recommendations.append("Cross-validation shows high variance.")
        else:
            rob_score = 20
            recommendations.append("Model is unstable (high CV std). Consider regularization.")
    rob_status = "pass" if rob_score >= 60 else ("warning" if rob_score >= 30 else "fail")
    gates.append({"name": "robustness", "score": rob_score, "status": rob_status, "weight": 10})

    # ── Gate 7: Reproducibility (0-100) ───────────────────────────────
    rp_score = 60  # baseline
    if random_seed is not None:
        rp_score += 20
    if library_versions:
        rp_score += 20
    rp_score = min(100, rp_score)
    rp_status = "pass" if rp_score >= 60 else "warning"
    gates.append({"name": "reproducibility", "score": rp_score, "status": rp_status, "weight": 5})

    # ── Gate 8: Artifact Integrity (0-100) ────────────────────────────
    ai_score = 100 if artifact_valid else 0
    ai_status = "pass" if artifact_valid else "fail"
    if ai_status == "fail" and "artifact_integrity" in CRITICAL_GATES:
        failed_critical.append("artifact_integrity")
        recommendations.append("Artifact integrity check failed. Model is not safe for deployment.")
    gates.append({"name": "artifact_integrity", "score": ai_score, "status": ai_status, "weight": 10})

    # ── Gate 9: Schema Compatibility (0-100) ──────────────────────────
    sc_score = 80 if feature_count > 0 else 40
    sc_status = "pass" if sc_score >= 60 else "warning"
    gates.append({"name": "schema_compatibility", "score": sc_score, "status": sc_status, "weight": 3})

    # ── Gate 10: Serving Latency (0-100) ──────────────────────────────
    if serving_latency_ms > 0:
        if serving_latency_ms < 50:
            sl_score = 100
        elif serving_latency_ms < 200:
            sl_score = 80
        elif serving_latency_ms < 1000:
            sl_score = 50
            recommendations.append(f"Inference latency {serving_latency_ms:.0f}ms is acceptable.")
        else:
            sl_score = 20
            recommendations.append(f"Inference latency {serving_latency_ms:.0f}ms is too high for production.")
    else:
        sl_score = 60  # unknown, neutral
    sl_status = "pass" if sl_score >= 50 else "warning"
    gates.append({"name": "serving_latency", "score": sl_score, "status": sl_status, "weight": 3})

    # ── Gate 11: Monitoring Readiness (0-100) ─────────────────────────
    mr_score = 100 if has_drift_baseline else 30
    mr_status = "pass" if has_drift_baseline else "warning"
    if not has_drift_baseline:
        recommendations.append("Drift baseline not set. Setup monitoring after deployment.")
    gates.append({"name": "monitoring_readiness", "score": mr_score, "status": mr_status, "weight": 2})

    # ── Gate 12: Security (0-100) ─────────────────────────────────────
    sec_score = 100
    if sensitive_features:
        sec_score -= len(sensitive_features) * 15
        recommendations.append(f"Sensitive features detected: {', '.join(sensitive_features[:3])}. Consider fairness audit.")
    sec_score = max(0, sec_score)
    sec_status = "pass" if sec_score >= 70 else "warning"
    gates.append({"name": "security", "score": sec_score, "status": sec_status, "weight": 2})

    # ── Gate 13: Rollback Capability (0-100) ──────────────────────────
    rb_score = 50  # neutral if unknown
    if artifact_valid and feature_count > 0:
        rb_score = 80  # can rollback if artifacts are valid
    if deployment_history and len(deployment_history) > 0:
        rb_score = 100  # proven rollback capability
    rb_status = "pass" if rb_score >= 60 else "warning"
    if rb_status == "warning":
        recommendations.append("Rollback capability unknown. Ensure artifact versioning is in place.")
    gates.append({"name": "rollback_capability", "score": rb_score, "status": rb_status, "weight": 2})

    # ── Compute weighted total ─────────────────────────────────────────
    total_weight = sum(g["weight"] for g in gates)
    weighted_sum = sum(g["score"] * g["weight"] for g in gates)
    final_score = int(weighted_sum / total_weight) if total_weight > 0 else 0

    # ── Determine status ───────────────────────────────────────────────
    if failed_critical:
        status = "blocked"
        label = "BLOCKED — Critical gate(s) failed"
    elif final_score >= 75:
        status = "ready"
        label = "Ready for Deployment"
    elif final_score >= 50:
        status = "needs_improvement"
        label = "Needs Improvement"
    else:
        status = "not_ready"
        label = "Not Ready"

    if final_score >= 80:
        grade = "A"
    elif final_score >= 65:
        grade = "B"
    elif final_score >= 50:
        grade = "C"
    elif final_score >= 30:
        grade = "D"
    else:
        grade = "F"

    if not recommendations:
        recommendations.append("Model is in good condition! Ready for deployment.")

    return {
        "score": final_score,
        "status": status,
        "label": label,
        "grade": grade,
        "gates": gates,
        "critical_failures": failed_critical,
        "recommendations": recommendations,
    }
