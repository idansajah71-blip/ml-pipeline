"""Feature Engineering — Auto-create features from scraped data."""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FeatureResult:
    original_features: int = 0
    created_features: int = 0
    total_features: int = 0
    feature_names: list[str] = field(default_factory=list)
    feature_descriptions: dict = field(default_factory=dict)
    feature_importance: dict = field(default_factory=dict)
    duration_ms: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "original_features": self.original_features,
            "created_features": self.created_features,
            "total_features": self.total_features,
            "feature_names": self.feature_names[:100],
            "feature_descriptions": self.feature_descriptions,
            "feature_importance": dict(list(self.feature_importance.items())[:20]),
            "duration_ms": round(self.duration_ms, 2),
            "summary": self.summary,
        }


class FeatureEngineer:

    def create_interaction_features(self, df: pd.DataFrame,
                                    columns: list[str] = None) -> pd.DataFrame:
        numeric = df.select_dtypes(include=[np.number])
        cols = columns or numeric.columns.tolist()
        new_df = df.copy()

        for i, c1 in enumerate(cols):
            for c2 in cols[i + 1:]:
                if c1 in new_df.columns and c2 in new_df.columns:
                    new_df[f"{c1}_x_{c2}"] = new_df[c1] * new_df[c2]
                    new_df[f"{c1}_div_{c2}"] = new_df[c1] / new_df[c2].replace(0, np.nan)
        return new_df

    def create_polynomial_features(self, df: pd.DataFrame,
                                   columns: list[str] = None,
                                   degree: int = 2) -> pd.DataFrame:
        numeric = df.select_dtypes(include=[np.number])
        cols = columns or numeric.columns.tolist()
        new_df = df.copy()

        for col in cols:
            if col in new_df.columns:
                for d in range(2, degree + 1):
                    new_df[f"{col}_pow{d}"] = new_df[col] ** d
        return new_df

    def create_statistical_features(self, df: pd.DataFrame,
                                    numeric_cols: list[str] = None) -> pd.DataFrame:
        numeric = df.select_dtypes(include=[np.number])
        cols = numeric_cols or numeric.columns.tolist()
        new_df = df.copy()

        row_data = new_df[cols].values
        new_df["row_mean"] = np.nanmean(row_data, axis=1)
        new_df["row_std"] = np.nanstd(row_data, axis=1)
        new_df["row_max"] = np.nanmax(row_data, axis=1)
        new_df["row_min"] = np.nanmin(row_data, axis=1)
        new_df["row_range"] = new_df["row_max"] - new_df["row_min"]
        new_df["row_median"] = np.nanmedian(row_data, axis=1)
        new_df["row_skew"] = pd.DataFrame(row_data).skew(axis=1).values
        return new_df

    def create_aggregation_features(self, df: pd.DataFrame,
                                    group_col: str,
                                    value_cols: list[str] = None) -> pd.DataFrame:
        numeric = df.select_dtypes(include=[np.number])
        cols = value_cols or numeric.columns.tolist()
        new_df = df.copy()

        for col in cols:
            if col in new_df.columns and group_col in new_df.columns:
                grouped = new_df.groupby(group_col)[col]
                new_df[f"{col}_group_mean"] = grouped.transform("mean")
                new_df[f"{col}_group_std"] = grouped.transform("std").fillna(0)
                new_df[f"{col}_group_rank"] = grouped.rank(pct=True)
                new_df[f"{col}_deviation"] = new_df[col] - new_df[f"{col}_group_mean"]
        return new_df

    def create_text_features(self, df: pd.DataFrame, text_col: str) -> pd.DataFrame:
        new_df = df.copy()
        if text_col not in new_df.columns:
            return new_df

        new_df[f"{text_col}_length"] = new_df[text_col].astype(str).str.len()
        new_df[f"{text_col}_word_count"] = new_df[text_col].astype(str).str.split().str.len()
        new_df[f"{text_col}_avg_word_length"] = (
            new_df[text_col].astype(str).apply(
                lambda x: np.mean([len(w) for w in x.split()]) if x.split() else 0
            )
        )
        new_df[f"{text_col}_digit_count"] = new_df[text_col].astype(str).str.count(r"\d")
        new_df[f"{text_col}_special_count"] = new_df[text_col].astype(str).str.count(r"[^a-zA-Z0-9\s]")
        new_df[f"{text_col}_uppercase_count"] = new_df[text_col].astype(str).str.count(r"[A-Z]")
        return new_df

    def create_datetime_features(self, df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        new_df = df.copy()
        if date_col not in new_df.columns:
            return new_df

        dt = pd.to_datetime(new_df[date_col], errors="coerce")
        new_df[f"{date_col}_year"] = dt.dt.year
        new_df[f"{date_col}_month"] = dt.dt.month
        new_df[f"{date_col}_day"] = dt.dt.day
        new_df[f"{date_col}_dayofweek"] = dt.dt.dayofweek
        new_df[f"{date_col}_hour"] = dt.dt.hour
        new_df[f"{date_col}_is_weekend"] = dt.dt.dayofweek.isin([5, 6]).astype(int)
        new_df[f"{date_col}_quarter"] = dt.dt.quarter
        new_df[f"{date_col}_is_month_start"] = dt.dt.is_month_start.astype(int)
        new_df[f"{date_col}_is_month_end"] = dt.dt.is_month_end.astype(int)
        return new_df

    def create_lag_features(self, df: pd.DataFrame, value_col: str,
                            lags: list[int] = None) -> pd.DataFrame:
        if lags is None:
            lags = [1, 2, 3, 7, 14, 30]
        new_df = df.copy()
        if value_col not in new_df.columns:
            return new_df

        for lag in lags:
            new_df[f"{value_col}_lag_{lag}"] = new_df[value_col].shift(lag)
        for window in [3, 7, 14, 30]:
            new_df[f"{value_col}_rolling_mean_{window}"] = new_df[value_col].rolling(window, min_periods=1).mean()
            new_df[f"{value_col}_rolling_std_{window}"] = new_df[value_col].rolling(window, min_periods=1).std().fillna(0)
        return new_df

    def create_all_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, FeatureResult]:
        start = datetime.now()
        result = FeatureResult(original_features=len(df.columns))
        new_df = df.copy()

        numeric_cols = new_df.select_dtypes(include=[np.number]).columns.tolist()
        text_cols = new_df.select_dtypes(include=["object"]).columns.tolist()
        date_cols = [c for c in new_df.columns if "date" in c.lower() or "time" in c.lower()]

        if len(numeric_cols) >= 2:
            new_df = self.create_statistical_features(new_df, numeric_cols[:5])
            if len(numeric_cols) <= 8:
                new_df = self.create_interaction_features(new_df, numeric_cols[:4])
                new_df = self.create_polynomial_features(new_df, numeric_cols[:3], degree=2)

        for col in text_cols[:3]:
            new_df = self.create_text_features(new_df, col)

        for col in date_cols[:2]:
            try:
                new_df = self.create_datetime_features(new_df, col)
            except Exception:
                pass

        for col in numeric_cols[:2]:
            new_df = self.create_lag_features(new_df, col, lags=[1, 2, 3])

        new_df = new_df.replace([np.inf, -np.inf], np.nan)
        result.total_features = len(new_df.columns)
        result.created_features = result.total_features - result.original_features
        result.feature_names = list(new_df.columns)
        result.duration_ms = (datetime.now() - start).total_seconds() * 1000
        result.summary = f"Created {result.created_features} features ({result.original_features}→{result.total_features})"
        return new_df, result
