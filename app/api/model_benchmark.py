from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.error_utils import sanitize_error_message, log_error
from app.models.user import User
from app.models.model import MLModel
from app.models.dataset import Dataset
from app.models.experiment import Experiment

router = APIRouter(prefix="/benchmark", tags=["Model Benchmark"])
logger = logging.getLogger(__name__)


@router.post("/{model_id}")
async def benchmark_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model or not model.file_path:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        from app.ml.trainer import ModelTrainer

        trainer = ModelTrainer()
        trainer.load_model(model.file_path)

        dataset_result = await db.execute(
            select(Dataset).where(Dataset.target_column == model.target_column)
        )
        datasets = dataset_result.scalars().all()

        if not datasets:
            experiment_result = await db.execute(
                select(Experiment).where(Experiment.model_id == model_id).order_by(Experiment.created_at.desc())
            )
            experiment = experiment_result.scalar_one_or_none()
            if experiment and experiment.dataset_id:
                dataset_result = await db.execute(
                    select(Dataset).where(Dataset.id == experiment.dataset_id)
                )
                datasets = dataset_result.scalars().all()

        if not datasets:
            raise HTTPException(status_code=400, detail="No dataset found for benchmarking")

        dataset = datasets[0]

        from app.ml.processor import DataProcessor
        processor = DataProcessor()

        with open(dataset.file_path, "rb") as f:
            file_content = f.read()

        df = processor.load_data(file_content, dataset.file_path.split("/")[-1])
        _, X_test, _, y_test, preprocess_metadata = processor.preprocess(
            df, model.target_column, test_size=0.2
        )

        problem_type = model.parameters.get('problem_type', 'classification') if model.parameters else 'classification'
        trainer.problem_type = problem_type

        benchmark_results = trainer.benchmark(
            X_test, y_test,
            feature_names=preprocess_metadata.get('feature_names', []),
        )

        return benchmark_results

    except HTTPException:
        raise
    except Exception as e:
        log_error(e, context=f"Benchmark failed for model {model_id}")
        raise HTTPException(status_code=500, detail=sanitize_error_message(e))
