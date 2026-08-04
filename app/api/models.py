from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
import time

from app.core.database import get_db
from app.core.security import get_current_active_user, require_data_scientist
from app.core.redis import cache_get, cache_set, cache_delete
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.model import (
    ModelCreate, ModelResponse, ModelUpdate, ModelListResponse,
    TrainRequest, TrainResponse, PredictRequest, PredictResponse,
    BatchPredictRequest, BatchPredictResponse,
)
from app.services.model_service import ModelService
from app.ml.pipeline import MLPipeline

router = APIRouter(prefix="/models", tags=["Models"])


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
    return {"message": "Model deleted successfully"}


@router.post("/{model_id}/train", response_model=TrainResponse)
async def train_model(
    model_id: UUID,
    train_request: TrainRequest,
    current_user: User = Depends(require_data_scientist),
    db: AsyncSession = Depends(get_db),
):
    service = ModelService(db)
    experiment = await service.train_model(model_id, train_request, current_user.id)
    await cache_delete(f"model:{model_id}")
    await cache_delete(f"user_models:{current_user.id}")
    return TrainResponse(
        experiment_id=experiment.id,
        message="Training completed successfully",
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
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    start_time = time.time()
    result = pipeline.predict(predict_data.data, model.feature_names)
    latency_ms = int((time.time() - start_time) * 1000)

    if "predictions" in result:
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
        await db.flush()

    result["model_version"] = model.version
    result["latency_ms"] = latency_ms
    return result


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
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

    start_time = time.time()
    result = pipeline.predict(batch_data.data, model.feature_names)
    latency_ms = int((time.time() - start_time) * 1000)

    if "predictions" in result:
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
        await db.flush()

    return BatchPredictResponse(
        predictions=result.get("predictions", []),
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
