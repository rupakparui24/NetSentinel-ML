"""Train and register a demo intrusion-detection model."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from netsentinel.core.config import get_settings
from netsentinel.services.data_validation import DataValidationService
from netsentinel.services.model_registry import ModelRegistry
from netsentinel.services.model_training import ModelTrainingService
from netsentinel.services.sample_data import generate_synthetic_network_flows


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the NetSentinel demo model.")
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--output-data", type=Path, default=PROJECT_ROOT / "data" / "sample" / "network_flows.csv")
    args = parser.parse_args()

    settings = get_settings()
    df = generate_synthetic_network_flows(n_rows=args.rows, seed=settings.random_seed)
    args.output_data.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output_data, index=False)

    report = DataValidationService().generate_quality_report(df)
    result = ModelTrainingService().train_all(
        df,
        registry=ModelRegistry(settings.model_registry_dir),
        reference_data_path=settings.reference_data_path,
        promote_best=True,
    )
    print(json.dumps({"data_quality": report, "training": result.to_dict()}, indent=2))


if __name__ == "__main__":
    main()
