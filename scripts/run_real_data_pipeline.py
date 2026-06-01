"""Download, prepare, and train on CSE-CIC-IDS2018 real network-flow data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from netsentinel.core.config import get_settings
from netsentinel.services.model_registry import ModelRegistry
from netsentinel.services.model_training import ModelTrainingService
from netsentinel.services.real_dataset import CSECICIDS2018Service


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the real CSE-CIC-IDS2018 data pipeline.")
    parser.add_argument(
        "--files",
        nargs="+",
        default=["bruteforce"],
        help="Friendly presets or official CSV names. Presets: bruteforce, dos, ddos, web, infiltration, botnet, all.",
    )
    parser.add_argument("--max-rows", type=int, default=120_000, help="Prepared sample size for local training.")
    parser.add_argument("--attack-fraction", type=float, default=0.40, help="Target attack-row fraction in sample.")
    parser.add_argument("--force-download", action="store_true", help="Re-download files even if present.")
    parser.add_argument("--skip-download", action="store_true", help="Use files already present in data/raw.")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Use .part files when a large download was interrupted. Useful for quick local experiments.",
    )
    parser.add_argument("--download-only", action="store_true", help="Download files and stop.")
    parser.add_argument("--prepare-only", action="store_true", help="Download and prepare files, but do not train.")
    parser.add_argument("--download-timeout", type=int, default=180, help="Per-read timeout in seconds.")
    parser.add_argument("--download-retries", type=int, default=5, help="Resume/retry attempts per file.")
    parser.add_argument(
        "--prepared-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "cse_cic_ids2018_prepared.csv",
    )
    parser.add_argument("--report-output", type=Path, default=PROJECT_ROOT / "reports" / "real_data_pipeline.json")
    args = parser.parse_args()

    settings = get_settings()
    dataset = CSECICIDS2018Service()
    file_names = dataset.resolve_files(args.files)

    if args.skip_download:
        downloads = []
        raw_paths = []
        for file_name in file_names:
            full_path = dataset.raw_dir / file_name
            part_path = full_path.with_suffix(full_path.suffix + ".part")
            if full_path.exists():
                raw_paths.append(full_path)
            elif args.allow_partial and part_path.exists():
                print(f"Using partial file: {part_path}")
                raw_paths.append(part_path)
            else:
                raw_paths.append(full_path)
    else:
        print(f"Downloading {len(file_names)} file(s) from CSE-CIC-IDS2018...")
        downloads = dataset.download_files(
            file_names,
            force=args.force_download,
            timeout=args.download_timeout,
            retries=args.download_retries,
        )
        raw_paths = [Path(result.path) for result in downloads]
        for result in downloads:
            status = "skipped" if result.skipped else "downloaded"
            size_mb = result.size_bytes / (1024 * 1024)
            print(f"- {status}: {result.file_name} ({size_mb:.1f} MB)")

    if args.download_only:
        print(json.dumps({"downloads": [result.to_dict() for result in downloads]}, indent=2))
        return

    print("Preparing dataset...")
    prepared, prepare_report = dataset.prepare_files(
        raw_paths,
        output_path=args.prepared_output,
        max_rows=args.max_rows,
        attack_fraction=args.attack_fraction,
    )

    training_payload: dict | None = None
    if not args.prepare_only:
        print("Training model on prepared real data...")
        training = ModelTrainingService().train_all(
            prepared,
            registry=ModelRegistry(settings.model_registry_dir),
            reference_data_path=settings.reference_data_path,
            promote_best=True,
            tags={
                "source": "cse-cic-ids2018",
                "dataset": "CSE-CIC-IDS2018",
                "files": ",".join(file_names),
                "purpose": "real-data-portfolio-training",
            },
        )
        training_payload = training.to_dict()

    report = {
        "downloads": [result.to_dict() for result in downloads],
        "preparation": prepare_report.to_dict(),
        "training": training_payload,
    }
    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Report written to {args.report_output}")


if __name__ == "__main__":
    main()
