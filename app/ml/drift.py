"""
Drift Detection — comprehensive drift monitoring with immutable baseline.

Supports:
- Numeric drift: PSI (reference-only bins) + KS test
- Categorical drift: PSI on category distributions
- Missingness drift: compare missing rate per feature
- Schema drift: detect new/removed columns
- Prediction drift: compare prediction distributions
- Immutable reference baseline (frozen on first call)
- Delayed-label performance monitoring
"""

import numpy as np
import pandas as pd
import copy
from typing import Dict, Any, Optional, List
from scipy import stats

from app.ml.data_utils import load_dataframe


class ReferenceBaseline:
    """
    Immutable reference baseline for drift detection.
    Once frozen, the baseline cannot be modified.
    """

    def __init__(self):
        self._frozen = False
        self._data: Dict[str, Any] = {}

    def freeze(
        self,
        bin_edges: Dict[str, List[float]],
        numeric_stats: Dict[str, Dict[str, float]],
        categorical_distributions: Dict[str, Dict[str, float]],
        missing_rates: Dict[str, float],
        schema: List[str],
        n_samples: int,
    ) -> None:
        """Freeze the baseline. Cannot be called twice."""
        if self._frozen:
            raise RuntimeError("Baseline already frozen. Create a new ReferenceBaseline to re-freeze.")
        self._data = {
            'bin_edges': copy.deepcopy(bin_edges),
            'numeric_stats': copy.deepcopy(numeric_stats),
            'categorical_distributions': copy.deepcopy(categorical_distributions),
            'missing_rates': copy.deepcopy(missing_rates),
            'schema': list(schema),
            'n_samples': n_samples,
        }
        self._frozen = True

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    def get(self, key: str) -> Any:
        if not self._frozen:
            raise RuntimeError("Baseline not frozen yet.")
        return self._data.get(key)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize frozen baseline for persistence."""
        if not self._frozen:
            return {'frozen': False}
        return {'frozen': True, **self._data}

    @classmethod
    def from_dict(cls, state: Dict[str, Any]) -> 'ReferenceBaseline':
        """Deserialize baseline from saved state."""
        b = cls()
        if state.get('frozen', False):
            b._data = {k: v for k, v in state.items() if k != 'frozen'}
            b._frozen = True
        return b


class DriftDetector:
    def __init__(self):
        self._baseline = ReferenceBaseline()

    @property
    def baseline(self) -> ReferenceBaseline:
        return self._baseline

    def detect(
        self,
        reference_content: bytes,
        current_content: bytes,
        filename: str,
        target_column: Optional[str] = None,
        threshold_psi: float = 0.2,
        threshold_ks: float = 0.05,
        reference_bin_edges: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, Any]:
        ref_df = self._load(reference_content, filename)
        curr_df = self._load(current_content, filename)

        # Schema drift (before filtering to common columns)
        ref_schema = set(ref_df.columns)
        curr_schema = set(curr_df.columns)
        schema_drift = {
            'added_columns': sorted(curr_schema - ref_schema),
            'removed_columns': sorted(ref_schema - curr_schema),
            'drifted': bool(curr_schema - ref_schema or ref_schema - curr_schema),
        }

        common_cols = [c for c in ref_df.columns if c in curr_df.columns]
        ref_df = ref_df[common_cols]
        curr_df = curr_df[common_cols]

        numeric_cols = ref_df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = ref_df.select_dtypes(include=['object', 'category', 'str']).columns.tolist()

        psi_results = {}
        ks_results = {}
        distribution_shift = {}
        saved_bin_edges = {}

        # ── Numeric drift ──
        for col in numeric_cols:
            ref_data = ref_df[col].dropna()
            curr_data = curr_df[col].dropna()

            if len(ref_data) == 0 or len(curr_data) == 0:
                continue

            if reference_bin_edges and col in reference_bin_edges:
                breakpoints = reference_bin_edges[col]
            else:
                breakpoints = self._compute_reference_bins(ref_data)

            saved_bin_edges[col] = breakpoints

            psi_results[col] = self._calculate_psi_with_edges(ref_data, curr_data, breakpoints)
            ks_results[col] = self._calculate_ks(ref_data, curr_data)
            distribution_shift[col] = {
                "ref_mean": float(ref_data.mean()),
                "curr_mean": float(curr_data.mean()),
                "mean_shift": float(curr_data.mean() - ref_data.mean()),
                "ref_std": float(ref_data.std()),
                "curr_std": float(curr_data.std()),
                "std_shift": float(curr_data.std() - ref_data.std()),
            }

        # ── Categorical drift ──
        cat_psi_results = {}
        for col in categorical_cols:
            ref_data = ref_df[col].fillna('__MISSING__').astype(str)
            curr_data = curr_df[col].fillna('__MISSING__').astype(str)

            if len(ref_data) == 0 or len(curr_data) == 0:
                continue

            cat_psi_results[col] = self._calculate_categorical_psi(ref_data, curr_data)

        # ── Missingness drift ──
        missingness = {}
        for col in common_cols:
            ref_missing = float(ref_df[col].isna().mean())
            curr_missing = float(curr_df[col].isna().mean())
            missingness[col] = {
                'ref_missing_rate': round(ref_missing, 6),
                'curr_missing_rate': round(curr_missing, 6),
                'delta': round(curr_missing - ref_missing, 6),
                'drifted': abs(curr_missing - ref_missing) > 0.1,
            }

        drifted_features = []
        for col in numeric_cols:
            if col in psi_results and psi_results[col]["psi"] > threshold_psi:
                drifted_features.append({"feature": col, "metric": "psi", "value": psi_results[col]["psi"]})
            if col in ks_results and ks_results[col]["p_value"] < threshold_ks:
                drifted_features.append({"feature": col, "metric": "ks", "value": ks_results[col]["statistic"]})

        for col in categorical_cols:
            if col in cat_psi_results and cat_psi_results[col]["psi"] > threshold_psi:
                drifted_features.append({"feature": col, "metric": "cat_psi", "value": cat_psi_results[col]["psi"]})

        for col, m in missingness.items():
            if m['drifted']:
                drifted_features.append({"feature": col, "metric": "missingness", "value": m['delta']})

        severity = "low"
        if len(drifted_features) > len(common_cols) * 0.3:
            severity = "high"
        elif len(drifted_features) > len(common_cols) * 0.1:
            severity = "medium"

        return {
            "drift_detected": len(drifted_features) > 0,
            "severity": severity,
            "summary": {
                "total_features": len(common_cols),
                "numeric_features": len(numeric_cols),
                "categorical_features": len(categorical_cols),
                "drifted_features": len(drifted_features),
                "drift_percentage": round(len(drifted_features) / max(len(common_cols), 1) * 100, 2),
            },
            "psi": psi_results,
            "categorical_psi": cat_psi_results,
            "ks_test": ks_results,
            "distribution_shift": distribution_shift,
            "missingness": missingness,
            "schema_drift": schema_drift,
            "drifted_features": drifted_features,
            "thresholds": {
                "psi": threshold_psi,
                "ks": threshold_ks,
            },
            "reference_bin_edges": {k: v.tolist() for k, v in saved_bin_edges.items()},
        }

    def detect_prediction_drift(
        self,
        reference_predictions: List[float],
        current_predictions: List[float],
        threshold_psi: float = 0.2,
    ) -> Dict[str, Any]:
        """
        Detect drift in model predictions between two time periods.
        Useful for monitoring model performance degradation.
        """
        ref = np.array(reference_predictions)
        curr = np.array(current_predictions)

        if len(ref) == 0 or len(curr) == 0:
            return {'drift_detected': False, 'details': 'Empty prediction arrays'}

        # Use reference quantiles for binning
        breakpoints = np.percentile(ref, np.linspace(0, 100, 11))
        breakpoints = np.unique(breakpoints)

        psi = self._calculate_psi_with_edges(
            pd.Series(ref), pd.Series(curr), breakpoints
        )

        ks_stat, ks_p = stats.ks_2samp(ref, curr)

        ref_hist, _ = np.histogram(ref, bins=breakpoints)
        curr_hist, _ = np.histogram(curr, bins=breakpoints)

        return {
            'drift_detected': psi['psi'] > threshold_psi,
            'psi': psi,
            'ks': {
                'statistic': round(float(ks_stat), 6),
                'p_value': round(float(ks_p), 6),
                'drifted': ks_p < 0.05,
            },
            'reference_stats': {
                'mean': round(float(ref.mean()), 6),
                'std': round(float(ref.std()), 6),
                'median': round(float(np.median(ref)), 6),
            },
            'current_stats': {
                'mean': round(float(curr.mean()), 6),
                'std': round(float(curr.std()), 6),
                'median': round(float(np.median(curr)), 6),
            },
            'thresholds': {'psi': threshold_psi},
        }

    def monitor_delayed_labels(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        problem_type: str = 'classification',
    ) -> Dict[str, Any]:
        """
        Monitor model performance using delayed ground-truth labels.
        Returns accuracy/F1 for classification or RMSE/R2 for regression.
        """
        y_true = np.asarray(y_true)
        y_pred = np.asarray(y_pred)

        if len(y_true) == 0 or len(y_pred) == 0:
            return {'status': 'insufficient_data', 'n_samples': 0}

        n = len(y_true)

        if problem_type == 'classification':
            from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
            accuracy = float(accuracy_score(y_true, y_pred))
            f1 = float(f1_score(y_true, y_pred, average='weighted', zero_division=0))
            precision = float(precision_score(y_true, y_pred, average='weighted', zero_division=0))
            recall = float(recall_score(y_true, y_pred, average='weighted', zero_division=0))

            return {
                'status': 'ok',
                'problem_type': 'classification',
                'n_samples': n,
                'accuracy': round(accuracy, 6),
                'f1_weighted': round(f1, 6),
                'precision_weighted': round(precision, 6),
                'recall_weighted': round(recall, 6),
            }
        else:
            from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
            rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
            r2 = float(r2_score(y_true, y_pred))
            mae = float(mean_absolute_error(y_true, y_pred))

            return {
                'status': 'ok',
                'problem_type': 'regression',
                'n_samples': n,
                'rmse': round(rmse, 6),
                'r2': round(r2, 6),
                'mae': round(mae, 6),
            }

    def freeze_baseline(
        self,
        reference_content: bytes,
        filename: str,
        n_bins: int = 10,
    ) -> ReferenceBaseline:
        """
        Freeze a reference baseline from training data.
        This baseline is immutable and used for all future drift comparisons.
        """
        ref_df = self._load(reference_content, filename)
        numeric_cols = ref_df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = ref_df.select_dtypes(include=['object', 'category', 'str']).columns.tolist()

        bin_edges = {}
        numeric_stats = {}
        for col in numeric_cols:
            ref_data = ref_df[col].dropna()
            if len(ref_data) > 0:
                bin_edges[col] = self._compute_reference_bins(ref_data, n_bins).tolist()
                numeric_stats[col] = {
                    'mean': float(ref_data.mean()),
                    'std': float(ref_data.std()),
                    'min': float(ref_data.min()),
                    'max': float(ref_data.max()),
                    'median': float(ref_data.median()),
                }

        categorical_distributions = {}
        for col in categorical_cols:
            counts = ref_df[col].fillna('__MISSING__').value_counts(normalize=True)
            categorical_distributions[col] = counts.to_dict()

        missing_rates = {}
        for col in ref_df.columns:
            missing_rates[col] = float(ref_df[col].isna().mean())

        self._baseline.freeze(
            bin_edges=bin_edges,
            numeric_stats=numeric_stats,
            categorical_distributions=categorical_distributions,
            missing_rates=missing_rates,
            schema=list(ref_df.columns),
            n_samples=len(ref_df),
        )

        return self._baseline

    def _load(self, content: bytes, filename: str) -> pd.DataFrame:
        return load_dataframe(content, filename)

    def compute_baseline_bins(
        self, reference_content: bytes, filename: str, bins: int = 10
    ) -> Dict[str, np.ndarray]:
        """
        Compute bin edges from reference data only.
        Save these edges and reuse for all future batch evaluations.
        """
        ref_df = self._load(reference_content, filename)
        numeric_cols = ref_df.select_dtypes(include=[np.number]).columns.tolist()

        bin_edges = {}
        for col in numeric_cols:
            ref_data = ref_df[col].dropna()
            if len(ref_data) > 0:
                bin_edges[col] = self._compute_reference_bins(ref_data, bins)
        return bin_edges

    def _compute_reference_bins(self, ref_data: pd.Series, bins: int = 10) -> np.ndarray:
        """Compute percentile-based bin edges from reference data only."""
        ref_vals = ref_data.values
        breakpoints = np.percentile(ref_vals, np.linspace(0, 100, bins + 1))
        return np.unique(breakpoints)

    def _calculate_psi_with_edges(
        self, ref: pd.Series, curr: pd.Series, breakpoints: np.ndarray
    ) -> Dict[str, float]:
        """Calculate PSI using pre-defined bin edges."""
        ref_vals = ref.values
        curr_vals = curr.values

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

    def _calculate_psi(self, ref: pd.Series, curr: pd.Series, bins: int = 10) -> Dict[str, float]:
        """Legacy PSI calculation (for backward compatibility). Bins from reference only."""
        breakpoints = self._compute_reference_bins(ref, bins)
        return self._calculate_psi_with_edges(ref, curr, breakpoints)

    def _calculate_ks(self, ref: pd.Series, curr: pd.Series) -> Dict[str, float]:
        statistic, p_value = stats.ks_2samp(ref.values, curr.values)
        return {
            "statistic": round(float(statistic), 6),
            "p_value": round(float(p_value), 6),
            "drifted": p_value < 0.05,
        }

    def _calculate_categorical_psi(self, ref: pd.Series, curr: pd.Series) -> Dict[str, float]:
        """Calculate PSI for categorical features using category-level distributions."""
        ref_counts = ref.value_counts(normalize=True)
        curr_counts = curr.value_counts(normalize=True)

        all_categories = set(ref_counts.index) | set(curr_counts.index)

        eps = 1e-6
        psi = 0.0
        for cat in all_categories:
            ref_pct = ref_counts.get(cat, 0.0) + eps
            curr_pct = curr_counts.get(cat, 0.0) + eps
            psi += (curr_pct - ref_pct) * np.log(curr_pct / ref_pct)

        return {
            "psi": round(float(psi), 6),
            "n_categories_ref": len(ref_counts),
            "n_categories_curr": len(curr_counts),
            "drifted": psi > 0.2,
        }

    def detect_single_batch(
        self,
        training_content: bytes,
        prediction_data: List[Dict[str, Any]],
        filename: str,
        reference_bin_edges: Optional[Dict[str, np.ndarray]] = None,
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
                if reference_bin_edges and col in reference_bin_edges:
                    breakpoints = reference_bin_edges[col]
                else:
                    breakpoints = self._compute_reference_bins(train_numeric[col].dropna())

                psi_results[col] = self._calculate_psi_with_edges(
                    train_numeric[col].dropna(),
                    pred_numeric[col].dropna(),
                    breakpoints,
                )

        drifted = [col for col, r in psi_results.items() if r["drifted"]]

        return {
            "drift_detected": len(drifted) > 0,
            "drifted_features": drifted,
            "psi": psi_results,
            "severity": "high" if len(drifted) > len(train_numeric.columns) * 0.3 else "medium" if drifted else "low",
        }
