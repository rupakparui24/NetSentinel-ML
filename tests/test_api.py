import importlib

from fastapi.testclient import TestClient

from netsentinel.core.config import get_settings


def test_prediction_api_bootstraps_and_predicts(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NETSENTINEL_MODEL_REGISTRY_DIR", str(tmp_path / "registry"))
    monkeypatch.setenv("NETSENTINEL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("NETSENTINEL_DEMO_TRAINING_ROWS", "300")
    get_settings.cache_clear()

    import netsentinel.api.main as api_main

    importlib.reload(api_main)

    with TestClient(api_main.app) as client:
        health = client.get("/api/v1/health")
        response = client.post(
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

    assert health.status_code == 200
    assert response.status_code == 200
    payload = response.json()
    assert payload["prediction"] in {"benign", "malicious"}
    assert payload["explanation"]
