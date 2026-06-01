"""Automation for real public intrusion-detection datasets."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

from netsentinel.services.feature_engineering import FeatureEngineeringService

CSE_CIC_IDS2018_BASE_URL = "https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com"
CSE_CIC_IDS2018_PREFIX = "Processed Traffic Data for ML Algorithms"

CSE_CIC_IDS2018_FILES = {
    "bruteforce": "Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv",
    "dos": "Friday-16-02-2018_TrafficForML_CICFlowMeter.csv",
    "ddos": "Tuesday-20-02-2018_TrafficForML_CICFlowMeter.csv",
    "web": "Thursday-22-02-2018_TrafficForML_CICFlowMeter.csv",
    "infiltration": "Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv",
    "botnet": "Friday-02-03-2018_TrafficForML_CICFlowMeter.csv",
}


@dataclass
class DownloadResult:
    dataset: str
    file_name: str
    url: str
    path: str
    size_bytes: int
    skipped: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PreparedDatasetReport:
    dataset: str
    output_path: str
    rows: int
    source_files: list[str]
    label_counts: dict[str, int]
    attack_type_counts: dict[str, int]
    max_rows: int | None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class CSECICIDS2018Service:
    """Download and prepare CSE-CIC-IDS2018 CSV files from public AWS S3."""

    def __init__(
        self,
        raw_dir: str | Path = "data/raw/cse_cic_ids2018",
        processed_dir: str | Path = "data/processed",
    ) -> None:
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.feature_engineer = FeatureEngineeringService()

    def resolve_files(self, presets_or_files: list[str]) -> list[str]:
        """Resolve friendly preset names to official CSV names."""

        if not presets_or_files:
            return [CSE_CIC_IDS2018_FILES["bruteforce"]]
        if "all" in presets_or_files:
            return list(CSE_CIC_IDS2018_FILES.values())
        resolved: list[str] = []
        for item in presets_or_files:
            resolved.append(CSE_CIC_IDS2018_FILES.get(item, item))
        return resolved

    def download_files(
        self,
        file_names: list[str],
        force: bool = False,
        timeout: int = 180,
        retries: int = 5,
    ) -> list[DownloadResult]:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        results: list[DownloadResult] = []
        for file_name in file_names:
            results.append(self.download_file(file_name=file_name, force=force, timeout=timeout, retries=retries))
        return results

    def download_file(
        self,
        file_name: str,
        force: bool = False,
        timeout: int = 180,
        retries: int = 5,
    ) -> DownloadResult:
        target = self.raw_dir / file_name
        url = self.url_for(file_name)
        if target.exists() and target.stat().st_size > 0 and not force:
            return DownloadResult(
                dataset="CSE-CIC-IDS2018",
                file_name=file_name,
                url=url,
                path=str(target),
                size_bytes=target.stat().st_size,
                skipped=True,
            )

        temp_path = target.with_suffix(target.suffix + ".part")
        if force:
            temp_path.unlink(missing_ok=True)
            target.unlink(missing_ok=True)

        remote_size = self.remote_size(url, timeout=timeout)
        for attempt in range(1, retries + 1):
            try:
                downloaded = temp_path.stat().st_size if temp_path.exists() else 0
                if remote_size and downloaded >= remote_size:
                    temp_path.replace(target)
                    break
                headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}
                with requests.get(url, stream=True, timeout=(20, timeout), headers=headers) as response:
                    if downloaded and response.status_code != 206:
                        downloaded = 0
                        temp_path.unlink(missing_ok=True)
                        response.close()
                        continue
                    response.raise_for_status()
                    mode = "ab" if downloaded else "wb"
                    with temp_path.open(mode) as file:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                file.write(chunk)
                if remote_size is None or temp_path.stat().st_size >= remote_size:
                    temp_path.replace(target)
                    break
            except requests.RequestException:
                if attempt == retries:
                    raise
                time.sleep(min(2**attempt, 30))

        if not target.exists():
            raise RuntimeError(f"Download did not complete after {retries} attempts: {file_name}")

        return DownloadResult(
            dataset="CSE-CIC-IDS2018",
            file_name=file_name,
            url=url,
            path=str(target),
            size_bytes=target.stat().st_size,
        )

    def prepare_files(
        self,
        raw_paths: list[str | Path],
        output_path: str | Path | None = None,
        max_rows: int | None = 120_000,
        attack_fraction: float = 0.40,
        chunksize: int = 80_000,
        random_seed: int = 42,
    ) -> tuple[pd.DataFrame, PreparedDatasetReport]:
        """Clean, balance-sample, and save a prepared dataset for training."""

        output = Path(output_path) if output_path else self.processed_dir / "cse_cic_ids2018_prepared.csv"
        output.parent.mkdir(parents=True, exist_ok=True)

        rng = np.random.default_rng(random_seed)
        benign_frames: list[pd.DataFrame] = []
        attack_frames: list[pd.DataFrame] = []
        max_attack = None if max_rows is None else int(max_rows * attack_fraction)
        max_benign = None if max_rows is None else max_rows - max_attack
        notes: list[str] = []

        for raw_path in raw_paths:
            path = Path(raw_path)
            if not path.exists():
                raise FileNotFoundError(f"Dataset file not found: {path}")
            for chunk in pd.read_csv(path, chunksize=chunksize, low_memory=False, on_bad_lines="skip"):
                cleaned = self.clean_chunk(chunk)
                if cleaned.empty:
                    continue

                benign = cleaned[cleaned["label"] == 0]
                attack = cleaned[cleaned["label"] == 1]
                if max_rows is None:
                    benign_frames.append(benign)
                    attack_frames.append(attack)
                    continue

                benign_needed = max_benign - sum(len(frame) for frame in benign_frames)
                attack_needed = max_attack - sum(len(frame) for frame in attack_frames)
                if benign_needed > 0 and not benign.empty:
                    benign_frames.append(self._sample(benign, min(benign_needed, len(benign)), rng))
                if attack_needed > 0 and not attack.empty:
                    attack_frames.append(self._sample(attack, min(attack_needed, len(attack)), rng))
                if benign_needed <= 0 and attack_needed <= 0:
                    break

        frames = benign_frames + attack_frames
        if not frames:
            raise ValueError("No valid rows were prepared from the selected dataset files.")

        prepared = pd.concat(frames, ignore_index=True)
        if max_rows is not None and len(prepared) > max_rows:
            prepared = self._sample(prepared, max_rows, rng)
        prepared = prepared.sample(frac=1.0, random_state=random_seed).reset_index(drop=True)
        prepared.to_csv(output, index=False)

        if prepared["label"].nunique() < 2:
            notes.append("Prepared dataset has only one class; choose another file or increase max_rows.")

        report = PreparedDatasetReport(
            dataset="CSE-CIC-IDS2018",
            output_path=str(output),
            rows=len(prepared),
            source_files=[str(Path(path)) for path in raw_paths],
            label_counts={str(key): int(value) for key, value in prepared["label"].value_counts().items()},
            attack_type_counts={
                str(key): int(value) for key, value in prepared["attack_type"].value_counts().head(20).items()
            },
            max_rows=max_rows,
            notes=notes,
        )
        return prepared, report

    def clean_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        normalized = self.feature_engineer.normalize_columns(chunk)
        if "label" not in normalized.columns:
            return pd.DataFrame()

        attack_type = normalized["label"].astype(str).str.strip()
        labels = self.feature_engineer.extract_labels(normalized)
        if labels is None:
            return pd.DataFrame()

        normalized = normalized.replace([np.inf, -np.inf, "Infinity", "inf", "-inf"], np.nan)
        normalized["attack_type"] = attack_type
        normalized["label"] = labels
        normalized = normalized.dropna(subset=["label"])
        return normalized

    def save_report(self, report: PreparedDatasetReport | dict, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = report.to_dict() if hasattr(report, "to_dict") else report
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target

    def url_for(self, file_name: str) -> str:
        key = f"{CSE_CIC_IDS2018_PREFIX}/{file_name}"
        return f"{CSE_CIC_IDS2018_BASE_URL}/{quote(key)}"

    def remote_size(self, url: str, timeout: int = 180) -> int | None:
        response = requests.head(url, timeout=(20, timeout))
        response.raise_for_status()
        content_length = response.headers.get("content-length")
        return int(content_length) if content_length else None

    def _sample(self, frame: pd.DataFrame, rows: int, rng: np.random.Generator) -> pd.DataFrame:
        if rows >= len(frame):
            return frame
        seed = int(rng.integers(0, 2**31 - 1))
        return frame.sample(n=rows, random_state=seed)
