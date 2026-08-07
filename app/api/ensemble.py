from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
import uuid
import numpy as np

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.safe_joblib import safe_load
from app.models.user import User
from app.models.model import MLModel

router = APIRouter(prefix="/ensemble", tags=["Multi-model Ensemble"])


class EnsembleCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    name: str
    description: Optional[str] = None
    model_ids: List[UUID]
    strategy: str = "voting"
    weights: Optional[dict] = None


class EnsembleResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    name: str
    strategy: str
    model_ids: List[str]
    weights: dict
    created_at: str


class EnsemblePredictRequest(BaseModel):
    ensemble_id: str
    data: dict


ensembles_store = {}


@router.post("", response_model=EnsembleResponse, status_code=201)
async def create_ensemble(
    data: EnsembleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if len(data.model_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models required")

    models_list = []
    for mid in data.model_ids:
        result = await db.execute(select(MLModel).where(MLModel.id == mid))
        model = result.scalar_one_or_none()
        if not model:
            raise HTTPException(status_code=404, detail=f"Model {mid} not found")
        models_list.append(model)

    ensemble_id = str(uuid.uuid4())
    weights = data.weights or {str(mid): 1.0 / len(data.model_ids) for mid in data.model_ids}

    ensembles_store[ensemble_id] = {
        "id": ensemble_id,
        "name": data.name,
        "description": data.description,
        "strategy": data.strategy,
        "model_ids": [str(mid) for mid in data.model_ids],
        "weights": weights,
        "owner_id": str(current_user.id),
        "created_at": "2026-01-01T00:00:00",
    }

    return EnsembleResponse(**ensembles_store[ensemble_id])


@router.get("")
async def list_ensembles(
    current_user: User = Depends(get_current_active_user),
):
    user_ensembles = [e for e in ensembles_store.values() if e.get("owner_id") == str(current_user.id)]
    return {"ensembles": user_ensembles}


@router.post("/predict")
async def ensemble_predict(
    data: EnsemblePredictRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    ensemble = ensembles_store.get(data.ensemble_id)
    if not ensemble:
        raise HTTPException(status_code=404, detail="Ensemble not found")

    predictions = []
    for mid in ensemble["model_ids"]:
        result = await db.execute(select(MLModel).where(MLModel.id == UUID(mid)))
        model = result.scalar_one_or_none()
        if not model or not model.file_path:
            continue

        try:
            model_data = safe_load(model.file_path)
            ml_model = model_data.get("model") if isinstance(model_data, dict) else model_data
            scaler = model_data.get("scaler") if isinstance(model_data, dict) else None

            import pandas as pd
            df = pd.DataFrame([data.data])
            if scaler:
                df = scaler.transform(df)

            pred = ml_model.predict(df)[0]
            weight = float(ensemble["weights"].get(mid, 1.0 / len(ensemble["model_ids"])))
            predictions.append({
                "model_id": mid,
                "prediction": pred.tolist() if hasattr(pred, 'tolist') else str(pred),
                "weight": weight,
            })
        except Exception:
            continue

    if not predictions:
        raise HTTPException(status_code=400, detail="No models could predict")

    if ensemble["strategy"] == "voting":
        from collections import Counter
        preds = [str(p["prediction"]) for p in predictions]
        weights = [p["weight"] for p in predictions]
        weighted_votes = Counter()
        for pred, w in zip(preds, weights):
            weighted_votes[pred] += w
        final = weighted_votes.most_common(1)[0][0]
    elif ensemble["strategy"] == "averaging":
        numeric_preds = [float(p["prediction"]) for p in predictions if str(p["prediction"]).replace('.','').replace('-','').isdigit()]
        if numeric_preds:
            final = sum(numeric_preds) / len(numeric_preds)
        else:
            final = predictions[0]["prediction"]
    else:
        final = predictions[0]["prediction"]

    return {
        "ensemble": ensemble["name"],
        "strategy": ensemble["strategy"],
        "final_prediction": final,
        "model_predictions": predictions,
    }
