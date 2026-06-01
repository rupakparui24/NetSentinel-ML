"""Fast explainability helpers for tree-based tabular models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class FeatureContribution:
    feature: str
    value: float
    contribution: float
    baseline: float
    direction: str

    def to_dict(self) -> dict:
        return asdict(self)


class ExplainabilityService:
    """Return global and local explanations without requiring SHAP at runtime.

    The approximation uses fitted tree feature importances combined with the
    sample's distance from reference data. The service can be replaced with
    SHAP later without changing the API contract.
    """

    def global_feature_importance(self, model: Any, feature_columns: list[str], top_k: int = 10) -> list[dict]:
        importances = self._feature_importances(model, feature_columns)
        ranked = sorted(importances.items(), key=lambda item: item[1], reverse=True)[:top_k]
        return [{"feature": feature, "importance": round(float(score), 6)} for feature, score in ranked]

    def explain_prediction(
        self,
        model: Any,
        row: pd.DataFrame,
        reference: pd.DataFrame,
        top_k: int = 5,
    ) -> list[dict]:
        feature_columns = list(row.columns)
        importances = self._feature_importances(model, feature_columns)
        means = reference[feature_columns].mean(numeric_only=True).reindex(feature_columns).fillna(0)
        stds = reference[feature_columns].std(numeric_only=True).replace(0, 1).reindex(feature_columns).fillna(1)

        contributions: list[FeatureContribution] = []
        sample = row.iloc[0]
        for feature in feature_columns:
            z_score = (float(sample[feature]) - float(means[feature])) / float(stds[feature])
            contribution = abs(z_score) * importances.get(feature, 0.0)
            direction = "above_baseline" if z_score >= 0 else "below_baseline"
            contributions.append(
                FeatureContribution(
                    feature=feature,
                    value=round(float(sample[feature]), 4),
                    contribution=round(float(contribution), 6),
                    baseline=round(float(means[feature]), 4),
                    direction=direction,
                )
            )

        contributions.sort(key=lambda item: item.contribution, reverse=True)
        return [item.to_dict() for item in contributions[:top_k]]

    def counterfactual(
        self,
        row: pd.DataFrame,
        reference: pd.DataFrame,
        contributions: list[dict],
        top_k: int = 3,
    ) -> list[dict]:
        """Suggest minimal feature shifts toward the reference baseline."""

        changes: list[dict] = []
        for item in contributions[:top_k]:
            feature = item["feature"]
            current = float(row.iloc[0][feature])
            baseline = float(reference[feature].mean()) if feature in reference else 0.0
            delta = baseline - current
            changes.append(
                {
                    "feature": feature,
                    "current": round(current, 4),
                    "suggested": round(baseline, 4),
                    "delta": round(delta, 4),
                }
            )
        return changes

    def _feature_importances(self, model: Any, feature_columns: list[str]) -> dict[str, float]:
        estimator = model
        if hasattr(model, "named_steps"):
            estimator = model.named_steps.get("model", model)

        raw: np.ndarray
        if hasattr(estimator, "feature_importances_"):
            raw = np.asarray(estimator.feature_importances_, dtype=float)
        elif hasattr(estimator, "coef_"):
            raw = np.abs(np.asarray(estimator.coef_, dtype=float)).ravel()
        else:
            raw = np.ones(len(feature_columns), dtype=float)

        if len(raw) != len(feature_columns):
            raw = np.resize(raw, len(feature_columns))
        total = float(raw.sum()) or 1.0
        normalized = raw / total
        return dict(zip(feature_columns, normalized, strict=False))
