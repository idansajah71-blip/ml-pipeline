"""Time Series Forecaster — Multiple forecasting methods for scraped time data."""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logger = logging.getLogger(__name__)


@dataclass
class ForecastResult:
    method: str = ""
    periods: int = 0
    predictions: list[float] = field(default_factory=list)
    confidence_lower: list[float] = field(default_factory=list)
    confidence_upper: list[float] = field(default_factory=list)
    timestamps: list[str] = field(default_factory=list)
    mae: float = 0.0
    rmse: float = 0.0
    r2: float = 0.0
    trend: str = ""
    seasonality_detected: bool = False
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "method": self.method, "periods": self.periods,
            "predictions": [round(p, 4) for p in self.predictions],
            "confidence_lower": [round(p, 4) for p in self.confidence_lower],
            "confidence_upper": [round(p, 4) for p in self.confidence_upper],
            "timestamps": self.timestamps,
            "mae": round(self.mae, 4), "rmse": round(self.rmse, 4),
            "r2": round(self.r2, 4), "trend": self.trend,
            "seasonality_detected": self.seasonality_detected,
            "summary": self.summary,
        }


class Forecaster:

    def __init__(self):
        self._seasonal_period = 12

    def detect_trend(self, series: pd.Series) -> str:
        x = np.arange(len(series)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(x, series.values)
        slope = model.coef_[0]
        if slope > 0.01:
            return "increasing"
        elif slope < -0.01:
            return "decreasing"
        return "stable"

    def detect_seasonality(self, series: pd.Series) -> bool:
        if len(series) < 24:
            return False
        from scipy.signal import periodogram
        try:
            freqs, psd = periodogram(series.values)
            dominant_freq_idx = np.argmax(psd[1:]) + 1
            return psd[dominant_freq_idx] > 2 * np.mean(psd)
        except Exception:
            return False

    def forecast_linear(self, series: pd.Series, periods: int = 10) -> ForecastResult:
        x = np.arange(len(series)).reshape(-1, 1)
        model = LinearRegression()
        model.fit(x, series.values)

        future_x = np.arange(len(series), len(series) + periods).reshape(-1, 1)
        preds = model.predict(future_x)
        residuals = series.values - model.predict(x)
        std_resid = np.std(residuals)

        result = ForecastResult(
            method="linear", periods=periods, predictions=preds.tolist(),
            confidence_lower=(preds - 1.96 * std_resid).tolist(),
            confidence_upper=(preds + 1.96 * std_resid).tolist(),
        )
        result.mae = mean_absolute_error(series.values, model.predict(x))
        result.rmse = float(np.sqrt(mean_squared_error(series.values, model.predict(x))))
        result.r2 = model.score(x, series.values)
        result.trend = self.detect_trend(series)
        result.seasonality_detected = self.detect_seasonality(series)
        result.summary = f"Linear: trend={result.trend}, R²={result.r2:.3f}"
        return result

    def forecast_moving_average(self, series: pd.Series, periods: int = 10,
                                window: int = 5) -> ForecastResult:
        ma = series.rolling(window=window).mean().dropna()
        last_ma = ma.iloc[-1]
        trend = (ma.iloc[-1] - ma.iloc[0]) / max(len(ma), 1)

        preds = [last_ma + trend * (i + 1) for i in range(periods)]
        std = series.std()

        train_pred = series.rolling(window=window).mean().dropna().values
        actual = series.values[window-1:]
        if len(train_pred) > 0 and len(actual) > 0:
            min_len = min(len(train_pred), len(actual))
            train_pred = train_pred[:min_len]
            actual = actual[:min_len]

        result = ForecastResult(
            method="moving_average", periods=periods, predictions=preds,
            confidence_lower=[p - 1.96 * std for p in preds],
            confidence_upper=[p + 1.96 * std for p in preds],
        )
        if len(train_pred) > 0 and len(actual) > 0:
            result.mae = mean_absolute_error(actual, train_pred)
            result.rmse = float(np.sqrt(mean_squared_error(actual, train_pred)))
            result.r2 = r2_score(actual, train_pred) if len(actual) > 1 else 0.0
        result.trend = self.detect_trend(series)
        result.summary = f"Moving Average (window={window}): trend={result.trend}"
        return result

    def forecast_polynomial(self, series: pd.Series, periods: int = 10,
                            degree: int = 2) -> ForecastResult:
        x = np.arange(len(series)).reshape(-1, 1)
        poly = PolynomialFeatures(degree=degree)
        x_poly = poly.fit_transform(x)

        model = Ridge(alpha=1.0)
        model.fit(x_poly, series.values)

        future_x = np.arange(len(series), len(series) + periods).reshape(-1, 1)
        future_poly = poly.transform(future_x)
        preds = model.predict(future_poly)

        train_pred = model.predict(x_poly)
        residuals = series.values - train_pred
        std = np.std(residuals)

        result = ForecastResult(
            method=f"polynomial_d{degree}", periods=periods, predictions=preds.tolist(),
            confidence_lower=(preds - 1.96 * std).tolist(),
            confidence_upper=(preds + 1.96 * std).tolist(),
        )
        result.mae = mean_absolute_error(series.values, train_pred)
        result.rmse = float(np.sqrt(mean_squared_error(series.values, train_pred)))
        result.r2 = model.score(x_poly, series.values)
        result.trend = self.detect_trend(series)
        result.summary = f"Polynomial (deg={degree}): R²={result.r2:.3f}"
        return result

    def forecast_gradient_boosting(self, series: pd.Series, periods: int = 10,
                                   n_estimators: int = 100) -> ForecastResult:
        x = np.arange(len(series)).reshape(-1, 1)
        model = GradientBoostingRegressor(n_estimators=n_estimators, random_state=42)
        model.fit(x, series.values)

        future_x = np.arange(len(series), len(series) + periods).reshape(-1, 1)
        preds = model.predict(future_x)

        train_pred = model.predict(x)
        residuals = series.values - train_pred
        std = np.std(residuals)

        result = ForecastResult(
            method="gradient_boosting", periods=periods, predictions=preds.tolist(),
            confidence_lower=(preds - 1.96 * std).tolist(),
            confidence_upper=(preds + 1.96 * std).tolist(),
        )
        result.mae = mean_absolute_error(series.values, train_pred)
        result.rmse = float(np.sqrt(mean_squared_error(series.values, train_pred)))
        result.r2 = model.score(x, series.values)
        result.trend = self.detect_trend(series)
        result.summary = f"Gradient Boosting: R²={result.r2:.3f}"
        return result

    def forecast_auto(self, series: pd.Series, periods: int = 10) -> ForecastResult:
        candidates = []
        for name, fn in [
            ("linear", self.forecast_linear),
            ("ma", lambda s, p: self.forecast_moving_average(s, p)),
            ("poly", lambda s, p: self.forecast_polynomial(s, p)),
            ("gb", lambda s, p: self.forecast_gradient_boosting(s, p)),
        ]:
            try:
                r = fn(series, periods)
                score = r.r2 if r.r2 > 0 else 0
                candidates.append((name, r, score))
            except Exception:
                pass

        if candidates:
            candidates.sort(key=lambda x: x[2], reverse=True)
            best = candidates[0][1]
            best.summary = f"AUTO (best={candidates[0][0]}): {best.summary}"
            return best
        return self.forecast_linear(series, periods)

    def forecast_from_dataframe(self, df: pd.DataFrame, value_col: str,
                                time_col: str = None, periods: int = 10) -> dict:
        if value_col not in df.columns:
            return {"error": f"Column '{value_col}' not found in dataframe"}
        
        series = df[value_col].dropna()
        if len(series) < 3:
            return {"error": "Insufficient data points for forecasting (need at least 3)"}
        
        result = self.forecast_auto(series, periods)

        if time_col and time_col in df.columns:
            try:
                dates = pd.to_datetime(df[time_col])
                freq = (dates.iloc[-1] - dates.iloc[-2])
                future_dates = [dates.iloc[-1] + freq * (i + 1) for i in range(periods)]
                result.timestamps = [str(d) for d in future_dates]
            except Exception:
                pass

        return result.to_dict()
