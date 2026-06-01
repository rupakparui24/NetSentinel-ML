"""Smoke-test the FastAPI app in process."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fastapi.testclient import TestClient

from netsentinel.api.main import app


def main() -> None:
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        health.raise_for_status()
        prediction = client.post(
            "/api/v1/predict",
            json={
                "duration": 0.18,
                "protocol": "TCP",
                "src_port": 49152,
                "dst_port": 22,
                "src_bytes": 8420,
                "dst_bytes": 920,
                "src_packets": 52,
                "dst_packets": 9,
                "tcp_flags": 12,
            },
        )
        prediction.raise_for_status()
        performance = client.get("/api/v1/performance")
        performance.raise_for_status()
    print(
        json.dumps(
            {
                "health": health.json()["status"],
                "prediction": prediction.json()["prediction"],
                "confidence": prediction.json()["confidence"],
                "total_predictions": performance.json()["metrics"]["total_predictions"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
