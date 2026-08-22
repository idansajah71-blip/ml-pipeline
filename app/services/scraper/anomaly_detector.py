"""Anomaly Detection — Detect outliers in scraped data using multiple methods."""
import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class AnomalyResult:
    method: str = ""
    total_rows: int = 0
    anomalies_found: int = 0
    anomaly_percentage: float = 0.0
    anomaly_indices: list[int] = field(default_factory=list)
    scores: list[float] = field(default_factory=list)
    threshold: float = 0.0
    columns_analyzed: list[str] = field(default_factory=list)
    anomaly_details: list[dict] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method, "total_rows": self.total_rows,
            "anomalies_found": self.anomalies_found,
            "anomaly_percentage": round(self.anomaly_percentage, 2),
            "anomaly_indices": self.anomaly_indices[:100],
            "threshold": round(self.threshold, 4),
            "columns_analyzed": self.columns_analyzed,
            "anomaly_details": self.anomaly_details[:50],
            "summary": self.summary,
        }


class AnomalyDetector:

    def detect_zscore(self, df: pd.DataFrame, columns: list[str] = None,
                      threshold: float = 3.0) -> AnomalyResult:
        numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
        result = AnomalyResult(method="zscore", columns_analyzed=numeric_cols)

        if not numeric_cols:
            result.summary = "No numeric columns found"
            return result

        z_scores = np.abs(stats.zscore(df[numeric_cols].fillna(0)))
        anomaly_mask = (z_scores > threshold).any(axis=1)
        anomaly_indices = np.where(anomaly_mask)[0].tolist()

        result.total_rows = len(df)
        result.anomalies_found = len(anomaly_indices)
        result.anomaly_percentage = len(anomaly_indices) / max(len(df), 1) * 100
        result.anomaly_indices = anomaly_indices
        result.threshold = threshold

        for idx in anomaly_indices[:50]:
            row = df.iloc[idx]
            details = {"row": int(idx)}
            for col in numeric_cols:
                col_z = np.abs(stats.zscore(df[col].fillna(0)))
                if col_z[idx] > threshold:
                    details[col] = {
                        "value": float(row[col]) if pd.notna(row[col]) else None,
                        "z_score": round(float(col_z[idx]), 2),
                    }
            result.anomaly_details.append(details)

        result.summary = f"Z-score: {result.anomalies_found} anomalies ({result.anomaly_percentage:.1f}%)"
        return result

    def detect_iqr(self, df: pd.DataFrame, columns: list[str] = None,
                   multiplier: float = 1.5) -> AnomalyResult:
        numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
        result = AnomalyResult(method="iqr", columns_analyzed=numeric_cols)

        if not numeric_cols:
            result.summary = "No numeric columns found"
            return result

        all_anomalies = set()
        details_map = {}

        for col in numeric_cols:
            series = df[col].dropna()
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            lower = q1 - multiplier * iqr
            upper = q3 + multiplier * iqr

            mask = (df[col] < lower) | (df[col] > upper)
            indices = np.where(mask)[0]
            all_anomalies.update(indices)

            for idx in indices:
                if idx not in details_map:
                    details_map[idx] = {"row": int(idx)}
                details_map[idx][col] = {
                    "value": float(df[col].iloc[idx]) if pd.notna(df[col].iloc[idx]) else None,
                    "lower_bound": round(lower, 4),
                    "upper_bound": round(upper, 4),
                }

        result.total_rows = len(df)
        result.anomalies_found = len(all_anomalies)
        result.anomaly_percentage = len(all_anomalies) / max(len(df), 1) * 100
        result.anomaly_indices = sorted(all_anomalies)
        result.threshold = multiplier
        result.anomaly_details = [details_map[i] for i in sorted(details_map.keys())[:50]]
        result.summary = f"IQR: {result.anomalies_found} anomalies ({result.anomaly_percentage:.1f}%)"
        return result

    def detect_isolation_forest(self, df: pd.DataFrame, columns: list[str] = None,
                                contamination: float = 0.05) -> AnomalyResult:
        numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
        result = AnomalyResult(method="isolation_forest", columns_analyzed=numeric_cols)

        if not numeric_cols or len(df) < 10:
            result.summary = "Insufficient data for Isolation Forest"
            return result

        X = df[numeric_cols].fillna(0).values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        iso = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
        predictions = iso.fit_predict(X_scaled)
        scores = iso.decision_function(X_scaled)

        anomaly_mask = predictions == -1
        anomaly_indices = np.where(anomaly_mask)[0].tolist()

        result.total_rows = len(df)
        result.anomalies_found = len(anomaly_indices)
        result.anomaly_percentage = len(anomaly_indices) / max(len(df), 1) * 100
        result.anomaly_indices = anomaly_indices
        result.threshold = contamination
        result.scores = scores.tolist()

        for idx in anomaly_indices[:50]:
            result.anomaly_details.append({
                "row": int(idx),
                "score": round(float(scores[idx]), 4),
            })

        result.summary = f"Isolation Forest: {result.anomalies_found} anomalies ({result.anomaly_percentage:.1f}%)"
        return result

    def detect_lof(self, df: pd.DataFrame, columns: list[str] = None,
                   n_neighbors: int = 20, contamination: float = 0.05) -> AnomalyResult:
        numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()
        result = AnomalyResult(method="lof", columns_analyzed=numeric_cols)

        if not numeric_cols or len(df) < n_neighbors + 1:
            result.summary = "Insufficient data for LOF"
            return result

        X = df[numeric_cols].fillna(0).values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        lof = LocalOutlierFactor(n_neighbors=n_neighbors, contamination=contamination)
        predictions = lof.fit_predict(X_scaled)

        anomaly_mask = predictions == -1
        anomaly_indices = np.where(anomaly_mask)[0].tolist()

        result.total_rows = len(df)
        result.anomalies_found = len(anomaly_indices)
        result.anomaly_percentage = len(anomaly_indices) / max(len(df), 1) * 100
        result.anomaly_indices = anomaly_indices
        result.threshold = contamination

        result.summary = f"LOF: {result.anomalies_found} anomalies ({result.anomaly_percentage:.1f}%)"
        return result

    def detect_all(self, df: pd.DataFrame, columns: list[str] = None) -> dict:
        results = {}
        results["zscore"] = self.detect_zscore(df, columns).to_dict()
        results["iqr"] = self.detect_iqr(df, columns).to_dict()
        results["isolation_forest"] = self.detect_isolation_forest(df, columns).to_dict()
        if len(df) > 25:
            results["lof"] = self.detect_lof(df, columns).to_dict()

        all_indices = set()
        for r in results.values():
            all_indices.update(r.get("anomaly_indices", []))

        results["consensus"] = {
            "total_unique_anomalies": len(all_indices),
            "anomaly_indices": sorted(all_indices),
            "methods_used": list(results.keys()),
        }
        return results
