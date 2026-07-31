import os
import uuid
import json
from typing import Optional, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models.model import MLModel, ModelStatus
from app.models.dataset import Dataset
from app.models.experiment import Experiment, ExperimentStatus
from app.schemas.model import ModelCreate, TrainRequest
from app.ml.pipeline import MLPipeline
from app.core.config import get_settings

settings = get_settings()


class ModelService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.artifacts_dir = settings.ML_ARTIFACTS_DIR

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
            .where(MLModel.owner_id == owner_id)
            .order_by(MLModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

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

        experiment = Experiment(
            name=f"Training {model.name} v{model.version}",
            status=ExperimentStatus.RUNNING,
            parameters=train_request.parameters,
            dataset_id=train_request.dataset_id,
            model_id=model_id,
            owner_id=owner_id,
        )
        self.db.add(experiment)
        await self.db.flush()

        try:
            with open(dataset.file_path, "rb") as f:
                file_content = f.read()

            target_col = train_request.target_column or dataset.target_column
            if not target_col:
                raise HTTPException(status_code=400, detail="Target column required")

            pipeline = MLPipeline()
            result = pipeline.run_training(
                file_content=file_content,
                filename=os.path.basename(dataset.file_path),
                target_column=target_col,
                algorithm=train_request.algorithm,
                parameters=train_request.parameters,
            )

            if result['status'] == 'completed':
                model_dir = os.path.join(self.artifacts_dir, f"model_{model.id}_v{model.version}")
                artifacts = pipeline.save_artifacts(model_dir)

                model.status = ModelStatus.TRAINED
                model.file_path = artifacts['model_path']
                model.metrics = result.get('metrics', {})
                model.parameters = result.get('parameters', {})
                model.feature_names = result.get('data_info', {}).get('features', [])

                experiment.status = ExperimentStatus.COMPLETED
                experiment.results = result
                experiment.duration_seconds = str(result.get('duration_seconds', 0))
            else:
                experiment.status = ExperimentStatus.FAILED
                experiment.results = result
                model.status = ModelStatus.FAILED

            await self.db.flush()
            await self.db.refresh(experiment)
            return experiment

        except Exception as e:
            experiment.status = ExperimentStatus.FAILED
            experiment.results = {'error': str(e)}
            model.status = ModelStatus.FAILED
            await self.db.flush()
            raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

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
