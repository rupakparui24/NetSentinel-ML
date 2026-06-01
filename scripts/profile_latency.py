"""Profile local prediction latency using the in-process API."""

from __future__ import annotations

import statistics
import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from fastapi.testclient import TestClient

from netsentinel.api.main import app
from netsentinel.services.sample_data import generate_synthetic_network_flows


def main() -> None:
    sample = generate_synthetic_network_flows(n_rows=150, seed=77).drop(columns=["label", "attack_type"])
    latencies: list[float] = []
    with TestClient(app) as client:
        for payload in sample.to_dict(orient="records"):
            start = perf_counter()
            response = client.post("/api/v1/predict", json=payload)
            response.raise_for_status()
            latencies.append((perf_counter() - start) * 1000)
    p50 = statistics.median(latencies)
    p95 = sorted(latencies)[int(len(latencies) * 0.95) - 1]
    print(f"count={len(latencies)} p50={p50:.2f}ms p95={p95:.2f}ms")


if __name__ == "__main__":
    main()
