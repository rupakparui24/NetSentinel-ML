"""Training service for baseline and advanced tabular models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from netsentinel.services.feature_engineering import FEATURE_COLUMNS, FeatureEngineeringService
from netsentinel.services.model_evaluation import ModelEvaluationService
from netsentinel.services.model_registry import ModelRecord, ModelRegistry


@dataclass
class CandidateResult:
    name: str
    model: Any
    metrics: dict[str, float]
    inference_latency_ms: float
    params: dict[str, Any]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload.pop("model", None)
        return payload


@dataclass
class TrainingRunResult:
    best_model: ModelRecord
    candidates: list[CandidateResult]
    reference_rows: int

    def to_dict(self) -> dict:
        return {
            "best_model": self.best_model.to_dict(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "reference_rows": self.reference_rows,
        }


class ModelTrainingService:
    """Train multiple model candidates and register the best one."""

    def __init__(
        self,
        feature_engineer: FeatureEngineeringService | None = None,
        evaluator: ModelEvaluationService | None = None,
    ) -> None:
        self.feature_engineer = feature_engineer or FeatureEngineeringService()
        self.evaluator = evaluator or ModelEvaluationService()

    def train_all(
        self,
        df: pd.DataFrame,
        registry: ModelRegistry,
        reference_data_path: str | Path | None = None,
        promote_best: bool = True,
        tags: dict[str, str] | None = None,
    ) -> TrainingRunResult:
        """Train RF and gradient boosting candidates, then register the winner."""

        build = self.feature_engineer.build_features(df)
        if build.labels is None:
            raise ValueError("Training data must include a label column.")

        x_train, x_test, y_train, y_test = train_test_split(
            build.features,
            build.labels,
            test_size=0.2,
            random_state=42,
            stratify=build.labels,
        )

        candidates = [
            self.train_random_forest(x_train, y_train, x_test, y_test),
            self.train_gradient_boosting(x_train, y_train, x_test, y_test),
        ]
        best = sorted(candidates, key=lambda item: (item.metrics.get("f1", 0), -item.inference_latency_ms))[-1]
        stage = "production" if promote_best else "staging"
        record = registry.register_model(
            name=best.name,
            model=best.model,
            metrics=best.metrics | {"inference_latency_ms": best.inference_latency_ms},
            feature_columns=FEATURE_COLUMNS,
            params=best.params,
            stage=stage,
            tags=tags or {"source": "synthetic-demo", "purpose": "portfolio-mvp"},
        )

        if reference_data_path is not None:
            path = Path(reference_data_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            x_train.to_csv(path, index=False)

        return TrainingRunResult(best_model=record, candidates=candidates, reference_rows=len(x_train))

    def train_random_forest(self, x_train, y_train, x_test, y_test) -> CandidateResult:
        params = {
            "n_estimators": 90,
            "max_depth": 14,
            "min_samples_split": 8,
            "class_weight": "balanced",
            "random_state": 42,
            "n_jobs": -1,
        }
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", RandomForestClassifier(**params)),
            ]
        )
        model.fit(x_train, y_train)
        result = self.evaluator.evaluate(model, x_test, y_test)
        return CandidateResult(
            name="random_forest",
            model=model,
            metrics=result.metrics,
            inference_latency_ms=result.inference_latency_ms,
            params=params,
        )

    def train_gradient_boosting(self, x_train, y_train, x_test, y_test) -> CandidateResult:
        params = {
            "n_estimators": 120,
            "learning_rate": 0.06,
            "max_depth": 3,
            "random_state": 42,
        }
        model = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("model", GradientBoostingClassifier(**params)),
            ]
        )
        model.fit(x_train, y_train)
        result = self.evaluator.evaluate(model, x_test, y_test)
        return CandidateResult(
            name="gradient_boosting",
            model=model,
            metrics=result.metrics,
            inference_latency_ms=result.inference_latency_ms,
            params=params,
        )
