"""Train the bootstrap SentinelAI risk classifier."""

from app.ml.risk_classifier import RiskClassifier


def main() -> None:
    """Train and persist the bootstrap classifier."""
    RiskClassifier.train_bootstrap()


if __name__ == "__main__":
    main()
