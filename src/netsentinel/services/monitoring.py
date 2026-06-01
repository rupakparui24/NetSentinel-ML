"""In-memory operational metrics plus Prometheus export."""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from time import time

import numpy as np
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


@dataclass
class MetricsSnapshot:
    total_predictions: int
    error_rate: float
    throughput_rps: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    average_confidence: float
    drift_score: float

    def to_dict(self) -> dict:
        return asdict(self)


class MetricsCollector:
    """Collect operational metrics needed by the dashboard and API."""

    def __init__(self, window_size: int = 1000) -> None:
        self.window_size = window_size
        self.latencies: deque[float] = deque(maxlen=window_size)
        self.confidences: deque[float] = deque(maxlen=window_size)
        self.events: deque[float] = deque(maxlen=window_size)
        self.total_predictions = 0
        self.total_errors = 0
        self.drift_score = 0.0

        self.registry = CollectorRegistry()
        self.prediction_counter = Counter(
            "netsentinel_predictions_total",
            "Total predictions served",
            registry=self.registry,
        )
        self.error_counter = Counter(
            "netsentinel_prediction_errors_total",
            "Total prediction errors",
            registry=self.registry,
        )
        self.latency_histogram = Histogram(
            "netsentinel_prediction_latency_ms",
            "Prediction latency in milliseconds",
            registry=self.registry,
        )
        self.drift_gauge = Gauge("netsentinel_drift_score", "Latest drift score", registry=self.registry)

    def record_prediction(self, latency_ms: float, confidence: float) -> None:
        self.total_predictions += 1
        self.prediction_counter.inc()
        self.latencies.append(float(latency_ms))
        self.confidences.append(float(confidence))
        self.events.append(time())
        self.latency_histogram.observe(float(latency_ms))

    def record_error(self) -> None:
        self.total_errors += 1
        self.error_counter.inc()

    def update_drift(self, drift_score: float) -> None:
        self.drift_score = float(drift_score)
        self.drift_gauge.set(float(drift_score))

    def snapshot(self) -> MetricsSnapshot:
        latencies = np.asarray(self.latencies, dtype=float)
        confidences = np.asarray(self.confidences, dtype=float)
        now = time()
        recent_events = [event for event in self.events if now - event <= 60]
        total = max(self.total_predictions + self.total_errors, 1)
        return MetricsSnapshot(
            total_predictions=self.total_predictions,
            error_rate=round(self.total_errors / total, 4),
            throughput_rps=round(len(recent_events) / 60, 4),
            latency_p50_ms=round(float(np.percentile(latencies, 50)), 4) if len(latencies) else 0.0,
            latency_p95_ms=round(float(np.percentile(latencies, 95)), 4) if len(latencies) else 0.0,
            latency_p99_ms=round(float(np.percentile(latencies, 99)), 4) if len(latencies) else 0.0,
            average_confidence=round(float(confidences.mean()), 4) if len(confidences) else 0.0,
            drift_score=round(self.drift_score, 4),
        )

    def prometheus(self) -> bytes:
        return generate_latest(self.registry)
