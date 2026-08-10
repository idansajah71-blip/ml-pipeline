import os
import json
import traceback
from datetime import datetime, timedelta
from celery import current_task
from app.core.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()


def publish_progress(experiment_id: str, data: dict):
    try:
        import redis as sync_redis
        r = sync_redis.from_url(settings.REDIS_URL, decode_responses=True)
        r.publish(f"training:{experiment_id}", json.dumps(data, default=str))
        r.close()
    except Exception:
        pass


def get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


@celery_app.task(bind=True, name="ml.train_model")
def train_model_task(
    self,
    model_id: str,
    experiment_id: str,
    dataset_path: str,
    algorithm: str,
    parameters: dict,
    target_column: str,
    owner_id: str,
):
    from app.ml.pipeline import MLPipeline

    task_id = self.request.id
    start_time = datetime.utcnow()

    try:
        self.update_state(state="STARTED", meta={"step": "loading_data", "progress": 5})
        publish_progress(experiment_id, {"step": "loading_data", "progress": 5, "status": "started"})

        with open(dataset_path, "rb") as f:
            file_content = f.read()

        self.update_state(state="STARTED", meta={"step": "preprocessing", "progress": 15})
        publish_progress(experiment_id, {"step": "preprocessing", "progress": 15, "status": "started"})

        pipeline = MLPipeline()

        self.update_state(state="STARTED", meta={"step": "training", "progress": 30, "algorithm": algorithm})
        publish_progress(experiment_id, {"step": "training", "progress": 30, "algorithm": algorithm, "status": "started"})

        result = pipeline.run_training(
            file_content=file_content,
            filename=os.path.basename(dataset_path),
            target_column=target_column,
            algorithm=algorithm,
            parameters=parameters,
        )

        self.update_state(state="STARTED", meta={"step": "saving_artifacts", "progress": 85})
        publish_progress(experiment_id, {"step": "saving_artifacts", "progress": 85, "status": "started"})

        if result["status"] == "completed":
            model_dir = os.path.join(
                settings.ML_ARTIFACTS_DIR, f"model_{model_id}_v1"
            )
            artifacts = pipeline.save_artifacts(model_dir)
            result["artifacts"] = artifacts

        self.update_state(state="STARTED", meta={"step": "completed", "progress": 100})
        publish_progress(experiment_id, {"step": "completed", "progress": 100, "status": "completed", "metrics": result.get("metrics", {})})

        duration = (datetime.utcnow() - start_time).total_seconds()
        result["duration_seconds"] = round(duration, 2)
        result["task_id"] = task_id

        # ── Create in-app notification + email on success ──────────────────
        _notify_training_complete(owner_id, model_id, experiment_id, result, duration)

        return result

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        publish_progress(experiment_id, {"step": "failed", "progress": 0, "status": "failed", "error": str(e)})
        error_result = {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "duration_seconds": round(duration, 2),
            "task_id": task_id,
        }

        # ── Create in-app notification + email on failure ──────────────────
        _notify_training_failed(owner_id, model_id, experiment_id, str(e))

        return error_result


@celery_app.task(bind=True, name="ml.automl")
def automl_task(
    self,
    model_id: str,
    experiment_id: str,
    dataset_path: str,
    target_column: str,
    algorithms: list,
    owner_id: str,
):
    from app.ml.pipeline import MLPipeline

    task_id = self.request.id
    start_time = datetime.utcnow()
    results = []

    try:
        with open(dataset_path, "rb") as f:
            file_content = f.read()

        total = len(algorithms)
        for i, algo in enumerate(algorithms):
            progress = int((i / total) * 90) + 5
            self.update_state(
                state="STARTED",
                meta={
                    "step": f"training_{algo}",
                    "progress": progress,
                    "current_algorithm": algo,
                    "completed": i,
                    "total": total,
                },
            )
            publish_progress(experiment_id, {
                "step": f"training_{algo}",
                "progress": progress,
                "current_algorithm": algo,
                "completed": i,
                "total": total,
                "status": "started",
            })

            pipeline = MLPipeline()
            result = pipeline.run_training(
                file_content=file_content,
                filename=os.path.basename(dataset_path),
                target_column=target_column,
                algorithm=algo,
            )
            result["algorithm"] = algo
            results.append(result)

        results.sort(
            key=lambda x: x.get("metrics", {}).get("f1_macro", 0), reverse=True
        )

        duration = (datetime.utcnow() - start_time).total_seconds()
        publish_progress(experiment_id, {
            "step": "completed",
            "progress": 100,
            "status": "completed",
            "best_algorithm": results[0]["algorithm"] if results else None,
            "results_count": len(results),
        })
        result_data = {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "status": "completed",
            "results": results,
            "best_algorithm": results[0]["algorithm"] if results else None,
            "best_metrics": results[0].get("metrics", {}) if results else {},
            "duration_seconds": round(duration, 2),
            "task_id": task_id,
        }

        # Notify on AutoML completion
        _notify_training_complete(owner_id, model_id, experiment_id, results[0] if results else {}, duration)

        return result_data

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        publish_progress(experiment_id, {"step": "failed", "progress": 0, "status": "failed", "error": str(e)})

        # Notify on AutoML failure
        _notify_training_failed(owner_id, model_id, experiment_id, str(e))

        return {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "duration_seconds": round(duration, 2),
            "task_id": task_id,
        }


@celery_app.task(name="ml.check_model_performance")
def check_model_performance():
    from app.models.model import MLModel, ModelStatus
    from app.models.prediction import Prediction
    from sqlalchemy import func

    session = get_sync_session()
    try:
        deployed_models = session.query(MLModel).filter(
            MLModel.status == ModelStatus.DEPLOYED
        ).all()

        alerts = []
        for model in deployed_models:
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            recent_preds = session.query(Prediction).filter(
                Prediction.model_id == model.id,
                Prediction.created_at >= recent_cutoff,
            ).all()

            if not recent_preds:
                continue

            avg_confidence = sum(p.confidence or 0 for p in recent_preds) / len(recent_preds)
            avg_latency = sum(p.latency_ms or 0 for p in recent_preds) / len(recent_preds)

            if avg_confidence < 0.5:
                alerts.append({
                    "model_id": str(model.id),
                    "model_name": model.name,
                    "alert": "low_confidence",
                    "value": round(avg_confidence, 4),
                    "threshold": 0.5,
                    "prediction_count": len(recent_preds),
                })

            if avg_latency > 1000:
                alerts.append({
                    "model_id": str(model.id),
                    "model_name": model.name,
                    "alert": "high_latency",
                    "value": round(avg_latency, 2),
                    "threshold": 1000,
                    "prediction_count": len(recent_preds),
                })

        return {
            "status": "completed",
            "models_checked": len(deployed_models),
            "alerts": alerts,
            "checked_at": datetime.utcnow().isoformat(),
        }

    finally:
        session.close()


@celery_app.task(name="ml.scheduled_retraining_check")
def scheduled_retraining_check():
    from app.models.model import MLModel, ModelStatus
    from app.models.experiment import Experiment

    session = get_sync_session()
    try:
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        stale_models = session.query(MLModel).filter(
            MLModel.status == ModelStatus.DEPLOYED,
            MLModel.updated_at < thirty_days_ago,
        ).all()

        retrain_candidates = []
        for model in stale_models:
            latest_experiment = session.query(Experiment).filter(
                Experiment.model_id == model.id,
                Experiment.status == "completed",
            ).order_by(Experiment.created_at.desc()).first()

            retrain_candidates.append({
                "model_id": str(model.id),
                "model_name": model.name,
                "algorithm": model.algorithm,
                "last_updated": model.updated_at.isoformat() if model.updated_at else None,
                "last_experiment": latest_experiment.id if latest_experiment else None,
                "days_stale": (datetime.utcnow() - model.updated_at).days if model.updated_at else None,
            })

        return {
            "status": "completed",
            "stale_models": len(retrain_candidates),
            "candidates": retrain_candidates,
            "checked_at": datetime.utcnow().isoformat(),
        }

    finally:
        session.close()


@celery_app.task(bind=True, name="ml.retrain_model")
def retrain_model_task(self, model_id: str, owner_id: str):
    from app.models.model import MLModel
    from app.models.dataset import Dataset
    from app.models.experiment import Experiment, ExperimentStatus
    from app.ml.pipeline import MLPipeline

    session = get_sync_session()
    try:
        model = session.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return {"status": "failed", "error": "Model not found"}

        dataset = None
        if experiments := session.query(Experiment).filter(
            Experiment.model_id == model_id
        ).order_by(Experiment.created_at.desc()).all():
            for exp in experiments:
                if exp.dataset_id:
                    dataset = session.query(Dataset).filter(Dataset.id == exp.dataset_id).first()
                    if dataset:
                        break

        if not dataset:
            return {"status": "failed", "error": "No dataset found for retraining"}

        experiment = Experiment(
            name=f"Retraining {model.name} v{model.version + 1}",
            status=ExperimentStatus.RUNNING,
            parameters=model.parameters or {},
            dataset_id=dataset.id,
            model_id=model.id,
            owner_id=model.owner_id,
        )
        session.add(experiment)
        session.commit()

        with open(dataset.file_path, "rb") as f:
            file_content = f.read()

        pipeline = MLPipeline()
        result = pipeline.run_training(
            file_content=file_content,
            filename=os.path.basename(dataset.file_path),
            target_column=model.target_column or "target",
            algorithm=model.algorithm,
            parameters=model.parameters,
        )

        if result["status"] == "completed":
            model.version += 1
            model_dir = os.path.join(settings.ML_ARTIFACTS_DIR, f"model_{model.id}_v{model.version}")
            artifacts = pipeline.save_artifacts(model_dir)
            model.file_path = artifacts["model_path"]
            model.metrics = result.get("metrics", {})
            model.status = ModelStatus.TRAINED
            experiment.status = ExperimentStatus.COMPLETED
            experiment.results = result
            experiment.duration_seconds = str(result.get("duration_seconds", 0))
        else:
            model.status = ModelStatus.FAILED
            experiment.status = ExperimentStatus.FAILED
            experiment.results = result

        session.commit()

        return {
            "status": result["status"],
            "model_id": model_id,
            "new_version": model.version,
            "metrics": result.get("metrics", {}),
        }

    except Exception as e:
        session.rollback()
        return {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
    finally:
        session.close()


# ── Notification helpers ──────────────────────────────────────────────────────

def _get_model_name(session, model_id: str) -> str:
    """Fetch model name from DB."""
    try:
        from app.models.model import MLModel
        model = session.query(MLModel).filter(MLModel.id == model_id).first()
        return model.name if model else f"Model {model_id[:8]}"
    except Exception:
        return f"Model {model_id[:8]}"


def _get_owner_email(session, owner_id: str) -> str:
    """Fetch owner email from DB."""
    try:
        from app.models.user import User
        user = session.query(User).filter(User.id == owner_id).first()
        return user.email if user else ""
    except Exception:
        return ""


def _notify_training_complete(owner_id: str, model_id: str, experiment_id: str, result: dict, duration: float):
    """Create in-app notification and send email on training completion."""
    session = get_sync_session()
    try:
        model_name = _get_model_name(session, model_id)
        metrics = result.get("metrics", {})

        acc = metrics.get("accuracy", metrics.get("r2", metrics.get("f1", None)))
        metrics_text = ""
        if acc is not None:
            if isinstance(acc, float) and acc <= 1:
                metrics_text = f" (akurasi: {acc:.0%})"
            else:
                metrics_text = f" (skor: {acc:.2f})"

        from app.api.in_app_notifications import create_notification_sync
        create_notification_sync(
            session,
            user_id=owner_id,
            notification_type="training_complete",
            title=f"Training Selesai: {model_name}",
            message=f"Model '{model_name}' selesai dilatih dalam {duration:.1f} detik{metrics_text}.",
            link=f"/experiments?id={experiment_id}",
        )

        email = _get_owner_email(session, owner_id)
        if email:
            try:
                from app.core.notifications import send_training_notification_email
                send_training_notification_email(
                    to_email=email,
                    model_name=model_name,
                    status="completed",
                    metrics=metrics,
                    experiment_id=experiment_id,
                )
            except Exception as e:
                logger.warning(f"Failed to send training completion email: {e}")

    except Exception as e:
        logger.warning(f"Failed to create training completion notification: {e}")
    finally:
        session.close()


def _notify_training_failed(owner_id: str, model_id: str, experiment_id: str, error: str):
    """Create in-app notification and send email on training failure."""
    session = get_sync_session()
    try:
        model_name = _get_model_name(session, model_id)

        from app.api.in_app_notifications import create_notification_sync
        create_notification_sync(
            session,
            user_id=owner_id,
            notification_type="training_failed",
            title=f"Training Gagal: {model_name}",
            message=f"Training model '{model_name}' gagal: {error[:200]}",
            link=f"/experiments?id={experiment_id}",
        )

        email = _get_owner_email(session, owner_id)
        if email:
            try:
                from app.core.notifications import send_training_notification_email
                send_training_notification_email(
                    to_email=email,
                    model_name=model_name,
                    status="failed",
                    error=error,
                    experiment_id=experiment_id,
                )
            except Exception as e:
                logger.warning(f"Failed to send training failure email: {e}")

    except Exception as e:
        logger.warning(f"Failed to create training failure notification: {e}")
    finally:
        session.close()
