from celery import chain, group
from app.core.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()


def get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine(settings.SYNC_DATABASE_URL)
    return sessionmaker(bind=engine)()


@celery_app.task(name="ml.auto_retrain_on_drift")
def auto_retrain_on_drift(model_id: str, drift_score: float, feature_name: str):
    from app.models.model import MLModel, ModelStatus
    from app.models.experiment import Experiment, ExperimentStatus

    session = get_sync_session()
    try:
        model = session.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return {"status": "failed", "error": "Model not found"}

        if drift_score < 2.0:
            return {"status": "skipped", "reason": "Drift score below threshold"}

        experiment = Experiment(
            name=f"Auto-retrain {model.name} (drift in {feature_name})",
            status=ExperimentStatus.RUNNING,
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
            experiment.results = {"error": "No dataset found"}
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
            import os
            model.version += 1
            model_dir = os.path.join(settings.ML_ARTIFACTS_DIR, f"model_{model.id}_v{model.version}")
            artifacts = pipeline.save_artifacts(model_dir)
            model.file_path = artifacts["model_path"]
            model.metrics = result.get("metrics", {})
            experiment.status = ExperimentStatus.COMPLETED
            experiment.results = result
        else:
            experiment.status = ExperimentStatus.FAILED
            experiment.results = result

        session.commit()

        return {
            "status": result["status"],
            "model_id": model_id,
            "new_version": model.version,
            "drift_score": drift_score,
            "feature": feature_name,
        }

    except Exception as e:
        session.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


@celery_app.task(name="ml.run_auto_retrain_pipeline")
def run_auto_retrain_pipeline():
    from app.models.feature_monitoring import FeatureDriftAlert

    session = get_sync_session()
    try:
        alerts = session.query(FeatureDriftAlert).filter(
            FeatureDriftAlert.severity == "critical",
            FeatureDriftAlert.acknowledged == 0,
        ).all()

        triggered = []
        for alert in alerts:
            if alert.model_id:
                result = auto_retrain_on_drift.delay(
                    str(alert.model_id),
                    alert.drift_score or 3.0,
                    alert.feature_name,
                )
                triggered.append({
                    "alert_id": str(alert.id),
                    "model_id": str(alert.model_id),
                    "task_id": result.id,
                })
                alert.acknowledged = 1

        session.commit()

        return {
            "status": "completed",
            "triggered_retrains": len(triggered),
            "details": triggered,
        }

    except Exception as e:
        session.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()
