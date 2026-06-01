"""API request models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NetworkFlowRequest(BaseModel):
    """Network flow fields accepted by the prediction API."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": "2026-05-28T10:00:00",
                "duration": 0.18,
                "protocol": "TCP",
                "src_port": 49152,
                "dst_port": 22,
                "src_bytes": 8420,
                "dst_bytes": 920,
                "src_packets": 52,
                "dst_packets": 9,
                "tcp_flags": 12,
            }
        }
    )

    timestamp: datetime | None = None
    duration: float = Field(default=1.0, ge=0)
    protocol: str = Field(default="TCP")
    src_port: int = Field(default=49152, ge=0, le=65535)
    dst_port: int = Field(default=443, ge=0, le=65535)
    src_bytes: float = Field(default=0, ge=0)
    dst_bytes: float = Field(default=0, ge=0)
    src_packets: int = Field(default=1, ge=0)
    dst_packets: int = Field(default=1, ge=0)
    tcp_flags: int = Field(default=0, ge=0)
    flow_bytes_per_sec: float | None = Field(default=None, ge=0)
    flow_packets_per_sec: float | None = Field(default=None, ge=0)
    packet_size_mean: float | None = Field(default=None, ge=0)
    packet_size_std: float | None = Field(default=None, ge=0)

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"TCP", "UDP", "ICMP", "1", "6", "17"}:
            raise ValueError("protocol must be TCP, UDP, ICMP, 1, 6, or 17")
        return normalized


class BatchPredictionRequest(BaseModel):
    flows: list[NetworkFlowRequest] = Field(min_length=1, max_length=500)


class DriftCheckRequest(BaseModel):
    flows: list[NetworkFlowRequest] = Field(min_length=20, max_length=5000)


class ModelSwitchRequest(BaseModel):
    model_id: str


class RetrainRequest(BaseModel):
    rows: int = Field(default=900, ge=200, le=10000)
    drift: bool = False
