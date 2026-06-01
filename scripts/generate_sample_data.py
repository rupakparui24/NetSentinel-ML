"""Generate a local synthetic network-flow dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from netsentinel.services.sample_data import generate_synthetic_network_flows


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NetSentinel synthetic network flows.")
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--attack-rate", type=float, default=0.22)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--drift", action="store_true")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data" / "sample" / "network_flows.csv")
    args = parser.parse_args()

    df = generate_synthetic_network_flows(
        n_rows=args.rows,
        attack_rate=args.attack_rate,
        seed=args.seed,
        drift=args.drift,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False)
    print(f"Wrote {len(df)} rows to {args.output}")


if __name__ == "__main__":
    main()
