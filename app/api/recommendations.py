from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional
import os

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.dataset import Dataset
from app.ml.processor import DataProcessor
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/recommendations", tags=["Recommendations"])
processor = DataProcessor()


class ColumnAnalysis(BaseModel):
    name: str
    dtype: str
    null_count: int
    null_pct: float
    unique_count: Optional[int] = None
    suggested_role: str  # 'target', 'feature', 'id', 'datetime'


class RecommendationResponse(BaseModel):
    suggested_problem_type: str  # 'classification' or 'regression'
    reason: str
    suggested_algorithms: List[dict]
    dataset_size: str  # 'small', 'medium', 'large'
    rows: int
    columns: int
    missing_pct: float
    warnings: List[str]
    column_analyses: List[ColumnAnalysis]


def analyze_column(df, col_name) -> dict:
    """Analyze a single column and return characteristics."""
    series = df[col_name]
    dtype = str(series.dtype)
    null_count = int(series.isna().sum())
    null_pct = round(null_count / len(series) * 100, 1) if len(series) > 0 else 0
    unique_count = int(series.nunique())

    return {
        "name": col_name,
        "dtype": dtype,
        "null_count": null_count,
        "null_pct": null_pct,
        "unique_count": unique_count,
    }


def classify_column_role(series, col_name, target_col):
    """Determine the role of a column."""
    if col_name == target_col:
        return "target"

    dtype = str(series.dtype)
    unique_ratio = series.nunique() / max(len(series), 1)

    if unique_ratio > 0.9 and dtype in ("int64", "float64"):
        return "id"
    if "datetime" in dtype or "time" in dtype:
        return "datetime"
    return "feature"


def suggest_problem_type(series):
    """Suggest classification or regression based on target column characteristics."""
    dtype = str(series.dtype)
    nunique = series.nunique()
    total = len(series.dropna())

    if total == 0:
        return "classification", "Kolom target kosong, default ke klasifikasi"

    if dtype == "object" or dtype == "bool":
        return "classification", f"Kolom bertipe '{dtype}' → klasifikasi"

    if nunique <= 10 and nunique / total < 0.05:
        return "classification", f"Kolom numerik dengan {nunique} nilai unik (< 5% dari total) → klasifikasi"

    if nunique <= 20:
        ratio = nunique / total
        if ratio < 0.1:
            return "classification", f"Kolom numerik dengan {nunique} nilai unik dan rasio rendah ({ratio:.1%}) → kemungkinan klasifikasi"

    return "regression", f"Kolom numerik dengan {nunique} nilai unik kontinu → regresi"


def suggest_algorithms(problem_type, rows, columns, missing_pct):
    """Suggest algorithms based on dataset characteristics."""
    suggestions = []

    if problem_type == "classification":
        algorithms = [
            {"key": "random_forest", "reason": "Pilihan aman, stabil untuk semua ukuran data"},
            {"key": "logistic_regression", "reason": "Baseline cepat, mudah diinterpretasi"},
            {"key": "xgboost", "reason": "Akurasi tinggi, industry standard"},
            {"key": "lightgbm", "reason": "Sangat cepat, hemat memori"},
            {"key": "catboost", "reason": "Otomatis menangani fitur kategori"},
            {"key": "gradient_boosting", "reason": "Akurat, cocok untuk data tabular"},
        ]
    else:
        algorithms = [
            {"key": "random_forest", "reason": "Baseline regresi yang stabil"},
            {"key": "xgboost", "reason": "Performa regresi maksimal"},
            {"key": "lightgbm", "reason": "Cepat untuk dataset besar"},
            {"key": "gradient_boosting", "reason": "Akurasi tinggi untuk prediksi angka"},
            {"key": "ridge", "reason": "Regresi linier dengan regularisasi, hindari overfitting"},
            {"key": "catboost", "reason": "Menangani kategori otomatis"},
        ]

    if rows < 500:
        suggestions.append({"key": "knn", "reason": "Dataset kecil, KNN efektif"})
        suggestions.append({"key": "svm", "reason": "SVM bagus untuk dataset kecil"})
    elif rows > 10000:
        suggestions.append({"key": "lightgbm", "reason": "Dataset besar, LightGBM paling cepat"})
        suggestions.append({"key": "xgboost", "reason": "XGBoost optimal untuk data > 10k baris"})

    if missing_pct > 20:
        suggestions.append({"key": "catboost", "reason": "CatBoost menangani missing values dengan baik"})

    seen = set()
    result = []
    for algo in algorithms + suggestions:
        if algo["key"] not in seen:
            seen.add(algo["key"])
            result.append(algo)

    return result[:6]


@router.get("/{dataset_id}/analyze", response_model=RecommendationResponse)
async def analyze_dataset_for_recommendation(
    dataset_id: UUID,
    target_column: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Dataset).where(Dataset.id == dataset_id))
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    if not os.path.exists(dataset.file_path):
        raise HTTPException(status_code=404, detail="Dataset file not found")

    with open(dataset.file_path, "rb") as f:
        content = f.read()

    filename = os.path.basename(dataset.file_path)
    df = processor.load_data(content, filename)

    if target_column not in df.columns:
        raise HTTPException(status_code=400, detail=f"Target column '{target_column}' not found")

    rows, columns = df.shape
    total_missing = df.isna().sum().sum()
    total_cells = rows * columns
    missing_pct = round(total_missing / total_cells * 100, 1) if total_cells > 0 else 0

    target_series = df[target_column]
    problem_type, reason = suggest_problem_type(target_series)
    algos = suggest_algorithms(problem_type, rows, columns, missing_pct)

    if rows < 50:
        warnings = ["Dataset sangat kecil (< 50 baris). Model mungkin tidak akurat."]
    elif rows < 200:
        warnings = ["Dataset relatif kecil. Pertimbangkan untuk menambah data."]
    else:
        warnings = []

    if missing_pct > 30:
        warnings.append(f"Tingkat missing values tinggi ({missing_pct}%). Pertimbangkan untuk membersihkan data.")

    if rows > 100000:
        if not any(a["key"] in ("lightgbm", "xgboost") for a in algos[:2]):
            warnings.append("Dataset besar. Pertimbangkan algoritma yang lebih cepat seperti LightGBM.")

    column_analyses = []
    for col in df.columns:
        analysis = analyze_column(df, col)
        analysis["suggested_role"] = classify_column_role(df[col], col, target_column)
        column_analyses.append(ColumnAnalysis(**analysis))

    return RecommendationResponse(
        suggested_problem_type=problem_type,
        reason=reason,
        suggested_algorithms=algos,
        dataset_size="small" if rows < 1000 else "medium" if rows < 10000 else "large",
        rows=rows,
        columns=columns,
        missing_pct=missing_pct,
        warnings=warnings,
        column_analyses=column_analyses,
    )
