"""Synthetic network-flow data for demos, tests, and local training."""

from __future__ import annotations

import numpy as np
import pandas as pd

PROTOCOLS = np.array(["TCP", "UDP", "ICMP"])
COMMON_PORTS = np.array([22, 53, 80, 123, 443, 8080])
HIGH_RISK_PORTS = np.array([21, 22, 23, 3389, 4444, 5900])


def generate_synthetic_network_flows(
    n_rows: int = 1000,
    attack_rate: float = 0.22,
    seed: int = 42,
    drift: bool = False,
) -> pd.DataFrame:
    """Generate realistic-enough flow records without external datasets.

    The distribution is intentionally learnable but not perfectly separable.
    It lets the project run on a laptop while leaving the CICIDS2017 ingestion
    path ready for a real dataset.
    """

    rng = np.random.default_rng(seed)
    is_attack = rng.random(n_rows) < attack_rate

    protocol = rng.choice(PROTOCOLS, size=n_rows, p=[0.72, 0.22, 0.06])
    dst_port = rng.choice(COMMON_PORTS, size=n_rows, p=[0.08, 0.16, 0.28, 0.06, 0.36, 0.06])
    src_port = rng.integers(1024, 65535, size=n_rows)
    duration = rng.gamma(shape=2.4, scale=0.45, size=n_rows)
    src_packets = rng.poisson(lam=18, size=n_rows) + 1
    dst_packets = rng.poisson(lam=16, size=n_rows) + 1
    src_bytes = rng.lognormal(mean=8.0, sigma=0.75, size=n_rows)
    dst_bytes = rng.lognormal(mean=8.2, sigma=0.72, size=n_rows)
    tcp_flags = rng.poisson(lam=2, size=n_rows)

    attack_types = np.full(n_rows, "BENIGN", dtype=object)
    attack_indices = np.where(is_attack)[0]
    attack_kind = rng.choice(
        ["DDoS", "PortScan", "BruteForce", "Exfiltration"],
        size=len(attack_indices),
        p=[0.36, 0.28, 0.22, 0.14],
    )

    for kind in ["DDoS", "PortScan", "BruteForce", "Exfiltration"]:
        idx = attack_indices[attack_kind == kind]
        if len(idx) == 0:
            continue
        attack_types[idx] = kind

        if kind == "DDoS":
            duration[idx] = rng.gamma(shape=1.0, scale=0.12, size=len(idx)) + 0.01
            src_packets[idx] = rng.poisson(lam=260 if not drift else 340, size=len(idx)) + 10
            dst_packets[idx] = rng.poisson(lam=30, size=len(idx)) + 1
            src_bytes[idx] = rng.lognormal(mean=11.2 if not drift else 11.6, sigma=0.55, size=len(idx))
            dst_bytes[idx] = rng.lognormal(mean=7.4, sigma=0.55, size=len(idx))
            dst_port[idx] = rng.choice([80, 443, 8080], size=len(idx))
            tcp_flags[idx] = rng.poisson(lam=9, size=len(idx))

        elif kind == "PortScan":
            duration[idx] = rng.gamma(shape=1.1, scale=0.08, size=len(idx)) + 0.01
            src_packets[idx] = rng.poisson(lam=5, size=len(idx)) + 1
            dst_packets[idx] = rng.poisson(lam=1, size=len(idx)) + 1
            src_bytes[idx] = rng.lognormal(mean=5.8, sigma=0.45, size=len(idx))
            dst_bytes[idx] = rng.lognormal(mean=4.8, sigma=0.5, size=len(idx))
            dst_port[idx] = rng.integers(1, 65535, size=len(idx))
            tcp_flags[idx] = rng.poisson(lam=7, size=len(idx))

        elif kind == "BruteForce":
            duration[idx] = rng.gamma(shape=2.0, scale=0.2, size=len(idx)) + 0.05
            src_packets[idx] = rng.poisson(lam=48, size=len(idx)) + 3
            dst_packets[idx] = rng.poisson(lam=12, size=len(idx)) + 1
            src_bytes[idx] = rng.lognormal(mean=8.6, sigma=0.55, size=len(idx))
            dst_bytes[idx] = rng.lognormal(mean=6.8, sigma=0.5, size=len(idx))
            dst_port[idx] = rng.choice(HIGH_RISK_PORTS, size=len(idx))
            tcp_flags[idx] = rng.poisson(lam=10, size=len(idx))

        else:
            duration[idx] = rng.gamma(shape=4.0, scale=0.7, size=len(idx)) + 0.1
            src_packets[idx] = rng.poisson(lam=95, size=len(idx)) + 8
            dst_packets[idx] = rng.poisson(lam=22, size=len(idx)) + 1
            src_bytes[idx] = rng.lognormal(mean=10.4 if not drift else 10.9, sigma=0.7, size=len(idx))
            dst_bytes[idx] = rng.lognormal(mean=7.1, sigma=0.6, size=len(idx))
            dst_port[idx] = rng.choice([443, 8080, 4444], size=len(idx), p=[0.58, 0.22, 0.20])
            tcp_flags[idx] = rng.poisson(lam=5, size=len(idx))

    if drift:
        protocol = rng.choice(PROTOCOLS, size=n_rows, p=[0.55, 0.36, 0.09])
        duration *= rng.normal(loc=1.18, scale=0.08, size=n_rows)
        src_bytes *= rng.normal(loc=1.22, scale=0.12, size=n_rows)

    total_packets = np.maximum(src_packets + dst_packets, 1)
    total_bytes = src_bytes + dst_bytes
    safe_duration = np.maximum(duration, 0.01)

    start = pd.Timestamp("2026-05-01T00:00:00")
    timestamps = start + pd.to_timedelta(rng.integers(0, 60 * 60 * 24 * 14, n_rows), unit="s")

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "duration": duration.round(4),
            "protocol": protocol,
            "src_port": src_port.astype(int),
            "dst_port": dst_port.astype(int),
            "src_bytes": src_bytes.round(2),
            "dst_bytes": dst_bytes.round(2),
            "src_packets": src_packets.astype(int),
            "dst_packets": dst_packets.astype(int),
            "tcp_flags": tcp_flags.astype(int),
            "flow_bytes_per_sec": (total_bytes / safe_duration).round(2),
            "flow_packets_per_sec": (total_packets / safe_duration).round(2),
            "packet_size_mean": (total_bytes / total_packets).round(2),
            "packet_size_std": rng.gamma(shape=2.0, scale=22.0, size=n_rows).round(2),
            "attack_type": attack_types,
            "label": is_attack.astype(int),
        }
    )
    return df
