"""Alert generation and acknowledgement."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from uuid import uuid4

from netsentinel.services.monitoring import MetricsSnapshot


@dataclass
class Alert:
    alert_id: str
    severity: str
    title: str
    message: str
    created_at: str
    acknowledged: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


class AlertingService:
    """Create alerts for drift, latency, and error-rate thresholds."""

    def __init__(self) -> None:
        self.alerts: list[Alert] = []

    def evaluate(self, metrics: MetricsSnapshot, drift_threshold: float = 0.3) -> list[Alert]:
        generated: list[Alert] = []
        if metrics.drift_score > drift_threshold:
            generated.append(
                self._create(
                    "critical",
                    "Data drift detected",
                    f"Latest drift score is {metrics.drift_score}, above threshold {drift_threshold}.",
                )
            )
        if metrics.latency_p95_ms > 300:
            generated.append(
                self._create(
                    "warning",
                    "Prediction latency spike",
                    f"P95 latency is {metrics.latency_p95_ms} ms.",
                )
            )
        if metrics.error_rate > 0.05:
            generated.append(
                self._create(
                    "critical",
                    "Prediction error rate elevated",
                    f"Error rate is {metrics.error_rate:.2%}.",
                )
            )
        self.alerts.extend(generated)
        return generated

    def list_alerts(self) -> list[dict]:
        return [alert.to_dict() for alert in self.alerts]

    def acknowledge(self, alert_id: str) -> Alert:
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return alert
        raise KeyError(f"Alert not found: {alert_id}")

    def _create(self, severity: str, title: str, message: str) -> Alert:
        return Alert(
            alert_id=str(uuid4()),
            severity=severity,
            title=title,
            message=message,
            created_at=datetime.now(UTC).isoformat(),
        )
