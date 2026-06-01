"""Feature engineering for network-flow records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "duration",
    "protocol_code",
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
    "bytes_per_packet",
    "packet_ratio",
    "byte_ratio",
    "is_well_known_port",
    "is_high_risk_port",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_business_hours",
]

LABEL_ALIASES = {"BENIGN": 0, "NORMAL": 0, "MALICIOUS": 1, "ATTACK": 1}
PROTOCOL_CODES = {"ICMP": 1, "TCP": 6, "UDP": 17}
HIGH_RISK_PORTS = {21, 22, 23, 3389, 4444, 5900}

ALIASES = {
    "timestamp": "timestamp",
    "flowid": "flow_id",
    "flow_id": "flow_id",
    "flowduration": "duration",
    "duration": "duration",
    "protocol": "protocol",
    "sourceport": "src_port",
    "srcport": "src_port",
    "src_port": "src_port",
    "destinationport": "dst_port",
    "dstport": "dst_port",
    "dst_port": "dst_port",
    "totalfwdpackets": "src_packets",
    "totfwdpkts": "src_packets",
    "src_packets": "src_packets",
    "totalbackwardpackets": "dst_packets",
    "totbwdpkts": "dst_packets",
    "dst_packets": "dst_packets",
    "totallengthoffwdpackets": "src_bytes",
    "totlenfwdpkts": "src_bytes",
    "src_bytes": "src_bytes",
    "totallengthofbwdpackets": "dst_bytes",
    "totlenbwdpkts": "dst_bytes",
    "dst_bytes": "dst_bytes",
    "flowbytes/s": "flow_bytes_per_sec",
    "flowbyts/s": "flow_bytes_per_sec",
    "flow_bytes_per_sec": "flow_bytes_per_sec",
    "flowpackets/s": "flow_packets_per_sec",
    "flowpkts/s": "flow_packets_per_sec",
    "flow_packets_per_sec": "flow_packets_per_sec",
    "avgpacket_size": "packet_size_mean",
    "packetlengthmean": "packet_size_mean",
    "pktlenmean": "packet_size_mean",
    "packet_size_mean": "packet_size_mean",
    "packetlengthstd": "packet_size_std",
    "pktlenstd": "packet_size_std",
    "packet_size_std": "packet_size_std",
    "tcp_flags": "tcp_flags",
    "finflagcnt": "fin_flag_count",
    "synflagcnt": "syn_flag_count",
    "rstflagcnt": "rst_flag_count",
    "pshflagcnt": "psh_flag_count",
    "ackflagcnt": "ack_flag_count",
    "urgflagcnt": "urg_flag_count",
    "cweflagcount": "cwe_flag_count",
    "eceflagcnt": "ece_flag_count",
    "label": "label",
    "attack_type": "attack_type",
}


@dataclass(frozen=True)
class FeatureBuildResult:
    features: pd.DataFrame
    labels: pd.Series | None


class FeatureEngineeringService:
    """Create consistent model features for training and inference."""

    def __init__(self, version: str = "1.0") -> None:
        self.version = version

    def build_features(self, df: pd.DataFrame) -> FeatureBuildResult:
        """Return numeric ML features and optional binary labels."""

        normalized = self.normalize_columns(df)
        features = pd.DataFrame(index=normalized.index)

        duration = self._numeric(normalized, "duration", default=1.0).clip(lower=0.01)
        src_packets = self._numeric(normalized, "src_packets", default=1).clip(lower=0)
        dst_packets = self._numeric(normalized, "dst_packets", default=1).clip(lower=0)
        src_bytes = self._numeric(normalized, "src_bytes", default=0).clip(lower=0)
        dst_bytes = self._numeric(normalized, "dst_bytes", default=0).clip(lower=0)
        dst_port = self._numeric(normalized, "dst_port", default=0).clip(lower=0, upper=65535)
        src_port = self._numeric(normalized, "src_port", default=0).clip(lower=0, upper=65535)
        tcp_flags = self._tcp_flags(normalized).clip(lower=0)

        total_packets = (src_packets + dst_packets).replace(0, 1)
        total_bytes = src_bytes + dst_bytes

        features["duration"] = duration
        features["protocol_code"] = self._protocol_code(normalized)
        features["src_port"] = src_port
        features["dst_port"] = dst_port
        features["src_bytes"] = src_bytes
        features["dst_bytes"] = dst_bytes
        features["src_packets"] = src_packets
        features["dst_packets"] = dst_packets
        features["tcp_flags"] = tcp_flags
        features["flow_bytes_per_sec"] = self._numeric(
            normalized,
            "flow_bytes_per_sec",
            default=np.nan,
        ).fillna(total_bytes / duration)
        features["flow_packets_per_sec"] = self._numeric(
            normalized,
            "flow_packets_per_sec",
            default=np.nan,
        ).fillna(total_packets / duration)
        features["packet_size_mean"] = self._numeric(
            normalized,
            "packet_size_mean",
            default=np.nan,
        ).fillna(total_bytes / total_packets)
        features["packet_size_std"] = self._numeric(
            normalized,
            "packet_size_std",
            default=np.nan,
        ).fillna(features["packet_size_mean"] * 0.10)
        features["bytes_per_packet"] = total_bytes / total_packets
        features["packet_ratio"] = (src_packets + 1) / (dst_packets + 1)
        features["byte_ratio"] = (src_bytes + 1) / (dst_bytes + 1)
        features["is_well_known_port"] = (dst_port < 1024).astype(int)
        features["is_high_risk_port"] = dst_port.astype(int).isin(HIGH_RISK_PORTS).astype(int)

        temporal = self._temporal_features(normalized)
        features = pd.concat([features, temporal], axis=1)
        features = features.reindex(columns=FEATURE_COLUMNS).replace([np.inf, -np.inf], np.nan).fillna(0.0)

        labels = self.extract_labels(normalized)
        return FeatureBuildResult(features=features.astype(float), labels=labels)

    def normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize common CICIDS and demo column names to internal names."""

        renamed: dict[str, str] = {}
        for column in df.columns:
            key = re.sub(r"[^a-zA-Z0-9_/]+", "", str(column)).lower()
            if key in ALIASES:
                renamed[column] = ALIASES[key]
            else:
                key_with_underscore = str(column).strip().lower().replace(" ", "_")
                renamed[column] = ALIASES.get(key_with_underscore, key_with_underscore)
        return df.rename(columns=renamed)

    def extract_labels(self, df: pd.DataFrame) -> pd.Series | None:
        """Extract binary labels when a label column exists."""

        if "label" not in df.columns:
            return None
        series = df["label"]
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().all():
            return numeric.astype(int).clip(lower=0, upper=1)
        normalized = series.astype(str).str.upper().map(lambda value: LABEL_ALIASES.get(value, 1))
        return normalized.astype(int)

    def save_feature_store(self, features: pd.DataFrame, path: str | Path) -> Path:
        """Persist features with a lightweight metadata sidecar."""

        target = Path(path)
        target.mkdir(parents=True, exist_ok=True)
        feature_path = target / f"features_v{self.version}.csv"
        metadata_path = target / f"features_v{self.version}.json"
        features.to_csv(feature_path, index=False)
        metadata_path.write_text(
            pd.Series(
                {
                    "version": self.version,
                    "rows": len(features),
                    "columns": ",".join(features.columns),
                }
            ).to_json(indent=2),
            encoding="utf-8",
        )
        return feature_path

    def _numeric(self, df: pd.DataFrame, column: str, default: float) -> pd.Series:
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce")
        return pd.Series(default, index=df.index, dtype=float)

    def _protocol_code(self, df: pd.DataFrame) -> pd.Series:
        if "protocol" not in df.columns:
            return pd.Series(PROTOCOL_CODES["TCP"], index=df.index, dtype=float)
        raw = df["protocol"]
        numeric = pd.to_numeric(raw, errors="coerce")
        mapped = raw.astype(str).str.upper().map(PROTOCOL_CODES)
        return numeric.fillna(mapped).fillna(0).astype(float)

    def _tcp_flags(self, df: pd.DataFrame) -> pd.Series:
        if "tcp_flags" in df.columns:
            return self._numeric(df, "tcp_flags", default=0)
        flag_columns = [
            "fin_flag_count",
            "syn_flag_count",
            "rst_flag_count",
            "psh_flag_count",
            "ack_flag_count",
            "urg_flag_count",
            "cwe_flag_count",
            "ece_flag_count",
        ]
        available = [column for column in flag_columns if column in df.columns]
        if not available:
            return pd.Series(0, index=df.index, dtype=float)
        flags = pd.DataFrame({column: self._numeric(df, column, default=0) for column in available})
        return flags.sum(axis=1)

    def _temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        temporal = pd.DataFrame(index=df.index)
        if "timestamp" in df.columns:
            parsed = pd.to_datetime(df["timestamp"], errors="coerce")
            if parsed.isna().mean() > 0.5:
                parsed = pd.to_datetime(df["timestamp"], errors="coerce", dayfirst=True)
            temporal["hour"] = parsed.dt.hour.fillna(0).astype(int)
            temporal["day_of_week"] = parsed.dt.dayofweek.fillna(0).astype(int)
        else:
            temporal["hour"] = self._numeric(df, "hour", 0).astype(int).clip(0, 23)
            temporal["day_of_week"] = self._numeric(df, "day_of_week", 0).astype(int).clip(0, 6)
        temporal["is_weekend"] = (temporal["day_of_week"] >= 5).astype(int)
        temporal["is_business_hours"] = temporal["hour"].between(9, 17).astype(int)
        return temporal
