from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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
from app.models.model import MLModel

router = APIRouter(prefix="/marketplace", tags=["Model Marketplace"])

# ── Real ML model loading ────────────────────────────────────────────────────
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


# ---------------------------------------------------------------------------
# In-memory stores (same pattern as existing codebase)
# ---------------------------------------------------------------------------
marketplace_store: List[Dict[str, Any]] = []
ratings_store: Dict[str, List[Dict[str, Any]]] = {}  # share_id -> list of ratings


def _get_all_public() -> List[Dict[str, Any]]:
    """Return platform models + community shares."""
    community = [s for s in marketplace_store if s.get("is_public") == 1 and s.get("status") == "approved"]
    return PLATFORM_MODELS + community


class ShareCreate(BaseModel):
    model_config = {"protected_namespaces": ()}

    model_id: UUID
    shared_with_org: Optional[str] = None
    permission: str = "read"
    is_public: bool = False
    tags: List[str] = []


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
    feature_names: Optional[List[str]] = None
    target_column: Optional[str] = None
    algorithm: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    is_platform_model: bool = False


class RatingCreate(BaseModel):
    rating: float
    review: Optional[str] = None


class ColumnMatchRequest(BaseModel):
    share_id: str
    user_columns: List[str]


class ColumnMatchResult(BaseModel):
    required_column: str
    suggested_user_column: Optional[str]
    confidence: float  # 0-1


class PlatformModelPredict(BaseModel):
    share_id: str
    data: List[Dict[str, Any]]
    column_mapping: Optional[Dict[str, str]] = None  # {required_col: user_col}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _similarity_score(a: str, b: str) -> float:
    """Simple string similarity for column matching (no external deps)."""
    a = a.lower().replace("_", " ").replace("-", " ")
    b = b.lower().replace("_", " ").replace("-", " ")
    if a == b:
        return 1.0
    # token overlap
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    jaccard = len(intersection) / len(union)
    # prefix match bonus
    prefix = 0.2 if (a.startswith(b[:3]) or b.startswith(a[:3])) else 0.0
    return min(1.0, jaccard + prefix)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/categories")
async def list_categories(current_user: User = Depends(get_current_active_user)):
    """Return category metadata for the gallery view."""
    return {"categories": CATEGORIES}


@router.get("/discover")
async def discover_models(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_platform: Optional[bool] = None,
    current_user: User = Depends(get_current_active_user),
):
    """Discover public models with optional filters."""
    public = _get_all_public()
    if category and category != "komunitas":
        public = [m for m in public if m.get("category") == category]
    if category == "komunitas":
        public = [m for m in public if not m.get("is_platform_model")]
    if is_platform is not None:
        public = [m for m in public if m.get("is_platform_model", False) == is_platform]
    if tag:
        public = [m for m in public if tag in m.get("tags", [])]
    if search:
        q = search.lower()
        public = [
            m for m in public
            if q in m.get("model_name", "").lower()
            or q in m.get("description", "").lower()
            or q in " ".join(m.get("tags", [])).lower()
        ]
    return {"models": public, "total": len(public)}


@router.get("/platform-models")
async def list_platform_models(current_user: User = Depends(get_current_active_user)):
    """Return the curated platform (ready-to-use) models."""
    return {"models": PLATFORM_MODELS}


@router.get("/{share_id}")
async def get_model_detail(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get full detail of a single marketplace model."""
    model = next((m for m in _get_all_public() if m["id"] == share_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")
    return model


@router.post("/column-match")
async def match_columns(
    data: ColumnMatchRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Given a marketplace model's required columns and a user's uploaded column names,
    return best-match suggestions with confidence scores.
    """
    model = next((m for m in _get_all_public() if m["id"] == data.share_id), None)
    if not model:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    required = model.get("feature_names", [])
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
):
    """
    Run inference on a platform or community model using the user's data.
    Uses real trained joblib models when available, falls back to simulation.
    """
    # Look up model in platform list first, then community shares
    model_meta = next((m for m in PLATFORM_MODELS if m["id"] == data.share_id), None)
    if not model_meta:
        model_meta = next((s for s in marketplace_store if s["id"] == data.share_id), None)
    if not model_meta:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    required_cols = model_meta.get("feature_names", [])
    mapping = data.column_mapping or {}
    result_type = model_meta.get("result_type", "classification")

    # Try to load real trained model
    real_model = _load_platform_model(data.share_id)
    meta_info = real_model["meta"] if real_model else None

    predictions = []
    for i, row in enumerate(data.data):
        # Apply column mapping: rename user columns -> required columns
        mapped_row: Dict[str, Any] = {}
        for req_col in required_cols:
            user_col = mapping.get(req_col, req_col)
            if user_col in row:
                mapped_row[req_col] = row[user_col]
            elif req_col in row:
                mapped_row[req_col] = row[req_col]
            else:
                mapped_row[req_col] = 0

        feature_vals = []
        for v in mapped_row.values():
            try:
                feature_vals.append(float(v))
            except (ValueError, TypeError):
                feature_vals.append(0.0)

        if real_model:
            # ── Real ML model prediction ────────────────────────────────
            X = np.array([feature_vals])
            clf = real_model["model"]

            if result_type == "regression":
                pred_value = float(clf.predict(X)[0])
                pred_value = round(max(0, pred_value), 2)
                predictions.append({
                    "index": i,
                    "prediction": pred_value,
                    "prediction_label": f"{pred_value} {model_meta.get('result_unit', '')}".strip(),
                    "result_type": "regression",
                })
            else:
                # Classification with probabilities
                pred_class = int(clf.predict(X)[0])
                proba = clf.predict_proba(X)[0] if hasattr(clf, 'predict_proba') else None

                # Map class index to label
                labels_from_meta = meta_info.get("labels") if meta_info else None
                class_labels = model_meta.get("class_labels", {})

                if labels_from_meta:
                    label_map = {idx: labels_from_meta[idx] if idx < len(labels_from_meta) else str(idx)
                                 for idx in range(len(labels_from_meta))}
                elif class_labels:
                    label_map = {int(k): v for k, v in class_labels.items()}
                else:
                    label_map = {idx: str(idx) for idx in range(len(proba) if proba is not None else 2)}

                pred_label = label_map.get(pred_class, str(pred_class))

                if proba is not None:
                    prob_dict = {}
                    for idx, p in enumerate(proba):
                        lbl = label_map.get(idx, str(idx))
                        prob_dict[lbl] = round(float(p), 3)
                    top_prob = round(float(max(proba)), 3)
                else:
                    prob_dict = {pred_label: 1.0}
                    top_prob = 1.0

                predictions.append({
                    "index": i,
                    "prediction": pred_class,
                    "prediction_label": pred_label,
                    "probability": top_prob,
                    "probabilities": prob_dict,
                    "result_type": "classification",
                })
        else:
            # ── Fallback: simulation (for community models without artifacts) ──
            feature_sum = sum(feature_vals)
            if result_type == "regression":
                base = model_meta.get("metrics", {}).get("mae", 50)
                pred_value = round(max(0, feature_sum * 0.8 + base * 1.5), 2)
                predictions.append({
                    "index": i,
                    "prediction": pred_value,
                    "prediction_label": f"{pred_value} {model_meta.get('result_unit', '')}".strip(),
                    "result_type": "regression",
                })
            else:
                class_labels = model_meta.get("class_labels", {"0": "Kelas 0", "1": "Kelas 1"})
                prob_positive = round(min(0.99, max(0.01, (feature_sum % 10) / 10)), 2)
                predicted_class = "1" if prob_positive >= 0.5 else "0"
                predictions.append({
                    "index": i,
                    "prediction": predicted_class,
                    "prediction_label": class_labels.get(predicted_class, predicted_class),
                    "probability": prob_positive,
                    "probabilities": {
                        class_labels.get("0", "0"): round(1 - prob_positive, 2),
                        class_labels.get("1", "1"): prob_positive,
                    },
                    "result_type": "classification",
                })

    # Bump download count and track usage
    _track_usage(data.share_id, str(current_user.id))

    return {
        "model_name": model_meta["model_name"],
        "result_label": model_meta.get("result_label", "Hasil"),
        "result_unit": model_meta.get("result_unit"),
        "result_type": result_type,
        "predictions": predictions,
        "total": len(predictions),
    }


@router.post("/share", response_model=ShareResponse, status_code=201)
async def share_model(
    data: ShareCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(MLModel).where(MLModel.id == data.model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # ── Feature 5: Quality validation before sharing ──────────────────────
    warnings = []
    metrics = model.metrics or {}
    accuracy = metrics.get("accuracy", metrics.get("f1", 0))
    r2 = metrics.get("r2", 0)
    if accuracy > 0 and accuracy < 0.6:
        warnings.append(f"Akurasi model rendah ({accuracy:.0%}). Pertimbangkan untuk melatih ulang.")
    if r2 > 0 and r2 < 0.5:
        warnings.append(f"Skor R² rendah ({r2:.2f}). Model mungkin belum cukup akurat.")

    # ── Feature 6: Moderation — auto-approve or pending ───────────────────
    status = "approved"
    if not model.name or len(model.name.strip()) < 3:
        status = "pending"
    if not model.description or len(model.description.strip()) < 10:
        status = "pending"
    if accuracy > 0 and accuracy < 0.5:
        status = "pending"
    if r2 > 0 and r2 < 0.4:
        status = "pending"

    share = {
        "id": str(uuid.uuid4()),
        "model_id": str(data.model_id),
        "model_name": model.name,
        "shared_by": str(current_user.id),
        "shared_with_org": data.shared_with_org,
        "permission": data.permission,
        "is_public": 1 if data.is_public else 0,
        "downloads": 0,
        "rating": 0.0,
        "rating_count": 0,
        "tags": data.tags,
        "created_at": "2026-08-07T00:00:00",
        "category": "komunitas",
        "description": model.description or "",
        "use_case": "",
        "feature_names": model.feature_names or [],
        "target_column": model.target_column,
        "algorithm": model.algorithm,
        "metrics": metrics,
        "is_platform_model": False,
        "status": status,
        "usage_log": [],
    }
    marketplace_store.append(share)
    resp = ShareResponse(**share)
    if warnings:
        resp_dict = resp.model_dump()
        resp_dict["warnings"] = warnings
        resp_dict["status"] = status
        return resp_dict
    return resp


@router.post("/{share_id}/download")
async def download_model(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
):
    # Handle platform models
    for m in PLATFORM_MODELS:
        if m["id"] == share_id:
            m["downloads"] = m.get("downloads", 0) + 1
            return {"status": "downloaded", "model_id": share_id}

    share = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    share["downloads"] += 1
    return {"status": "downloaded", "model_id": share["model_id"]}


@router.post("/{share_id}/rate")
async def rate_model(
    share_id: str,
    data: RatingCreate,
    current_user: User = Depends(get_current_active_user),
):
    if not 1 <= data.rating <= 5:
        raise HTTPException(status_code=400, detail="Rating harus antara 1–5")

    # Find in platform models first
    target = next((m for m in PLATFORM_MODELS if m["id"] == share_id), None)
    if not target:
        target = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    # Track individual ratings
    if share_id not in ratings_store:
        ratings_store[share_id] = []
    ratings_store[share_id].append({
        "user_id": str(current_user.id),
        "rating": data.rating,
        "review": data.review,
    })

    # Recalculate average
    all_ratings = [r["rating"] for r in ratings_store[share_id]]
    new_avg = round(sum(all_ratings) / len(all_ratings), 1)
    target["rating"] = new_avg
    target["rating_count"] = len(all_ratings)

    return {"status": "rated", "new_rating": new_avg, "rating_count": len(all_ratings)}


# ── Feature 7: Usage tracking & statistics ───────────────────────────────────

usage_store: Dict[str, List[Dict[str, Any]]] = {}  # model_id -> list of usage events


def _track_usage(model_id: str, user_id: str):
    """Record a usage event for a model."""
    if model_id not in usage_store:
        usage_store[model_id] = []
    usage_store[model_id].append({
        "user_id": user_id,
        "timestamp": "2026-08-07T00:00:00",
    })
    # Also bump download count on the model
    for m in PLATFORM_MODELS:
        if m["id"] == model_id:
            m["downloads"] = m.get("downloads", 0) + 1
            break
    for s in marketplace_store:
        if s["id"] == model_id:
            s["downloads"] = s.get("downloads", 0) + 1
            break


@router.get("/{share_id}/stats")
async def get_model_stats(
    share_id: str,
    current_user: User = Depends(get_current_active_user),
):
    """Get usage statistics for a model owner."""
    model_meta = next((m for m in PLATFORM_MODELS if m["id"] == share_id), None)
    if not model_meta:
        model_meta = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not model_meta:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    events = usage_store.get(share_id, [])
    unique_users = len(set(e["user_id"] for e in events))
    total_uses = len(events)

    return {
        "model_id": share_id,
        "model_name": model_meta.get("model_name", ""),
        "total_uses": total_uses,
        "unique_users": unique_users,
        "downloads": model_meta.get("downloads", 0),
        "rating": model_meta.get("rating", 0),
        "rating_count": model_meta.get("rating_count", 0),
    }


@router.get("/my-models")
async def get_my_models(
    current_user: User = Depends(get_current_active_user),
):
    """Get all models shared by the current user with stats."""
    my_shares = [s for s in marketplace_store if s.get("shared_by") == str(current_user.id)]
    result = []
    for share in my_shares:
        events = usage_store.get(share["id"], [])
        result.append({
            **share,
            "total_uses": len(events),
            "unique_users": len(set(e["user_id"] for e in events)),
        })
    return {"models": result, "total": len(result)}


@router.post("/{share_id}/moderate")
async def moderate_model(
    share_id: str,
    action: str,
    current_user: User = Depends(get_current_active_user),
):
    """Approve or reject a pending model (admin only in future, now any owner)."""
    share = next((s for s in marketplace_store if s["id"] == share_id), None)
    if not share:
        raise HTTPException(status_code=404, detail="Model tidak ditemukan")

    if action == "approve":
        share["status"] = "approved"
    elif action == "reject":
        share["status"] = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Action harus 'approve' atau 'reject'")

    return {"status": share["status"], "model_id": share_id}
