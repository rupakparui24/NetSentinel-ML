# Incident Response Runbook

## Performance Degradation

1. Check `GET /api/v1/performance`.
2. Compare P95 latency with the target of 150 ms and alert threshold of 300 ms.
3. Confirm whether errors are schema validation failures or model-runtime failures.
4. Run `python scripts/profile_latency.py`.
5. Roll back to the previous production model if a newly promoted model is slower or less accurate.

## Data Drift

1. Run a protected drift check with a recent traffic batch through `POST /api/v1/drift/check`.
2. Inspect the feature-level PSI, KL divergence, and KS statistics.
3. Identify whether the shift is expected business traffic, noisy input, or a new attack pattern.
4. Trigger `POST /api/v1/retrain` with recent data only after validation.
5. Promote the retrained model only if holdout F1 and precision improve.

## High Error Rate

1. Review API request payloads against `/docs`.
2. Check `models/registry/registry.json` and artifact paths.
3. Run `python scripts/smoke_test.py`.
4. Restart the API process or container after artifact issues are corrected.

## Model Rollback

1. List models with `GET /api/v1/models`.
2. Pick the previous healthy model ID.
3. Call `POST /api/v1/models/switch` with the API key.
4. Validate `/api/v1/health` and run a prediction smoke test.
