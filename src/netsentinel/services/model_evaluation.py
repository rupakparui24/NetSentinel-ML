"""Model evaluation utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


@dataclass
class EvaluationResult:
    """Serializable model evaluation result."""

    metrics: dict[str, float]
    confusion_matrix: list[list[int]]
    classification_report: dict[str, Any]
    inference_latency_ms: float
    model_size_bytes: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ModelEvaluationService:
    """Compute the metrics called out in the project requirements."""

    def evaluate(self, model: Any, x_test, y_test) -> EvaluationResult:
        start = perf_counter()
        y_pred = model.predict(x_test)
        latency_ms = (perf_counter() - start) * 1000 / max(len(x_test), 1)

        metrics = {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        }

        y_score = self._score(model, x_test)
        if y_score is not None and len(np.unique(y_test)) == 2:
            metrics["auc_roc"] = float(roc_auc_score(y_test, y_score))

        return EvaluationResult(
            metrics=metrics,
            confusion_matrix=confusion_matrix(y_test, y_pred).astype(int).tolist(),
            classification_report=classification_report(y_test, y_pred, output_dict=True, zero_division=0),
            inference_latency_ms=round(float(latency_ms), 4),
        )

    def model_size_bytes(self, model: Any, temp_path: str | Path) -> int:
        """Estimate serialized model size."""

        path = Path(temp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, path)
        size = path.stat().st_size
        path.unlink(missing_ok=True)
        return int(size)

    def _score(self, model: Any, x_test) -> np.ndarray | None:
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x_test)
            if proba.ndim == 2 and proba.shape[1] > 1:
                return proba[:, 1]
        if hasattr(model, "decision_function"):
            return model.decision_function(x_test)
        return None
