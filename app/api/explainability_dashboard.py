from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
import logging

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.config import get_settings
from app.core.error_utils import sanitize_error_message, log_error
from app.core.safe_joblib import safe_load
from app.models.user import User
from app.models.model import MLModel
from app.models.dataset import Dataset

settings = get_settings()
router = APIRouter(prefix="/explain", tags=["Explainability Dashboard"])
logger = logging.getLogger(__name__)


class ExplainGlobalRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    n_samples: int = 100
    method: str = "shap"


class ExplainPredictionRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    input_data: dict
    method: str = "shap"


def _get_shap_explanation(ml_model, X_background, X_explain, feature_names):
    import shap
    explainer = shap.KernelExplainer(ml_model.predict, X_background)
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
    return feature_importance


def _get_lime_global_explanation(ml_model, X_train, feature_names, n_samples=100):
    from app.ml.lime_explainer import LIMEExplainer

    explainer_obj = LIMEExplainer()
    explainer_obj.fit(X_train, feature_names)
    result = explainer_obj.explain_global(ml_model, X_train, feature_names, n_samples=n_samples)
    return result.get('feature_importance', {})


def _get_lime_prediction_explanation(ml_model, instance, X_train, feature_names, num_features=20):
    from app.ml.lime_explainer import LIMEExplainer

    explainer_obj = LIMEExplainer()
    explainer_obj.fit(X_train, feature_names)
    result = explainer_obj.explain_prediction(ml_model, instance, num_features=num_features)
    return result


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
        model_data = safe_load(model.file_path)
        ml_model = model_data.get("model") if isinstance(model_data, dict) else model_data
        feature_names = model_data.get("feature_names", []) if isinstance(model_data, dict) else []

        X_background = np.random.randn(min(data.n_samples, 50), len(feature_names) or 10).astype(float)

        method = data.method.lower()

        if method == "lime":
            try:
                dataset_result = await db.execute(
                    select(Dataset).where(Dataset.target_column == model.target_column)
                )
                datasets = dataset_result.scalars().all()
                if datasets:
                    df = pd.read_csv(datasets[0].file_path)
                    X_train = df.drop(columns=[model.target_column]).select_dtypes(include='number').values
                    feature_importance = _get_lime_global_explanation(
                        ml_model, X_train, feature_names, n_samples=data.n_samples
                    )
                else:
                    feature_importance = _get_shap_explanation(ml_model, X_background, X_background[:20], feature_names)
            except Exception:
                feature_importance = _get_shap_explanation(ml_model, X_background, X_background[:20], feature_names)
        else:
            feature_importance = _get_shap_explanation(ml_model, X_background, X_background[:20], feature_names)

        return {
            "feature_importance": feature_importance,
            "n_samples": data.n_samples,
            "top_features": list(feature_importance.keys())[:10],
            "method": method,
        }
    except Exception as e:
        log_error(e, context=f"Global explainability failed for model {data.model_id}")
        return {"error": "Failed to generate explanation.", "feature_importance": {}}


@router.post("/prediction")
async def prediction_explain(
    data: ExplainPredictionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model or not model.file_path:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        import shap
        model_data = safe_load(model.file_path)
        ml_model = model_data.get("model") if isinstance(model_data, dict) else model_data
        feature_names = model_data.get("feature_names", []) if isinstance(model_data, dict) else []

        df = pd.DataFrame([data.input_data])
        X = df.values.astype(float)

        method = data.method.lower()

        if method == "lime":
            try:
                dataset_result = await db.execute(
                    select(Dataset).where(Dataset.target_column == model.target_column)
                )
                datasets = dataset_result.scalars().all()
                if datasets:
                    train_df = pd.read_csv(datasets[0].file_path)
                    X_train = train_df.drop(columns=[model.target_column]).select_dtypes(include='number').values
                    lime_result = _get_lime_prediction_explanation(
                        ml_model, X[0], X_train, feature_names
                    )
                    return {
                        "prediction": ml_model.predict(X)[0].tolist() if hasattr(ml_model.predict(X)[0], 'tolist') else str(ml_model.predict(X)[0]),
                        "contributions": lime_result.get('contributions', []),
                        "method": "lime",
                    }
            except Exception:
                pass

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
            "method": "shap",
        }
    except Exception as e:
        log_error(e, context=f"Prediction explanation failed for model {data.model_id}")
        return {"error": "Failed to explain prediction."}
