# Real Data Pipeline

The project can train on the official CSE-CIC-IDS2018 public dataset from AWS Open Data.

Source:

- https://registry.opendata.aws/cse-cic-ids2018/

## Default Local Run

```bash
python scripts/run_real_data_pipeline.py --files bruteforce --max-rows 40000
```

This does four things:

1. Downloads `Wednesday-14-02-2018_TrafficForML_CICFlowMeter.csv`.
2. Cleans CICFlowMeter columns and labels.
3. Creates a balanced local sample with benign and attack rows.
4. Trains and registers the best model as production.

## If Download Is Interrupted

The downloader supports resume. Run the same command again.

If you already have a `.part` file and want to train from the downloaded portion:

```bash
python scripts/run_real_data_pipeline.py --files bruteforce --skip-download --allow-partial --max-rows 40000
```

This is useful for laptop demos because even a partial official CSV can contain hundreds of thousands of real rows.

## File Presets

```text
bruteforce
dos
ddos
web
infiltration
botnet
all
```

Start with one preset. Use `all` only when you have time, disk space, and memory available.

## Output

```text
data/raw/cse_cic_ids2018/
data/processed/cse_cic_ids2018_prepared.csv
models/registry/
reports/real_data_pipeline.json
```

Generated data, model artifacts, and reports are ignored by Git because they can be large and machine-specific.

## Current Local Result

The pipeline was run from an interrupted official CSV download using:

```bash
python scripts/run_real_data_pipeline.py --files bruteforce --skip-download --allow-partial --max-rows 40000
```

Prepared sample:

```text
40,000 rows
24,000 benign
16,000 attack
Attack type present: FTP-BruteForce
```

Registered production model:

```text
gradient_boosting
source tag: cse-cic-ids2018
```
