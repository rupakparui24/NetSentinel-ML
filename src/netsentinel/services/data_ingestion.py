"""Batch and streaming ingestion utilities."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pandas as pd

from netsentinel.services.data_validation import DataValidationService


@dataclass
class RejectedRecord:
    row_index: int
    reason: str


@dataclass
class IngestionResult:
    source: str
    records_received: int
    records_accepted: int
    records_rejected: int
    quality_score: float
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    rejected_records: list[RejectedRecord] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["rejected_records"] = [asdict(record) for record in self.rejected_records]
        return payload


class DataIngestionService:
    """Read files or streams, validate them, and report ingestion metrics."""

    def __init__(self, validator: DataValidationService | None = None) -> None:
        self.validator = validator or DataValidationService()

    def ingest_batch(self, file_path: str | Path) -> tuple[pd.DataFrame, IngestionResult]:
        """Load a CSV, JSON, JSONL, or Parquet file and validate records."""

        path = Path(file_path)
        df = self._read_file(path)
        result = self._build_result(df, source=str(path))
        return df, result

    def ingest_stream(self, records: Iterable[dict]) -> tuple[pd.DataFrame, IngestionResult]:
        """Validate an iterable of records as a simulated stream batch."""

        df = pd.DataFrame(list(records))
        result = self._build_result(df, source="stream")
        return df, result

    def _read_file(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")

        suffix = path.suffix.lower()
        if suffix == ".csv":
            return pd.read_csv(path)
        if suffix == ".json":
            return pd.read_json(path)
        if suffix == ".jsonl":
            return pd.read_json(path, lines=True)
        if suffix == ".parquet":
            return pd.read_parquet(path)
        raise ValueError(f"Unsupported input format: {suffix}")

    def _build_result(self, df: pd.DataFrame, source: str) -> IngestionResult:
        validation = self.validator.validate_schema(df)
        rejected = self._find_rejected_records(df)
        accepted = max(len(df) - len(rejected), 0)
        return IngestionResult(
            source=source,
            records_received=int(len(df)),
            records_accepted=int(accepted),
            records_rejected=int(len(rejected)),
            quality_score=validation.quality_score,
            errors=validation.errors,
            warnings=validation.warnings,
            rejected_records=rejected[:25],
        )

    def _find_rejected_records(self, df: pd.DataFrame) -> list[RejectedRecord]:
        rejected: list[RejectedRecord] = []
        required = {name: rule for name, rule in self.validator.schema.items() if rule.required}
        for idx, row in df.iterrows():
            reasons: list[str] = []
            for column, rule in required.items():
                if column not in df.columns or pd.isna(row[column]):
                    reasons.append(f"missing {column}")
                    continue
                if rule.min_value is not None or rule.max_value is not None:
                    value = pd.to_numeric(pd.Series([row[column]]), errors="coerce").iloc[0]
                    if pd.isna(value):
                        reasons.append(f"invalid {column}")
                    elif rule.min_value is not None and value < rule.min_value:
                        reasons.append(f"{column} below range")
                    elif rule.max_value is not None and value > rule.max_value:
                        reasons.append(f"{column} above range")
            if reasons:
                rejected.append(RejectedRecord(row_index=int(idx), reason="; ".join(reasons)))
        return rejected
