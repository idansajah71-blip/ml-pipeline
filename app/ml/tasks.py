import os
import json
import traceback
from datetime import datetime
from celery import current_task
from app.core.celery_app import celery_app
from app.core.config import get_settings

settings = get_settings()


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

        with open(dataset_path, "rb") as f:
            file_content = f.read()

        self.update_state(state="STARTED", meta={"step": "preprocessing", "progress": 15})

        pipeline = MLPipeline()

        self.update_state(state="STARTED", meta={"step": "training", "progress": 30})

        result = pipeline.run_training(
            file_content=file_content,
            filename=os.path.basename(dataset_path),
            target_column=target_column,
            algorithm=algorithm,
            parameters=parameters,
        )

        self.update_state(state="STARTED", meta={"step": "saving_artifacts", "progress": 85})

        if result["status"] == "completed":
            model_dir = os.path.join(
                settings.ML_ARTIFACTS_DIR, f"model_{model_id}_v1"
            )
            artifacts = pipeline.save_artifacts(model_dir)
            result["artifacts"] = artifacts

        self.update_state(state="STARTED", meta={"step": "completed", "progress": 100})

        duration = (datetime.utcnow() - start_time).total_seconds()
        result["duration_seconds"] = round(duration, 2)
        result["task_id"] = task_id

        return result

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        error_result = {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "duration_seconds": round(duration, 2),
            "task_id": task_id,
        }
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
        return {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "status": "completed",
            "results": results,
            "best_algorithm": results[0]["algorithm"] if results else None,
            "best_metrics": results[0].get("metrics", {}) if results else {},
            "duration_seconds": round(duration, 2),
            "task_id": task_id,
        }

    except Exception as e:
        duration = (datetime.utcnow() - start_time).total_seconds()
        return {
            "experiment_id": experiment_id,
            "model_id": model_id,
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "duration_seconds": round(duration, 2),
            "task_id": task_id,
        }
