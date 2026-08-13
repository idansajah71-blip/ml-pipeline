"""
Calibration Module — proper probability calibration for classification models.

Implements:
- Platt scaling (sigmoid calibration)
- Isotonic regression calibration
- Separate calibration set (not training, not test)
- Pre/post calibration metrics (Brier, ECE, reliability curve)
- Calibration is applied to validation set probabilities, then used at inference
"""

import numpy as np
import logging
from typing import Dict, Any, Optional, Tuple
from sklearn.model_selection import train_test_split
from sklearn.metrics import brier_score_loss, log_loss

logger = logging.getLogger(__name__)


class ModelCalibrator:
    """
    Calibrates predicted probabilities using a held-out calibration set.

    Usage:
        calibrator = ModelCalibrator()
        calibrator.fit(y_val, y_proba_val)  # fit on validation set
        calibrated_proba = calibrator.transform(y_proba_new)  # apply to new predictions
    """

    def __init__(self, method: str = 'isotonic'):
        """
        Args:
            method: 'platt' for sigmoid scaling, 'isotonic' for isotonic regression
        """
        self.method = method
        self._calibrator = None
        self._isotonic_map: Optional[Dict[str, Any]] = None
        self._is_fitted = False
        self._pre_metrics: Dict[str, float] = {}
        self._post_metrics: Dict[str, float] = {}
        self._reliability_data: Dict[str, Any] = {}

    def fit(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10,
    ) -> Dict[str, Any]:
        """
        Fit calibrator on a held-out calibration set.

        Args:
            y_true: Ground truth labels (binary: 0 or 1)
            y_proba: Uncalibrated predicted probabilities for positive class
            n_bins: Number of bins for ECE computation

        Returns:
            Dict with pre/post calibration metrics
        """
        y_true = np.asarray(y_true)
        y_proba = np.asarray(y_proba).clip(1e-7, 1 - 1e-7)

        # Compute pre-calibration metrics
        self._pre_metrics = self._compute_metrics(y_true, y_proba, n_bins)

        if self.method == 'platt':
            self._fit_platt(y_true, y_proba)
        elif self.method == 'isotonic':
            self._fit_isotonic(y_true, y_proba)
        else:
            raise ValueError(f"Unknown calibration method: {self.method}")

        self._is_fitted = True

        # Compute post-calibration metrics
        calibrated = self.transform(y_proba)
        self._post_metrics = self._compute_metrics(y_true, calibrated, n_bins)
        self._reliability_data = self._compute_reliability(y_true, calibrated, n_bins)

        return {
            'method': self.method,
            'pre_calibration': self._pre_metrics,
            'post_calibration': self._post_metrics,
            'reliability': self._reliability_data,
            'improvement': {
                'brier': self._pre_metrics['brier_score'] - self._post_metrics['brier_score'],
                'ece': self._pre_metrics['ece'] - self._post_metrics['ece'],
            },
        }

    def transform(self, y_proba: np.ndarray) -> np.ndarray:
        """Apply calibration to uncalibrated probabilities."""
        if not self._is_fitted:
            raise RuntimeError("Calibrator not fitted. Call fit() first.")

        y_proba = np.asarray(y_proba).clip(1e-7, 1 - 1e-7)

        if self.method == 'platt':
            a, b = self._calibrator
            logits = np.log(y_proba / (1 - y_proba))
            calibrated = 1.0 / (1.0 + np.exp(-(a * logits + b)))
            return calibrated.clip(1e-7, 1 - 1e-7)
        elif self.method == 'isotonic':
            x = np.array(self._isotonic_map['x'])
            y = np.array(self._isotonic_map['y'])
            return np.interp(y_proba, x, y).clip(1e-7, 1 - 1e-7)

    def fit_transform(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10,
    ) -> np.ndarray:
        """Fit calibrator and return calibrated probabilities."""
        self.fit(y_true, y_proba, n_bins)
        return self.transform(y_proba)

    def _fit_platt(self, y_true: np.ndarray, y_proba: np.ndarray) -> None:
        """Fit Platt scaling (sigmoid)."""
        from scipy.optimize import minimize

        def sigmoid_loss(params):
            a, b = params
            logits = a * np.log(y_proba / (1 - y_proba)) + b
            loss = -np.mean(
                y_true * np.log(1 / (1 + np.exp(-logits))) +
                (1 - y_true) * np.log(1 - 1 / (1 + np.exp(-logits)))
            )
            return loss

        result = minimize(sigmoid_loss, x0=[1.0, 0.0], method='Nelder-Mead')
        self._calibrator = tuple(result.x)

    def _fit_isotonic(self, y_true: np.ndarray, y_proba: np.ndarray) -> None:
        """Fit isotonic regression calibration."""
        from sklearn.isotonic import IsotonicRegression

        ir = IsotonicRegression(y_min=1e-7, y_max=1 - 1e-7, out_of_bounds='clip')
        ir.fit(y_proba, y_true)
        self._calibrator = ir
        self._isotonic_map = {
            'x': ir.X_thresholds_.tolist(),
            'y': ir.y_thresholds_.tolist(),
        }

    def _compute_metrics(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10,
    ) -> Dict[str, float]:
        """Compute calibration metrics."""
        y_true = np.asarray(y_true)
        y_proba = np.asarray(y_proba).clip(1e-7, 1 - 1e-7)

        # Brier score
        brier = float(brier_score_loss(y_true, y_proba))

        # ECE
        ece = self._compute_ece(y_true, y_proba, n_bins)

        # Log loss
        try:
            ll = float(log_loss(y_true, y_proba))
        except Exception:
            ll = float('nan')

        return {
            'brier_score': brier,
            'ece': ece,
            'log_loss': ll,
        }

    def _compute_ece(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10,
    ) -> float:
        """Compute Expected Calibration Error."""
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0

        for i in range(n_bins):
            lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
            mask = (y_proba >= lo) & (y_proba < hi)
            if mask.sum() == 0:
                continue
            bin_acc = y_true[mask].mean()
            bin_conf = y_proba[mask].mean()
            ece += mask.sum() / len(y_true) * abs(bin_acc - bin_conf)

        return float(ece)

    def _compute_reliability(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        n_bins: int = 10,
    ) -> Dict[str, Any]:
        """Compute reliability diagram data."""
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        fraction_of_positives = []
        mean_predicted_value = []
        bin_counts = []

        for i in range(n_bins):
            lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
            mask = (y_proba >= lo) & (y_proba < hi)
            if mask.sum() == 0:
                fraction_of_positives.append(0.0)
                mean_predicted_value.append((lo + hi) / 2)
                bin_counts.append(0)
            else:
                fraction_of_positives.append(float(y_true[mask].mean()))
                mean_predicted_value.append(float(y_proba[mask].mean()))
                bin_counts.append(int(mask.sum()))

        return {
            'fraction_of_positives': fraction_of_positives,
            'mean_predicted_value': mean_predicted_value,
            'bin_counts': bin_counts,
            'n_bins': n_bins,
        }

    @property
    def pre_metrics(self) -> Dict[str, float]:
        return self._pre_metrics

    @property
    def post_metrics(self) -> Dict[str, float]:
        return self._post_metrics

    @property
    def reliability_data(self) -> Dict[str, Any]:
        return self._reliability_data

    def to_dict(self) -> Dict[str, Any]:
        """Serialize calibrator state for saving."""
        if not self._is_fitted:
            return {'method': self.method, 'is_fitted': False}

        state = {
            'method': self.method,
            'is_fitted': True,
            'pre_metrics': self._pre_metrics,
            'post_metrics': self._post_metrics,
            'reliability_data': self._reliability_data,
        }

        if self.method == 'platt':
            state['platt_params'] = list(self._calibrator)
        elif self.method == 'isotonic':
            state['isotonic_x'] = self._isotonic_map['x']
            state['isotonic_y'] = self._isotonic_map['y']

        return state

    @classmethod
    def from_dict(cls, state: Dict[str, Any]) -> 'ModelCalibrator':
        """Deserialize calibrator from saved state."""
        cal = cls(method=state['method'])
        if not state.get('is_fitted', False):
            return cal

        cal._pre_metrics = state.get('pre_metrics', {})
        cal._post_metrics = state.get('post_metrics', {})
        cal._reliability_data = state.get('reliability_data', {})
        cal._is_fitted = True

        if state['method'] == 'platt':
            cal._calibrator = tuple(state['platt_params'])
        elif state['method'] == 'isotonic':
            cal._isotonic_map = {
                'x': state['isotonic_x'],
                'y': state['isotonic_y'],
            }

        return cal
