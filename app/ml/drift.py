import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from io import BytesIO
from scipy import stats

from app.ml.data_utils import load_dataframe


class DriftDetector:
    def detect(
        self,
        reference_content: bytes,
        current_content: bytes,
        filename: str,
        target_column: Optional[str] = None,
        threshold_psi: float = 0.2,
        threshold_ks: float = 0.05,
    ) -> Dict[str, Any]:
        ref_df = self._load(reference_content, filename)
        curr_df = self._load(current_content, filename)

        common_cols = [c for c in ref_df.columns if c in curr_df.columns]
        ref_df = ref_df[common_cols]
        curr_df = curr_df[common_cols]

        numeric_cols = ref_df.select_dtypes(include=[np.number]).columns.tolist()

        psi_results = {}
        ks_results = {}
        distribution_shift = {}

        for col in numeric_cols:
            ref_data = ref_df[col].dropna()
            curr_data = curr_df[col].dropna()

            if len(ref_data) == 0 or len(curr_data) == 0:
                continue

            psi_results[col] = self._calculate_psi(ref_data, curr_data)
            ks_results[col] = self._calculate_ks(ref_data, curr_data)
            distribution_shift[col] = {
                "ref_mean": float(ref_data.mean()),
                "curr_mean": float(curr_data.mean()),
                "mean_shift": float(curr_data.mean() - ref_data.mean()),
                "ref_std": float(ref_data.std()),
                "curr_std": float(curr_data.std()),
                "std_shift": float(curr_data.std() - ref_data.std()),
            }

        drifted_features = []
        for col in numeric_cols:
            if col in psi_results and psi_results[col]["psi"] > threshold_psi:
                drifted_features.append({"feature": col, "metric": "psi", "value": psi_results[col]["psi"]})
            if col in ks_results and ks_results[col]["p_value"] < threshold_ks:
                drifted_features.append({"feature": col, "metric": "ks", "value": ks_results[col]["statistic"]})

        severity = "low"
        if len(drifted_features) > len(numeric_cols) * 0.3:
            severity = "high"
        elif len(drifted_features) > len(numeric_cols) * 0.1:
            severity = "medium"

        return {
            "drift_detected": len(drifted_features) > 0,
            "severity": severity,
            "summary": {
                "total_features": len(numeric_cols),
                "drifted_features": len(drifted_features),
                "drift_percentage": round(len(drifted_features) / max(len(numeric_cols), 1) * 100, 2),
            },
            "psi": psi_results,
            "ks_test": ks_results,
            "distribution_shift": distribution_shift,
            "drifted_features": drifted_features,
            "thresholds": {
                "psi": threshold_psi,
                "ks": threshold_ks,
            },
        }

    def _load(self, content: bytes, filename: str) -> pd.DataFrame:
        return load_dataframe(content, filename)

    def _calculate_psi(self, ref: pd.Series, curr: pd.Series, bins: int = 10) -> Dict[str, float]:
        ref_vals = ref.values
        curr_vals = curr.values

        combined = np.concatenate([ref_vals, curr_vals])
        breakpoints = np.percentile(combined, np.linspace(0, 100, bins + 1))
        breakpoints = np.unique(breakpoints)

        ref_hist, _ = np.histogram(ref_vals, bins=breakpoints)
        curr_hist, _ = np.histogram(curr_vals, bins=breakpoints)

        ref_pct = (ref_hist + 1) / (len(ref_vals) + len(breakpoints))
        curr_pct = (curr_hist + 1) / (len(curr_vals) + len(breakpoints))

        psi = float(np.sum((curr_pct - ref_pct) * np.log(curr_pct / ref_pct)))

        return {
            "psi": round(psi, 6),
            "bins": len(breakpoints) - 1,
            "drifted": psi > 0.2,
        }

    def _calculate_ks(self, ref: pd.Series, curr: pd.Series) -> Dict[str, float]:
        statistic, p_value = stats.ks_2samp(ref.values, curr.values)
        return {
            "statistic": round(float(statistic), 6),
            "p_value": round(float(p_value), 6),
            "drifted": p_value < 0.05,
        }

    def detect_single_batch(
        self,
        training_content: bytes,
        prediction_data: List[Dict[str, Any]],
        filename: str,
    ) -> Dict[str, Any]:
        train_df = self._load(training_content, filename)
        pred_df = pd.DataFrame(prediction_data)

        common_cols = [c for c in train_df.columns if c in pred_df.columns]
        train_numeric = train_df[common_cols].select_dtypes(include=[np.number])
        pred_numeric = pred_df[common_cols].select_dtypes(include=[np.number])

        if train_numeric.empty or pred_numeric.empty:
            return {"drift_detected": False, "details": "No numeric columns to compare"}

        psi_results = {}
        for col in train_numeric.columns:
            if col in pred_numeric.columns:
                psi_results[col] = self._calculate_psi(
                    train_numeric[col].dropna(),
                    pred_numeric[col].dropna(),
                )

        drifted = [col for col, r in psi_results.items() if r["drifted"]]

        return {
            "drift_detected": len(drifted) > 0,
            "drifted_features": drifted,
            "psi": psi_results,
            "severity": "high" if len(drifted) > len(train_numeric.columns) * 0.3 else "medium" if drifted else "low",
        }
