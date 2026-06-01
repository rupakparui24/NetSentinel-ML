"""Runtime prediction orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

import pandas as pd

from netsentinel.core.config import Settings, get_settings
from netsentinel.services.alerting import AlertingService
from netsentinel.services.drift_detection import DriftDetectionService, DriftReport
from netsentinel.services.explainability import ExplainabilityService
from netsentinel.services.feature_engineering import FeatureEngineeringService
from netsentinel.services.model_registry import ModelRecord, ModelRegistry
from netsentinel.services.model_training import ModelTrainingService, TrainingRunResult
from netsentinel.services.monitoring import MetricsCollector
from netsentinel.services.sample_data import generate_synthetic_network_flows


@dataclass
class PredictionOutcome:
    prediction_id: str
    model_id: str
    label: int
    prediction: str
    confidence: float
    latency_ms: float
    explanation: list[dict]
    counterfactual: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


class PredictionService:
    """Serve predictions while tracking metrics, explanations, and drift."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.registry = ModelRegistry(self.settings.model_registry_dir)
        self.feature_engineer = FeatureEngineeringService()
        self.explainer = ExplainabilityService()
        self.metrics = MetricsCollector(window_size=self.settings.metrics_window_size)
        self.alerts = AlertingService()
        self.drift_detector = DriftDetectionService(threshold=self.settings.drift_threshold)
        self.predictions: dict[str, PredictionOutcome] = {}
        self.model: Any | None = None
        self.active_record: ModelRecord | None = None
        self.reference_features = pd.DataFrame()
        self._load_or_bootstrap()

    def predict_one(self, payload: dict) -> PredictionOutcome:
        """Predict one network flow."""

        start = perf_counter()
        try:
            row = self.feature_engineer.build_features(pd.DataFrame([payload])).features
            raw_prediction = int(self.model.predict(row)[0])
            confidence = self._confidence(row, raw_prediction)
            latency = round((perf_counter() - start) * 1000, 4)
            explanation = self.explainer.explain_prediction(
                self.model,
                row,
                self.reference_features,
                top_k=5,
            )
            counterfactual = self.explainer.counterfactual(row, self.reference_features, explanation)
            outcome = PredictionOutcome(
                prediction_id=str(uuid4()),
                model_id=self.active_record.model_id if self.active_record else "unregistered",
                label=raw_prediction,
                prediction="malicious" if raw_prediction == 1 else "benign",
                confidence=round(confidence, 4),
                latency_ms=latency,
                explanation=explanation,
                counterfactual=counterfactual,
            )
            self.predictions[outcome.prediction_id] = outcome
            self.metrics.record_prediction(latency_ms=latency, confidence=confidence)
            return outcome
        except Exception:
            self.metrics.record_error()
            raise

    def predict_batch(self, payloads: list[dict]) -> list[PredictionOutcome]:
        return [self.predict_one(payload) for payload in payloads]

    def explain(self, prediction_id: str) -> PredictionOutcome:
        if prediction_id not in self.predictions:
            raise KeyError(f"Prediction not found: {prediction_id}")
        return self.predictions[prediction_id]

    def model_catalog(self) -> list[dict]:
        return self.registry.list_models()

    def switch_model(self, model_id: str) -> ModelRecord:
        record = self.registry.promote(model_id, stage="production")
        self.active_record = record
        self.model = self.registry.load_model(model_id)
        return record

    def check_drift(self, payloads: list[dict]) -> DriftReport:
        current = self.feature_engineer.build_features(pd.DataFrame(payloads)).features
        report = self.drift_detector.detect(self.reference_features, current)
        self.metrics.update_drift(report.drift_score)
        self.alerts.evaluate(self.metrics.snapshot(), drift_threshold=self.settings.drift_threshold)
        return report

    def retrain(self, rows: int | None = None, drift: bool = False) -> TrainingRunResult:
        sample = generate_synthetic_network_flows(
            n_rows=rows or self.settings.demo_training_rows,
            seed=self.settings.random_seed + 11,
            drift=drift,
        )
        result = ModelTrainingService(self.feature_engineer).train_all(
            sample,
            registry=self.registry,
            reference_data_path=self.settings.reference_data_path,
            promote_best=True,
        )
        self.active_record = result.best_model
        self.model = self.registry.load_model(result.best_model.model_id)
        self.reference_features = self._load_reference_features(sample)
        return result

    def performance(self) -> dict:
        snapshot = self.metrics.snapshot()
        generated = self.alerts.evaluate(snapshot, drift_threshold=self.settings.drift_threshold)
        return {
            "metrics": snapshot.to_dict(),
            "alerts": self.alerts.list_alerts(),
            "new_alerts": [alert.to_dict() for alert in generated],
        }

    def _load_or_bootstrap(self) -> None:
        self.active_record = self.registry.get_active_record()
        if self.active_record is None:
            self.retrain(rows=self.settings.demo_training_rows)
            return
        self.model = self.registry.load_model(self.active_record.model_id)
        if self.settings.reference_data_path.exists():
            self.reference_features = pd.read_csv(self.settings.reference_data_path)
        else:
            sample = generate_synthetic_network_flows(
                n_rows=self.settings.demo_training_rows, seed=self.settings.random_seed
            )
            self.reference_features = self._load_reference_features(sample)

    def _load_reference_features(self, sample: pd.DataFrame) -> pd.DataFrame:
        if self.settings.reference_data_path.exists():
            return pd.read_csv(self.settings.reference_data_path)
        features = self.feature_engineer.build_features(sample).features
        self.settings.reference_data_path.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(self.settings.reference_data_path, index=False)
        return features

    def _confidence(self, row: pd.DataFrame, prediction: int) -> float:
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(row)[0]
            if len(probabilities) > prediction:
                return float(probabilities[prediction])
            return float(max(probabilities))
        if hasattr(self.model, "decision_function"):
            score = float(self.model.decision_function(row)[0])
            return 1 / (1 + pow(2.718281828, -abs(score)))
        return 0.5
