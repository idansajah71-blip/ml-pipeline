from typing import Dict, Any, Optional
import logging
import os

logger = logging.getLogger(__name__)


def _get_mlflow():
    try:
        import mlflow
        return mlflow
    except ImportError:
        return None


mlflow = _get_mlflow()


class MLflowTracker:
    """
    MLflow experiment tracking integration.
    
    Tracks experiments, parameters, metrics, and model artifacts.
    Falls back gracefully if MLflow is not installed.
    """

    def __init__(self, tracking_uri: Optional[str] = None, experiment_name: str = "ml-pipeline"):
        self.is_available = mlflow is not None
        self.tracking_uri = tracking_uri
        self.experiment_name = experiment_name
        self.run = None

        if self.is_available:
            try:
                if tracking_uri:
                    mlflow.set_tracking_uri(tracking_uri)
                mlflow.set_experiment(experiment_name)
            except Exception as e:
                logger.warning(f"MLflow initialization failed: {e}")
                self.is_available = False

    def start_run(
        self,
        run_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        if not self.is_available:
            return None

        try:
            self.run = mlflow.start_run(run_name=run_name, tags=tags)
            return self.run.info.run_id
        except Exception as e:
            logger.warning(f"Failed to start MLflow run: {e}")
            return None

    def log_params(self, params: Dict[str, Any]):
        if not self.is_available or self.run is None:
            return

        try:
            flat_params = {}
            for k, v in params.items():
                if isinstance(v, (dict, list)):
                    flat_params[k] = str(v)
                elif isinstance(v, (int, float, str, bool)):
                    flat_params[k] = v
                else:
                    flat_params[k] = str(v)
            mlflow.log_params(flat_params)
        except Exception as e:
            logger.warning(f"Failed to log MLflow params: {e}")

    def log_metrics(self, metrics: Dict[str, Any], step: Optional[int] = None):
        if not self.is_available or self.run is None:
            return

        try:
            flat_metrics = {}
            for k, v in metrics.items():
                if isinstance(v, (int, float)):
                    flat_metrics[k] = v
                elif isinstance(v, bool):
                    flat_metrics[k] = int(v)
            if flat_metrics:
                mlflow.log_metrics(flat_metrics, step=step)
        except Exception as e:
            logger.warning(f"Failed to log MLflow metrics: {e}")

    def log_model(self, model, artifact_path: str = "model", registered_model_name: Optional[str] = None):
        if not self.is_available or self.run is None:
            return

        try:
            if registered_model_name:
                mlflow.sklearn.log_model(
                    model,
                    artifact_path=artifact_path,
                    registered_model_name=registered_model_name,
                )
            else:
                mlflow.sklearn.log_model(model, artifact_path=artifact_path)
        except Exception as e:
            logger.warning(f"Failed to log MLflow model: {e}")

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        if not self.is_available or self.run is None:
            return

        try:
            mlflow.log_artifact(local_path, artifact_path=artifact_path)
        except Exception as e:
            logger.warning(f"Failed to log MLflow artifact: {e}")

    def log_dict(self, data: Dict[str, Any], filename: str):
        if not self.is_available or self.run is None:
            return

        try:
            mlflow.log_dict(data, filename)
        except Exception as e:
            logger.warning(f"Failed to log MLflow dict: {e}")

    def set_tags(self, tags: Dict[str, str]):
        if not self.is_available or self.run is None:
            return

        try:
            mlflow.set_tags(tags)
        except Exception as e:
            logger.warning(f"Failed to set MLflow tags: {e}")

    def end_run(self, status: str = "COMPLETED"):
        if not self.is_available or self.run is None:
            return

        try:
            mlflow.end_run(status=status)
            self.run = None
        except Exception as e:
            logger.warning(f"Failed to end MLflow run: {e}")

    def track_training(
        self,
        algorithm: str,
        parameters: Dict[str, Any],
        metrics: Dict[str, Any],
        model=None,
        artifact_dir: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        run_name: Optional[str] = None,
    ) -> Optional[str]:
        if not self.is_available:
            return None

        run_id = self.start_run(
            run_name=run_name or f"{algorithm}_training",
            tags=tags or {},
        )

        if run_id is None:
            return None

        try:
            self.log_params(parameters)
            self.log_metrics(metrics)

            if model is not None:
                self.log_model(model)

            if artifact_dir and os.path.exists(artifact_dir):
                for filename in os.listdir(artifact_dir):
                    filepath = os.path.join(artifact_dir, filename)
                    if os.path.isfile(filepath):
                        self.log_artifact(filepath)

            self.end_run(status="COMPLETED")
            return run_id

        except Exception as e:
            logger.error(f"MLflow tracking failed: {e}")
            self.end_run(status="FAILED")
            return None

    def get_experiment_runs(self, max_results: int = 10) -> list:
        if not self.is_available:
            return []

        try:
            experiment = mlflow.get_experiment_by_name(self.experiment_name)
            if experiment is None:
                return []

            runs = mlflow.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=max_results,
            )
            return runs.to_dict('records') if not runs.empty else []
        except Exception as e:
            logger.warning(f"Failed to get MLflow runs: {e}")
            return []


def get_mlflow_tracker(
    tracking_uri: Optional[str] = None,
    experiment_name: str = "ml-pipeline",
) -> MLflowTracker:
    return MLflowTracker(tracking_uri=tracking_uri, experiment_name=experiment_name)
