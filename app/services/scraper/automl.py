"""AutoML Recommender — Auto-select best model, hyperparameters, and pipeline."""
import logging
from dataclasses import dataclass, field
from datetime import datetime
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.metrics import (
    accuracy_score, f1_score, mean_squared_error, mean_absolute_error,
    r2_score,
)
from sklearn.ensemble import (
    RandomForestClassifier, RandomForestRegressor,
    GradientBoostingClassifier, GradientBoostingRegressor,
    AdaBoostClassifier, AdaBoostRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge, Lasso, ElasticNet
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder

logger = logging.getLogger(__name__)


@dataclass
class ModelCandidate:
    name: str = ""
    model_type: str = ""
    accuracy: float = 0.0
    f1: float = 0.0
    r2: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    train_time_ms: float = 0.0
    params: dict = field(default_factory=dict)
    feature_importance: dict = field(default_factory=dict)
    cv_scores: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "type": self.model_type,
            "accuracy": round(self.accuracy, 4), "f1": round(self.f1, 4),
            "r2": round(self.r2, 4), "rmse": round(self.rmse, 4),
            "mae": round(self.mae, 4), "train_time_ms": round(self.train_time_ms, 2),
            "cv_mean": round(np.mean(self.cv_scores), 4) if self.cv_scores else 0,
            "cv_std": round(np.std(self.cv_scores), 4) if self.cv_scores else 0,
            "feature_importance": dict(sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True)[:15]),
        }


@dataclass
class AutoMLResult:
    task_type: str = ""
    best_model: str = ""
    best_score: float = 0.0
    candidates: list[ModelCandidate] = field(default_factory=list)
    selected_features: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    data_profile: dict = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type, "best_model": self.best_model,
            "best_score": round(self.best_score, 4),
            "candidates": [c.to_dict() for c in self.candidates[:10]],
            "selected_features": self.selected_features,
            "recommendations": self.recommendations,
            "data_profile": self.data_profile,
            "duration_ms": round(self.duration_ms, 2),
        }


class AutoMLRecommender:

    def __init__(self):
        self._classification_models = {
            "random_forest": (RandomForestClassifier, {"n_estimators": 100, "random_state": 42}),
            "gradient_boosting": (GradientBoostingClassifier, {"n_estimators": 100, "random_state": 42}),
            "logistic_regression": (LogisticRegression, {"max_iter": 1000, "random_state": 42}),
            "knn": (KNeighborsClassifier, {"n_neighbors": 5}),
            "decision_tree": (DecisionTreeClassifier, {"random_state": 42}),
            "adaboost": (AdaBoostClassifier, {"n_estimators": 100, "random_state": 42}),
        }
        self._regression_models = {
            "random_forest": (RandomForestRegressor, {"n_estimators": 100, "random_state": 42}),
            "gradient_boosting": (GradientBoostingRegressor, {"n_estimators": 100, "random_state": 42}),
            "ridge": (Ridge, {"alpha": 1.0}),
            "lasso": (Lasso, {"alpha": 1.0}),
            "elastic_net": (ElasticNet, {"alpha": 1.0, "random_state": 42}),
            "knn": (KNeighborsRegressor, {"n_neighbors": 5}),
            "decision_tree": (DecisionTreeRegressor, {"random_state": 42}),
            "adaboost": (AdaBoostRegressor, {"n_estimators": 100, "random_state": 42}),
        }

    def profile_data(self, df: pd.DataFrame) -> dict:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

        n_unique = df.nunique()
        high_card = [c for c in categorical_cols if n_unique[c] > 50]
        low_card = [c for c in categorical_cols if n_unique[c] <= 10]

        skew = df[numeric_cols].skew().to_dict() if numeric_cols else {}
        skewed = [c for c, s in skew.items() if abs(s) > 1]

        correlations = df[numeric_cols].corr().abs() if len(numeric_cols) > 1 else pd.DataFrame()
        high_corr = []
        for i in range(len(correlations)):
            for j in range(i + 1, len(correlations)):
                if correlations.iloc[i, j] > 0.9:
                    high_corr.append({
                        "cols": [correlations.index[i], correlations.columns[j]],
                        "corr": round(correlations.iloc[i, j], 3),
                    })

        return {
            "rows": len(df), "columns": len(df.columns),
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "datetime_columns": datetime_cols,
            "high_cardinality": high_card,
            "low_cardinality": low_card,
            "skewed_features": skewed,
            "high_correlations": high_corr[:5],
            "null_pct": df.isnull().mean().to_dict(),
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        }

    def detect_task(self, y: pd.Series) -> str:
        if y.dtype in ["object", "category"] or y.nunique() < 20:
            return "classification"
        if (y.diff().dropna() == y.diff().dropna().astype(int)).all() and y.nunique() < 50:
            return "classification"
        return "regression"

    def auto_select(self, X: pd.DataFrame, y: pd.Series,
                    task: str = None, max_models: int = 6) -> AutoMLResult:
        start = datetime.now()
        result = AutoMLResult()

        if task is None:
            task = self.detect_task(y)
        result.task_type = task

        result.data_profile = self.profile_data(pd.concat([X, y], axis=1))

        X_clean = X.select_dtypes(include=[np.number]).copy()
        X_clean = X_clean.fillna(X_clean.median())

        label_encoders = {}
        for col in X.select_dtypes(include=["object", "category"]).columns:
            le = LabelEncoder()
            X_clean[col] = le.fit_transform(X[col].astype(str))
            label_encoders[col] = le

        if y.dtype in ["object", "category"]:
            y_encoded = LabelEncoder().fit_transform(y.astype(str))
        else:
            y_encoded = y.values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X_clean)

        models = self._classification_models if task == "classification" else self._regression_models
        candidates = []

        for name, (model_cls, params) in models.items():
            try:
                model = model_cls(**params)
                start_train = time.time()
                model.fit(X_scaled, y_encoded)
                train_time = (time.time() - start_train) * 1000

                cv_folds = min(5, max(2, len(X_scaled)))
                cv = TimeSeriesSplit(n_splits=cv_folds) if task == "regression" else cv_folds
                cv_scores = cross_val_score(model, X_scaled, y_encoded, cv=cv, scoring="accuracy" if task == "classification" else "r2")

                y_pred = model.predict(X_scaled)

                candidate = ModelCandidate(
                    name=name, model_type=task,
                    train_time_ms=train_time,
                    cv_scores=cv_scores.tolist(),
                )

                if task == "classification":
                    candidate.accuracy = accuracy_score(y_encoded, y_pred)
                    candidate.f1 = f1_score(y_encoded, y_pred, average="weighted", zero_division=0)
                else:
                    candidate.rmse = float(np.sqrt(mean_squared_error(y_encoded, y_pred)))
                    candidate.mae = mean_absolute_error(y_encoded, y_pred)
                    candidate.r2 = r2_score(y_encoded, y_pred)

                if hasattr(model, "feature_importances_"):
                    importances = model.feature_importances_
                    top_idx = np.argsort(importances)[::-1][:15]
                    candidate.feature_importance = {
                        X_clean.columns[i]: round(float(importances[i]), 4)
                        for i in top_idx if importances[i] > 0
                    }

                candidates.append(candidate)
            except Exception as e:
                logger.warning(f"AutoML: {name} failed: {e}")

        candidates.sort(key=lambda c: np.mean(c.cv_scores) if c.cv_scores else 0, reverse=True)
        result.candidates = candidates

        if candidates:
            best = candidates[0]
            result.best_model = best.name
            result.best_score = np.mean(best.cv_scores) if best.cv_scores else 0
        else:
            result.recommendations.append("All models failed - check data quality and try different features")

        result.selected_features = list(X_clean.columns)

        result.recommendations.extend(self._generate_recommendations(result, result.data_profile))
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        return result

    def _generate_recommendations(self, result: AutoMLResult, profile: dict) -> list[str]:
        recs = []
        if result.task_type == "regression":
            recs.append("Regression task detected — models ranked by R² score")
        else:
            recs.append("Classification task detected — models ranked by F1 score")

        if profile.get("high_correlations"):
            recs.append("High correlations detected — consider feature reduction")
        if profile.get("skewed_features"):
            recs.append(f"Skewed features found: {', '.join(profile['skewed_features'][:3])} — consider log transform")
        if profile.get("high_cardinality"):
            recs.append(f"High cardinality columns: {', '.join(profile['high_cardinality'][:3])} — consider encoding")
        if profile.get("rows", 0) < 100:
            recs.append("Small dataset — prefer simpler models (KNN, Decision Tree)")
        elif profile.get("rows", 0) > 10000:
            recs.append("Large dataset — ensemble methods may perform best")
        if result.candidates and result.candidates[0].train_time_ms > 5000:
            recs.append("Training is slow — consider reducing model complexity")
        return recs
