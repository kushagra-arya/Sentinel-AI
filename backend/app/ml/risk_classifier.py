"""Risk classification training and inference utilities.

The training path prefers XGBoost for the primary classifier and falls back to
Random Forest when XGBoost is unavailable. A deterministic rules fallback keeps
the API operational in constrained environments; Phase 10 will replace the
bootstrap sample with the full synthetic demo dataset.
"""

from dataclasses import dataclass
from pathlib import Path
import pickle
from typing import Any

from app.models.enums import RiskLevel

MODEL_VERSION = "risk-classifier-bootstrap-v1"
MODEL_PATH = Path(__file__).with_name("risk_classifier.pkl")
FEATURE_NAMES = [
    "gas",
    "temperature",
    "pressure",
    "humidity",
    "worker_count",
    "maintenance_active",
    "permit_type_code",
]
LABELS = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
PERMIT_TYPE_CODES = {
    "none": 0.0,
    "hot_work": 1.0,
    "confined_space": 2.0,
    "electrical": 3.0,
}


@dataclass(frozen=True)
class RiskFeatures:
    """Input feature vector for risk classification."""

    gas: float
    temperature: float
    pressure: float
    humidity: float
    worker_count: int
    maintenance_active: bool
    permit_type: str

    def to_vector(self) -> list[float]:
        """Return numeric model features in training order."""
        return [
            self.gas,
            self.temperature,
            self.pressure,
            self.humidity,
            float(self.worker_count),
            1.0 if self.maintenance_active else 0.0,
            PERMIT_TYPE_CODES.get(self.permit_type, 0.0),
        ]


@dataclass(frozen=True)
class RiskPrediction:
    """Risk classification output with model provenance."""

    risk_level: RiskLevel
    score: float
    model_name: str
    model_version: str


class RiskClassifier:
    """Train and run an auditable plant risk classifier."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        """Load a persisted model if present, otherwise use deterministic fallback."""
        self.model_path = model_path
        self.model: Any | None = None
        self.model_name = "deterministic_fallback"
        if model_path.exists():
            with model_path.open("rb") as file:
                payload = pickle.load(file)
            self.model = payload["model"]
            self.model_name = payload["model_name"]

    def predict(self, features: RiskFeatures) -> RiskPrediction:
        """Classify a feature vector into low/medium/high/critical risk."""
        if self.model is None:
            return self._fallback_predict(features)
        vector = [features.to_vector()]
        label_index = int(self.model.predict(vector)[0])
        probabilities = self.model.predict_proba(vector)[0]
        return RiskPrediction(
            risk_level=LABELS[label_index],
            score=float(max(probabilities)),
            model_name=self.model_name,
            model_version=MODEL_VERSION,
        )

    @staticmethod
    def train_bootstrap(model_path: Path = MODEL_PATH) -> str:
        """Train the bootstrap classifier and persist it to disk."""
        features, labels = bootstrap_training_sample()
        model_name = "xgboost"
        try:
            from xgboost import XGBClassifier

            model = XGBClassifier(
                n_estimators=24,
                max_depth=3,
                learning_rate=0.2,
                objective="multi:softprob",
                eval_metric="mlogloss",
                random_state=42,
            )
        except ImportError:
            from sklearn.ensemble import RandomForestClassifier

            model_name = "random_forest"
            model = RandomForestClassifier(n_estimators=80, max_depth=5, random_state=42)

        model.fit(features, labels)
        with model_path.open("wb") as file:
            pickle.dump(
                {
                    "model": model,
                    "model_name": model_name,
                    "model_version": MODEL_VERSION,
                    "feature_names": FEATURE_NAMES,
                    "note": "Bootstrap sample; Phase 10 full synthetic dataset supersedes this.",
                },
                file,
            )
        return MODEL_VERSION

    @staticmethod
    def _fallback_predict(features: RiskFeatures) -> RiskPrediction:
        """Return a deterministic conservative prediction when ML packages are unavailable."""
        score = 0.15
        if features.gas >= 35:
            score += 0.35
        elif features.gas >= 20:
            score += 0.2
        if features.temperature >= 75 or features.pressure >= 115:
            score += 0.22
        if features.maintenance_active:
            score += 0.12
        if features.worker_count > 0:
            score += 0.08
        if features.permit_type == "confined_space":
            score += 0.18
        score = min(score, 0.99)
        if score >= 0.85:
            level = RiskLevel.CRITICAL
        elif score >= 0.65:
            level = RiskLevel.HIGH
        elif score >= 0.35:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW
        return RiskPrediction(
            risk_level=level,
            score=score,
            model_name="deterministic_fallback",
            model_version=MODEL_VERSION,
        )


def bootstrap_training_sample() -> tuple[list[list[float]], list[int]]:
    """Generate a small deterministic sample until Phase 10 provides full data."""
    rows: list[list[float]] = []
    labels: list[int] = []
    for gas in [5.0, 15.0, 25.0, 45.0]:
        for temperature in [30.0, 55.0, 85.0]:
            for maintenance_active in [False, True]:
                worker_count = 0 if gas < 20 else 3
                permit_type = "confined_space" if gas >= 45 else "hot_work"
                features = RiskFeatures(
                    gas=gas,
                    temperature=temperature,
                    pressure=95.0 + gas * 0.4,
                    humidity=45.0,
                    worker_count=worker_count,
                    maintenance_active=maintenance_active,
                    permit_type=permit_type,
                )
                score = RiskClassifier._fallback_predict(features).score
                if score >= 0.85:
                    label = 3
                elif score >= 0.65:
                    label = 2
                elif score >= 0.35:
                    label = 1
                else:
                    label = 0
                rows.append(features.to_vector())
                labels.append(label)
    return rows, labels
