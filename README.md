# NetSentinel-ML

End-to-end machine learning system for network intrusion detection.

I built NetSentinel-ML as a complete ML engineering project, not just a training notebook. It includes data ingestion, feature engineering, model training, model registry, prediction APIs, live packet capture, drift monitoring, explainability, alerts, and a Streamlit dashboard that a user can interact with.

The goal was to design a local-first intrusion detection platform that demonstrates practical MLOps, cybersecurity analytics, API development, and dashboard-driven ML operations.

## Project Highlights

- Built a FastAPI prediction service for single and batch network-flow scoring.
- Built a Streamlit dashboard for operations, prediction, CSV upload, live capture, model comparison, drift checks, and runbooks.
- Added live packet capture using Wireshark/tshark and converted packets into ML-ready flow records.
- Implemented feature engineering for demo flow fields and common CICIDS-style network traffic columns.
- Trained and compared Random Forest and Gradient Boosting classifiers.
- Added a local model registry with model stages, active model loading, promotion, archiving, and retraining.
- Added drift detection using PSI, KL divergence, and KS statistics.
- Added prediction explanations with top contributing features and counterfactual-style suggestions.
- Added Prometheus-style metrics, alerting, health checks, smoke tests, and Docker support.
- Added a real-data pipeline for CSE-CIC-IDS2018, with synthetic data fallback for lightweight local demos.

## Why This Project Matters

Many ML projects stop after model training. NetSentinel-ML focuses on the full application lifecycle:

```text
Data ingestion
  -> Validation
  -> Feature engineering
  -> Model training
  -> Model registry
  -> Prediction API
  -> Dashboard
  -> Monitoring
  -> Drift detection
  -> Retraining
```

This makes the project closer to how ML systems are actually used: models need APIs, monitoring, explanations, retraining workflows, and a usable interface.

## System Architecture

```text
Streamlit Dashboard / API Clients
              |
              v
FastAPI Gateway
  - request validation
  - API key checks for protected actions
  - prediction and management endpoints
              |
              v
Prediction Runtime
  - active model loading
  - feature engineering
  - explanations
  - metrics
              |
              +--> Model Registry
              +--> Drift Detection
              +--> Alerting
              +--> Prometheus Metrics
              |
              v
Data Pipeline
  - synthetic demo data
  - CSV/JSON/Parquet ingestion
  - CSE-CIC-IDS2018 preparation
  - tshark live packet capture
```

## Core Features

### Prediction API

The API accepts network-flow fields such as protocol, ports, duration, bytes, packets, and TCP flags. It returns:

- prediction: `benign` or `malicious`
- confidence score
- latency
- prediction ID
- top feature contributions
- counterfactual-style suggestions

### Dashboard

The Streamlit dashboard includes:

- Operations metrics
- Manual prediction form
- CSV upload for batch scoring
- Live packet capture and automatic analysis
- Model registry view
- Drift simulation
- Incident response runbooks

### Live Packet Capture

The project can use `tshark` to capture packets from a selected network interface, aggregate them into bidirectional flow records, and send those flows to the batch prediction API.

```text
Network interface
  -> tshark packet capture
  -> packet-to-flow aggregation
  -> batch prediction API
  -> dashboard results
```

### Drift Detection

Drift detection compares current traffic against the reference training distribution. It helps answer:

```text
Has network traffic changed enough that the model may need retraining?
```

The drift report includes feature-level PSI, KL divergence, KS statistic, and a combined drift score.

### Model Lifecycle

The project supports:

- train
- evaluate
- register
- promote active model
- archive model
- switch model
- retrain through API

This is intentionally implemented with a local file-based registry so the project can run on a student laptop without requiring MLflow or cloud infrastructure.

## Tech Stack

| Area | Tools |
| --- | --- |
| Language | Python |
| API | FastAPI, Uvicorn, Pydantic |
| ML | scikit-learn, pandas, NumPy, SciPy |
| Models | Random Forest, Gradient Boosting |
| Dashboard | Streamlit, Plotly |
| Monitoring | Prometheus-style metrics, custom alerts |
| Packet Capture | Wireshark/tshark |
| Testing | pytest, ruff |
| Deployment | Docker, Docker Compose |

## Project Structure

```text
src/netsentinel/
  api/                 FastAPI routes and request schemas
  core/                settings and structured logging
  services/            ML, data, registry, prediction, drift, alerts

dashboard/             Streamlit dashboard
scripts/               training, smoke test, latency profiling, capture
tests/                 unit and API tests
docs/                  architecture, runbook, model card, API examples
```

## Quickstart

### 1. Create environment

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

### 2. Train a lightweight demo model

```powershell
python scripts/train_demo_model.py --rows 1000
```

Use `1000` rows for low-end laptops. Use `2000` or more only if your system has enough RAM.

### 3. Start the API

```powershell
uvicorn netsentinel.api.main:app --reload --app-dir src
```

API docs:

```text
http://localhost:8000/docs
```

### 4. Start the dashboard

Open a second terminal:

```powershell
.venv\Scripts\activate
streamlit run dashboard/app.py
```

Dashboard:

```text
http://localhost:8501
```

## Live Capture

If Wireshark/tshark is installed:

```powershell
python scripts/capture_and_predict.py --tshark-path "C:\Program Files\Wireshark\tshark.exe" --interface 4 --window-seconds 10
```

You can also use the dashboard:

```text
Capture tab -> choose interface -> Capture and analyze
```

If packet capture fails on Windows, run PowerShell as Administrator.

## API Examples

### Single prediction

```powershell
curl -X POST http://localhost:8000/api/v1/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"duration\":0.18,\"protocol\":\"TCP\",\"src_port\":49152,\"dst_port\":22,\"src_bytes\":8420,\"dst_bytes\":920,\"src_packets\":52,\"dst_packets\":9,\"tcp_flags\":12}"
```

### Batch prediction

```powershell
curl -X POST http://localhost:8000/api/v1/predict/batch ^
  -H "Content-Type: application/json" ^
  -d "{\"flows\":[{\"duration\":0.18,\"protocol\":\"TCP\",\"src_port\":49152,\"dst_port\":22,\"src_bytes\":8420,\"dst_bytes\":920,\"src_packets\":52,\"dst_packets\":9,\"tcp_flags\":12}]}"
```

### Retrain model

Protected management endpoints use the demo API key from `.env.example`.

```powershell
curl -X POST http://localhost:8000/api/v1/retrain ^
  -H "Content-Type: application/json" ^
  -H "x-api-key: dev-netsentinel-key" ^
  -d "{\"rows\":1000,\"drift\":true}"
```

## Real Dataset Pipeline

The project includes an optional pipeline for CSE-CIC-IDS2018:

```powershell
python scripts/run_real_data_pipeline.py --files bruteforce --max-rows 40000
```

For low-end systems, start with the synthetic demo model first. The real dataset is larger and may take more disk, memory, and time.

## Validation

Run:

```powershell
pytest
ruff check .
python scripts/smoke_test.py
```

Recent local validation:

```text
pytest: 12 passed
ruff check .: passed
API smoke test: passed
batch prediction: passed
drift check: passed
```

## Model Notes

The default demo model is intentionally lightweight and CPU-friendly. It is suitable for portfolio demonstration, local experimentation, and learning how ML systems are operated.

During analysis, the synthetic-data model performed strongly on synthetic traffic but produced many false positives on a prepared real CSE-CIC sample. This is expected for a student/portfolio system and highlights why real-world IDS models need broader datasets, calibration, and human review.

This project should not be used as a production intrusion detection system without:

- validation on representative real network traffic
- false-positive calibration
- human review workflow
- better model monitoring
- persistent storage
- security hardening

## What I Learned

Through this project, I practiced:

- designing service-oriented ML applications
- building FastAPI services with typed schemas
- building Streamlit dashboards for ML workflows
- converting raw network packets into flow-level ML features
- handling model lifecycle operations
- monitoring drift and runtime metrics
- testing API and ML service behavior
- writing a project that can run locally without cloud dependencies

## Future Improvements

- Add MLflow experiment tracking and registry backend
- Add SHAP-based local and global explanations
- Add XGBoost and Optuna tuning
- Add multi-class attack classification
- Add PostgreSQL for metadata and prediction history
- Add Redis or API gateway based rate limiting
- Add Grafana dashboards
- Add SIEM-style export/integration

## Recruiter Demo Path

1. Start the API and dashboard.
2. Show manual prediction for a suspicious SSH-like flow.
3. Upload a CSV and run batch scoring.
4. Use the Capture tab to capture live traffic and analyze it.
5. Run a drift check and explain the changed features.
6. Show the model registry and retraining endpoint.
7. Open the API docs at `/docs`.

## Status

This is a recruiter-facing MVP that demonstrates end-to-end ML engineering for cybersecurity. It is designed to be understandable, runnable on a laptop, and extendable toward a more production-grade MLOps architecture.
