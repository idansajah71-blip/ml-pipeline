"""
Readiness scoring for ML models.
Computes a 0-100 score indicating whether a model is ready to be published
to the marketplace for others to use.
"""
from typing import Dict, Any, Optional


def compute_readiness_score(
    metrics: Dict[str, Any],
    feature_count: int = 0,
    training_samples: int = 0,
    result_type: str = "classification",
    cv_scores: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Compute a readiness score (0-100) for a trained model.
    
    Returns:
        {
            "score": int,           # 0-100
            "label": str,           # "Siap Dipublikasikan" | "Perlu Perbaikan" | "Belum Siap"
            "grade": str,           # "A" | "B" | "C" | "D" | "F"
            "factors": [...],       # List of scoring factors with impact
            "recommendations": [...] # Human-readable improvement suggestions
        }
    """
    score = 0
    factors = []
    recommendations = []

    # ── Factor 1: Primary metric (40 points max) ──────────────────────────
    if result_type == "classification":
        primary = metrics.get("accuracy", metrics.get("f1", 0))
        metric_name = "Akurasi" if "accuracy" in metrics else "F1 Score"
    else:
        primary = metrics.get("r2", 0)
        metric_name = "R² Score"

    if primary >= 0.90:
        pts = 40
        factors.append({"name": metric_name, "value": primary, "points": pts, "max": 40, "status": "excellent"})
    elif primary >= 0.80:
        pts = 35
        factors.append({"name": metric_name, "value": primary, "points": pts, "max": 40, "status": "good"})
    elif primary >= 0.70:
        pts = 25
        factors.append({"name": metric_name, "value": primary, "points": pts, "max": 40, "status": "adequate"})
        recommendations.append(f"{metric_name} masih {primary:.0%}. Pertimbangkan hyperparameter tuning.")
    elif primary >= 0.50:
        pts = 15
        factors.append({"name": metric_name, "value": primary, "points": pts, "max": 40, "status": "low"})
        recommendations.append(f"{metric_name} rendah ({primary:.0%}). Model belum cukup akurat untuk dipublikasikan.")
    else:
        pts = 0
        factors.append({"name": metric_name, "value": primary, "points": pts, "max": 40, "status": "poor"})
        recommendations.append(f"{metric_name} sangat rendah ({primary:.0%}). Sebaiknya dilatih ulang dengan data lebih banyak atau algoritma berbeda.")
    score += pts

    # ── Factor 2: Secondary metrics (20 points max) ───────────────────────
    secondary_pts = 0
    if result_type == "classification":
        for m_name in ["precision", "recall", "f1"]:
            val = metrics.get(m_name, 0)
            if val >= 0.80:
                secondary_pts += 3
            elif val >= 0.70:
                secondary_pts += 2
            elif val >= 0.60:
                secondary_pts += 1
    else:
        mae = metrics.get("mae", 0)
        rmse = metrics.get("rmse", 0)
        if mae > 0 and primary > 0:
            mae_ratio = mae / (primary * 100 + 1)
            if mae_ratio < 0.1:
                secondary_pts += 10
            elif mae_ratio < 0.2:
                secondary_pts += 7
            elif mae_ratio < 0.3:
                secondary_pts += 4
        if rmse > 0 and mae > 0:
            rmse_mae_ratio = rmse / mae if mae > 0 else 999
            if 1.0 <= rmse_mae_ratio <= 1.5:
                secondary_pts += 10
            elif rmse_mae_ratio <= 2.0:
                secondary_pts += 5
    secondary_pts = min(20, secondary_pts)
    factors.append({"name": "Metrik Sekunder", "value": secondary_pts, "points": secondary_pts, "max": 20, "status": "good" if secondary_pts >= 15 else "adequate" if secondary_pts >= 8 else "low"})
    score += secondary_pts

    # ── Factor 3: Training data size (20 points max) ──────────────────────
    if training_samples >= 10000:
        data_pts = 20
        data_status = "excellent"
    elif training_samples >= 5000:
        data_pts = 16
        data_status = "good"
    elif training_samples >= 1000:
        data_pts = 12
        data_status = "adequate"
    elif training_samples >= 300:
        data_pts = 6
        data_status = "low"
        recommendations.append("Data training kurang dari 1000 baris. Pertimbangkan menambah data untuk hasil lebih robust.")
    else:
        data_pts = 2
        data_status = "poor"
        recommendations.append("Data training sangat sedikit (<300 baris). Model mungkin overfitting.")
    factors.append({"name": "Jumlah Data Training", "value": training_samples, "points": data_pts, "max": 20, "status": data_status})
    score += data_pts

    # ── Factor 4: Feature count & quality (10 points max) ─────────────────
    if 3 <= feature_count <= 50:
        feat_pts = 10
        feat_status = "good"
    elif feature_count > 50:
        feat_pts = 6
        feat_status = "adequate"
        recommendations.append("Jumlah fitur cukup banyak. Pertimbangkan feature selection untuk mengurangi noise.")
    elif feature_count >= 2:
        feat_pts = 5
        feat_status = "adequate"
    else:
        feat_pts = 2
        feat_status = "low"
        recommendations.append("Terlalu sedikit fitur. Model mungkin tidak cukup informasi untuk prediksi akurat.")
    factors.append({"name": "Jumlah Fitur", "value": feature_count, "points": feat_pts, "max": 10, "status": feat_status})
    score += feat_pts

    # ── Factor 5: Cross-validation stability (10 points max) ──────────────
    if cv_scores and len(cv_scores) >= 3:
        import statistics
        mean_cv = statistics.mean(cv_scores)
        std_cv = statistics.stdev(cv_scores) if len(cv_scores) > 1 else 0
        cv_range = max(cv_scores) - min(cv_scores)
        if std_cv < 0.03 and mean_cv >= 0.75:
            cv_pts = 10
            cv_status = "excellent"
        elif std_cv < 0.05 and mean_cv >= 0.70:
            cv_pts = 8
            cv_status = "good"
        elif std_cv < 0.10:
            cv_pts = 5
            cv_status = "adequate"
            recommendations.append("Cross-validation menunjukkan variasi yang cukup besar. Model mungkin tidak stabil.")
        else:
            cv_pts = 2
            cv_status = "poor"
            recommendations.append("Cross-validation tidak stabil (std tinggi). Pertimbangkan regularization atau lebih banyak data.")
        factors.append({"name": "Stabilitas Cross-Validation", "value": round(mean_cv, 3), "points": cv_pts, "max": 10, "status": cv_status, "std": round(std_cv, 4)})
        score += cv_pts
    else:
        factors.append({"name": "Stabilitas Cross-Validation", "value": None, "points": 0, "max": 10, "status": "unknown"})
        recommendations.append("Cross-validation scores tidak tersedia. Pertimbangkan menjalankan CV untuk evaluasi lebih robust.")

    # ── Determine label and grade ──────────────────────────────────────────
    if score >= 80:
        label = "Siap Dipublikasikan"
        grade = "A"
    elif score >= 65:
        label = "Cukup Baik"
        grade = "B"
    elif score >= 50:
        label = "Perlu Perbaikan"
        grade = "C"
    elif score >= 30:
        label = "Belum Siap"
        grade = "D"
    else:
        label = "Sangat Perlu Perbaikan"
        grade = "F"

    if not recommendations:
        recommendations.append("Model dalam kondisi baik! Siap untuk dipublikasikan ke marketplace.")

    return {
        "score": min(100, score),
        "label": label,
        "grade": grade,
        "factors": factors,
        "recommendations": recommendations,
    }
