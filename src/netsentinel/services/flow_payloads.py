"""Helpers for converting tabular network flows into API payloads."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from netsentinel.services.feature_engineering import FeatureEngineeringService

FLOW_PAYLOAD_COLUMNS = [
    "timestamp",
    "duration",
    "protocol",
    "src_port",
    "dst_port",
    "src_bytes",
    "dst_bytes",
    "src_packets",
    "dst_packets",
    "tcp_flags",
    "flow_bytes_per_sec",
    "flow_packets_per_sec",
    "packet_size_mean",
    "packet_size_std",
]

INTEGER_COLUMNS = {"src_port", "dst_port", "src_packets", "dst_packets", "tcp_flags"}
PROTOCOL_ALIASES = {
    "1": "ICMP",
    "1.0": "ICMP",
    "ICMP": "ICMP",
    "6": "TCP",
    "6.0": "TCP",
    "TCP": "TCP",
    "17": "UDP",
    "17.0": "UDP",
    "UDP": "UDP",
}


def normalize_flow_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize common CSV column names to fields accepted by the prediction API."""

    normalized = FeatureEngineeringService().normalize_columns(df)
    return normalized.replace([np.inf, -np.inf, "Infinity", "inf", "-inf", ""], np.nan)


def dataframe_to_flow_payloads(df: pd.DataFrame, limit: int | None = None) -> list[dict]:
    """Convert a dataframe of network flows into JSON-safe prediction payloads."""

    normalized = normalize_flow_dataframe(df)
    if limit is not None:
        normalized = normalized.head(limit)

    payloads: list[dict] = []
    for _, row in normalized.iterrows():
        payload: dict[str, Any] = {}
        for column in FLOW_PAYLOAD_COLUMNS:
            if column not in normalized.columns:
                continue
            value = _coerce_value(column, row[column])
            if value is not None:
                payload[column] = value
        payloads.append(payload)
    return payloads


def _coerce_value(column: str, value: Any) -> Any:
    if _is_missing(value):
        return None

    if column == "protocol":
        protocol = PROTOCOL_ALIASES.get(str(value).strip().upper())
        return protocol or str(value).strip().upper()

    if column == "timestamp":
        return _coerce_timestamp(value)

    if column in INTEGER_COLUMNS:
        number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        if pd.isna(number):
            return None
        return int(number)

    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(number):
        return None
    return float(number)


def _coerce_timestamp(value: Any) -> str | None:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, datetime | date):
        return value.isoformat()

    parsed = pd.to_datetime(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(parsed):
        return None
    return parsed.isoformat()


def _is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
