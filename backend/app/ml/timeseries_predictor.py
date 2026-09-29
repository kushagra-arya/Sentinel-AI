"""Thirty-minute telemetry trend prediction for risk forecasting."""

from dataclasses import dataclass
from datetime import datetime

from app.models.enums import RiskLevel


@dataclass(frozen=True)
class TrendPoint:
    """A telemetry point used for time-series forecasting."""

    measured_at: datetime
    value: float


@dataclass(frozen=True)
class TrendPrediction:
    """Predicted telemetry value and risk trajectory."""

    signal: str
    predicted_value: float
    horizon_minutes: int
    trend: str
    risk_level: RiskLevel
    minutes_to_high_risk: int | None


class TimeSeriesPredictor:
    """Predict telemetry values thirty minutes ahead using trend extrapolation.

    LightGBM or XGBoost can be introduced behind this interface once the Phase
    10 synthetic dataset exists. The current implementation uses auditable
    linear slope extrapolation so forecasts are explainable and deterministic.
    """

    horizon_minutes = 30

    def predict(self, signal: str, points: list[TrendPoint]) -> TrendPrediction:
        """Predict one signal thirty minutes ahead from recent points."""
        if len(points) < 2:
            latest = points[-1].value if points else 0.0
            return TrendPrediction(
                signal=signal,
                predicted_value=latest,
                horizon_minutes=self.horizon_minutes,
                trend="insufficient_data",
                risk_level=RiskLevel.LOW,
                minutes_to_high_risk=None,
            )

        ordered = sorted(points, key=lambda point: point.measured_at)
        first = ordered[0]
        last = ordered[-1]
        elapsed_minutes = max((last.measured_at - first.measured_at).total_seconds() / 60.0, 1.0)
        slope = (last.value - first.value) / elapsed_minutes
        predicted = last.value + slope * self.horizon_minutes
        threshold = self._high_risk_threshold(signal)
        minutes_to_high = None
        if slope > 0 and last.value < threshold <= predicted:
            minutes_to_high = max(int((threshold - last.value) / slope), 0)
        risk_level = RiskLevel.HIGH if predicted >= threshold else RiskLevel.LOW
        trend = "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat"
        return TrendPrediction(
            signal=signal,
            predicted_value=round(predicted, 4),
            horizon_minutes=self.horizon_minutes,
            trend=trend,
            risk_level=risk_level,
            minutes_to_high_risk=minutes_to_high,
        )

    @staticmethod
    def _high_risk_threshold(signal: str) -> float:
        """Return high-risk thresholds used for forward-looking dashboard hints."""
        return {
            "gas": 50.0,
            "temperature": 80.0,
            "pressure": 120.0,
        }[signal]
