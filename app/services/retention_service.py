import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from app.models.dataset import Dataset
from app.models.model import MLModel, ModelStatus
from app.models.experiment import Experiment
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

RETENTION_POLICIES = {
    "free": {
        "dataset_retention_days": 30,
        "model_retention_days": 60,
        "experiment_retention_days": 90,
        "max_storage_mb": 500,
    },
    "starter": {
        "dataset_retention_days": 90,
        "model_retention_days": 180,
        "experiment_retention_days": 365,
        "max_storage_mb": 5000,
    },
    "pro": {
        "dataset_retention_days": 365,
        "model_retention_days": 730,
        "experiment_retention_days": 1095,
        "max_storage_mb": 50000,
    },
    "enterprise": {
        "dataset_retention_days": -1,  # Unlimited
        "model_retention_days": -1,
        "experiment_retention_days": -1,
        "max_storage_mb": -1,
    },
}


class DataRetentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def get_retention_policy(self, tier: str) -> Dict[str, Any]:
        return RETENTION_POLICIES.get(tier, RETENTION_POLICIES["free"])

    async def check_user_storage(self, user_id: str, tier: str) -> Dict[str, Any]:
        policy = self.get_retention_policy(tier)

        if policy["max_storage_mb"] == -1:
            return {"within_limit": True, "unlimited": True}

        result = await self.db.execute(
            select(Dataset).where(Dataset.owner_id == user_id)
        )
        datasets = result.scalars().all()

        total_size_mb = 0
        for dataset in datasets:
            if dataset.file_path and os.path.exists(dataset.file_path):
                size_bytes = os.path.getsize(dataset.file_path)
                total_size_mb += size_bytes / (1024 * 1024)

        return {
            "within_limit": total_size_mb < policy["max_storage_mb"],
            "current_mb": round(total_size_mb, 2),
            "limit_mb": policy["max_storage_mb"],
            "usage_percentage": round((total_size_mb / policy["max_storage_mb"]) * 100, 1) if policy["max_storage_mb"] > 0 else 0,
        }

    async def enforce_retention(self, tier: str = "free") -> Dict[str, Any]:
        policy = self.get_retention_policy(tier)
        deleted_items = {"datasets": 0, "models": 0, "experiments": 0, "files_freed_mb": 0}

        if policy["dataset_retention_days"] > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=policy["dataset_retention_days"])
            result = await self.db.execute(
                select(Dataset).where(
                    and_(
                        Dataset.created_at < cutoff_date,
                        Dataset.is_archived == False,
                    )
                )
            )
            old_datasets = result.scalars().all()

            for dataset in old_datasets:
                if dataset.file_path and os.path.exists(dataset.file_path):
                    size_mb = os.path.getsize(dataset.file_path) / (1024 * 1024)
                    os.remove(dataset.file_path)
                    deleted_items["files_freed_mb"] += size_mb

                await self.db.delete(dataset)
                deleted_items["datasets"] += 1

        if policy["model_retention_days"] > 0:
            cutoff_date = datetime.utcnow() - timedelta(days=policy["model_retention_days"])
            result = await self.db.execute(
                select(MLModel).where(
                    and_(
                        MLModel.created_at < cutoff_date,
                        MLModel.status.notin_([ModelStatus.DEPLOYED, ModelStatus.PRODUCTION]),
                    )
                )
            )
            old_models = result.scalars().all()

            for model in old_models:
                if model.file_path and os.path.exists(model.file_path):
                    model_dir = os.path.dirname(model.file_path)
                    if os.path.exists(model_dir):
                        size_mb = sum(
                            os.path.getsize(os.path.join(model_dir, f))
                            for f in os.listdir(model_dir)
                            if os.path.isfile(os.path.join(model_dir, f))
                        ) / (1024 * 1024)
                        shutil.rmtree(model_dir)
                        deleted_items["files_freed_mb"] += size_mb

                await self.db.delete(model)
                deleted_items["models"] += 1

        await self.db.flush()

        logger.info(f"Retention enforcement completed: {deleted_items}")
        return deleted_items

    async def get_storage_usage(self, user_id: str) -> Dict[str, Any]:
        result = await self.db.execute(
            select(Dataset).where(Dataset.owner_id == user_id)
        )
        datasets = result.scalars().all()

        result = await self.db.execute(
            select(MLModel).where(MLModel.owner_id == user_id)
        )
        models = result.scalars().all()

        dataset_count = len(datasets)
        model_count = len(models)
        deployed_count = sum(1 for m in models if m.status == ModelStatus.DEPLOYED)

        storage_by_type = {"datasets": 0, "models": 0}

        for dataset in datasets:
            if dataset.file_path and os.path.exists(dataset.file_path):
                storage_by_type["datasets"] += os.path.getsize(dataset.file_path) / (1024 * 1024)

        for model in models:
            if model.file_path and os.path.exists(model.file_path):
                model_dir = os.path.dirname(model.file_path)
                if os.path.exists(model_dir):
                    storage_by_type["models"] += sum(
                        os.path.getsize(os.path.join(model_dir, f))
                        for f in os.listdir(model_dir)
                        if os.path.isfile(os.path.join(model_dir, f))
                    ) / (1024 * 1024)

        return {
            "datasets": {"count": dataset_count, "size_mb": round(storage_by_type["datasets"], 2)},
            "models": {"count": model_count, "deployed": deployed_count, "size_mb": round(storage_by_type["models"], 2)},
            "total_size_mb": round(sum(storage_by_type.values()), 2),
        }

    async def cleanup_deleted_users(self) -> Dict[str, Any]:
        from app.models.user import User

        result = await self.db.execute(
            select(User).where(User.is_active == False)
        )
        inactive_users = result.scalars().all()

        deleted_items = {"users": 0, "datasets": 0, "models": 0, "files_freed_mb": 0}

        for user in inactive_users:
            user_datasets = await self.db.execute(
                select(Dataset).where(Dataset.owner_id == user.id)
            )
            for dataset in user_datasets.scalars().all():
                if dataset.file_path and os.path.exists(dataset.file_path):
                    size_mb = os.path.getsize(dataset.file_path) / (1024 * 1024)
                    os.remove(dataset.file_path)
                    deleted_items["files_freed_mb"] += size_mb
                await self.db.delete(dataset)
                deleted_items["datasets"] += 1

            user_models = await self.db.execute(
                select(MLModel).where(MLModel.owner_id == user.id)
            )
            for model in user_models.scalars().all():
                if model.file_path and os.path.exists(model.file_path):
                    model_dir = os.path.dirname(model.file_path)
                    if os.path.exists(model_dir):
                        size_mb = sum(
                            os.path.getsize(os.path.join(model_dir, f))
                            for f in os.listdir(model_dir)
                            if os.path.isfile(os.path.join(model_dir, f))
                        ) / (1024 * 1024)
                        shutil.rmtree(model_dir)
                        deleted_items["files_freed_mb"] += size_mb
                await self.db.delete(model)
                deleted_items["models"] += 1

            await self.db.delete(user)
            deleted_items["users"] += 1

        await self.db.flush()

        logger.info(f"Inactive user cleanup completed: {deleted_items}")
        return deleted_items
