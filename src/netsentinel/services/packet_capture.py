"""Packet capture helpers backed by tshark."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from io import StringIO
from typing import Any

import pandas as pd

TSHARK_FIELDS = [
    "frame.time_epoch",
    "ip.src",
    "ip.dst",
    "ip.proto",
    "frame.len",
    "tcp.srcport",
    "tcp.dstport",
    "udp.srcport",
    "udp.dstport",
    "tcp.flags",
]

DEFAULT_CAPTURE_FILTER = "tcp or udp or icmp"
PROTOCOL_NAMES = {1: "ICMP", 6: "TCP", 17: "UDP"}


def list_tshark_interfaces(tshark_path: str) -> list[str]:
    """Return interfaces as tshark displays them, for example `4. ... (Wi-Fi)`."""

    try:
        completed = subprocess.run(
            [tshark_path, "-D"],
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("tshark was not found. Install Wireshark/tshark or set the tshark path.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("tshark interface listing timed out.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "unknown tshark error"
        raise RuntimeError(f"tshark interface listing failed: {stderr}")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def interface_value(interface_line: str) -> str:
    """Extract the numeric interface value from a tshark interface list row."""

    if "." not in interface_line:
        return interface_line.strip()
    prefix = interface_line.split(".", 1)[0].strip()
    return prefix or interface_line.strip()


def build_tshark_command(
    tshark_path: str,
    interface: str,
    window_seconds: int,
    packet_limit: int | None = None,
    capture_filter: str = DEFAULT_CAPTURE_FILTER,
) -> list[str]:
    command = [tshark_path, "-i", str(interface)]
    if window_seconds > 0:
        command.extend(["-a", f"duration:{window_seconds}"])
    if packet_limit:
        command.extend(["-c", str(packet_limit)])
    if capture_filter:
        command.extend(["-f", capture_filter])

    command.extend(["-T", "fields"])
    for option in ["header=y", "separator=,", "quote=d", "occurrence=f"]:
        command.extend(["-E", option])
    for field in TSHARK_FIELDS:
        command.extend(["-e", field])
    return command


def run_tshark_capture(
    tshark_path: str,
    interface: str,
    window_seconds: int = 10,
    packet_limit: int | None = None,
    capture_filter: str = DEFAULT_CAPTURE_FILTER,
) -> pd.DataFrame:
    """Capture packets and return the tshark field output as a dataframe."""

    command = build_tshark_command(
        tshark_path=tshark_path,
        interface=interface,
        window_seconds=window_seconds,
        packet_limit=packet_limit,
        capture_filter=capture_filter,
    )
    timeout = window_seconds + 30 if window_seconds > 0 else None
    try:
        completed = subprocess.run(command, capture_output=True, check=False, text=True, timeout=timeout)
    except FileNotFoundError as exc:
        raise RuntimeError("tshark was not found. Install Wireshark/tshark or set the tshark path.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("tshark capture timed out before producing results.") from exc

    if completed.returncode != 0:
        stderr = completed.stderr.strip() or "unknown tshark error"
        raise RuntimeError(f"tshark failed: {stderr}")
    return read_tshark_csv(completed.stdout)


def read_tshark_csv(text: str) -> pd.DataFrame:
    if not text.strip():
        return pd.DataFrame(columns=TSHARK_FIELDS)
    return pd.read_csv(StringIO(text))


def packets_to_flow_records(packets: pd.DataFrame) -> list[dict]:
    """Aggregate packet rows into bidirectional flow records."""

    flows: dict[tuple, dict] = {}
    for _, row in packets.iterrows():
        src_ip = _string(row.get("ip.src"))
        dst_ip = _string(row.get("ip.dst"))
        if not src_ip or not dst_ip:
            continue

        protocol = _protocol_name(row)
        if protocol is None:
            continue
        src_port = _first_port(row, ["tcp.srcport", "udp.srcport"])
        dst_port = _first_port(row, ["tcp.dstport", "udp.dstport"])
        timestamp = _parse_float(row.get("frame.time_epoch"), default=0.0)
        packet_length = max(_parse_float(row.get("frame.len"), default=0.0), 0.0)
        flags = _parse_int(row.get("tcp.flags"), default=0)

        key = (protocol, src_ip, src_port, dst_ip, dst_port)
        reverse_key = (protocol, dst_ip, dst_port, src_ip, src_port)
        if key in flows:
            flow_key = key
            forward = True
        elif reverse_key in flows:
            flow_key = reverse_key
            forward = False
        else:
            flow_key = key
            forward = True
            flows[flow_key] = {
                "timestamp": _timestamp_iso(timestamp),
                "protocol": protocol,
                "src_ip": src_ip,
                "dst_ip": dst_ip,
                "src_port": src_port,
                "dst_port": dst_port,
                "src_bytes": 0.0,
                "dst_bytes": 0.0,
                "src_packets": 0,
                "dst_packets": 0,
                "tcp_flags": 0,
                "_first_seen": timestamp,
                "_last_seen": timestamp,
                "_packet_sizes": [],
            }

        flow = flows[flow_key]
        flow["_first_seen"] = min(flow["_first_seen"], timestamp)
        flow["_last_seen"] = max(flow["_last_seen"], timestamp)
        flow["_packet_sizes"].append(packet_length)
        flow["tcp_flags"] = int(flow["tcp_flags"]) | flags
        if forward:
            flow["src_bytes"] += packet_length
            flow["src_packets"] += 1
        else:
            flow["dst_bytes"] += packet_length
            flow["dst_packets"] += 1

    return [_finalize_flow(flow) for flow in flows.values()]


def packet_preview(packets: pd.DataFrame, rows: int = 100) -> pd.DataFrame:
    """Return a compact packet preview suitable for the dashboard."""

    if packets.empty:
        return packets
    preview = packets.head(rows).copy()
    if "ip.proto" in preview.columns:
        preview["protocol"] = preview["ip.proto"].map(lambda value: PROTOCOL_NAMES.get(_parse_int(value, 0), value))
    preview["src_port"] = preview.apply(lambda row: _first_port(row, ["tcp.srcport", "udp.srcport"]), axis=1)
    preview["dst_port"] = preview.apply(lambda row: _first_port(row, ["tcp.dstport", "udp.dstport"]), axis=1)
    columns = [
        "frame.time_epoch",
        "ip.src",
        "ip.dst",
        "protocol",
        "frame.len",
        "src_port",
        "dst_port",
        "tcp.flags",
    ]
    return preview[[column for column in columns if column in preview.columns]]


def _finalize_flow(flow: dict) -> dict:
    duration = max(float(flow["_last_seen"] - flow["_first_seen"]), 0.01)
    total_bytes = float(flow["src_bytes"] + flow["dst_bytes"])
    total_packets = max(int(flow["src_packets"] + flow["dst_packets"]), 1)
    packet_sizes = pd.Series(flow["_packet_sizes"], dtype=float)

    finalized = {key: value for key, value in flow.items() if not key.startswith("_")}
    finalized["duration"] = round(duration, 6)
    finalized["src_bytes"] = round(float(finalized["src_bytes"]), 2)
    finalized["dst_bytes"] = round(float(finalized["dst_bytes"]), 2)
    finalized["flow_bytes_per_sec"] = round(total_bytes / duration, 2)
    finalized["flow_packets_per_sec"] = round(total_packets / duration, 2)
    finalized["packet_size_mean"] = round(total_bytes / total_packets, 2)
    finalized["packet_size_std"] = round(float(packet_sizes.std(ddof=0)) if len(packet_sizes) > 1 else 0.0, 2)
    return finalized


def _protocol_name(row: pd.Series) -> str | None:
    raw = row.get("ip.proto")
    number = _parse_int(raw, default=0)
    if number in PROTOCOL_NAMES:
        return PROTOCOL_NAMES[number]
    if not _is_missing(row.get("tcp.srcport")) or not _is_missing(row.get("tcp.dstport")):
        return "TCP"
    if not _is_missing(row.get("udp.srcport")) or not _is_missing(row.get("udp.dstport")):
        return "UDP"
    return None


def _first_port(row: pd.Series, columns: list[str]) -> int:
    for column in columns:
        value = row.get(column)
        if not _is_missing(value):
            return _parse_int(value, default=0)
    return 0


def _parse_float(value: Any, default: float) -> float:
    if _is_missing(value):
        return default
    parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return default if pd.isna(parsed) else float(parsed)


def _parse_int(value: Any, default: int) -> int:
    if _is_missing(value):
        return default
    text = str(value).strip()
    try:
        return int(text, 0)
    except ValueError:
        parsed = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        return default if pd.isna(parsed) else int(parsed)


def _timestamp_iso(epoch_seconds: float) -> str:
    if epoch_seconds <= 0:
        return datetime.now(timezone.utc).isoformat()
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _string(value: Any) -> str:
    return "" if _is_missing(value) else str(value).strip()


def _is_missing(value: Any) -> bool:
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
