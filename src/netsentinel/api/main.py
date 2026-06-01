"""FastAPI application for NetSentinel-ML."""

from __future__ import annotations

from collections import defaultdict, deque
from contextlib import asynccontextmanager
from time import time
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from netsentinel.api.schemas import (
    BatchPredictionRequest,
    DriftCheckRequest,
    ModelSwitchRequest,
    NetworkFlowRequest,
    RetrainRequest,
)
from netsentinel.core.config import get_settings
from netsentinel.core.logging import get_logger
from netsentinel.services.prediction_service import PredictionService

logger = get_logger(__name__)
settings = get_settings()
runtime: PredictionService | None = None


class SimpleRateLimiter:
    """Small in-memory rate limiter for local development and demos."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, request: Request) -> None:
        key = request.headers.get("x-api-key") or (request.client.host if request.client else "local")
        now = time()
        bucket = self.events[key]
        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()
        if len(bucket) >= self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded.")
        bucket.append(now)


limiter = SimpleRateLimiter(settings.rate_limit_per_minute)


def get_runtime() -> PredictionService:
    global runtime
    if runtime is None:
        runtime = PredictionService(settings)
    return runtime


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key.")


def rate_limit(request: Request) -> None:
    limiter.check(request)


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_runtime()
    logger.info("NetSentinel runtime initialized")
    yield


app = FastAPI(
    title="NetSentinel-ML",
    description="Network intrusion detection API with explainability, drift detection, and MLOps hooks.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict:
    return {"service": "NetSentinel-ML", "docs": "/docs", "health": f"{settings.api_prefix}/health"}


@app.get(f"{settings.api_prefix}/health")
def health(service: PredictionService = Depends(get_runtime)) -> dict:
    active = service.active_record.to_dict() if service.active_record else None
    return {"status": "ok", "environment": settings.environment, "active_model": active}


@app.post(f"{settings.api_prefix}/predict", dependencies=[Depends(rate_limit)])
def predict(
    payload: NetworkFlowRequest,
    service: PredictionService = Depends(get_runtime),
) -> dict:
    return service.predict_one(payload.model_dump(mode="json", exclude_none=True)).to_dict()


@app.post(f"{settings.api_prefix}/predict/batch", dependencies=[Depends(rate_limit)])
def predict_batch(
    payload: BatchPredictionRequest,
    service: PredictionService = Depends(get_runtime),
) -> dict:
    outcomes = [
        item.to_dict()
        for item in service.predict_batch([flow.model_dump(mode="json", exclude_none=True) for flow in payload.flows])
    ]
    return {"count": len(outcomes), "predictions": outcomes}


@app.get(f"{settings.api_prefix}/explain/{{prediction_id}}")
def explain(prediction_id: str, service: PredictionService = Depends(get_runtime)) -> dict:
    try:
        return service.explain(prediction_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/models")
def list_models(service: PredictionService = Depends(get_runtime)) -> dict:
    return {"models": service.model_catalog()}


@app.get(f"{settings.api_prefix}/models/{{model_id}}")
def get_model(model_id: str, service: PredictionService = Depends(get_runtime)) -> dict:
    try:
        return service.registry.get_record(model_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/models/switch", dependencies=[Depends(require_api_key)])
def switch_model(payload: ModelSwitchRequest, service: PredictionService = Depends(get_runtime)) -> dict:
    try:
        return service.switch_model(payload.model_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.delete(f"{settings.api_prefix}/models/{{model_id}}", dependencies=[Depends(require_api_key)])
def archive_model(model_id: str, service: PredictionService = Depends(get_runtime)) -> dict:
    try:
        return service.registry.archive(model_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get(f"{settings.api_prefix}/drift")
def drift_status(service: PredictionService = Depends(get_runtime)) -> dict:
    snapshot = service.metrics.snapshot()
    return {"drift_score": snapshot.drift_score, "threshold": settings.drift_threshold}


@app.post(f"{settings.api_prefix}/drift/check", dependencies=[Depends(require_api_key)])
def check_drift(payload: DriftCheckRequest, service: PredictionService = Depends(get_runtime)) -> dict:
    report = service.check_drift([flow.model_dump(mode="json", exclude_none=True) for flow in payload.flows])
    return report.to_dict()


@app.get(f"{settings.api_prefix}/performance")
def performance(service: PredictionService = Depends(get_runtime)) -> dict:
    return service.performance()


@app.get(f"{settings.api_prefix}/alerts")
def alerts(service: PredictionService = Depends(get_runtime)) -> dict:
    return {"alerts": service.alerts.list_alerts()}


@app.post(f"{settings.api_prefix}/alerts/{{alert_id}}/ack", dependencies=[Depends(require_api_key)])
def acknowledge_alert(alert_id: str, service: PredictionService = Depends(get_runtime)) -> dict:
    try:
        return service.alerts.acknowledge(alert_id).to_dict()
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post(f"{settings.api_prefix}/retrain", dependencies=[Depends(require_api_key)])
def retrain(payload: RetrainRequest, service: PredictionService = Depends(get_runtime)) -> dict:
    return service.retrain(rows=payload.rows, drift=payload.drift).to_dict()


@app.get("/metrics")
def prometheus_metrics(service: PredictionService = Depends(get_runtime)) -> Response:
    return Response(service.metrics.prometheus(), media_type="text/plain; version=0.0.4")
