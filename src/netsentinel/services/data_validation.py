"""Data quality validation for network-flow datasets."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

import pandas as pd

ColumnType = Literal["numeric", "integer", "categorical", "datetime"]


@dataclass(frozen=True)
class ColumnRule:
    """Validation rule for one dataframe column."""

    dtype: ColumnType
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: tuple[str, ...] | None = None


@dataclass
class ValidationResult:
    """Data validation output."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    quality_score: float = 100.0
    missing_values: dict[str, int] = field(default_factory=dict)
    outlier_counts: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


NETWORK_FLOW_SCHEMA: dict[str, ColumnRule] = {
    "timestamp": ColumnRule("datetime", required=False),
    "duration": ColumnRule("numeric", min_value=0),
    "protocol": ColumnRule("categorical", allowed_values=("TCP", "UDP", "ICMP", "6", "17", "1")),
    "src_port": ColumnRule("integer", min_value=0, max_value=65535),
    "dst_port": ColumnRule("integer", min_value=0, max_value=65535),
    "src_bytes": ColumnRule("numeric", min_value=0),
    "dst_bytes": ColumnRule("numeric", min_value=0),
    "src_packets": ColumnRule("integer", min_value=0),
    "dst_packets": ColumnRule("integer", min_value=0),
    "tcp_flags": ColumnRule("integer", min_value=0),
    "flow_bytes_per_sec": ColumnRule("numeric", min_value=0, required=False),
    "flow_packets_per_sec": ColumnRule("numeric", min_value=0, required=False),
    "packet_size_mean": ColumnRule("numeric", min_value=0, required=False),
    "packet_size_std": ColumnRule("numeric", min_value=0, required=False),
    "label": ColumnRule("integer", min_value=0, max_value=1, required=False),
}


class DataValidationService:
    """Validate schema, ranges, missing values, and outliers."""

    def __init__(self, schema: dict[str, ColumnRule] | None = None) -> None:
        self.schema = schema or NETWORK_FLOW_SCHEMA

    def validate_schema(self, df: pd.DataFrame) -> ValidationResult:
        """Validate a dataframe against the configured network-flow schema."""

        errors: list[str] = []
        warnings: list[str] = []
        if df.empty:
            errors.append("Dataset is empty.")

        required_columns = {name for name, rule in self.schema.items() if rule.required}
        missing_columns = sorted(required_columns - set(df.columns))
        if missing_columns:
            errors.append(f"Missing required columns: {', '.join(missing_columns)}")

        for column, rule in self.schema.items():
            if column not in df.columns:
                continue
            errors.extend(self._validate_column(column, df[column], rule))

        missing_values = self.check_missing_values(df)
        if missing_values:
            warnings.append(f"Missing values detected in {len(missing_values)} columns.")

        outlier_counts = self.detect_outliers(df)
        noisy_outliers = {key: value for key, value in outlier_counts.items() if value > 0}
        if noisy_outliers:
            warnings.append(f"IQR outliers detected in {len(noisy_outliers)} numeric columns.")

        quality_score = self._calculate_quality_score(df, errors, warnings, missing_values, outlier_counts)
        return ValidationResult(
            is_valid=not errors,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
            missing_values=missing_values,
            outlier_counts=outlier_counts,
        )

    def check_missing_values(self, df: pd.DataFrame) -> dict[str, int]:
        """Return missing-value counts by column."""

        if df.empty:
            return {}
        missing = df.isna().sum()
        return {column: int(count) for column, count in missing.items() if count > 0}

    def detect_outliers(self, df: pd.DataFrame) -> dict[str, int]:
        """Detect outliers in numeric columns using the IQR method."""

        numeric = df.select_dtypes(include=["number"])
        outliers: dict[str, int] = {}
        for column in numeric.columns:
            series = numeric[column].dropna()
            if series.empty or series.nunique() <= 1:
                outliers[column] = 0
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                outliers[column] = 0
                continue
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            outliers[column] = int(((series < lower) | (series > upper)).sum())
        return outliers

    def generate_quality_report(self, df: pd.DataFrame) -> dict:
        """Build a serializable data-quality report."""

        result = self.validate_schema(df)
        return {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "quality": result.to_dict(),
            "dtypes": {column: str(dtype) for column, dtype in df.dtypes.items()},
        }

    def _validate_column(self, column: str, series: pd.Series, rule: ColumnRule) -> list[str]:
        errors: list[str] = []
        if rule.dtype in {"numeric", "integer"}:
            coerced = pd.to_numeric(series, errors="coerce")
            invalid_type_count = int((series.notna() & coerced.isna()).sum())
            if invalid_type_count:
                errors.append(f"{column} has {invalid_type_count} non-numeric values.")
            if rule.dtype == "integer":
                non_integer = coerced.dropna() % 1 != 0
                if bool(non_integer.any()):
                    errors.append(f"{column} contains non-integer values.")
            if rule.min_value is not None and bool((coerced.dropna() < rule.min_value).any()):
                errors.append(f"{column} contains values below {rule.min_value}.")
            if rule.max_value is not None and bool((coerced.dropna() > rule.max_value).any()):
                errors.append(f"{column} contains values above {rule.max_value}.")

        elif rule.dtype == "categorical" and rule.allowed_values is not None:
            allowed = {value.upper() for value in rule.allowed_values}
            normalized = series.dropna().astype(str).str.upper()
            invalid = normalized[~normalized.isin(allowed)]
            if not invalid.empty:
                examples = ", ".join(sorted(invalid.unique()[:5]))
                errors.append(f"{column} has unsupported values: {examples}.")

        elif rule.dtype == "datetime":
            parsed = pd.to_datetime(series, errors="coerce")
            invalid_datetime = int((series.notna() & parsed.isna()).sum())
            if invalid_datetime:
                errors.append(f"{column} has {invalid_datetime} invalid datetimes.")
        return errors

    def _calculate_quality_score(
        self,
        df: pd.DataFrame,
        errors: list[str],
        warnings: list[str],
        missing_values: dict[str, int],
        outlier_counts: dict[str, int],
    ) -> float:
        if df.empty:
            return 0.0
        total_cells = max(int(df.shape[0] * df.shape[1]), 1)
        missing_penalty = min(sum(missing_values.values()) / total_cells * 100, 35)
        outlier_penalty = min(sum(outlier_counts.values()) / max(len(df), 1) * 2, 20)
        error_penalty = min(len(errors) * 12, 60)
        warning_penalty = min(len(warnings) * 4, 15)
        return round(max(0.0, 100 - missing_penalty - outlier_penalty - error_penalty - warning_penalty), 2)
