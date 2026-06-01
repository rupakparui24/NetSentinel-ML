"""Data drift detection with PSI, KL divergence, and KS statistics."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import entropy, ks_2samp


@dataclass
class FeatureDrift:
    feature: str
    psi: float
    kl_divergence: float
    ks_statistic: float
    drift_score: float
    drifted: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DriftReport:
    drift_score: float
    drifted: bool
    threshold: float
    features: list[FeatureDrift] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["features"] = [feature.to_dict() for feature in self.features]
        return payload


class DriftDetectionService:
    """Compare reference and current feature distributions."""

    def __init__(self, threshold: float = 0.3, bins: int = 10) -> None:
        self.threshold = threshold
        self.bins = bins

    def detect(self, reference: pd.DataFrame, current: pd.DataFrame) -> DriftReport:
        common = [column for column in reference.columns if column in current.columns]
        feature_reports: list[FeatureDrift] = []
        for feature in common:
            expected = pd.to_numeric(reference[feature], errors="coerce").dropna()
            observed = pd.to_numeric(current[feature], errors="coerce").dropna()
            if expected.empty or observed.empty:
                continue
            psi = self.population_stability_index(expected.to_numpy(), observed.to_numpy())
            kl = self.kl_divergence(expected.to_numpy(), observed.to_numpy())
            ks = float(ks_2samp(expected.to_numpy(), observed.to_numpy()).statistic)
            score = float(max(min(psi, 1.0), min(kl, 1.0), ks))
            feature_reports.append(
                FeatureDrift(
                    feature=feature,
                    psi=round(psi, 6),
                    kl_divergence=round(kl, 6),
                    ks_statistic=round(ks, 6),
                    drift_score=round(score, 6),
                    drifted=score > self.threshold,
                )
            )

        drift_score = max((feature.drift_score for feature in feature_reports), default=0.0)
        return DriftReport(
            drift_score=round(float(drift_score), 6),
            drifted=drift_score > self.threshold,
            threshold=self.threshold,
            features=sorted(feature_reports, key=lambda item: item.drift_score, reverse=True),
        )

    def save_report(self, report: DriftReport, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        return target

    def population_stability_index(self, expected: np.ndarray, actual: np.ndarray) -> float:
        expected = np.asarray(expected, dtype=float)
        actual = np.asarray(actual, dtype=float)
        quantiles = np.linspace(0, 1, self.bins + 1)
        breakpoints = np.unique(np.quantile(expected, quantiles))
        if len(breakpoints) <= 2:
            breakpoints = np.linspace(float(expected.min()), float(expected.max()) + 1e-6, self.bins + 1)
        expected_counts, _ = np.histogram(expected, bins=breakpoints)
        actual_counts, _ = np.histogram(actual, bins=breakpoints)
        expected_pct = np.clip(expected_counts / max(expected_counts.sum(), 1), 1e-6, None)
        actual_pct = np.clip(actual_counts / max(actual_counts.sum(), 1), 1e-6, None)
        return float(np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct)))

    def kl_divergence(self, expected: np.ndarray, actual: np.ndarray) -> float:
        expected = np.asarray(expected, dtype=float)
        actual = np.asarray(actual, dtype=float)
        low = min(float(expected.min()), float(actual.min()))
        high = max(float(expected.max()), float(actual.max()))
        if low == high:
            high = low + 1e-6
        expected_hist, edges = np.histogram(expected, bins=self.bins, range=(low, high), density=True)
        actual_hist, _ = np.histogram(actual, bins=edges, density=True)
        expected_hist = np.clip(expected_hist, 1e-6, None)
        actual_hist = np.clip(actual_hist, 1e-6, None)
        return float(entropy(actual_hist, expected_hist))
