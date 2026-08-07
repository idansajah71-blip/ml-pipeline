import os
import uuid
import json
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException
import logging

from app.models.model import MLModel, ModelStatus
from app.models.dataset import Dataset
from app.models.experiment import Experiment, ExperimentStatus
from app.schemas.model import ModelCreate, TrainRequest, TrainingMode
from app.ml.pipeline import MLPipeline
from app.ml.auto_pipeline import AutoMLPipeline
from app.core.config import get_settings
from app.core.error_utils import sanitize_error_message, log_error

settings = get_settings()
logger = logging.getLogger(__name__)


class ModelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.artifacts_dir = settings.ML_ARTIFACTS_DIR

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
                detail=(
                    "Async training is temporarily unavailable. Training will continue synchronously. "
                    "Install celery/redis if you want background training."
                ),
            )
        if train_model_task is None or not hasattr(train_model_task, "delay"):
            raise HTTPException(
                status_code=503,
                detail=(
                    "Async training is temporarily unavailable. Training will continue synchronously. "
                    "Install celery/redis if you want background training."
                ),
            )

        result = train_model_task.delay(
            model_id=str(model_id),
            experiment_id=str(experiment_id),
            dataset_path=dataset_path,
            algorithm=algorithm,
            parameters=parameters or {},
            target_column=target_column,
            owner_id=str(owner_id),
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

            if train_request.mode == TrainingMode.SIMPLE:
                pipeline = AutoMLPipeline()
                result = pipeline.run_training(
                    file_content=file_content,
                    filename=os.path.basename(dataset.file_path),
                    target_column=target_col,
                )
            else:
                pipeline = MLPipeline()
                result = pipeline.run_training(
                    file_content=file_content,
                    filename=os.path.basename(dataset.file_path),
                    target_column=target_col,
                    algorithm=train_request.algorithm,
                    parameters=train_request.parameters,
                )

            if result["status"] == "completed":
                model_dir = os.path.join(
                    self.artifacts_dir, f"model_{model.id}_v{model.version}"
                )
                artifacts = pipeline.save_artifacts(model_dir)

                model.status = ModelStatus.TRAINED
                model.file_path = artifacts["model_path"]
                model.metrics = result.get("metrics", {})
                model.parameters = result.get("parameters", {})
                model.feature_names = result.get("data_info", {}).get("features", [])

                if train_request.mode == TrainingMode.SIMPLE and hasattr(pipeline, 'generate_human_summary'):
                    result['human_summary'] = pipeline.generate_human_summary()

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

        for field, value in update_data.items():
            if hasattr(model, field) and value is not None:
                setattr(model, field, value)

        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def delete_model(self, model_id: UUID, owner_id: UUID) -> bool:
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

        model.stage = stage
        if stage == "production":
            model.status = ModelStatus.DEPLOYED
        elif stage == "archived":
            model.status = ModelStatus.ARCHIVED

        await self.db.flush()
        await self.db.refresh(model)
        return model

    async def rollback_model(self, model_id: UUID, owner_id: UUID) -> MLModel:
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

        model.version = previous_version.version + 1
        model.file_path = previous_version.file_path
        model.metrics = previous_version.metrics
        model.parameters = previous_version.parameters
        model.feature_names = previous_version.feature_names
        model.status = ModelStatus.TRAINED

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
