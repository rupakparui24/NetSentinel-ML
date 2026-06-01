# Model Card

## Model

Current production model is selected automatically between:

- Random Forest classifier
- Gradient Boosting classifier

The selected model is registered in `models/registry/registry.json` and stored as a `joblib` artifact.

## Intended Use

Binary classification of network flows as:

- `benign`
- `malicious`

The project is intended for portfolio demonstration, local experimentation, and MLOps learning. It is not a drop-in replacement for a production IDS.

## Training Data

The default data generator creates synthetic flows with benign and attack-like distributions for:

- DDoS
- Port scanning
- Brute force
- Exfiltration-like traffic

The data generator is deterministic by seed and can simulate drift.

## Features

The model uses 22 engineered features including:

- Duration
- Protocol code
- Source and destination ports
- Bytes and packets in each direction
- Flow rates
- Packet-size statistics
- Port-risk indicators
- Temporal features

## Metrics

Training records:

- Accuracy
- Precision
- Recall
- F1
- AUC-ROC when available
- Inference latency

Run:

```bash
python scripts/train_demo_model.py --rows 2000
```

## Limitations

- Synthetic data is not a substitute for CICIDS2017 or live traffic.
- Explanations are a fast approximation, not exact SHAP values.
- The file registry is local and not safe for concurrent multi-writer production use.
- Labels are binary in the MVP; multi-class attack classification is a planned extension.

## Responsible Use

Use this system as a learning and demonstration project. Before security operations use, validate with real traffic, calibrate false positive cost, add human review, and document incident response procedures.
