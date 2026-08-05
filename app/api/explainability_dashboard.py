from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
import numpy as np
import joblib
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import get_settings
from app.core.error_utils import sanitize_error_message, log_error
from app.models.user import User
from app.models.model import MLModel

settings = get_settings()
router = APIRouter(prefix="/explain", tags=["Explainability Dashboard"])
logger = logging.getLogger(__name__)


class ExplainGlobalRequest(BaseModel):
    model_id: UUID
    n_samples: int = 100


@router.post("/global")
async def global_explainability(
    data: ExplainGlobalRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model or not model.file_path:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        import shap
        model_data = joblib.load(model.file_path)
        ml_model = model_data.get("model") if isinstance(model_data, dict) else model_data
        feature_names = model_data.get("feature_names", []) if isinstance(model_data, dict) else []

        X_background = np.random.randn(min(data.n_samples, 50), len(feature_names) or 10).astype(float)

        if hasattr(ml_model, 'predict'):
            explainer = shap.KernelExplainer(ml_model.predict, X_background)
            X_explain = np.random.randn(min(data.n_samples, 20), X_background.shape[1])
            shap_values = explainer.shap_values(X_explain)

            if isinstance(shap_values, list):
                mean_abs = np.mean([np.abs(sv) for sv in shap_values], axis=0)
            else:
                mean_abs = np.mean(np.abs(shap_values), axis=0)

            if len(mean_abs.shape) > 1:
                mean_abs = np.mean(mean_abs, axis=0)

            feature_importance = {}
            for i, name in enumerate(feature_names[:len(mean_abs)]):
                feature_importance[name] = round(float(mean_abs[i]), 6)
            for i in range(len(feature_names), len(mean_abs)):
                feature_importance[f"feature_{i}"] = round(float(mean_abs[i]), 6)

            feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[:20])

            return {
                "feature_importance": feature_importance,
                "n_samples": data.n_samples,
                "top_features": list(feature_importance.keys())[:10],
            }
    except Exception as e:
        log_error(e, context=f"Global explainability failed for model {data.model_id}")
        return {"error": "Failed to generate explanation. Please check your model and try again.", "feature_importance": {}}


@router.post("/prediction")
async def prediction_explain(
    model_id: UUID,
    input_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model or not model.file_path:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        import shap
        model_data = joblib.load(model.file_path)
        ml_model = model_data.get("model") if isinstance(model_data, dict) else model_data
        feature_names = model_data.get("feature_names", []) if isinstance(model_data, dict) else []

        df = pd.DataFrame([input_data])
        X = df.values.astype(float)

        X_background = np.random.randn(20, X.shape[1]).astype(float)
        explainer = shap.KernelExplainer(ml_model.predict, X_background)
        shap_values = explainer.shap_values(X)

        if isinstance(shap_values, list):
            sv = shap_values[0][0] if len(shap_values[0].shape) > 1 else shap_values[0]
        else:
            sv = shap_values[0] if len(shap_values.shape) > 1 else shap_values

        contributions = []
        for i, val in enumerate(sv):
            fname = feature_names[i] if i < len(feature_names) else f"feature_{i}"
            contributions.append({
                "feature": fname,
                "value": round(float(X[0][i]), 4),
                "contribution": round(float(val), 6),
                "direction": "positive" if val > 0 else "negative",
            })

        contributions.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        prediction = ml_model.predict(X)[0]

        return {
            "prediction": prediction.tolist() if hasattr(prediction, 'tolist') else str(prediction),
            "contributions": contributions[:20],
            "base_value": round(float(np.mean(sv)), 6),
        }
    except Exception as e:
        log_error(e, context=f"Prediction explanation failed for model {model_id}")
        return {"error": "Failed to explain prediction. Please check your input data and try again."}
