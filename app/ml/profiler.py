import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from io import BytesIO


class DatasetProfiler:
    def profile(
        self, file_content: bytes, filename: str, target_column: Optional[str] = None
    ) -> Dict[str, Any]:
        df = self._load_data(file_content, filename)

        profile = {
            "summary": self._get_summary(df),
            "column_profiles": self._get_column_profiles(df),
            "missing_values": self._get_missing_values(df),
            "outliers": self._get_outlier_info(df),
            "correlations": self._get_correlations(df),
        }

        if target_column and target_column in df.columns:
            profile["class_distribution"] = self._get_class_distribution(
                df, target_column
            )

        return profile

    def _load_data(self, file_content: bytes, filename: str) -> pd.DataFrame:
        if filename.endswith(".csv"):
            return pd.read_csv(BytesIO(file_content))
        elif filename.endswith((".xls", ".xlsx")):
            return pd.read_excel(BytesIO(file_content))
        else:
            raise ValueError(f"Unsupported file format: {filename}")

    def _get_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

        return {
            "rows": len(df),
            "columns": len(df.columns),
            "numeric_columns": len(numeric_cols),
            "categorical_columns": len(categorical_cols),
            "memory_usage_bytes": int(df.memory_usage(deep=True).sum()),
            "duplicated_rows": int(df.duplicated().sum()),
            "total_missing": int(df.isnull().sum().sum()),
            "missing_percentage": round(
                df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100, 2
            ),
            "column_names": list(df.columns),
        }

    def _get_column_profiles(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        profiles = {}

        for col in df.columns:
            col_data = df[col]
            profile: Dict[str, Any] = {
                "dtype": str(col_data.dtype),
                "non_null_count": int(col_data.count()),
                "null_count": int(col_data.isnull().sum()),
                "null_percentage": round(
                    col_data.isnull().sum() / len(col_data) * 100, 2
                ),
                "unique_count": int(col_data.nunique()),
            }

            if pd.api.types.is_numeric_dtype(col_data):
                stats = col_data.describe()
                profile["statistics"] = {
                    "mean": float(stats.get("mean", 0)),
                    "std": float(stats.get("std", 0)),
                    "min": float(stats.get("min", 0)),
                    "25%": float(stats.get("25%", 0)),
                    "50%": float(stats.get("50%", 0)),
                    "75%": float(stats.get("75%", 0)),
                    "max": float(stats.get("max", 0)),
                    "skewness": float(col_data.skew()) if len(col_data.dropna()) > 1 else 0,
                    "kurtosis": float(col_data.kurtosis()) if len(col_data.dropna()) > 1 else 0,
                }
            else:
                value_counts = col_data.value_counts()
                profile["statistics"] = {
                    "top_values": value_counts.head(10).to_dict(),
                    "unique_values": int(col_data.nunique()),
                    "mode": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                }

            profiles[col] = profile

        return profiles

    def _get_missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        missing = df.isnull().sum()
        missing_pct = (missing / len(df) * 100).round(2)

        columns_with_missing = [
            col for col in df.columns if missing[col] > 0
        ]

        return {
            "total_missing": int(missing.sum()),
            "total_cells": df.shape[0] * df.shape[1],
            "missing_percentage": round(
                missing.sum() / (df.shape[0] * df.shape[1]) * 100, 2
            ),
            "columns_with_missing": columns_with_missing,
            "missing_by_column": {
                col: {
                    "count": int(missing[col]),
                    "percentage": float(missing_pct[col]),
                }
                for col in columns_with_missing
            },
            "complete_rows": int((~df.isnull().any(axis=1)).sum()),
            "complete_rows_percentage": round(
                (~df.isnull().any(axis=1)).sum() / len(df) * 100, 2
            ),
        }

    def _get_outlier_info(self, df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        outliers = {}

        for col in numeric_cols:
            col_data = df[col].dropna()
            if len(col_data) == 0:
                continue

            q1 = float(col_data.quantile(0.25))
            q3 = float(col_data.quantile(0.75))
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_count = int(((col_data < lower_bound) | (col_data > upper_bound)).sum())

            outliers[col] = {
                "q1": q1,
                "q3": q3,
                "iqr": round(iqr, 4),
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "outlier_count": outlier_count,
                "outlier_percentage": round(outlier_count / len(col_data) * 100, 2),
            }

        return outliers

    def _get_correlations(self, df: pd.DataFrame) -> Dict[str, Any]:
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return {"matrix": {}, "strong_correlations": []}

        corr_matrix = numeric_df.corr().round(4).to_dict()

        strong_corrs = []
        cols = numeric_df.columns.tolist()
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                corr_val = numeric_df[cols[i]].corr(numeric_df[cols[j]])
                if abs(corr_val) > 0.7:
                    strong_corrs.append({
                        "feature_1": cols[i],
                        "feature_2": cols[j],
                        "correlation": round(float(corr_val), 4),
                        "strength": "strong_positive" if corr_val > 0 else "strong_negative",
                    })

        return {
            "matrix": corr_matrix,
            "strong_correlations": strong_corrs,
        }

    def _get_class_distribution(
        self, df: pd.DataFrame, target_column: str
    ) -> Dict[str, Any]:
        target_data = df[target_column]
        value_counts = target_data.value_counts()
        total = len(target_data)

        distribution = {}
        for cls, count in value_counts.items():
            distribution[str(cls)] = {
                "count": int(count),
                "percentage": round(count / total * 100, 2),
            }

        counts = value_counts.values
        imbalance_ratio = float(counts.max() / counts.min()) if counts.min() > 0 else float("inf")

        return {
            "column": target_column,
            "num_classes": len(value_counts),
            "distribution": distribution,
            "imbalance_ratio": round(imbalance_ratio, 2),
            "is_imbalanced": imbalance_ratio > 3,
            "majority_class": str(value_counts.index[0]),
            "minority_class": str(value_counts.index[-1]),
        }
