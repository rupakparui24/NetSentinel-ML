# Learning Curve

This project is structured to show progression from ML basics to production-minded ML engineering.

## Stage 1: Data Foundation

- Built ingestion for CSV, JSON, JSONL, and Parquet.
- Added schema checks, range validation, missing-value reporting, and IQR outlier detection.
- Kept synthetic data generation local so experiments are reproducible.

## Stage 2: Feature Engineering

- Normalized network-flow names into one internal schema.
- Added rates, packet ratios, port-risk flags, and time-based features.
- Saved reference features for monitoring and drift comparison.

## Stage 3: Model Development

- Compared Random Forest and Gradient Boosting candidates.
- Measured accuracy, precision, recall, F1, AUC, and prediction latency.
- Registered the best model with metadata and stage labels.

## Stage 4: Serving

- Exposed single and batch prediction APIs.
- Added request validation, rate limiting, and API-key protection for management actions.
- Returned confidence, explanation, and counterfactual details in every prediction.

## Stage 5: MLOps and Monitoring

- Added model switching, retraining, drift detection, alerting, and Prometheus metrics.
- Added Docker Compose and CI so the project can be reviewed and reproduced.

## Stage 6: Future Growth

- Add CICIDS2017 notebooks and dataset cards.
- Add MLflow and Optuna for experiment history.
- Add SHAP for deeper explanations.
- Add XGBoost and an LSTM autoencoder for model breadth.
- Persist prediction history in PostgreSQL.
