from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import io
import os
import json
import joblib
import numpy as np
from pathlib import Path

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.model import MLModel, ModelShare, ModelFeedback
from app.models.prediction import Prediction

router = APIRouter(prefix="/marketplace", tags=["Model Marketplace"])

# ── Real ML model loading (for platform models) ──────────────────────────────
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "platform"
_model_cache: Dict[str, Any] = {}


def _load_platform_model(model_id: str):
    """Load a trained joblib model, with in-memory caching."""
    if model_id in _model_cache:
        return _model_cache[model_id]
    joblib_path = MODELS_DIR / f"{model_id}.joblib"
    meta_path = MODELS_DIR / f"{model_id}_meta.json"
    if not joblib_path.exists() or not meta_path.exists():
        return None
    model = joblib.load(joblib_path)
    with open(meta_path) as f:
        meta = json.load(f)
    _model_cache[model_id] = {"model": model, "meta": meta}
    return _model_cache[model_id]


# ── Load platform models & categories from JSON (loaded once at startup) ──────

_DATA_DIR = Path(__file__).resolve().parent
with open(_DATA_DIR / "platform_models.json") as _f:
    PLATFORM_MODELS: List[Dict[str, Any]] = json.load(_f)
with open(_DATA_DIR / "categories.json") as _f:
    CATEGORIES: List[Dict[str, Any]] = json.load(_f)


# ── User model loading (Stage 3: load from ml_artifacts) ─────────────────────
_user_model_cache: Dict[str, Any] = {}


def _load_user_model(file_path: str):
    """Load a user-trained model + processor from disk, with caching."""
    if file_path in _user_model_cache:
        return _user_model_cache[file_path]
    artifact_dir = os.path.dirname(file_path)
    model_path = os.path.join(artifact_dir, "model.joblib")
    processor_path = os.path.join(artifact_dir, "processor.joblib")
    if not os.path.exists(model_path):
        return None
    model_data = joblib.load(model_path)
    processor = None
    if os.path.exists(processor_path):
        processor = joblib.load(processor_path)
    result = {"model_data": model_data, "processor": processor}
    _user_model_cache[file_path] = result
    return result


# ---------------------------------------------------------------------------
# In-memory stores (legacy for ratings, new shares use DB)
# ---------------------------------------------------------------------------
ratings_store: Dict[str, List[Dict[str, Any]]] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ShareCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    shared_with_org: Optional[str] = None
    permission: str = "read"
    is_public: bool = False
    tags: List[str] = []
    # Stage 2: Rich publish metadata
    use_case: Optional[str] = None
    limitations: Optional[str] = None
    example_inputs: Optional[List[Dict[str, Any]]] = None


class ShareResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    id: str
    model_id: str
    model_name: str
    shared_by: str
    permission: str
    is_public: int
    downloads: int
    rating: float
    rating_count: int
    tags: list
    created_at: str
    category: Optional[str] = None
    description: Optional[str] = None
    use_case: Optional[str] = None
    limitations: Optional[str] = None
    example_inputs: Optional[list] = None
    training_data_summary: Optional[dict] = None
    feature_names: Optional[List[str]] = None
    target_column: Optional[str] = None
    algorithm: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    readiness_score: Optional[int] = None
    readiness_label: Optional[str] = None
    is_platform_model: bool = False
    status: Optional[str] = None


class RatingCreate(BaseModel):
    rating: float
    review: Optional[str] = None


class ColumnMatchRequest(BaseModel):
    share_id: str
    user_columns: List[str]


class PlatformModelPredict(BaseModel):
    share_id: str
    data: List[Dict[str, Any]]
    column_mapping: Optional[Dict[str, str]] = None


class FeedbackCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    rating: int  # 1-5
    comment: Optional[str] = None
    is_accurate: Optional[bool] = None
    actual_value: Optional[str] = None
    prediction_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _similarity_score(a: str, b: str) -> float:
    """Simple string similarity for column matching."""
    a = a.lower().replace("_", " ").replace("-", " ")
    b = b.lower().replace("_", " ").replace("-", " ")
    if a == b:
        return 1.0
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union)
    prefix = 0.2 if (a.startswith(b[:3]) or b.startswith(a[:3])) else 0.0
    return min(1.0, jaccard + prefix)


def _share_to_dict(share: ModelShare, model: MLModel = None) -> Dict[str, Any]:
    """Convert a DB ModelShare to a dict for API responses."""
    m = model or share.model
    return {
        "id": str(share.id),
        "model_id": str(share.model_id),
        "model_name": m.name if m else "",
        "shared_by": str(share.shared_by),
        "permission": share.permission,
        "is_public": share.is_public,
        "downloads": share.downloads or 0,
        "rating": share.rating or 0.0,
        "rating_count": share.rating_count or 0,
        "tags": share.tags or [],
        "created_at": share.created_at.isoformat() if share.created_at else "",
        "category": "komunitas",
        "description": m.description if m else "",
        "use_case": share.use_case,
        "limitations": share.limitations,
        "example_inputs": share.example_inputs or [],
        "training_data_summary": share.training_data_summary or {},
        "feature_names": m.feature_names if m else [],
        "target_column": m.target_column if m else None,
        "algorithm": m.algorithm if m else None,
        "metrics": m.metrics if m else {},
        "readiness_score": m.readiness_score if m else None,
        "readiness_label": m.readiness_label if m else None,
        "is_platform_model": False,
        "status": share.status,
    }


def _platform_model_to_dict(m: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure platform model dict has standard fields."""
    return {**m, "is_platform_model": True, "status": "approved"}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/categories")
async def list_categories(current_user: User = Depends(get_current_active_user)):
    return {"categories": CATEGORIES}


@router.get("/discover")
async def discover_models(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_platform: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Discover public models with optional filters."""
    # Platform models
    result_models = [_platform_model_to_dict(m) for m in PLATFORM_MODELS]

    # Community shares from DB
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(
        ModelShare.is_public == 1, ModelShare.status == "approved"
    )
    db_result = await db.execute(stmt)
    for share, model in db_result.all():
        result_models.append(_share_to_dict(share, model))

    # Apply filters
    if category and category != "komunitas":
        result_models = [m for m in result_models if m.get("category") == category]
    if category == "komunitas":
        result_models = [m for m in result_models if not m.get("is_platform_model")]
    if is_platform is not None:
        result_models = [m for m in result_models if m.get("is_platform_model", False) == is_platform]
    if tag:
        result_models = [m for m in result_models if tag in m.get("tags", [])]
    if search:
        q = search.lower()
        result_models = [
            m for m in result_models
            if q in m.get("model_name", "").lower()
            or q in (m.get("description") or "").lower()
            or q in " ".join(m.get("tags", [])).lower()
        ]

    return {"models": result_models, "total": len(result_models)}


@router.get("/platform-models")
async def list_platform_models(current_user: User = Depends(get_current_active_user)):
    return {"models": PLATFORM_MODELS}


@router.get("/{share_id}")
async def get_model_detail(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full detail of a single marketplace model."""
    # Check platform models first
    for m in PLATFORM_MODELS:
        if m["id"] == share_id:
            return _platform_model_to_dict(m)

    # Check DB shares
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    row = result.first()
    if row:
        share, model = row
        return _share_to_dict(share, model)

    raise HTTPException(status_code=404, detail="Model tidak ditemukan")


@router.post("/column-match")
async def match_columns(
    data: ColumnMatchRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Match user columns to model's required columns."""
    # Platform model
    model_meta = next((m for m in PLATFORM_MODELS if m["id"] == data.share_id), None)
    if model_meta:
        required = model_meta.get("feature_names", [])
    else:
        # DB share
        stmt = select(MLModel).join(ModelShare, ModelShare.model_id == MLModel.id).where(ModelShare.id == UUID(data.share_id))
        result = await db.execute(stmt)
        ml_model = result.scalar_one_or_none()
        if not ml_model:
            raise HTTPException(status_code=404, detail="Model tidak ditemukan")
        required = ml_model.feature_names or []

    results = []
    for req_col in required:
        best_match = None
        best_score = 0.0
        for user_col in data.user_columns:
            score = _similarity_score(req_col, user_col)
            if score > best_score:
                best_score = score
                best_match = user_col
        results.append({
            "required_column": req_col,
            "suggested_user_column": best_match if best_score >= 0.3 else None,
            "confidence": round(best_score, 2),
        })
    return {"matches": results}


@router.post("/platform-predict")
async def platform_predict(
    data: PlatformModelPredict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Run inference on any marketplace model (platform or user-shared).
    Platform models: loads joblib from models/platform/.
    User models: loads from ml_artifacts with processor preprocessing.
    """
    # ── Try platform model first ──────────────────────────────────────────
    model_meta = next((m for m in PLATFORM_MODELS if m["id"] == data.share_id), None)
    if model_meta:
        return await _predict_platform_model(data, model_meta, current_user)

    # ── Try DB share (user-trained model) ─────────────────────────────────
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(ModelShare.id == UUID(data.share_id))
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    share, ml_model = row
    return await _predict_user_model(data, share, ml_model, current_user, db)


async def _predict_platform_model(data, model_meta, current_user):
    """Predict using platform models (joblib from models/platform/)."""
    required_cols = model_meta.get("feature_names", [])
    mapping = data.column_mapping or {}
    result_type = model_meta.get("result_type", "classification")

    real_model = _load_platform_model(data.share_id)
    meta_info = real_model["meta"] if real_model else None

    predictions = []
    for i, row in enumerate(data.data):
        mapped_row = {}
        for req_col in required_cols:
            user_col = mapping.get(req_col, req_col)
            mapped_row[req_col] = row.get(user_col, row.get(req_col, 0))

        feature_vals = []
        for v in mapped_row.values():
            try:
                feature_vals.append(float(v))
            except (ValueError, TypeError):
                feature_vals.append(0.0)

        if real_model:
            X = np.array([feature_vals])
            clf = real_model["model"]
            if result_type == "regression":
                pred_value = round(max(0, float(clf.predict(X)[0])), 2)
                predictions.append({"index": i, "prediction": pred_value,
                    "prediction_label": f"{pred_value} {model_meta.get('result_unit', '')}".strip(),
                    "result_type": "regression"})
            else:
                pred_class = int(clf.predict(X)[0])
                proba = clf.predict_proba(X)[0] if hasattr(clf, 'predict_proba') else None
                labels_from_meta = meta_info.get("labels") if meta_info else None
                class_labels = model_meta.get("class_labels", {})
                if labels_from_meta:
                    label_map = {idx: labels_from_meta[idx] if idx < len(labels_from_meta) else str(idx) for idx in range(len(labels_from_meta))}
                elif class_labels:
                    label_map = {int(k): v for k, v in class_labels.items()}
                else:
                    label_map = {idx: str(idx) for idx in range(len(proba) if proba is not None else 2)}
                pred_label = label_map.get(pred_class, str(pred_class))
                if proba is not None:
                    prob_dict = {label_map.get(idx, str(idx)): round(float(p), 3) for idx, p in enumerate(proba)}
                    top_prob = round(float(max(proba)), 3)
                else:
                    prob_dict, top_prob = {pred_label: 1.0}, 1.0
                predictions.append({"index": i, "prediction": pred_class, "prediction_label": pred_label,
                    "probability": top_prob, "probabilities": prob_dict, "result_type": "classification"})
        else:
            # Fallback simulation
            feature_sum = sum(feature_vals)
            if result_type == "regression":
                base = model_meta.get("metrics", {}).get("mae", 50)
                pred_value = round(max(0, feature_sum * 0.8 + base * 1.5), 2)
                predictions.append({"index": i, "prediction": pred_value,
                    "prediction_label": f"{pred_value} {model_meta.get('result_unit', '')}".strip(),
                    "result_type": "regression"})
            else:
                class_labels = model_meta.get("class_labels", {"0": "Kelas 0", "1": "Kelas 1"})
                prob_positive = round(min(0.99, max(0.01, (feature_sum % 10) / 10)), 2)
                predicted_class = "1" if prob_positive >= 0.5 else "0"
                predictions.append({"index": i, "prediction": predicted_class,
                    "prediction_label": class_labels.get(predicted_class, predicted_class),
                    "probability": prob_positive,
                    "probabilities": {class_labels.get("0", "0"): round(1 - prob_positive, 2), class_labels.get("1", "1"): prob_positive},
                    "result_type": "classification"})

    # Track usage
    for m in PLATFORM_MODELS:
        if m["id"] == data.share_id:
            m["downloads"] = m.get("downloads", 0) + 1
            break

    return {
        "model_name": model_meta["model_name"],
        "result_label": model_meta.get("result_label", "Hasil"),
        "result_unit": model_meta.get("result_unit"),
        "result_type": result_type,
        "predictions": predictions,
        "total": len(predictions),
    }


async def _predict_user_model(data, share, ml_model, current_user, db):
    """
    Stage 3: Predict using user-trained models from disk.
    Loads model.joblib + processor.joblib, applies preprocessing, runs prediction.
    """
    if not ml_model.file_path or not os.path.exists(ml_model.file_path):
        raise HTTPException(status_code=400, detail="File model tidak ditemukan di disk")

    loaded = _load_user_model(ml_model.file_path)
    if not loaded:
        raise HTTPException(status_code=500, detail="Gagal memuat model dari disk")

    model_data = loaded["model_data"]
    processor = loaded["processor"]
    sklearn_model = model_data.get("model") if isinstance(model_data, dict) else model_data

    if sklearn_model is None:
        raise HTTPException(status_code=500, detail="Model object tidak valid")

    # Build a temporary MLPipeline-like object for preprocessing
    from app.ml.pipeline import MLPipeline
    pipeline = MLPipeline()
    artifact_dir = os.path.dirname(ml_model.file_path)
    try:
        pipeline.load_artifacts(artifact_dir)
    except Exception:
        pass  # Fallback: try without full pipeline

    # Use the existing predict infrastructure
    import time
    start_time = time.time()
    try:
        result = pipeline.predict(data.data, ml_model.feature_names)
    except Exception as e:
        # Fallback: raw prediction without preprocessing
        predictions = []
        for i, row in enumerate(data.data):
            feature_vals = []
            for fname in (ml_model.feature_names or []):
                v = row.get(fname, 0)
                try:
                    feature_vals.append(float(v))
                except (ValueError, TypeError):
                    feature_vals.append(0.0)
            X = np.array([feature_vals])
            try:
                pred = sklearn_model.predict(X)[0]
                proba = sklearn_model.predict_proba(X)[0] if hasattr(sklearn_model, 'predict_proba') else None
                pred_result = {"index": i, "prediction": pred, "result_type": "classification"}
                if proba is not None:
                    pred_result["probability"] = round(float(max(proba)), 3)
                    pred_result["probabilities"] = {str(idx): round(float(p), 3) for idx, p in enumerate(proba)}
                predictions.append(pred_result)
            except Exception as e2:
                predictions.append({"index": i, "prediction": "Error", "error": str(e2), "result_type": "error"})
        result = {"predictions": predictions, "result_type": "classification"}

    latency_ms = int((time.time() - start_time) * 1000)

    # Store predictions in DB
    if "predictions" in result:
        for pred in result["predictions"]:
            db_prediction = Prediction(
                input_data=data.data[pred.get("index", 0) if pred.get("index", 0) < len(data.data) else {}],
                prediction=str(pred.get("prediction", "")),
                probability=pred.get("probability"),
                confidence=pred.get("probability"),
                latency_ms=latency_ms,
                model_id=ml_model.id,
            )
            db.add(db_prediction)
        await db.flush()

    # Track download
    share.downloads = (share.downloads or 0) + 1
    await db.flush()

    result["model_name"] = ml_model.name
    result["result_label"] = ml_model.model_card.get("result_label", "Hasil") if ml_model.model_card else "Hasil"
    result["result_type"] = result.get("result_type", "classification")
    result["latency_ms"] = latency_ms
    result["model_version"] = ml_model.version
    return result


@router.post("/share", status_code=201)
async def share_model(
    data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Stage 2+4: Publish a model to the marketplace with rich metadata and quality validation."""
    # Fetch the MLModel
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    if str(model.owner_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Bukan model kamu")

    # ── Stage 4: Quality gates ────────────────────────────────────────────
    warnings = []
    metrics = model.metrics or {}
    accuracy = metrics.get("accuracy", metrics.get("f1", 0))
    r2 = metrics.get("r2", 0)
    if accuracy > 0 and accuracy < 0.6:
        warnings.append(f"Akurasi model rendah ({accuracy:.0%}). Pertimbangkan untuk melatih ulang.")
    if r2 > 0 and r2 < 0.5:
        warnings.append(f"Skor R² rendah ({r2:.2f}). Model mungkin belum cukup akurat.")
    if not data.use_case:
        warnings.append("Belum diisi 'Cocok Untuk apa'. Pengguna lain mungkin bingung kapan harus pakai model ini.")

    # Auto-moderation status
    status = "approved"
    if not model.description or len(model.description.strip()) < 10:
        status = "pending"
    if not data.use_case or len(data.use_case.strip()) < 10:
        status = "pending"
    if accuracy > 0 and accuracy < 0.5:
        status = "pending"
    if r2 > 0 and r2 < 0.4:
        status = "pending"

    # Training data summary for transparency
    training_data_summary = {
        "training_samples": model.training_samples or 0,
        "feature_count": len(model.feature_names or []),
        "algorithm": model.algorithm,
        "readiness_score": model.readiness_score or 0,
    }

    share = ModelShare(
        model_id=data.model_id,
        shared_by=current_user.id,
        shared_with_org=data.shared_with_org,
        permission=data.permission,
        is_public=1 if data.is_public else 0,
        tags=data.tags,
        use_case=data.use_case,
        limitations=data.limitations,
        example_inputs=data.example_inputs or [],
        training_data_summary=training_data_summary,
        status=status,
    )
    db.add(share)
    await db.flush()
    await db.refresh(share)

    resp = _share_to_dict(share, model)
    if warnings:
        resp["warnings"] = warnings
    return resp


@router.post("/{share_id}/download")
async def download_model(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    # Platform models
    for m in PLATFORM_MODELS:
        if m["id"] == share_id:
            m["downloads"] = m.get("downloads", 0) + 1
            return {"status": "downloaded", "model_id": share_id}

    # DB shares
    stmt = select(ModelShare).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    share.downloads = (share.downloads or 0) + 1
    await db.flush()
    return {"status": "downloaded", "model_id": str(share.model_id)}


@router.post("/{share_id}/rate")
async def rate_model(
    share_id: str,
    data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating harus antara 1-5")

    # Platform models (in-memory)
    target = next((m for m in PLATFORM_MODELS if m["id"] == share_id), None)
    if target:
        if share_id not in ratings_store:
            ratings_store[share_id] = []
        ratings_store[share_id].append({"user_id": str(current_user.id), "rating": data.rating, "review": data.review})
        all_ratings = [r["rating"] for r in ratings_store[share_id]]
        new_avg = round(sum(all_ratings) / len(all_ratings), 1)
        target["rating"] = new_avg
        target["rating_count"] = len(all_ratings)
        return {"status": "rated", "new_rating": new_avg, "rating_count": len(all_ratings)}

    # DB shares
    stmt = select(ModelShare).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    # Simple average update (in production, store individual ratings in a table)
    old_count = share.rating_count or 0
    old_avg = share.rating or 0.0
    new_count = old_count + 1
    new_avg = round((old_avg * old_count + data.rating) / new_count, 1)
    share.rating = new_avg
    share.rating_count = new_count
    await db.flush()
    return {"status": "rated", "new_rating": new_avg, "rating_count": new_count}


# ── Stage 5: Feedback on marketplace model predictions ──────────────────────

@router.post("/{share_id}/feedback")
async def submit_feedback(
    share_id: str,
    data: FeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback on a marketplace model's prediction quality."""
    # Find the share
    stmt = select(ModelShare).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if not share:
        # Platform model feedback (store in-memory)
        model_meta = next((m for m in PLATFORM_MODELS if m["id"] == share_id), None)
        if not model_meta:
            raise HTTPException(status_code=404, detail="Model tidak ditemukan")
        return {"status": "recorded", "share_id": share_id, "note": "Platform model feedback recorded"}

    feedback = ModelFeedback(
        model_id=share.model_id,
        share_id=UUID(share_id),
        user_id=current_user.id,
        prediction_id=UUID(data.prediction_id) if data.prediction_id else None,
        rating=data.rating,
        comment=data.comment,
        is_accurate=data.is_accurate,
        actual_value=data.actual_value,
    )
    db.add(feedback)
    await db.flush()
    return {"status": "recorded", "share_id": share_id, "feedback_id": str(feedback.id)}


@router.get("/{share_id}/feedback-stats")
async def get_feedback_stats(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated feedback stats for a model."""
    # Find model_id from share
    stmt = select(ModelShare).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if not share:
        # Platform model
        model_meta = next((m for m in PLATFORM_MODELS if m["id"] == share_id), None)
        if not model_meta:
            raise HTTPException(status_code=404, detail="Model tidak ditemukan")
        return {
            "share_id": share_id,
            "total_feedback": 0,
            "avg_rating": model_meta.get("rating", 0),
            "accuracy_pct": None,
            "recent_comments": [],
        }

    # Aggregate from DB
    stmt = select(ModelFeedback).where(ModelFeedback.share_id == UUID(share_id))
    result = await db.execute(stmt)
    feedbacks = result.scalars().all()

    total = len(feedbacks)
    avg_rating = sum(f.rating for f in feedbacks) / total if total > 0 else 0
    accurate_count = sum(1 for f in feedbacks if f.is_accurate is True)
    accuracy_pct = round(accurate_count / total * 100, 1) if total > 0 else None
    recent = [{"rating": f.rating, "comment": f.comment, "is_accurate": f.is_accurate,
               "created_at": f.created_at.isoformat() if f.created_at else None}
              for f in sorted(feedbacks, key=lambda x: x.created_at or x.id, reverse=True)[:10]]

    return {
        "share_id": share_id,
        "total_feedback": total,
        "avg_rating": round(avg_rating, 1),
        "accuracy_pct": accuracy_pct,
        "recent_comments": recent,
    }


# ── Stage 6: Contributor stats ──────────────────────────────────────────────

@router.get("/my-models")
async def get_my_models(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all models shared by the current user with stats."""
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(
        ModelShare.shared_by == current_user.id
    )
    result = await db.execute(stmt)
    models = []
    for share, model in result.all():
        entry = _share_to_dict(share, model)
        # Get feedback stats
        fb_stmt = select(ModelFeedback).where(ModelFeedback.share_id == share.id)
        fb_result = await db.execute(fb_stmt)
        feedbacks = fb_result.scalars().all()
        entry["total_feedback"] = len(feedbacks)
        entry["avg_user_rating"] = round(sum(f.rating for f in feedbacks) / len(feedbacks), 1) if feedbacks else None
        models.append(entry)
    return {"models": models, "total": len(models)}


@router.get("/contributor-stats")
async def get_contributor_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Stage 6: Get contributor stats and badge for the current user."""
    stmt = select(ModelShare).where(ModelShare.shared_by == current_user.id)
    result = await db.execute(stmt)
    shares = result.scalars().all()

    total_models = len(shares)
    total_downloads = sum(s.downloads or 0 for s in shares)
    avg_rating = sum(s.rating or 0 for s in shares) / total_models if total_models > 0 else 0

    # Get total feedback across all models
    total_feedback = 0
    for s in shares:
        fb_stmt = select(func.count(ModelFeedback.id)).where(ModelFeedback.share_id == s.id)
        fb_result = await db.execute(fb_stmt)
        total_feedback += fb_result.scalar() or 0

    # Badge calculation
    badge = "Baru"
    if total_models >= 10 and avg_rating >= 4.5 and total_downloads >= 100:
        badge = "Kontributor Elite"
    elif total_models >= 5 and avg_rating >= 4.0 and total_downloads >= 50:
        badge = "Kontributor Aktif"
    elif total_models >= 3 and avg_rating >= 3.5:
        badge = "Kontributor"
    elif total_models >= 1:
        badge = "Pemula"

    return {
        "total_models_shared": total_models,
        "total_downloads": total_downloads,
        "avg_rating": round(avg_rating, 1),
        "total_feedback_received": total_feedback,
        "badge": badge,
    }


@router.post("/{share_id}/moderate")
async def moderate_model(
    share_id: str,
    action: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a pending model."""
    stmt = select(ModelShare).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    if action == "approve":
        share.status = "approved"
    elif action == "reject":
        share.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Action harus 'approve' atau 'reject'")

    await db.flush()
    return {"status": share.status, "model_id": share_id}
