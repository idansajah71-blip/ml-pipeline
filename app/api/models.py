from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import time
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user, require_data_scientist
from app.core.redis import cache_get, cache_set, cache_delete
from app.core.error_utils import sanitize_error_message, log_error
from app.models.user import User
from app.models.prediction import Prediction
from app.models.model import MLModel, ModelStatus
from app.schemas.model import (
    ModelCreate, ModelResponse, ModelUpdate, ModelListResponse,
    TrainRequest, TrainResponse, PredictRequest, BatchPredictRequest,
    BatchPredictResponse, PredictionFeedbackRequest,
    PredictionFeedbackResponse, ModelStageUpdate,
    ModelCardUpdate, AutoMLRequest, AutoMLResponse, ExplainRequest,
    ExplainResponse, TaskStatusResponse,
)
from app.services.model_service import ModelService
from app.ml.pipeline import MLPipeline

router = APIRouter(prefix="/models", tags=["Models"])
logger = logging.getLogger(__name__)


@router.post("", response_model=ModelResponse, status_code=201)
async def create_model(
    model_data: ModelCreate,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.create_model(model_data, current_user.id)
    await cache_delete(f"user_models:{current_user.id}")
    return ModelResponse.model_validate(model)


@router.get("", response_model=ModelListResponse)
async def list_models(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"user_models:{current_user.id}:{skip}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        import json
        return ModelListResponse(**json.loads(cached))

    service = ModelService(db)
    models = await service.get_user_models(current_user.id, skip=skip, limit=limit)
    response = ModelListResponse(
        total=len(models),
        items=[ModelResponse.model_validate(m) for m in models],
    )

    import json
    await cache_set(cache_key, response.model_dump_json(), expire=300)
    return response


@router.get("/system")
async def list_system_models(
    current_user: User = Depends(get_current_active_user),
):
    """Return platform (built-in) models for the models page."""
    import json as _json
    from pathlib import Path

    _data_dir = Path(__file__).resolve().parent
    with open(_data_dir / "platform_models.json") as f:
        platform_models = _json.load(f)

    items = []
    for m in platform_models:
        items.append({
            "id": m["id"],
            "name": m["model_name"],
            "description": m.get("description", ""),
            "algorithm": m.get("algorithm", ""),
            "version": 1,
            "status": "trained",
            "file_path": None,
            "metrics": m.get("metrics", {}),
            "parameters": {},
            "feature_names": m.get("feature_names", []),
            "target_column": m.get("target_column"),
            "tags": m.get("tags", []),
            "is_default": 0,
            "task_id": None,
            "stage": "production",
            "parent_model_id": None,
            "model_card": {
                "use_case": m.get("use_case"),
                "result_label": m.get("result_label"),
                "result_unit": m.get("result_unit"),
                "result_type": m.get("result_type"),
                "category": m.get("category"),
                "is_platform_model": True,
            },
            "owner_id": str(current_user.id),
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
            "readiness_score": 100,
            "readiness_label": "Siap Dipublikasikan",
            "training_samples": 500,
            "is_system": True,
        })
    return {"total": len(items), "items": items}


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"model:{model_id}"
    cached = await cache_get(cache_key)
    if cached:
        import json
        return ModelResponse(**json.loads(cached))

    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    response = ModelResponse.model_validate(model)
    import json
    await cache_set(cache_key, response.model_dump_json(), expire=300)
    return response


@router.put("/{model_id}", response_model=ModelResponse)
async def update_model(
    model_id: UUID,
    update_data: ModelUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.update_model(model_id, update_data.model_dump(exclude_unset=True), current_user.id)
    await cache_delete(f"model:{model_id}")
    await cache_delete(f"user_models:{current_user.id}")
    return ModelResponse.model_validate(model)


@router.delete("/{model_id}")
async def delete_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    deleted = await service.delete_model(model_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Model not found")
    await cache_delete(f"model:{model_id}")
    await cache_delete(f"user_models:{current_user.id}")
    return {"message": "Model archived successfully"}


@router.get("/trash", response_model=List[ModelResponse])
async def list_trash_models(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    models = await service.get_archived_models(current_user.id, skip=skip, limit=limit)
    return [ModelResponse.model_validate(m) for m in models]


@router.post("/{model_id}/restore")
async def restore_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    restored = await service.restore_model(model_id, current_user.id)
    if not restored:
        raise HTTPException(status_code=404, detail="Model not found")
    await cache_delete(f"model:{model_id}")
    await cache_delete(f"user_models:{current_user.id}")
    return {"message": "Model restored successfully"}


@router.post("/{model_id}/train", response_model=TrainResponse)
async def train_model(
    model_id: UUID,
    train_request: TrainRequest,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    from app.models.experiment import ExperimentStatus
    service = ModelService(db)
    experiment = await service.train_model(model_id, train_request, current_user.id)
    await cache_delete(f"model:{model_id}")
    await cache_delete(f"user_models:{current_user.id}")
    return TrainResponse(
        experiment_id=experiment.id,
        message="Training completed successfully" if experiment.status == ExperimentStatus.COMPLETED
                 else f"Training {experiment.status.value}",
        status=experiment.status.value,
    )


@router.post("/{model_id}/predict")
async def predict(
    model_id: UUID,
    predict_data: PredictRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not model.file_path:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    pipeline = MLPipeline()
    try:
        import os
        pipeline.load_artifacts(os.path.dirname(model.file_path))
    except Exception as e:
        log_error(e, context=f"Failed to load model artifacts for model {model_id}")
        raise HTTPException(status_code=500, detail="Failed to load model. The model may be corrupted or missing.")

    start_time = time.time()
    result = pipeline.predict(predict_data.data, model.feature_names)
    latency_ms = int((time.time() - start_time) * 1000)

    if "predictions" in result:
        stored_predictions = []
        for pred in result["predictions"]:
            db_prediction = Prediction(
                input_data=predict_data.data[pred.get("index", 0)] if pred.get("index", 0) < len(predict_data.data) else {},
                prediction=pred.get("prediction", ""),
                probability=pred.get("probability"),
                confidence=pred.get("probability"),
                latency_ms=latency_ms,
                model_id=model_id,
            )
            db.add(db_prediction)
            stored_predictions.append((pred, db_prediction))
        await db.flush()
        result_predictions = []
        for pred, db_prediction in stored_predictions:
            result_predictions.append({
                "id": str(db_prediction.id),
                "index": pred.get("index", 0),
                "prediction": pred.get("prediction", ""),
                "probability": pred.get("predicted_probability") or pred.get("probability"),
                "probabilities": pred.get("probabilities"),
                "prediction_interval": pred.get("prediction_interval"),
            })
        result["predictions"] = result_predictions

    result["model_version"] = model.version
    result["latency_ms"] = latency_ms
    return result


@router.post("/{model_id}/predict/{prediction_id}/feedback", response_model=PredictionFeedbackResponse)
async def feedback_prediction(
    model_id: UUID,
    prediction_id: UUID,
    feedback_request: PredictionFeedbackRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = await db.execute(select(Prediction).where(Prediction.id == prediction_id, Prediction.model_id == model_id))
    prediction = stmt.scalar_one_or_none()
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    prediction.feedback_correct = feedback_request.correct
    prediction.feedback_comment = feedback_request.comment
    db.add(prediction)
    await db.flush()

    return PredictionFeedbackResponse(
        status="recorded",
        prediction_id=prediction_id,
        correct=feedback_request.correct,
    )


@router.post("/{model_id}/predict/batch", response_model=BatchPredictResponse)
async def batch_predict(
    model_id: UUID,
    batch_data: BatchPredictRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not model.file_path:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    pipeline = MLPipeline()
    try:
        import os
        pipeline.load_artifacts(os.path.dirname(model.file_path))
    except Exception as e:
        log_error(e, context=f"Failed to load model artifacts for batch prediction on model {model_id}")
        raise HTTPException(status_code=500, detail="Failed to load model. The model may be corrupted or missing.")

    start_time = time.time()
    result = pipeline.predict(batch_data.data, model.feature_names)
    latency_ms = int((time.time() - start_time) * 1000)

    result_predictions = []
    if "predictions" in result:
        stored_predictions = []
        for pred in result["predictions"]:
            idx = pred.get("index", 0)
            db_prediction = Prediction(
                input_data=batch_data.data[idx] if idx < len(batch_data.data) else {},
                prediction=pred.get("prediction", ""),
                probability=pred.get("probability"),
                confidence=pred.get("probability"),
                latency_ms=latency_ms,
                model_id=model_id,
            )
            db.add(db_prediction)
            stored_predictions.append((pred, db_prediction))
        await db.flush()
        for pred, db_prediction in stored_predictions:
            result_predictions.append({
                "id": str(db_prediction.id),
                "index": pred.get("index", 0),
                "prediction": pred.get("prediction", ""),
                "probability": pred.get("predicted_probability") or pred.get("probability"),
                "probabilities": pred.get("probabilities"),
                "prediction_interval": pred.get("prediction_interval"),
            })

    return BatchPredictResponse(
        predictions=result_predictions,
        model_version=model.version,
        latency_ms=latency_ms,
        total=len(batch_data.data),
    )


@router.post("/{model_id}/deploy")
async def deploy_model(
    model_id: UUID,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.update_model(
        model_id, {"status": "deployed"}, current_user.id
    )
    await cache_delete(f"model:{model_id}")
    return {"message": f"Model {model.name} v{model.version} deployed successfully"}


@router.get("/{model_id}/versions", response_model=List[ModelResponse])
async def get_model_versions(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    versions = await service.get_model_versions(model.name, current_user.id)
    return [ModelResponse.model_validate(v) for v in versions]


@router.post("/{model_id}/set-default")
async def set_default_model(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.set_default_model(model_id, current_user.id)
    await cache_delete(f"model:{model_id}")
    return {"message": f"Model {model.name} set as default"}


@router.get("/compare/{model_a_id}/{model_b_id}")
async def compare_models(
    model_a_id: UUID,
    model_b_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model_a = await service.get_model(model_a_id)
    model_b = await service.get_model(model_b_id)

    if not model_a or not model_b:
        raise HTTPException(status_code=404, detail="One or both models not found")

    return {
        "model_a": {
            "id": str(model_a.id),
            "name": model_a.name,
            "algorithm": model_a.algorithm,
            "version": model_a.version,
            "status": model_a.status.value,
            "metrics": model_a.metrics,
            "parameters": model_a.parameters,
            "created_at": model_a.created_at.isoformat(),
        },
        "model_b": {
            "id": str(model_b.id),
            "name": model_b.name,
            "algorithm": model_b.algorithm,
            "version": model_b.version,
            "status": model_b.status.value,
            "metrics": model_b.metrics,
            "parameters": model_b.parameters,
            "created_at": model_b.created_at.isoformat(),
        },
    }


@router.post("/{model_id}/stage", response_model=ModelResponse)
async def update_model_stage(
    model_id: UUID,
    stage_update: ModelStageUpdate,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.update_stage(model_id, stage_update.stage, current_user.id)
    await cache_delete(f"model:{model_id}")
    return ModelResponse.model_validate(model)


@router.post("/{model_id}/rollback", response_model=ModelResponse)
async def rollback_model(
    model_id: UUID,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.rollback_model(model_id, current_user.id)
    await cache_delete(f"model:{model_id}")
    return ModelResponse.model_validate(model)


@router.get("/{model_id}/card")
async def get_model_card(
    model_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return {"model_id": str(model.id), "model_card": model.model_card or {}}


@router.put("/{model_id}/card")
async def update_model_card(
    model_id: UUID,
    card_update: ModelCardUpdate,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.update_model_card(model_id, card_update.model_card, current_user.id)
    await cache_delete(f"model:{model_id}")
    return {"message": "Model card updated", "model_card": model.model_card}


@router.post("/automl", response_model=AutoMLResponse)
async def run_automl(
    automl_request: AutoMLRequest,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    from app.models.dataset import Dataset
    from app.models.experiment import Experiment as ExperimentModel, ExperimentStatus

    service = ModelService(db)

    dataset_result = await db.execute(
        select(Dataset).where(Dataset.id == automl_request.dataset_id)
    )
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    algorithms = automl_request.algorithms or [
        "random_forest", "gradient_boosting", "logistic_regression",
        "svm", "knn", "decision_tree", "adaboost", "bagging", "mlp",
    ]

    from app.ml.trainer import ModelTrainer
    algos = (
        ModelTrainer.ALGORITHMS
        if automl_request.problem_type == "classification"
        else ModelTrainer.REGRESSION_ALGORITHMS
    )
    invalid = [a for a in algorithms if a not in algos]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid algorithms: {invalid}")

    placeholder_model = MLModel(
        name=f"AutoML - {dataset.name}",
        algorithm="automl",
        status=ModelStatus.TRAINING,
        owner_id=current_user.id,
    )
    db.add(placeholder_model)
    await db.flush()

    experiment = ExperimentModel(
        name=f"AutoML - {dataset.name}",
        status=ExperimentStatus.RUNNING,
        parameters={"algorithms": algorithms},
        dataset_id=automl_request.dataset_id,
        model_id=placeholder_model.id,
        owner_id=current_user.id,
    )
    db.add(experiment)
    await db.flush()

    try:
        from app.ml.tasks import automl_task

        task_result = automl_task.delay(
            model_id="automl",
            experiment_id=str(experiment.id),
            dataset_path=dataset.file_path,
            target_column=automl_request.target_column,
            algorithms=algorithms,
            owner_id=str(current_user.id),
        )

        return AutoMLResponse(
            task_id=task_result.id,
            experiment_id=experiment.id,
            message="AutoML task started",
            status="running",
        )
    except Exception as e:
        log_error(e, context=f"AutoML task failed for dataset {automl_request.dataset_id}")
        experiment.status = ExperimentStatus.FAILED
        experiment.results = {"error": sanitize_error_message(e)}
        await db.flush()
        raise HTTPException(
            status_code=503,
            detail=(
                "Layanan AutoML background sedang tidak tersedia. "
                "Silakan coba lagi nanti, atau gunakan Training Wizard (mode sederhana) "
                "yang berjalan langsung tanpa antrean."
            ),
        )


# ── Auto Mode: Analyze dataset and suggest everything ────────────────────────

class AutoAnalyzeRequest(BaseModel):
    dataset_id: UUID
    target_column: Optional[str] = None  # user can override


class AutoAnalyzeResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    rows: int
    columns: int
    suggested_target: str
    target_reason: str
    problem_type: str
    problem_reason: str
    suggested_algorithm: str
    algorithm_reason: str
    column_summaries: List[dict]
    warnings: List[str]
    quality_score: float  # 0-100
    ready_to_train: bool


def _auto_detect_target(df) -> tuple:
    """Auto-detect the best target column. Returns (column_name, reason)."""
    import pandas as pd

    candidates = []
    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        nunique = series.nunique()
        total = len(series.dropna())
        if total == 0:
            continue
        unique_ratio = nunique / total

        # Skip ID-like columns
        if unique_ratio > 0.9 and dtype in ("int64", "float64"):
            continue
        # Skip datetime columns
        if "datetime" in dtype or "time" in dtype:
            continue

        score = 0
        reason_parts = []

        # Classification-like target
        if pd.api.types.is_string_dtype(series) or dtype == "bool":
            if nunique <= 20:
                score += 80
                reason_parts.append(f"kolom bertipe '{dtype}' dengan {nunique} kategori")
        elif nunique <= 20 and unique_ratio < 0.1:
            score += 70
            reason_parts.append(f"kolom numerik dengan {nunique} nilai unik (< 10%)")

        # Regression-like target
        elif pd.api.types.is_numeric_dtype(series) and nunique > 20:
            score += 50
            reason_parts.append(f"kolom numerik kontinu ({nunique} nilai unik)")

        # Check if column name suggests it's a target
        target_hints = [
            "target", "label", "output", "y", "class", "category",
            "churn", "price", "harga", "klasifikasi", "prediksi",
            "kemiskinan", "status", "hasil", "outcome", "value",
        ]
        col_lower = col.lower()
        for hint in target_hints:
            if hint in col_lower:
                score += 30
                reason_parts.append(f"nama kolom mengandung '{hint}'")
                break

        # Prefer columns with fewer missing values
        missing_pct = series.isna().sum() / len(series) * 100
        if missing_pct < 5:
            score += 10
        elif missing_pct > 30:
            score -= 20

        if score > 0:
            candidates.append((col, score, "; ".join(reason_parts) if reason_parts else "kandidat potensial"))

    if not candidates:
        # Fallback: last column
        last_col = df.columns[-1]
        return last_col, "Kolom terakhir dipilih sebagai target (fallback)"

    candidates.sort(key=lambda x: x[1], reverse=True)
    best = candidates[0]
    return best[0], best[2]


def _auto_detect_problem_type(series) -> tuple:
    """Auto-detect classification vs regression. Returns (type, reason)."""
    import pandas as pd

    dtype = str(series.dtype)
    nunique = series.nunique()
    total = len(series.dropna())

    if total == 0:
        return "classification", "Default ke klasifikasi (kolom kosong)"

    if pd.api.types.is_string_dtype(series) or dtype == "bool":
        return "classification", f"Tipe data '{dtype}' → klasifikasi"

    if nunique <= 10 and nunique / total < 0.05:
        return "classification", f"{nunique} nilai unik (< 5% dari total) → klasifikasi"

    if nunique <= 20 and nunique / total < 0.1:
        return "classification", f"{nunique} nilai unik dengan rasio rendah → klasifikasi"

    return "regression", f"{nunique} nilai unik kontinu → regresi"


def _auto_select_algorithm(problem_type: str, n_samples: int, n_features: int, missing_pct: float) -> tuple:
    """Auto-select the best algorithm. Returns (algorithm, reason)."""
    if problem_type == "classification":
        if n_samples < 1000:
            return "random_forest", "Dataset kecil → Random Forest (stabil & cepat)"
        elif n_samples < 10000:
            return "random_forest", "Dataset sedang → Random Forest (akurasi baik)"
        else:
            return "gradient_boosting", "Dataset besar → Gradient Boosting (performa maksimal)"
    else:
        if n_samples < 1000:
            return "random_forest", "Dataset kecil → Random Forest (anti overfitting)"
        elif n_samples < 10000:
            return "gradient_boosting", "Dataset sedang → Gradient Boosting (akurasi tinggi)"
        else:
            return "gradient_boosting", "Dataset besar → Gradient Boosting (performa optimal)"


@router.post("/auto-analyze", response_model=AutoAnalyzeResponse)
async def auto_analyze_dataset(
    request: AutoAnalyzeRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Auto-analyze a dataset: detect target, problem type, and suggest algorithm."""
    from app.models.dataset import Dataset
    import pandas as pd

    result = await db.execute(select(Dataset).where(Dataset.id == request.dataset_id))
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset tidak ditemukan")
    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Tidak punya akses")

    import os
    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="File dataset tidak ditemukan")

    from app.ml.data_utils import load_dataframe
    with open(dataset.file_path, "rb") as f:
        file_content = f.read()
    filename = os.path.basename(dataset.file_path)
    df = load_dataframe(file_content, filename)

    rows, columns = df.shape

    # Auto-detect target
    if request.target_column and request.target_column in df.columns:
        target_col = request.target_column
        target_reason = "Kolom yang kamu pilih"
    else:
        target_col, target_reason = _auto_detect_target(df)

    # Auto-detect problem type
    problem_type, problem_reason = _auto_detect_problem_type(df[target_col])

    # Auto-select algorithm
    total_cells = rows * columns
    total_missing = df.isna().sum().sum()
    missing_pct = round(total_missing / total_cells * 100, 1) if total_cells > 0 else 0
    algorithm, algorithm_reason = _auto_select_algorithm(problem_type, rows, columns, missing_pct)

    # Column summaries
    column_summaries = []
    for col in df.columns:
        series = df[col]
        dtype = str(series.dtype)
        null_count = int(series.isna().sum())
        null_pct = round(null_count / len(series) * 100, 1) if len(series) > 0 else 0
        nunique = int(series.nunique())
        col_type = "target" if col == target_col else "feature"
        if "datetime" in dtype or "time" in dtype:
            col_type = "datetime"
        elif nunique / max(len(series), 1) > 0.9 and dtype in ("int64", "float64"):
            col_type = "id"

        summary = {
            "name": col,
            "dtype": dtype,
            "null_pct": null_pct,
            "unique_count": nunique,
            "role": col_type,
        }
        if pd.api.types.is_numeric_dtype(series):
            summary["min"] = float(series.min()) if not series.isna().all() else None
            summary["max"] = float(series.max()) if not series.isna().all() else None
            summary["mean"] = round(float(series.mean()), 2) if not series.isna().all() else None
        column_summaries.append(summary)

    # Warnings
    warnings = []
    if rows < 50:
        warnings.append("Dataset sangat kecil (< 50 baris). Model mungkin kurang akurat.")
    elif rows < 200:
        warnings.append("Dataset relatif kecil. Pertimbangkan menambah data.")
    if missing_pct > 30:
        warnings.append(f"Tingkat missing values tinggi ({missing_pct}%).")
    target_missing = df[target_col].isna().sum() / len(df) * 100
    if target_missing > 1:
        warnings.append(f"Target '{target_col}' memiliki {target_missing:.1f}% missing values.")

    # Quality score
    quality_score = 100.0
    quality_score -= min(30, rows / 100)  # penalty for small datasets
    quality_score -= missing_pct * 0.5
    quality_score -= len(warnings) * 5
    quality_score = max(0, min(100, quality_score))

    return AutoAnalyzeResponse(
        dataset_id=str(dataset.id),
        dataset_name=dataset.name,
        rows=rows,
        columns=columns,
        suggested_target=target_col,
        target_reason=target_reason,
        problem_type=problem_type,
        problem_reason=problem_reason,
        suggested_algorithm=algorithm,
        algorithm_reason=algorithm_reason,
        column_summaries=column_summaries,
        warnings=warnings,
        quality_score=round(quality_score, 1),
        ready_to_train=quality_score > 30 and target_missing < 50,
    )


@router.post("/{model_id}/explain", response_model=ExplainResponse)
async def explain_prediction(
    model_id: UUID,
    explain_request: ExplainRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    model = await service.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if not model.file_path:
        raise HTTPException(status_code=400, detail="Model not trained yet")

    try:
        import numpy as np
        import shap
        import os

        pipeline = MLPipeline()
        pipeline.load_artifacts(os.path.dirname(model.file_path))

        input_df = pipeline.processor.preprocess_input(
            explain_request.data, model.feature_names
        )

        if hasattr(pipeline.trainer.model, "feature_importances_"):
            explainer = shap.TreeExplainer(pipeline.trainer.model)
        else:
            background = shap.sample(input_df, min(10, len(input_df)))
            explainer = shap.KernelExplainer(
                pipeline.trainer.model.predict_proba, background
            )

        shap_values = explainer.shap_values(input_df)

        if isinstance(shap_values, list):
            target_class = pipeline.trainer.model.classes_[-1]
            vals = shap_values[-1]
        else:
            vals = shap_values
            target_class = None

        explanations = []
        for i in range(len(explain_request.data)):
            contributions = []
            for j, feat in enumerate(model.feature_names):
                contributions.append({
                    "feature": feat,
                    "value": float(input_df.iloc[i, j]),
                    "contribution": float(vals[i, j]) if len(vals.shape) > 1 else float(vals[i]),
                    "direction": "positive" if (vals[i, j] if len(vals.shape) > 1 else vals[i]) > 0 else "negative",
                })
            contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

            predictions = pipeline.trainer.model.predict(input_df.iloc[[i]])
            proba = pipeline.trainer.model.predict_proba(input_df.iloc[[i]]) if hasattr(pipeline.trainer.model, "predict_proba") else None

            explanation = {
                "prediction": str(predictions[0]),
                "confidence": float(proba[0].max()) if proba is not None else None,
                "feature_contributions": contributions[:explain_request.top_k],
                "base_value": float(explainer.expected_value[-1] if isinstance(explainer.expected_value, list) else explainer.expected_value),
            }
            explanations.append(explanation)

        global_imp = {}
        mean_abs = np.abs(vals).mean(axis=0) if len(vals.shape) > 1 else np.abs(vals)
        for j, feat in enumerate(model.feature_names):
            global_imp[feat] = float(mean_abs[j])

        return ExplainResponse(
            explanations=explanations,
            global_importance=global_imp,
            feature_names=model.feature_names,
        )

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="SHAP not installed. Run: pip install shap",
        )
    except Exception as e:
        log_error(e, context=f"Explanation failed for model {model_id}")
        raise HTTPException(status_code=500, detail="Failed to generate explanation. Please check your input data.")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    from app.core.celery_app import celery_app as celery

    result = celery.AsyncResult(task_id)

    response = TaskStatusResponse(
        task_id=task_id,
        status=result.state,
    )

    if result.state == "STARTED":
        response.progress = result.info.get("progress", 0) if isinstance(result.info, dict) else 0
    elif result.state == "SUCCESS":
        response.result = result.result
    elif result.state == "FAILURE":
        response.result = {"error": str(result.result)}

    return response
