import os
import uuid
import json
import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
import logging

from app.models.model import MLModel, ModelStatus
from app.models.dataset import Dataset
from app.models.experiment import Experiment, ExperimentStatus
from app.schemas.model import ModelCreate, TrainRequest, TrainingMode
from app.ml.pipeline import MLPipeline
from app.ml.readiness import compute_readiness_score
from app.ml.auto_pipeline import AutoMLPipeline
from app.core.config import get_settings
from app.core.error_utils import sanitize_error_message, log_error

settings = get_settings()
logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.artifacts_dir = settings.ML_ARTIFACTS_DIR

    CELERY_UNAVAILABLE_MESSAGE = (
        "Layanan pelatihan background (Celery) sedang tidak tersedia. "
        "Pelatihan akan dijalankan langsung secara sinkron."
    )

    def _dispatch_async_training(
        self,
        model_id: str,
        experiment_id: str,
        dataset_path: str,
        algorithm: str,
        parameters: dict,
        target_column: str,
        owner_id: str,
    ) -> str:
        try:
            from app.ml.tasks import train_model_task
        except ImportError as exc:
            raise HTTPException(
                status_code=503,
                detail=self.CELERY_UNAVAILABLE_MESSAGE,
            )
        if train_model_task is None or not hasattr(train_model_task, "delay"):
            raise HTTPException(
                status_code=503,
                detail=self.CELERY_UNAVAILABLE_MESSAGE,
            )

        try:
            result = train_model_task.delay(
                model_id=str(model_id),
                experiment_id=str(experiment_id),
                dataset_path=dataset_path,
                algorithm=algorithm,
                parameters=parameters or {},
                target_column=target_column,
                owner_id=str(owner_id),
            )
        except Exception as exc:
            # Broker down / worker unreachable → signal the caller to fall back
            # to synchronous training instead of surfacing a raw 500.
            log_error(exc, context="Celery broker unavailable during training dispatch")
            raise HTTPException(
                status_code=503,
                detail=self.CELERY_UNAVAILABLE_MESSAGE,
            )
        return getattr(result, "id", str(uuid.uuid4()))

    async def create_model(self, model_data: ModelCreate, owner_id: UUID) -> MLModel:
        model = MLModel(
            name=model_data.name,
            description=model_data.description,
            algorithm=model_data.algorithm,
            target_column=model_data.target_column,
            tags=model_data.tags,
            owner_id=owner_id,
        )
        self.db.add(model)
        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def get_model(self, model_id: UUID) -> Optional[MLModel]:
        result = await self.db.execute(select(MLModel).where(MLModel.id == model_id))
        return result.scalar_one_or_none()

    async def get_user_models(self, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[MLModel]:
        result = await self.db.execute(
            select(MLModel)
            .where(MLModel.owner_id == owner_id, MLModel.status != ModelStatus.ARCHIVED)
            .order_by(MLModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_archived_models(self, owner_id: UUID, skip: int = 0, limit: int = 100) -> List[MLModel]:
        result = await self.db.execute(
            select(MLModel)
            .where(MLModel.owner_id == owner_id, MLModel.status == ModelStatus.ARCHIVED)
            .order_by(MLModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_model(self, model_id: UUID, owner_id: UUID) -> bool:
        model = await self.get_model(model_id)
        if not model:
            return False
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        model.status = ModelStatus.ARCHIVED
        await self.db.flush()
        return True

    async def restore_model(self, model_id: UUID, owner_id: UUID) -> bool:
        model = await self.get_model(model_id)
        if not model:
            return False
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        if model.status == ModelStatus.ARCHIVED:
            model.status = ModelStatus.TRAINED
        await self.db.flush()
        return True

    async def train_model(
        self,
        model_id: UUID,
        train_request: TrainRequest,
        owner_id: UUID,
    ) -> Experiment:
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        dataset_result = await self.db.execute(
            select(Dataset).where(Dataset.id == train_request.dataset_id)
        )
        dataset = dataset_result.scalar_one_or_none()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        target_col = train_request.target_column or dataset.target_column
        if not target_col:
            raise HTTPException(status_code=400, detail="Target column required")

        experiment = Experiment(
            name=f"Training {model.name} v{model.version} ({train_request.mode.value})",
            status=ExperimentStatus.RUNNING,
            parameters={**train_request.parameters, 'mode': train_request.mode.value},
            dataset_id=train_request.dataset_id,
            model_id=model_id,
            owner_id=owner_id,
        )
        self.db.add(experiment)
        await self.db.flush()

        if train_request.async_training:
            try:
                task_id = self._dispatch_async_training(
                    model_id=str(model.id),
                    experiment_id=str(experiment.id),
                    dataset_path=dataset.file_path,
                    algorithm=train_request.algorithm,
                    parameters=train_request.parameters,
                    target_column=target_col,
                    owner_id=str(owner_id),
                )
                model.task_id = task_id
                model.status = ModelStatus.TRAINING
                await self.db.flush()
                await self.db.refresh(experiment)
                return experiment
            except HTTPException as exc:
                if exc.status_code == 503:
                    logger.warning(
                        "Async training unavailable, falling back to synchronous training: %s",
                        exc.detail,
                    )
                else:
                    raise

        try:
            with open(dataset.file_path, "rb") as f:
                file_content = f.read()

            timeout = settings.TRAINING_TIMEOUT_SECONDS

            def _run_training(pipeline, training_fn):
                return training_fn(
                    file_content=file_content,
                    filename=os.path.basename(dataset.file_path),
                    target_column=target_col,
                )

            if train_request.mode == TrainingMode.SIMPLE:
                pipeline = AutoMLPipeline()
                training_fn = pipeline.run_training
            else:
                pipeline = MLPipeline()
                training_fn = (
                    lambda **kwargs: pipeline.run_training(
                        **kwargs,
                        algorithm=train_request.algorithm,
                        parameters=train_request.parameters,
                    )
                )

            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(_run_training, pipeline, training_fn),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.error(f"Training timed out after {timeout}s for model {model_id}")
                raise HTTPException(
                    status_code=504,
                    detail=f"Training exceeded timeout of {timeout} seconds. "
                    f"Please use async training or reduce dataset size.",
                )

            if result["status"] == "completed":
                model_dir = os.path.join(
                    self.artifacts_dir, f"model_{model.id}_v{model.version}"
                )
                artifacts = pipeline.save_artifacts(model_dir)

                model.status = ModelStatus.TRAINED
                model.file_path = artifacts.get("bundle_dir", os.path.dirname(artifacts["model_path"]))
                model.metrics = result.get("metrics", {})
                model.parameters = result.get("parameters", {})
                model.feature_names = result.get("data_info", {}).get("features", [])

                # ── Full lineage ───────────────────────────────────────
                model.artifact_hash = artifacts.get("artifact_hash")
                lib_versions = result.get("library_versions", {})
                model.python_version = lib_versions.get("python")
                model.sklearn_version = lib_versions.get("sklearn")
                model.random_seed = 42  # default
                model.training_config = {
                    "algorithm": result.get("algorithm"),
                    "parameters": result.get("parameters", {}),
                    "mode": train_request.mode.value if train_request.mode else "advanced",
                }
                # ── Dataset hash — compute from file content ───────────
                import hashlib
                try:
                    with open(dataset.file_path, 'rb') as f:
                        dataset_hash = hashlib.sha256(f.read()).hexdigest()
                    model.dataset_hash = dataset_hash
                except Exception:
                    model.dataset_hash = None
                model.preprocessing_version = "v1"
                model.feature_schema_version = "v1"
                model.evaluation_report = {
                    "metrics": result.get("metrics", {}),
                    "benchmark": result.get("benchmark"),
                    "cross_validation": result.get("metrics", {}).get("cross_validation"),
                    "calibration": result.get("metrics", {}).get("calibration"),
                    "data_info": result.get("data_info", {}),
                }
                import subprocess
                try:
                    model.git_commit_sha = subprocess.check_output(
                        ["git", "rev-parse", "--short", "HEAD"],
                        cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                        stderr=subprocess.DEVNULL,
                        timeout=3,
                    ).decode().strip()
                except Exception:
                    model.git_commit_sha = None

                if train_request.mode == TrainingMode.SIMPLE and hasattr(pipeline, 'generate_human_summary'):
                    result['human_summary'] = pipeline.generate_human_summary()

                # ── Artifact integrity check ───────────────────────────
                from app.ml.artifact_manager import ArtifactManager
                bundle_dir = artifacts.get("bundle_dir", os.path.dirname(artifacts["model_path"]))
                try:
                    am = ArtifactManager(os.path.dirname(bundle_dir))
                    verification = am.verify_bundle(bundle_dir)
                    artifact_valid = verification["valid"]
                except Exception:
                    artifact_valid = False

                # ── Compute missing_ratio from quality gate ────────────
                quality_result = result.get("quality_gate", {})
                quality_checks = quality_result.get("checks", [])
                missing_ratio = 0.0
                for check in quality_checks:
                    if check.get("check") == "missing_features" and check.get("status") == "WARNING":
                        import re
                        m = re.search(r'(\d+)%', check.get("message", ""))
                        if m:
                            missing_ratio = int(m.group(1)) / 100.0
                        break

                # ── Stage 1: Compute readiness score (all params) ──────
                data_info = result.get("data_info", {})
                training_samples = data_info.get("rows", 0) or data_info.get("n_samples", 0)
                result_type = result.get("problem_type", "classification")
                cv_data = result.get("cross_validation", {})
                cv_scores = result.get("cv_scores")
                if cv_scores is None:
                    for metric_values in cv_data.values():
                        if isinstance(metric_values, dict) and "scores" in metric_values:
                            cv_scores = metric_values["scores"]
                            break

                # Detect leakage from quality gate
                has_leakage = False
                for check in quality_checks:
                    if check.get("check") == "target_leakage" and check.get("status") == "BLOCKED":
                        has_leakage = True
                        break

                # Compute class imbalance
                class_imbalance_ratio = 1.0
                data_quality_issues = []
                for check in quality_checks:
                    if check.get("status") == "WARNING":
                        data_quality_issues.append(check.get("message", ""))
                    if check.get("check") == "single_class_target":
                        class_imbalance_ratio = 0.0

                readiness = compute_readiness_score(
                    metrics=model.metrics,
                    feature_count=len(model.feature_names or []),
                    training_samples=training_samples,
                    result_type=result_type,
                    cv_scores=cv_scores,
                    artifact_valid=artifact_valid,
                    has_drift_baseline=False,
                    serving_latency_ms=0.0,
                    feature_names=model.feature_names,
                    sensitive_features=None,
                    missing_ratio=missing_ratio,
                    class_imbalance_ratio=class_imbalance_ratio,
                    data_quality_issues=data_quality_issues or None,
                    has_leakage=has_leakage,
                    random_seed=model.random_seed,
                    library_versions=lib_versions or None,
                )
                model.readiness_score = readiness["score"]
                model.readiness_label = readiness["label"]
                model.readiness_details = readiness
                model.training_samples = training_samples
                model.cv_scores = cv_scores or []
                result["readiness"] = readiness

                experiment.status = ExperimentStatus.COMPLETED
                experiment.results = result
                experiment.duration_seconds = str(result.get("duration_seconds", 0))
            else:
                experiment.status = ExperimentStatus.FAILED
                experiment.results = result
                model.status = ModelStatus.FAILED

            await self.db.flush()
            await self.db.refresh(experiment)
            return experiment

        except Exception as e:
            log_error(e, context=f"Training failed for model {model_id}")
            experiment.status = ExperimentStatus.FAILED
            experiment.results = {"error": sanitize_error_message(e)}
            model.status = ModelStatus.FAILED
            await self.db.flush()
            raise HTTPException(status_code=500, detail="Training failed. Please check your dataset and try again.")

    async def update_model(self, model_id: UUID, update_data: dict, owner_id: UUID) -> MLModel:
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        ALLOWED_UPDATE_FIELDS = {"name", "description", "tags", "target_column"}
        for field, value in update_data.items():
            if field in ALLOWED_UPDATE_FIELDS and value is not None:
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def hard_delete_model(self, model_id: UUID, owner_id: UUID) -> bool:
        """Permanently delete model and its files. Use delete_model for soft delete."""
        model = await self.get_model(model_id)
        if not model:
            return False
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        if model.file_path and os.path.exists(model.file_path):
            model_dir = os.path.dirname(model.file_path)
            import shutil
            shutil.rmtree(model_dir, ignore_errors=True)

        await self.db.delete(model)
        return True

    async def get_model_versions(self, model_name: str, owner_id: UUID) -> List[MLModel]:
        result = await self.db.execute(
            select(MLModel)
            .where(MLModel.name == model_name, MLModel.owner_id == owner_id)
            .order_by(MLModel.version.desc())
        )
        return list(result.scalars().all())

    async def set_default_model(self, model_id: UUID, owner_id: UUID) -> MLModel:
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        result = await self.db.execute(
            select(MLModel)
            .where(MLModel.owner_id == owner_id, MLModel.is_default == 1)
        )
        current_default = result.scalars().all()
        for m in current_default:
            m.is_default = 0

        model.is_default = 1
        await self.db.flush()
        return model

    async def get_deployed_models(self) -> List[MLModel]:
        result = await self.db.execute(
            select(MLModel).where(MLModel.status == ModelStatus.DEPLOYED)
        )
        return list(result.scalars().all())

    async def update_stage(self, model_id: UUID, stage: str, owner_id: UUID) -> MLModel:
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        # ── ENFORCEMENT: Block production deployment if critical gates fail ──
        if stage == "production":
            readiness = model.readiness_details or {}
            status = readiness.get("status", "")
            critical_failures = readiness.get("critical_failures", [])

            if status == "blocked":
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Model BLOCKED from production deployment. "
                        f"Critical gate(s) failed: {', '.join(critical_failures)}. "
                        f"Fix these issues before promoting to production."
                    ),
                )

            if readiness.get("score", 0) < 50:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Model readiness score {readiness.get('score', 0)} is below minimum "
                        f"threshold of 50. Current status: {readiness.get('label', 'unknown')}. "
                        f"Improve the model before promoting to production."
                    ),
                )

            # Record deployment in history
            history = model.deployment_history or []
            history.append({
                "action": "deploy",
                "version": model.version,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "artifact_hash": model.artifact_hash,
                "readiness_score": readiness.get("score"),
            })
            model.deployment_history = history

        model.stage = stage
        if stage == "production":
            model.status = ModelStatus.DEPLOYED
        elif stage == "archived":
            model.status = ModelStatus.ARCHIVED

        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def rollback_model(self, model_id: UUID, owner_id: UUID) -> MLModel:
        """Atomic rollback: create a new version pointing to previous artifact bundle."""
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        result = await self.db.execute(
            select(MLModel)
            .where(
                MLModel.name == model.name,
                MLModel.owner_id == owner_id,
                MLModel.version < model.version,
            )
            .order_by(MLModel.version.desc())
            .limit(1)
        )
        previous_version = result.scalar_one_or_none()

        if not previous_version:
            raise HTTPException(status_code=400, detail="No previous version to rollback to")

        # Record deployment history
        history = model.deployment_history or []
        history.append({
            "action": "rollback",
            "from_version": model.version,
            "to_version": previous_version.version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "artifact_hash": previous_version.artifact_hash,
        })

        # Atomic rollback: new version pointing to previous bundle (immutable)
        model.version = model.version + 1
        model.file_path = previous_version.file_path  # same bundle dir
        model.artifact_hash = previous_version.artifact_hash
        model.metrics = previous_version.metrics
        model.parameters = previous_version.parameters
        model.feature_names = previous_version.feature_names
        model.dataset_hash = previous_version.dataset_hash
        model.preprocessing_version = previous_version.preprocessing_version
        model.training_config = previous_version.training_config
        model.random_seed = previous_version.random_seed
        model.status = ModelStatus.TRAINED
        model.deployment_history = history

        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def update_model_card(self, model_id: UUID, model_card: dict, owner_id: UUID) -> MLModel:
        model = await self.get_model(model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        if model.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="Not authorized")

        model.model_card = model_card
        await self.db.flush()
        await self.db.refresh(model)
        return model
