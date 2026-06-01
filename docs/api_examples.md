# API Examples

## Health

```bash
curl http://localhost:8000/api/v1/health
```

## Predict

```bash
curl -X POST http://localhost:8000/api/v1/predict ^
  -H "Content-Type: application/json" ^
  -d "{\"duration\":0.18,\"protocol\":\"TCP\",\"src_port\":49152,\"dst_port\":22,\"src_bytes\":8420,\"dst_bytes\":920,\"src_packets\":52,\"dst_packets\":9,\"tcp_flags\":12}"
```

## Batch Predict

```bash
curl -X POST http://localhost:8000/api/v1/predict/batch ^
  -H "Content-Type: application/json" ^
  -d "{\"flows\":[{\"duration\":0.18,\"protocol\":\"TCP\",\"dst_port\":22,\"src_bytes\":8420,\"dst_bytes\":920,\"src_packets\":52,\"dst_packets\":9,\"tcp_flags\":12}]}"
```

## Retrain

```bash
curl -X POST http://localhost:8000/api/v1/retrain ^
  -H "Content-Type: application/json" ^
  -H "x-api-key: dev-netsentinel-key" ^
  -d "{\"rows\":1200,\"drift\":true}"
```
