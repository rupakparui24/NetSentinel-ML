"""Capture packets with tshark, aggregate flows, and score them with NetSentinel."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from netsentinel.services.flow_payloads import dataframe_to_flow_payloads
from netsentinel.services.packet_capture import DEFAULT_CAPTURE_FILTER, packets_to_flow_records, run_tshark_capture

API_BATCH_SIZE = 500


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture packets with tshark and score network flows.")
    parser.add_argument("--interface", help="tshark interface name or number, for example Wi-Fi or 5.")
    parser.add_argument("--window-seconds", type=int, default=10, help="Capture duration in seconds.")
    parser.add_argument("--packet-limit", type=int, help="Optional maximum packets to capture.")
    parser.add_argument(
        "--capture-filter",
        default=DEFAULT_CAPTURE_FILTER,
        help="BPF capture filter passed to tshark.",
    )
    parser.add_argument("--api-url", default=os.getenv("API_URL", "http://localhost:8000"), help="NetSentinel API URL.")
    parser.add_argument("--tshark-path", default=os.getenv("TSHARK_PATH", "tshark"), help="Path to tshark executable.")
    parser.add_argument("--max-flows", type=int, default=500, help="Maximum aggregated flows to score.")
    parser.add_argument("--timeout", type=int, default=60, help="Prediction request timeout in seconds.")
    parser.add_argument("--input-csv", type=Path, help="Read tshark field CSV instead of live capture.")
    parser.add_argument("--output", type=Path, help="Path for scored flow CSV output.")
    args = parser.parse_args()
    if args.input_csv is None and not args.interface:
        parser.error("--interface is required unless --input-csv is provided")
    return args


def predict_flows(api_url: str, flows: list[dict], timeout: int) -> list[dict]:
    predictions: list[dict] = []
    endpoint = f"{api_url.rstrip('/')}/api/v1/predict/batch"
    for start in range(0, len(flows), API_BATCH_SIZE):
        batch = flows[start : start + API_BATCH_SIZE]
        response = requests.post(endpoint, json={"flows": batch}, timeout=timeout)
        response.raise_for_status()
        predictions.extend(response.json()["predictions"])
    return predictions


def default_output_path() -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return PROJECT_ROOT / "data" / "captures" / f"capture_predictions_{timestamp}.csv"


def main() -> int:
    args = parse_args()
    packets = (
        pd.read_csv(args.input_csv)
        if args.input_csv
        else run_tshark_capture(
            tshark_path=args.tshark_path,
            interface=args.interface,
            window_seconds=args.window_seconds,
            packet_limit=args.packet_limit,
            capture_filter=args.capture_filter,
        )
    )
    flow_records = packets_to_flow_records(packets)[: args.max_flows]
    payloads = dataframe_to_flow_payloads(pd.DataFrame(flow_records))

    if not payloads:
        print(json.dumps({"packets": len(packets), "flows": 0, "message": "No IP flows captured."}, indent=2))
        return 0

    predictions = predict_flows(args.api_url, payloads, timeout=args.timeout)
    scored = pd.concat(
        [pd.DataFrame(flow_records).head(len(payloads)).reset_index(drop=True), pd.DataFrame(predictions)],
        axis=1,
    )

    output_path = args.output or default_output_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scored.to_csv(output_path, index=False)

    malicious = scored[scored["prediction"] == "malicious"]
    summary = {
        "packets": int(len(packets)),
        "flows_scored": int(len(scored)),
        "malicious": int(len(malicious)),
        "benign": int((scored["prediction"] == "benign").sum()),
        "output": str(output_path),
    }
    print(json.dumps(summary, indent=2))

    if not malicious.empty:
        display_columns = [
            "src_ip",
            "dst_ip",
            "protocol",
            "src_port",
            "dst_port",
            "prediction",
            "confidence",
        ]
        print(malicious[display_columns].head(20).to_string(index=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, requests.RequestException) as exc:
        print(f"capture_and_predict failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
