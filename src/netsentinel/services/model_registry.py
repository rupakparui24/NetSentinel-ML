"""Lightweight local model registry."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib


@dataclass
class ModelRecord:
    model_id: str
    name: str
    stage: str
    artifact_path: str
    created_at: str
    metrics: dict[str, float]
    feature_columns: list[str]
    params: dict[str, Any] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class ModelRegistry:
    """Register, load, promote, and archive model artifacts."""

    def __init__(self, registry_dir: str | Path = "models/registry") -> None:
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.registry_path = self.registry_dir / "registry.json"
        if not self.registry_path.exists():
            self._save([])

    def register_model(
        self,
        name: str,
        model: Any,
        metrics: dict[str, float],
        feature_columns: list[str],
        params: dict[str, Any] | None = None,
        stage: str = "staging",
        tags: dict[str, str] | None = None,
    ) -> ModelRecord:
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        model_id = f"{name}-{timestamp}"
        artifact_path = self.registry_dir / f"{model_id}.joblib"
        joblib.dump(model, artifact_path)

        record = ModelRecord(
            model_id=model_id,
            name=name,
            stage=stage,
            artifact_path=str(artifact_path),
            created_at=datetime.now(UTC).isoformat(),
            metrics={key: float(value) for key, value in metrics.items()},
            feature_columns=feature_columns,
            params=params or {},
            tags=tags or {},
        )

        records = self.list_records()
        if stage == "production":
            for existing in records:
                if existing.stage == "production":
                    existing.stage = "archived"
        records.append(record)
        self._save(records)
        return record

    def list_records(self) -> list[ModelRecord]:
        payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        return [ModelRecord(**item) for item in payload]

    def list_models(self) -> list[dict]:
        return [record.to_dict() for record in self.list_records()]

    def get_record(self, model_id: str) -> ModelRecord:
        for record in self.list_records():
            if record.model_id == model_id:
                return record
        raise KeyError(f"Model not found: {model_id}")

    def load_model(self, model_id: str | None = None) -> Any:
        record = self.get_active_record() if model_id is None else self.get_record(model_id)
        return joblib.load(record.artifact_path)

    def get_active_record(self) -> ModelRecord | None:
        production = [record for record in self.list_records() if record.stage == "production"]
        if production:
            return sorted(production, key=lambda item: item.created_at)[-1]
        staging = [record for record in self.list_records() if record.stage == "staging"]
        if staging:
            return sorted(staging, key=lambda item: item.created_at)[-1]
        return None

    def promote(self, model_id: str, stage: str = "production") -> ModelRecord:
        records = self.list_records()
        selected: ModelRecord | None = None
        for record in records:
            if stage == "production" and record.stage == "production":
                record.stage = "archived"
            if record.model_id == model_id:
                record.stage = stage
                selected = record
        if selected is None:
            raise KeyError(f"Model not found: {model_id}")
        self._save(records)
        return selected

    def archive(self, model_id: str) -> ModelRecord:
        return self.promote(model_id=model_id, stage="archived")

    def _save(self, records: list[ModelRecord]) -> None:
        self.registry_path.write_text(
            json.dumps([record.to_dict() for record in records], indent=2),
            encoding="utf-8",
        )
