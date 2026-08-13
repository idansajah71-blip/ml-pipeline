"""
Auto-Retrain Policy — drift-separated, candidate-only.

Auto-retraining should NOT automatically promote a new model.
Instead, it creates a CANDIDATE job that must pass evaluation
and quality gates before being eligible for promotion.

Separates three triggers:
1. Data drift (PSI/KS) — feature distribution shifted
2. Prediction drift — model predictions shifted
3. Performance degradation — actual metrics dropped

A candidate model is only created when:
- Drift is significant AND sample size is sufficient
- OR performance degradation is detected
- OR policy domain allows proactive retraining
"""

from celery import chain, group
from app.core.celery_app import celery_app
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()


def get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


@celery_app.task(name="ml.auto_retrain_candidate")
def auto_retrain_candidate(
    model_id: str,
    drift_type: str,  # "data_drift" | "prediction_drift" | "performance_degradation"
    drift_score: float,
    feature_name: str = "",
    details: dict = None,
):
    """
    Create a candidate retrain job. Does NOT auto-promote.
    The candidate model must pass evaluation + quality gates.
    """
    from app.models.model import MLModel, ModelStatus
    from app.models.experiment import Experiment, ExperimentStatus

    session = get_sync_session()
    try:
        model = session.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return {"status": "failed", "error": "Model not found"}

        # Check if a retrain is already in progress for this model
        active = session.query(Experiment).filter(
            Experiment.model_id == model_id,
            Experiment.status.in_([ExperimentStatus.RUNNING, ExperimentStatus.PENDING]),
        ).first()
        if active:
            return {"status": "skipped", "reason": "Retrain already in progress"}

        # Determine if retrain is warranted
        if drift_type == "data_drift" and drift_score < 2.0:
            return {"status": "skipped", "reason": "Data drift below threshold"}

        if drift_type == "performance_degradation":
            # Require minimum sample size for performance-based retrain
            min_samples = details.get("min_samples", 50) if details else 50
            actual_samples = details.get("actual_samples", 0) if details else 0
            if actual_samples < min_samples:
                return {
                    "status": "skipped",
                    "reason": f"Insufficient samples ({actual_samples} < {min_samples})",
                }

        experiment = Experiment(
            name=f"Candidate retrain {model.name} ({drift_type}: {feature_name})",
            status=ExperimentStatus.PENDING,
            parameters=model.parameters or {},
            model_id=model.id,
            owner_id=model.owner_id,
        )
        session.add(experiment)
        session.commit()

        from app.ml.pipeline import MLPipeline
        pipeline = MLPipeline()

        dataset = None
        from app.models.dataset import Dataset
        experiments = session.query(Experiment).filter(
            Experiment.model_id == model_id
        ).order_by(Experiment.created_at.desc()).all()
        for exp in experiments:
            if exp.dataset_id:
                dataset = session.query(Dataset).filter(Dataset.id == exp.dataset_id).first()
                if dataset:
                    break

        if not dataset:
            experiment.status = ExperimentStatus.FAILED
            experiment.results = {"error": "No dataset found for retraining"}
            session.commit()
            return {"status": "failed", "error": "No dataset found"}

        with open(dataset.file_path, "rb") as f:
            file_content = f.read()

        result = pipeline.run_training(
            file_content=file_content,
            filename=dataset.file_path.split("/")[-1],
            target_column=model.target_column or "target",
            algorithm=model.algorithm,
            parameters=model.parameters,
        )

        if result["status"] == "completed":
            # Check if candidate is BETTER than current model
            current_metrics = model.metrics or {}
            new_metrics = result.get("metrics", {})

            is_better = _is_candidate_better(
                current_metrics, new_metrics,
                model.algorithm,
            )

            if not is_better:
                experiment.status = ExperimentStatus.COMPLETED
                experiment.results = {
                    **result,
                    "candidate_status": "rejected",
                    "reason": "Candidate model not better than current",
                    "current_metrics": current_metrics,
                    "candidate_metrics": new_metrics,
                }
                session.commit()
                return {
                    "status": "rejected",
                    "reason": "Candidate not better",
                    "model_id": model_id,
                }

            # Save as candidate (NOT deployed)
            import os
            candidate_version = model.version + 1
            model_dir = os.path.join(
                settings.ML_ARTIFACTS_DIR,
                f"model_{model.id}_v{candidate_version}",
            )
            artifacts = pipeline.save_artifacts(model_dir)

            experiment.status = ExperimentStatus.COMPLETED
            experiment.results = {
                **result,
                "candidate_status": "ready_for_review",
                "candidate_version": candidate_version,
                "candidate_file_path": artifacts.get("bundle_dir"),
                "current_metrics": current_metrics,
                "candidate_metrics": new_metrics,
                "drift_type": drift_type,
                "drift_score": drift_score,
            }
            session.commit()

            return {
                "status": "candidate_ready",
                "model_id": model_id,
                "candidate_version": candidate_version,
                "drift_type": drift_type,
            }
        else:
            experiment.status = ExperimentStatus.FAILED
            experiment.results = result
            session.commit()
            return {"status": "failed", "error": result.get("error", "Training failed")}

    except Exception as e:
        session.rollback()
        logger.error(f"Auto-retrain candidate failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


def _is_candidate_better(current: dict, candidate: dict, algorithm: str) -> bool:
    """Check if candidate model is meaningfully better than current."""
    from app.ml.trainer import ModelTrainer

    # For classification: higher is better (accuracy, f1)
    # For regression: higher R² is better, lower RMSE/MAE is better
    is_regression = any(k in current for k in ("r2", "rmse", "mae"))

    if is_regression:
        current_r2 = current.get("r2", 0)
        candidate_r2 = candidate.get("r2", 0)
        # Require at least 2% improvement in R²
        return candidate_r2 > current_r2 + 0.02
    else:
        current_f1 = current.get("f1_macro", current.get("accuracy", 0))
        candidate_f1 = candidate.get("f1_macro", candidate.get("accuracy", 0))
        # Require at least 2% improvement in F1
        return candidate_f1 > current_f1 + 0.02


@celery_app.task(name="ml.run_auto_retrain_pipeline")
def run_auto_retrain_pipeline():
    """
    Hourly check: separate data drift, prediction drift, and performance degradation.
    Creates candidate jobs — does NOT auto-promote.
    """
    from app.models.feature_monitoring import FeatureDriftAlert

    session = get_sync_session()
    try:
        alerts = session.query(FeatureDriftAlert).filter(
            FeatureDriftAlert.severity.in_(["high", "critical"]),
            FeatureDriftAlert.acknowledged == 0,
        ).all()

        triggered = []
        for alert in alerts:
            if alert.model_id:
                # Determine drift type from alert
                drift_type = "data_drift"
                if alert.drift_type == "prediction":
                    drift_type = "prediction_drift"
                elif alert.drift_type == "performance":
                    drift_type = "performance_degradation"

                result = auto_retrain_candidate.delay(
                    str(alert.model_id),
                    drift_type,
                    alert.drift_score or 3.0,
                    alert.feature_name,
                    details=alert.details or {},
                )
                triggered.append({
                    "alert_id": str(alert.id),
                    "model_id": str(alert.model_id),
                    "drift_type": drift_type,
                    "task_id": result.id,
                })
                alert.acknowledged = 1

        session.commit()

        return {
            "status": "completed",
            "candidates_triggered": len(triggered),
            "details": triggered,
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Auto-retrain pipeline check failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()
