from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import json
import numpy as np
from pathlib import Path
import asyncio

from app.core.database import get_db
from app.core.security import get_current_active_user, require_admin
from app.models.user import User
from app.models.model import MLModel, ModelShare, ModelFeedback, ModelReport
from app.models.prediction import Prediction
from app.core.config import get_settings

router = APIRouter(prefix="/marketplace", tags=["Model Marketplace"])

# Platform disclaimers
PLATFORM_DISCLAIMER = (
    "Model ini dibuat oleh pengguna komunitas, bukan hasil kurasi resmi platform. "
    "Hasil prediksi bersifat indikatif dan tidak boleh digunakan sebagai satu-satunya "
    "dasar pengambilan keputusan bisnis, medis, hukum, atau keuangan. "
    "Gunakan dengan pertimbangan sendiri."
)

COMMUNITY_MODEL_LIMITATIONS = (
    "Keterbatasan model komunitas: "
    "(1) Dilatih pada dataset terbatas, mungkin tidak representatif untuk semua kasus. "
    "(2) Belum melalui validasi independen dari tim platform. "
    "(3) Performa dapat berkurang pada data yang sangat berbeda dari data training. "
    "(4) Tidak ada jaminan uptime atau ketersediaan model. "
    "(5) Pengguna bertanggung jawab atas verifikasi hasil prediksi sebelum pengambilan keputusan."
)

DATA_PRIVACY_WARNING = (
    "Jangan unggah data pribadi, sensitif, atau rahasia ke model komunitas. "
    "Data yang dikirimkan akan diproses untuk prediksi dan tidak dijamin keamanannya."
)

PLATFORM_MODEL_LIMITATIONS = (
    "Model platform dilatih pada data sintetis untuk tujuan demonstrasi. "
    "Performa pada data dunia nyata mungkin berbeda. "
    "Gunakan sebagai referensi awal, bukan satu-satunya dasar keputusan."
)


# ── Cache eviction helper ─────────────────────────────────────────────────────
def _evict_cache_if_needed(cache: Dict[str, Any], max_size: int):
    """Evict oldest entries if cache exceeds max size."""
    if len(cache) > max_size:
        keys_to_remove = list(cache.keys())[:len(cache) - max_size + 10]
        for k in keys_to_remove:
            cache.pop(k, None)


# ── Prediction timeout wrapper ────────────────────────────────────────────────
class PredictionTimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise PredictionTimeoutError("Prediksi melewati batas waktu")


async def _run_with_timeout(coro, timeout_seconds: int):
    """Run an async coroutine with a timeout. Raises HTTPException on timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Prediksi melewati batas waktu ({timeout_seconds} detik). "
                   "Coba kurangi jumlah data atau gunakan model yang lebih sederhana."
        )

# ── Real ML model loading (for platform models) ──────────────────────────────
MODELS_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "platform"
_model_cache: Dict[str, Any] = {}


def _load_platform_model(model_id: str):
    """Load a trained joblib model, with in-memory caching. Uses safe_load for security."""
    if model_id in _model_cache:
        return _model_cache[model_id]
    joblib_path = MODELS_DIR / f"{model_id}.joblib"
    meta_path = MODELS_DIR / f"{model_id}_meta.json"
    if not joblib_path.exists() or not meta_path.exists():
        return None
    from app.core.safe_joblib import safe_load
    model = safe_load(str(joblib_path))
    with open(meta_path) as f:
        meta = json.load(f)
    _evict_cache_if_needed(_model_cache, get_settings().MARKETPLACE_MAX_MODEL_CACHE_SIZE)
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
    """Load a user-trained model + processor from disk, with caching.
    Uses safe_load to prevent arbitrary code execution from untrusted .joblib files.
    """
    if file_path in _user_model_cache:
        return _user_model_cache[file_path]
    artifact_dir = os.path.dirname(file_path)
    model_path = os.path.join(artifact_dir, "model.joblib")
    processor_path = os.path.join(artifact_dir, "processor.joblib")
    metadata_path = os.path.join(artifact_dir, "metadata.json")
    if not os.path.exists(model_path):
        return None
    from app.core.safe_joblib import safe_load
    model_data = safe_load(model_path)
    processor = None
    if os.path.exists(processor_path):
        processor = safe_load(processor_path)
    metadata = {}
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    result = {"model_data": model_data, "processor": processor, "metadata": metadata}
    _evict_cache_if_needed(_user_model_cache, get_settings().MARKETPLACE_MAX_MODEL_CACHE_SIZE)
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

    def model_post_init(self, __context):
        from app.core.config import get_settings
        settings = get_settings()
        if len(self.data) > settings.MARKETPLACE_MAX_INPUT_ROWS:
            raise ValueError(
                f"Terlalu banyak data: {len(self.data)} baris. "
                f"Maksimal {settings.MARKETPLACE_MAX_INPUT_ROWS} baris per prediksi."
            )


class FeedbackCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    rating: int  # 1-5
    comment: Optional[str] = None
    is_accurate: Optional[bool] = None
    actual_value: Optional[str] = None
    prediction_id: Optional[str] = None


REPORT_REASONS = ["inaccurate", "inappropriate", "misleading", "outdated", "other"]


class ReportCreate(BaseModel):
    reason: str  # must be one of REPORT_REASONS
    description: Optional[str] = None


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

    # Compute model confidence indicator
    model_confidence = "unknown"
    if m:
        metrics = m.metrics or {}
        accuracy = metrics.get("accuracy", metrics.get("f1", 0))
        r2 = metrics.get("r2", 0)
        readiness = m.readiness_score or 0
        training_samples = m.training_samples or 0

        # Score: 40% accuracy, 30% readiness, 30% data size
        confidence_score = 0
        if accuracy > 0:
            confidence_score += min(40, accuracy * 40)
        elif r2 > 0:
            confidence_score += min(40, r2 * 40)
        confidence_score += min(30, readiness * 0.3)
        confidence_score += min(30, min(30, training_samples / 100))

        if confidence_score >= 70:
            model_confidence = "high"
        elif confidence_score >= 40:
            model_confidence = "medium"
        else:
            model_confidence = "low"

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
        "model_confidence": model_confidence,
        "lifecycle_stage": share.lifecycle_stage if hasattr(share, 'lifecycle_stage') else "active",
        "deprecation_note": share.deprecation_note if hasattr(share, 'deprecation_note') else None,
        "deprecated_at": share.deprecated_at.isoformat() if hasattr(share, 'deprecated_at') and share.deprecated_at else None,
        "last_trained_at": share.last_trained_at.isoformat() if hasattr(share, 'last_trained_at') and share.last_trained_at else (m.updated_at.isoformat() if m and m.updated_at else None),
        "is_platform_model": False,
        "status": share.status,
        "disclaimer": PLATFORM_DISCLAIMER,
        "limitations_disclaimer": COMMUNITY_MODEL_LIMITATIONS,
        "data_privacy_warning": DATA_PRIVACY_WARNING,
    }


def _platform_model_to_dict(m: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure platform model dict has standard fields."""
    return {
        **m,
        "is_platform_model": True,
        "status": "approved",
        "disclaimer": "Model ini merupakan model platform yang sudah dikurasi. "
                      "Meskipun sudah diuji, hasil prediksi tetap bersifat indikatif.",
        "limitations_disclaimer": PLATFORM_MODEL_LIMITATIONS,
        "data_privacy_warning": DATA_PRIVACY_WARNING,
    }


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
    Enforces prediction timeout and input size limits.
    """
    settings = get_settings()
    timeout = settings.MARKETPLACE_PREDICTION_TIMEOUT_SECONDS

    # ── Try platform model first ──────────────────────────────────────────
    model_meta = next((m for m in PLATFORM_MODELS if m["id"] == data.share_id), None)
    if model_meta:
        return await _run_with_timeout(
            _predict_platform_model(data, model_meta, current_user),
            timeout
        )

    # ── Try DB share (user-trained model) ─────────────────────────────────
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(ModelShare.id == UUID(data.share_id))
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    share, ml_model = row
    return await _run_with_timeout(
        _predict_user_model(data, share, ml_model, current_user, db),
        timeout
    )


async def _predict_platform_model(data, model_meta, current_user):
    """Predict using platform models (joblib from models/platform/)."""
    required_cols = model_meta.get("feature_names", [])
    mapping = data.column_mapping or {}
    result_type = model_meta.get("result_type", "classification")

    real_model = _load_platform_model(data.share_id)
    if not real_model:
        raise HTTPException(
            status_code=500,
            detail=f"File model .joblib untuk '{data.share_id}' tidak ditemukan di server. "
                   "Model tidak dapat menjalankan inferensi ML. Hubungi admin untuk memeriksa integritas file model."
        )
    meta_info = real_model["meta"]

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

        X = np.array([feature_vals])
        clf = real_model["model"]
        meta_metrics = meta_info.get("metrics", {}) if meta_info else {}
        if result_type == "regression":
            pred_value = round(max(0, float(clf.predict(X)[0])), 2)
            # Conformal prediction interval using calibration residuals saved at training time
            from app.ml.prediction_interval import conformal_prediction_interval
            meta_metrics = meta_info.get("metrics", {}) if meta_info else {}
            cal_data = meta_metrics.get("calibration_residuals") or {}
            cal_residuals_list = cal_data.get("residuals")
            cal_predictions_list = cal_data.get("predictions")
            if cal_residuals_list and cal_predictions_list and len(cal_residuals_list) > 5:
                cal_residuals = np.array(cal_residuals_list)
                cal_predictions = np.array(cal_predictions_list)
                interval = conformal_prediction_interval(
                    cal_residuals, cal_predictions, pred_value, alpha=0.1
                )
            else:
                # No fallback — flag missing calibration data
                interval = {
                    "lower": None,
                    "upper": None,
                    "coverage_target": 0.9,
                    "warning": "No calibration residuals saved at training time. Retrain the model to enable conformal prediction intervals.",
                }
            predictions.append({
                "index": i,
                "prediction": pred_value,
                "prediction_label": f"{pred_value} {model_meta.get('result_unit', '')}".strip(),
                "result_type": "regression",
                "prediction_interval": {
                    "lower": round(interval["lower"], 4) if interval.get("lower") is not None else None,
                    "upper": round(interval["upper"], 4) if interval.get("upper") is not None else None,
                    "coverage_target": interval.get("coverage_target", 0.9),
                    **({"warning": interval["warning"]} if interval.get("warning") else {}),
                },
            })
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
            # Confidence level from probability
            if top_prob >= 0.85:
                confidence_level = "high"
            elif top_prob >= 0.6:
                confidence_level = "medium"
            else:
                confidence_level = "low"
            predictions.append({
                "index": i,
                "prediction": pred_class,
                "prediction_label": pred_label,
                "probability": top_prob,
                "probabilities": prob_dict,
                "result_type": "classification",
                "confidence_level": confidence_level,
            })

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
        "data_privacy_warning": DATA_PRIVACY_WARNING,
    }


async def _predict_user_model(data, share, ml_model, current_user, db):
    """
    Predict using user-trained models from disk.
    Loads model.joblib + processor.joblib, applies full preprocessing pipeline, runs prediction.
    Detects training mode (simple/advanced) from metadata to use correct pipeline class.
    """
    if not ml_model.file_path or not os.path.exists(ml_model.file_path):
        raise HTTPException(status_code=400, detail="File model tidak ditemukan di disk")

    loaded = _load_user_model(ml_model.file_path)
    if not loaded:
        raise HTTPException(status_code=500, detail="Gagal memuat model dari disk")

    model_data = loaded["model_data"]
    processor = loaded["processor"]
    metadata = loaded.get("metadata", {})
    sklearn_model = model_data.get("model") if isinstance(model_data, dict) else model_data

    if sklearn_model is None:
        raise HTTPException(status_code=500, detail="Model object tidak valid")

    # Check library version compatibility
    from app.ml.version_compat import check_version_compatibility, record_library_versions
    model_lib_versions = metadata.get("library_versions", {})
    current_lib_versions = record_library_versions()
    version_warnings = check_version_compatibility(model_lib_versions, current_lib_versions)

    # If critical mismatch, warn but still allow prediction (don't block)
    has_critical = any(w['severity'] == 'critical' for w in version_warnings)

    # Detect training mode and use the correct pipeline class
    training_mode = metadata.get("mode", "advanced")
    artifact_dir = os.path.dirname(ml_model.file_path)

    if training_mode == "simple":
        from app.ml.auto_pipeline import AutoMLPipeline
        pipeline = AutoMLPipeline()
    else:
        from app.ml.pipeline import MLPipeline
        pipeline = MLPipeline()

    try:
        pipeline.load_artifacts(artifact_dir)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gagal memuat preprocessor dari artifact: {str(e)}. "
                   "Model mungkin perlu dilatih ulang."
        )

    # Validate input data against training statistics
    input_warnings = pipeline.validate_input(data.data, ml_model.feature_names)

    import time
    start_time = time.time()
    try:
        result = pipeline.predict(data.data, ml_model.feature_names)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediksi gagal saat preprocessing: {str(e)}. "
                   "Pastikan input sesuai dengan format data training."
        )

    latency_ms = int((time.time() - start_time) * 1000)

    # Store predictions in DB
    if "predictions" in result:
        for pred in result["predictions"]:
            db_prediction = Prediction(
                input_data=data.data[pred["index"]] if pred.get("index", 0) < len(data.data) else None,
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
    result["input_validation"] = input_warnings
    if version_warnings:
        result["version_warnings"] = version_warnings
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

    # ── Stage 4: Quality gates (hard blocks + soft warnings) ───────────────
    settings = get_settings()
    warnings = []
    reject_reasons = []
    metrics = model.metrics or {}
    accuracy = metrics.get("accuracy", metrics.get("f1", 0))
    r2 = metrics.get("r2", 0)
    f1 = metrics.get("f1", 0)

    # Soft warnings for borderline quality
    if accuracy > 0 and accuracy < 0.6:
        warnings.append(f"Akurasi model rendah ({accuracy:.0%}). Pertimbangkan untuk melatih ulang.")
    if r2 > 0 and r2 < 0.5:
        warnings.append(f"Skor R² rendah ({r2:.2f}). Model mungkin belum cukup akurat.")
    if f1 > 0 and f1 < 0.5:
        warnings.append(f"Skor F1 rendah ({f1:.2f}). Pertimbangkan untuk melatih ulang.")
    if not data.use_case:
        warnings.append("Belum diisi 'Cocok Untuk apa'. Pengguna lain mungkin bingung kapan harus pakai model ini.")

    # Hard blocks — reject if below minimum thresholds
    if accuracy > 0 and accuracy < settings.MARKETPLACE_MIN_ACCURACY:
        reject_reasons.append(f"Akurasi terlalu rendah ({accuracy:.0%}). Minimum: {settings.MARKETPLACE_MIN_ACCURACY:.0%}")
    if r2 > 0 and r2 < settings.MARKETPLACE_MIN_R2:
        reject_reasons.append(f"Skor R² terlalu rendah ({r2:.2f}). Minimum: {settings.MARKETPLACE_MIN_R2}")
    if f1 > 0 and f1 < settings.MARKETPLACE_MIN_F1:
        reject_reasons.append(f"Skor F1 terlalu rendah ({f1:.2f}). Minimum: {settings.MARKETPLACE_MIN_F1}")
    if not model.training_samples or model.training_samples < 30:
        reject_reasons.append(f"Data training terlalu sedikit ({model.training_samples or 0} sampel). Minimum: 30 sampel")

    # Auto-moderation status
    status = "approved"
    if not model.description or len(model.description.strip()) < settings.MARKETPLACE_MIN_DESCRIPTION_LENGTH:
        status = "pending"
    if not data.use_case or len(data.use_case.strip()) < settings.MARKETPLACE_MIN_USE_CASE_LENGTH:
        status = "pending"

    # Hard reject: if any critical quality threshold is breached, block the publish
    if reject_reasons:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Model tidak memenuhi ambang batas kualitas minimum untuk dipublikasikan ke marketplace.",
                "reject_reasons": reject_reasons,
                "warnings": warnings,
                "suggestion": "Latih ulang model dengan data yang lebih banyak atau algoritma yang lebih cocok.",
            }
        )

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
    shares_models = result.all()

    if not shares_models:
        return {"models": [], "total": 0}

    share_ids = [share.id for share, _ in shares_models]

    fb_agg_result = await db.execute(
        select(
            ModelFeedback.share_id,
            func.count(ModelFeedback.id).label("total"),
            func.avg(ModelFeedback.rating).label("avg_rating"),
        ).where(ModelFeedback.share_id.in_(share_ids)).group_by(ModelFeedback.share_id)
    )
    fb_agg = {row.share_id: row for row in fb_agg_result.all()}

    models = []
    for share, model in shares_models:
        entry = _share_to_dict(share, model)
        agg = fb_agg.get(share.id)
        entry["total_feedback"] = agg.total if agg else 0
        entry["avg_user_rating"] = round(float(agg.avg_rating), 1) if agg and agg.avg_rating else None
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

    share_ids = [s.id for s in shares]
    if share_ids:
        fb_result = await db.execute(
            select(func.count(ModelFeedback.id)).where(ModelFeedback.share_id.in_(share_ids))
        )
        total_feedback = fb_result.scalar() or 0
    else:
        total_feedback = 0

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


# ── Reporting: users can report problematic models ────────────────────────────

@router.post("/{share_id}/report", status_code=201)
async def report_model(
    share_id: str,
    data: ReportCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Report a marketplace model for inaccurate, inappropriate, or misleading content."""
    if data.reason not in REPORT_REASONS:
        raise HTTPException(
            status_code=400,
            detail=f"Alasan tidak valid. Pilihan: {', '.join(REPORT_REASONS)}"
        )

    # Find the share and model
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    share, ml_model = row

    # Check if user already reported this model
    existing_stmt = select(ModelReport).where(
        ModelReport.share_id == UUID(share_id),
        ModelReport.reported_by == current_user.id,
        ModelReport.status == "pending",
    )
    existing = await db.execute(existing_stmt)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Kamu sudah melaporkan model ini")

    report = ModelReport(
        share_id=UUID(share_id),
        model_id=ml_model.id,
        reported_by=current_user.id,
        reason=data.reason,
        description=data.description,
        status="pending",
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)

    return {
        "status": "reported",
        "report_id": str(report.id),
        "message": "Laporan berhasil dikirim. Tim kami akan meninjau laporan Anda.",
    }


@router.get("/reports")
async def list_reports(
    status: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all reports (admin only)."""
    stmt = select(ModelReport, ModelShare, MLModel).join(
        ModelShare, ModelReport.share_id == ModelShare.id
    ).join(
        MLModel, ModelReport.model_id == MLModel.id
    )
    if status:
        stmt = stmt.where(ModelReport.status == status)
    stmt = stmt.order_by(ModelReport.created_at.desc())

    result = await db.execute(stmt)
    reports = []
    for report, share, model in result.all():
        reports.append({
            "id": str(report.id),
            "share_id": str(report.share_id),
            "model_name": model.name if model else "Unknown",
            "reason": report.reason,
            "description": report.description,
            "status": report.status,
            "admin_note": report.admin_note,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        })

    return {"reports": reports, "total": len(reports)}


@router.post("/reports/{report_id}/review")
async def review_report(
    report_id: str,
    action: str,
    admin_note: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Review a report: resolve (keep model) or dismiss (reject report). Admin action."""
    from datetime import datetime, timezone

    stmt = select(ModelReport).where(ModelReport.id == UUID(report_id))
    result = await db.execute(stmt)
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Laporan tidak ditemukan")

    if action == "resolve":
        report.status = "resolved"
        report.admin_note = admin_note or "Laporan ditinjau dan diselesaikan"
    elif action == "dismiss":
        report.status = "dismissed"
        report.admin_note = admin_note or "Laporan ditolak"
    elif action == "reject_model":
        # Reject the model itself
        report.status = "resolved"
        report.admin_note = admin_note or "Model ditolak berdasarkan laporan"
        share_stmt = select(ModelShare).where(ModelShare.id == report.share_id)
        share_result = await db.execute(share_stmt)
        share = share_result.scalar_one_or_none()
        if share:
            share.status = "rejected"
            share.review_note = f"Ditolak berdasarkan laporan: {report.reason}"
    else:
        raise HTTPException(status_code=400, detail="Action harus 'resolve', 'dismiss', atau 'reject_model'")

    report.reviewed_by = current_user.id
    report.reviewed_at = datetime.now(timezone.utc)
    await db.flush()

    return {"status": report.status, "report_id": report_id}


@router.post("/{share_id}/lifecycle")
async def update_lifecycle(
    share_id: str,
    stage: str,
    note: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update model lifecycle stage: active, deprecated, or archived."""
    from datetime import datetime, timezone

    if stage not in ("active", "deprecated", "archived"):
        raise HTTPException(status_code=400, detail="Stage harus 'active', 'deprecated', atau 'archived'")

    stmt = select(ModelShare).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    share = result.scalar_one_or_none()
    if not share:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    # Only the owner can change lifecycle
    if str(share.shared_by) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Bukan model kamu")

    share.lifecycle_stage = stage
    if stage == "deprecated":
        share.deprecation_note = note or "Model ini sudah usang dan mungkin tidak akurat"
        share.deprecated_at = datetime.now(timezone.utc)
    elif stage == "active":
        share.deprecation_note = None
        share.deprecated_at = None

    await db.flush()
    return {"status": "ok", "lifecycle_stage": stage, "share_id": share_id}


@router.get("/{share_id}/versions")
async def get_model_versions(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all published versions of a model (from the same owner, same model name)."""
    # First find the share to get the model
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(ModelShare.id == UUID(share_id))
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    share, current_model = row

    # Find all shares from the same owner for models with the same name
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(
        ModelShare.shared_by == current_model.owner_id,
        MLModel.name == current_model.name,
    ).order_by(MLModel.version.desc())
    result = await db.execute(stmt)

    versions = []
    for s, m in result.all():
        versions.append({
            "share_id": str(s.id),
            "model_id": str(m.id),
            "version": m.version,
            "lifecycle_stage": s.lifecycle_stage if hasattr(s, 'lifecycle_stage') else "active",
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "downloads": s.downloads or 0,
            "rating": s.rating or 0.0,
            "is_current": str(s.id) == share_id,
        })

    return {"versions": versions, "total": len(versions)}


@router.post("/{share_id}/moderate")
async def moderate_model(
    share_id: str,
    action: str,
    current_user: User = Depends(require_admin),
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


# ── Quick feedback: thumbs up/down on any prediction ──────────────────────────

class QuickFeedbackCreate(BaseModel):
    model_id: str
    is_correct: bool
    comment: Optional[str] = None
    prediction_id: Optional[str] = None


@router.post("/quick-feedback")
async def quick_feedback(
    data: QuickFeedbackCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Simplified feedback endpoint: user just says 'benar' or 'salah' on a prediction.
    Creates a ModelFeedback record with rating=5 (correct) or rating=1 (incorrect).
    """
    from uuid import UUID as _UUID

    model_uuid = _UUID(data.model_id)

    # Verify model exists
    model_result = await db.execute(select(MLModel).where(MLModel.id == model_uuid))
    ml_model = model_result.scalar_one_or_none()
    if not ml_model:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    # Find share_id if model is shared
    share_result = await db.execute(
        select(ModelShare).where(ModelShare.model_id == model_uuid, ModelShare.is_public == 1)
    )
    share = share_result.scalar_one_or_none()

    feedback = ModelFeedback(
        model_id=model_uuid,
        share_id=share.id if share else None,
        user_id=current_user.id,
        prediction_id=_UUID(data.prediction_id) if data.prediction_id else None,
        rating=5 if data.is_correct else 1,
        is_accurate=data.is_correct,
        comment=data.comment,
    )
    db.add(feedback)
    await db.flush()

    # Notify the model owner about feedback
    try:
        from app.api.in_app_notifications import create_notification
        owner_id = ml_model.owner_id
        if str(owner_id) != str(current_user.id):
            model_name = ml_model.name
            verdict = "benar" if data.is_correct else "salah"
            await create_notification(
                db=db,
                user_id=owner_id,
                notification_type="feedback_received",
                title=f"Feedback Prediksi: {model_name}",
                message=f"Seseorang menandai prediksi model '{model_name}' sebagai {verdict}.",
                link=f"/marketplace",
            )
    except Exception:
        pass  # Don't fail feedback if notification fails

    return {"status": "recorded", "feedback_id": str(feedback.id)}


# ── Usage statistics for shared model owners ──────────────────────────────────

@router.get("/my-models/stats")
async def get_my_models_usage_stats(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Aggregated usage statistics for all models shared by the current user.
    Returns: total downloads, avg rating, total feedback, per-model breakdown.
    """
    stmt = select(ModelShare, MLModel).join(MLModel, ModelShare.model_id == MLModel.id).where(
        ModelShare.shared_by == current_user.id
    )
    result = await db.execute(stmt)
    shares = result.all()

    if not shares:
        return {
            "total_models": 0,
            "total_downloads": 0,
            "avg_rating": 0.0,
            "total_feedback": 0,
            "models": [],
        }

    model_ids = list(set(model.id for _, model in shares))

    fb_agg_result = await db.execute(
        select(
            ModelFeedback.model_id,
            func.count(ModelFeedback.id).label("feedback_count"),
            func.avg(ModelFeedback.rating).label("avg_rating"),
            func.count().filter(ModelFeedback.is_accurate == True).label("accurate_count"),
        ).where(ModelFeedback.model_id.in_(model_ids)).group_by(ModelFeedback.model_id)
    )
    fb_agg = {row.model_id: row for row in fb_agg_result.all()}

    pred_agg_result = await db.execute(
        select(
            Prediction.model_id,
            func.count(Prediction.id).label("prediction_count"),
        ).where(Prediction.model_id.in_(model_ids)).group_by(Prediction.model_id)
    )
    pred_agg = {row.model_id: row for row in pred_agg_result.all()}

    total_downloads = 0
    total_rating = 0.0
    total_feedback = 0
    models_stats = []

    for share, model in shares:
        fb = fb_agg.get(model.id)
        pred = pred_agg.get(model.id)

        feedback_count = fb.feedback_count if fb else 0
        avg_fb_rating = float(fb.avg_rating) if fb and fb.avg_rating else 0
        accurate_count = fb.accurate_count if fb else 0
        prediction_count = pred.prediction_count if pred else 0
        accuracy_pct = round(accurate_count / feedback_count * 100, 1) if feedback_count > 0 else None

        downloads = share.downloads or 0
        rating = share.rating or 0.0
        total_downloads += downloads
        total_rating += rating
        total_feedback += feedback_count

        models_stats.append({
            "share_id": str(share.id),
            "model_id": str(model.id),
            "model_name": model.name,
            "algorithm": model.algorithm,
            "downloads": downloads,
            "rating": rating,
            "rating_count": share.rating_count or 0,
            "feedback_count": feedback_count,
            "prediction_count": prediction_count,
            "accuracy_from_feedback": accuracy_pct,
            "lifecycle_stage": share.lifecycle_stage if hasattr(share, 'lifecycle_stage') else "active",
            "status": share.status,
            "created_at": share.created_at.isoformat() if share.created_at else None,
        })

    num_models = len(shares)
    return {
        "total_models": num_models,
        "total_downloads": total_downloads,
        "avg_rating": round(total_rating / num_models, 1) if num_models > 0 else 0.0,
        "total_feedback": total_feedback,
        "models": models_stats,
    }
