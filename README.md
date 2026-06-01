# NetSentinel-ML

Production-minded network intrusion detection system with a full ML lifecycle: data validation, feature engineering, model training, registry, prediction API, drift detection, explainability, metrics, alerts, and a Streamlit dashboard.

This repository was built from the supplied `requirements.md`, `design.md`, and `tasks.md` as a recruiter-ready MVP. It is intentionally runnable on one laptop while preserving the architecture you would extend for CICIDS2017, MLflow, SHAP, XGBoost, Redis, and production deployment.

## What This Shows

- End-to-end ML engineering, not just notebook training
- Clean service boundaries for data, model, API, monitoring, and dashboard layers
- Model lifecycle basics: train, evaluate, register, promote, switch, retrain
- Explainable predictions with top contributing features and counterfactual suggestions
- Drift detection using PSI, KL divergence, and KS statistics
- FastAPI docs, Prometheus metrics, Docker Compose, and CI
- A practical learning curve from baseline ML to MLOps-style operation

## Architecture

```text
Streamlit Dashboard / API Clients
              |
              v
FastAPI Gateway: validation, rate limiting, auth, OpenAPI
              |
              v
Prediction Runtime: model registry, explainability, metrics
       |              |                |
       v              v                v
Data Pipeline   Drift Detection   Alerting/Prometheus
       |
       v
CSE-CIC-IDS2018 real data pipeline plus synthetic fallback
```

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python scripts/train_demo_model.py --rows 2000
uvicorn netsentinel.api.main:app --reload --app-dir src
```

API docs: `http://localhost:8000/docs`

Dashboard:

```bash
streamlit run dashboard/app.py
```

The dashboard Prediction tab supports both manual single-flow scoring and CSV upload for batch scoring. Uploaded CSVs can use the demo field names (`duration`, `protocol`, `src_port`, `dst_port`, etc.) or common CICIDS-style names such as `Flow Duration`, `Source Port`, `Destination Port`, and `Total Fwd Packets`.

Optional live capture with `tshark`:

```bash
python scripts/capture_and_predict.py --interface Wi-Fi --window-seconds 10
```

The script captures IP packets, aggregates them into bidirectional flow records, scores them with `/api/v1/predict/batch`, and writes results under `data/captures`. Install Wireshark/tshark first and run the terminal with packet-capture permissions if your OS requires it.

The same workflow is available in the dashboard under the `Capture` tab. Select the interface, click `Capture and analyze`, then review the packet preview, analyzed flows, prediction chart, and downloadable scored CSV.

Smoke test:

```bash
python scripts/smoke_test.py
pytest
```

Real-data pipeline:

```bash
python scripts/run_real_data_pipeline.py --files bruteforce --max-rows 40000
```

If the public S3 download is interrupted, resume it by running the same command again. For quick local experiments from an interrupted `.part` file:

```bash
python scripts/run_real_data_pipeline.py --files bruteforce --skip-download --allow-partial --max-rows 40000
```

Docker:

```bash
docker compose up --build
```

- API: `http://localhost:8000`
- Dashboard: `http://localhost:8501`
- Prometheus: `http://localhost:9090`

## API Examples

```bash
curl -X POST http://localhost:8000/api/v1/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"duration\":0.18,\"protocol\":\"TCP\",\"src_port\":49152,\"dst_port\":22,\"src_bytes\":8420,\"dst_bytes\":920,\"src_packets\":52,\"dst_packets\":9,\"tcp_flags\":12}"
```

Protected operations use the demo key from `.env.example`:

```bash
curl -X POST http://localhost:8000/api/v1/retrain ^
  -H "Content-Type: application/json" ^
  -H "x-api-key: dev-netsentinel-key" ^
  -d "{\"rows\":1200,\"drift\":true}"
```

## Project Layout

```text
src/netsentinel/
  api/                 FastAPI routes and request schemas
  core/                settings and structured logging
  services/            data, ML, registry, drift, metrics, alerts
dashboard/             Streamlit dashboard
scripts/               repeatable data, training, smoke, latency commands
tests/                 focused unit and API tests
docs/                  architecture, runbook, model card, learning curve
```

## Current Scope

Implemented now:

- CSV, JSON, JSONL, and Parquet ingestion
- Automated CSE-CIC-IDS2018 download, partial resume, cleaning, sampling, and training
- Data quality reports with range checks, missing values, and IQR outliers
- Feature engineering for common network-flow and CICIDS-style columns
- Random Forest and Gradient Boosting model comparison
- Local registry with stage promotion and rollback-friendly archived models
- Prediction, batch prediction, model management, monitoring, drift, retrain APIs
- Dashboard for operations, manual predictions, CSV batch scoring, model comparison, drift simulation, and runbooks
- Optional `tshark` capture script for lightweight packet capture to batch prediction

Next extensions:

- Add full CICIDS2017/CSE-CIC-IDS2018 EDA notebooks
- Add MLflow tracking and model registry backend
- Add SHAP plots for global and local explanations
- Add XGBoost, Optuna tuning, and an LSTM autoencoder
- Add PostgreSQL metadata storage and Redis caching

## Recruiter Demo Path

1. Run `python scripts/train_demo_model.py --rows 2000`.
2. Start the API and open `/docs`.
3. Submit a high-risk SSH-like flow to `/predict`.
4. Open the dashboard and show the explanation chart.
5. Run a drift simulation in the Drift tab.
6. Trigger `/api/v1/retrain` and show the model registry update.

## Notes

The default model can train on synthetic flow data so the project remains reproducible without a multi-gigabyte dataset. The real-data command uses the official CSE-CIC-IDS2018 public AWS dataset and stores downloaded files under `data/raw`.
