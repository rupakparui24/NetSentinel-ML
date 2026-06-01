# Architecture

NetSentinel-ML follows the layered design described in `design.md`, reduced to a local-first MVP that can be extended without replacing the core interfaces.

## Layers

```text
Client Layer
  Streamlit dashboard
  REST clients

API Layer
  FastAPI application
  Request validation
  API key checks for management actions
  In-memory rate limiting for predictions

Service Layer
  Data ingestion
  Data validation
  Feature engineering
  Model training and evaluation
  Model registry
  Prediction runtime
  Explainability
  Drift detection
  Metrics and alerting

Artifact Layer
  data/sample
  data/processed/reference_features.csv
  models/registry/*.joblib
  models/registry/registry.json
```

## Design Choices

- A file-based model registry keeps the project runnable without PostgreSQL or MLflow.
- Synthetic network-flow data makes demos deterministic and fast.
- The feature service normalizes both demo field names and common CICIDS-style names.
- Explainability uses feature importance plus reference-distribution distance as a fast fallback. SHAP can replace this implementation later behind the same response shape.
- Drift scoring combines PSI, KL divergence, and KS statistics so the dashboard can explain both distribution shift and feature-level contributors.

## Extension Points

- Add MLflow inside `ModelTrainingService.train_all` to log params, metrics, and model artifacts.
- Add XGBoost as another candidate in `ModelTrainingService`.
- Replace `ModelRegistry` with MLflow registry or a database-backed registry.
- Persist predictions and alerts in PostgreSQL.
- Replace `SimpleRateLimiter` with SlowAPI or an API gateway for multi-instance deployments.
