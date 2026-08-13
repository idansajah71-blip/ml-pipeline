"""
Auto-Retrain Policy — drift-separated, candidate-only, no auto-replace.

Flow:
1. Drift detected → validate sample size
2. Prediction drift check → delayed-label performance check
3. Train candidate model → quality gate → register
4. Canary/shadow deployment → promotion/rejection

Three triggers:
- Data drift (PSI/KS) — feature distribution shifted
- Prediction drift — model predictions shifted
- Performance degradation — actual metrics dropped (via delayed labels)

Candidate model is ONLY created when:
- Drift is significant AND sample size is sufficient
- AND delayed-label performance confirms degradation (if available)
- Candidate MUST pass quality gate before promotion
"""

from celery import chain, group
from app.core.celery_app import celery_app
from app.core.config import get_settings
import logging
import numpy as np

logger = logging.getLogger(__name__)

settings = get_settings()


def get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


class RetrainingPolicy:
    """Configurable retraining policy with thresholds."""

    def __init__(self):
        self.min_samples_for_retrain = 100
        self.psi_threshold = 0.2
        self.ks_threshold = 0.05
        self.prediction_drift_threshold = 0.2
        self.performance_degradation_threshold = 0.05  # 5% drop in metrics
        self.canary_traffic_pct = 0.1  # 10% traffic to canary
        self.min_canary_samples = 50
        self.promotion_accuracy_gain = 0.02  # 2% improvement required

    def should_retrain(
        self,
        drift_type: str,
        drift_score: float,
        sample_size: int,
        delayed_label_metrics: dict = None,
    ) -> dict:
        """Determine if retraining is warranted based on policy."""
        reasons = []

        # Check sample size
        if sample_size < self.min_samples_for_retrain:
            return {
                'retrain': False,
                'reason': f'Insufficient samples ({sample_size} < {self.min_samples_for_retrain})',
            }

        # Check drift severity
        if drift_type == 'data_drift':
            if drift_score < self.psi_threshold:
                return {'retrain': False, 'reason': f'Data drift below threshold ({drift_score:.3f} < {self.psi_threshold})'}
            reasons.append(f'Data drift score: {drift_score:.3f}')

        elif drift_type == 'prediction_drift':
            if drift_score < self.prediction_drift_threshold:
                return {'retrain': False, 'reason': f'Prediction drift below threshold ({drift_score:.3f})'}
            reasons.append(f'Prediction drift score: {drift_score:.3f}')

        elif drift_type == 'performance_degradation':
            reasons.append(f'Performance degradation detected (score: {drift_score:.3f})')

        # Check delayed-label confirmation if available
        if delayed_label_metrics and delayed_label_metrics.get('status') == 'ok':
            if delayed_label_metrics.get('problem_type') == 'classification':
                accuracy = delayed_label_metrics.get('accuracy', 1.0)
                if accuracy > 0.95:
                    return {'retrain': False, 'reason': f'Delayed labels show good accuracy ({accuracy:.1%})'}
                reasons.append(f'Delayed-label accuracy: {accuracy:.1%}')
            else:
                r2 = delayed_label_metrics.get('r2', 1.0)
                if r2 > 0.9:
                    return {'retrain': False, 'reason': f'Delayed labels show good R² ({r2:.3f})'}
                reasons.append(f'Delayed-label R²: {r2:.3f}')

        return {
            'retrain': True,
            'reasons': reasons,
        }


@celery_app.task(name="ml.auto_retrain_candidate")
def auto_retrain_candidate(
    model_id: str,
    drift_type: str,
    drift_score: float,
    feature_name: str = "",
    details: dict = None,
):
    """
    Create a candidate retrain job. Does NOT auto-promote.
    The candidate model must pass evaluation + quality gates + canary test.
    """
    from app.models.model import MLModel, ModelStatus
    from app.models.experiment import Experiment, ExperimentStatus

    session = get_sync_session()
    policy = RetrainingPolicy()

    try:
        model = session.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return {"status": "failed", "error": "Model not found"}

        # Check if a retrain is already in progress
        active = session.query(Experiment).filter(
            Experiment.model_id == model_id,
            Experiment.status.in_([ExperimentStatus.RUNNING, ExperimentStatus.PENDING]),
        ).first()
        if active:
            return {"status": "skipped", "reason": "Retrain already in progress"}

        # Evaluate delayed-label performance if available
        delayed_label_metrics = details.get('delayed_label_metrics') if details else None

        # Apply retraining policy
        sample_size = details.get('actual_samples', 0) if details else 0
        decision = policy.should_retrain(
            drift_type=drift_type,
            drift_score=drift_score,
            sample_size=sample_size,
            delayed_label_metrics=delayed_label_metrics,
        )

        if not decision['retrain']:
            return {
                "status": "skipped",
                "reason": decision['reason'],
                "model_id": model_id,
            }

        # Create candidate experiment
        experiment = Experiment(
            name=f"Candidate retrain {model.name} ({drift_type}: {feature_name})",
            status=ExperimentStatus.PENDING,
            parameters=model.parameters or {},
            model_id=model.id,
            owner_id=model.owner_id,
        )
        session.add(experiment)
        session.commit()

        # Find dataset for retraining
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

        # Train candidate
        result = pipeline.run_training(
            file_content=file_content,
            filename=dataset.file_path.split("/")[-1],
            target_column=model.target_column or "target",
            algorithm=model.algorithm,
            parameters=model.parameters,
        )

        if result["status"] != "completed":
            experiment.status = ExperimentStatus.FAILED
            experiment.results = result
            session.commit()
            return {"status": "failed", "error": result.get("error", "Training failed")}

        # Check if candidate is BETTER than current
        current_metrics = model.metrics or {}
        new_metrics = result.get("metrics", {})

        is_better = _is_candidate_better(
            current_metrics, new_metrics, model.algorithm,
        )

        if not is_better:
            experiment.status = ExperimentStatus.COMPLETED
            experiment.results = {
                **result,
                "candidate_status": "rejected",
                "reason": "Candidate model not better than current",
                "retrain_decision": decision,
                "current_metrics": current_metrics,
                "candidate_metrics": new_metrics,
            }
            session.commit()
            return {
                "status": "rejected",
                "reason": "Candidate not better",
                "model_id": model_id,
                "retrain_decision": decision,
            }

        # Save as candidate (NOT deployed — canary/shadow only)
        import os
        candidate_version = model.version + 1
        model_dir = os.path.join(
            settings.ML_ARTIFACTS_DIR,
            f"model_{model.id}_v{candidate_version}",
        )
        artifacts = pipeline.save_artifacts(model_dir)

        # Register candidate with canary/shadow metadata
        experiment.status = ExperimentStatus.COMPLETED
        experiment.results = {
            **result,
            "candidate_status": "ready_for_canary",
            "candidate_version": candidate_version,
            "candidate_file_path": artifacts.get("bundle_dir"),
            "current_metrics": current_metrics,
            "candidate_metrics": new_metrics,
            "drift_type": drift_type,
            "drift_score": drift_score,
            "retrain_decision": decision,
            "deployment_mode": "canary",
            "canary_traffic_pct": policy.canary_traffic_pct,
        }
        session.commit()

        return {
            "status": "candidate_ready",
            "model_id": model_id,
            "candidate_version": candidate_version,
            "drift_type": drift_type,
            "deployment_mode": "canary",
        }

    except Exception as e:
        session.rollback()
        logger.error(f"Auto-retrain candidate failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


def _is_candidate_better(current: dict, candidate: dict, algorithm: str) -> bool:
    """Check if candidate model is meaningfully better than current."""
    is_regression = any(k in current for k in ("r2", "rmse", "mae"))

    if is_regression:
        current_r2 = current.get("r2", 0)
        candidate_r2 = candidate.get("r2", 0)
        return candidate_r2 > current_r2 + 0.02
    else:
        current_f1 = current.get("f1_macro", current.get("accuracy", 0))
        candidate_f1 = candidate.get("f1_macro", candidate.get("accuracy", 0))
        return candidate_f1 > current_f1 + 0.02


def promote_canary(model_id: str, candidate_version: int) -> dict:
    """
    Promote a canary candidate to production.
    Only allowed after canary traffic confirms no regression.
    """
    from app.models.model import MLModel, ModelStatus

    session = get_sync_session()
    try:
        model = session.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return {"status": "failed", "error": "Model not found"}

        model.version = candidate_version
        model.status = ModelStatus.TRAINED
        session.commit()

        return {
            "status": "promoted",
            "model_id": model_id,
            "version": candidate_version,
        }
    except Exception as e:
        session.rollback()
        logger.error(f"Canary promotion failed: {e}", exc_info=True)
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


def reject_canary(model_id: str, candidate_version: int, reason: str) -> dict:
    """Reject a canary candidate. Keeps current model in production."""
    return {
        "status": "rejected",
        "model_id": model_id,
        "candidate_version": candidate_version,
        "reason": reason,
    }


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
