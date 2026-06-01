# NetSentinel-ML - Design Document

## Document Information

**Project:** NetSentinel-ML  
**Version:** 1.0  
**Last Updated:** May 28, 2026  
**Status:** Draft  
**Author:** [Your Name]

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Component Design](#2-component-design)
3. [Data Design](#3-data-design)
4. [API Design](#4-api-design)
5. [ML Pipeline Design](#5-ml-pipeline-design)
6. [MLOps Design](#6-mlops-design)
7. [Security Design](#7-security-design)
8. [Deployment Architecture](#8-deployment-architecture)
9. [Technology Stack](#9-technology-stack)
10. [Design Decisions](#10-design-decisions)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CLIENT LAYER                               │
│  ┌──────────────────┐         ┌──────────────────┐                 │
│  │  Streamlit UI    │         │  External API    │                 │
│  │  Dashboard       │         │  Clients         │                 │
│  └────────┬─────────┘         └────────┬─────────┘                 │
└───────────┼──────────────────────────────┼──────────────────────────┘
            │                              │
            └──────────────┬───────────────┘
                           │ HTTP/REST
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       API GATEWAY LAYER                             │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              FastAPI Application                             │  │
│  │  • Authentication & Authorization                            │  │
│  │  • Rate Limiting                                             │  │
│  │  • Request Validation                                        │  │
│  │  • Response Caching (Redis)                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Prediction    │ │   Monitoring    │ │   Management    │
│   Service       │ │   Service       │ │   Service       │
└────────┬────────┘ └────────┬────────┘ └────────┬────────┘
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       CORE SERVICES LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Feature    │  │    Model     │  │    Drift     │             │
│  │   Store      │  │   Registry   │  │   Detector   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │ Explainability│ │   Metrics    │  │   Alerting   │             │
│  │   Engine     │  │  Collector   │  │   Service    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   PostgreSQL    │ │     MLflow      │ │     Redis       │
│   (Metadata)    │ │  (Experiments)  │ │    (Cache)      │
└─────────────────┘ └─────────────────┘ └─────────────────┘
            │              │              │
            └──────────────┼──────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   Raw Data   │  │  Processed   │  │   Models     │             │
│  │   Storage    │  │    Data      │  │   Storage    │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Architecture Principles

**1. Separation of Concerns**
- Each service has a single, well-defined responsibility
- Clear boundaries between components
- Loose coupling, high cohesion

**2. Scalability**
- Stateless services for horizontal scaling
- Caching layer for performance
- Async processing for long-running tasks

**3. Observability**
- Comprehensive logging at all layers
- Metrics collection for monitoring
- Distributed tracing (future)

**4. Resilience**
- Graceful degradation on failures
- Circuit breakers for external dependencies
- Retry mechanisms with exponential backoff

**5. Security**
- Authentication and authorization
- Input validation at all entry points
- Secure secrets management

---

## 2. Component Design

### 2.1 Data Pipeline Components

#### 2.1.1 Data Ingestion Service

**Purpose:** Ingest network traffic data from multiple sources

**Responsibilities:**
- Accept data in multiple formats (CSV, JSON, Parquet)
- Validate data schema
- Handle batch and streaming ingestion
- Queue data for processing

**Interface:**
```python
class DataIngestionService:
    def ingest_batch(self, file_path: str, format: str) -> IngestionResult
    def ingest_stream(self, data: Dict) -> IngestionResult
    def validate_schema(self, data: pd.DataFrame) -> ValidationResult
```

**Data Flow:**
```
Raw Data → Schema Validation → Data Quality Checks → Feature Store
```

#### 2.1.2 Data Validation Service

**Purpose:** Ensure data quality before processing

**Responsibilities:**
- Validate data types and ranges
- Detect missing values and outliers
- Generate data quality reports
- Calculate quality scores

**Interface:**
```python
class DataValidationService:
    def validate_types(self, data: pd.DataFrame) -> TypeValidationResult
    def detect_outliers(self, data: pd.DataFrame) -> OutlierReport
    def check_missing_values(self, data: pd.DataFrame) -> MissingValueReport
    def generate_quality_report(self, data: pd.DataFrame) -> QualityReport
```

**Validation Rules:**
```yaml
port:
  type: integer
  range: [0, 65535]
  
packet_size:
  type: float
  range: [0, 65535]
  
protocol:
  type: categorical
  values: [TCP, UDP, ICMP]
  
timestamp:
  type: datetime
  format: ISO8601
```

#### 2.1.3 Feature Engineering Service

**Purpose:** Transform raw data into ML-ready features

**Responsibilities:**
- Extract statistical features
- Create time-based features
- Generate network-specific features
- Store features with versioning

**Interface:**
```python
class FeatureEngineeringService:
    def extract_statistical_features(self, data: pd.DataFrame) -> pd.DataFrame
    def extract_temporal_features(self, data: pd.DataFrame) -> pd.DataFrame
    def extract_network_features(self, data: pd.DataFrame) -> pd.DataFrame
    def store_features(self, features: pd.DataFrame, version: str) -> None
```

**Feature Categories:**

1. **Statistical Features:**
   - Mean, median, std, min, max
   - Percentiles (25th, 50th, 75th)
   - Skewness, kurtosis

2. **Temporal Features:**
   - Hour of day (0-23)
   - Day of week (0-6)
   - Is weekend (boolean)
   - Time since last connection

3. **Network Features:**
   - Packet size distribution (mean, std)
   - Protocol distribution (TCP%, UDP%, ICMP%)
   - Port usage patterns
   - Connection duration statistics
   - Bytes per second
   - Packets per second

### 2.2 Model Components

#### 2.2.1 Model Training Service

**Purpose:** Train and evaluate ML models

**Responsibilities:**
- Train multiple model types
- Perform hyperparameter tuning
- Evaluate models on test set
- Log experiments to MLflow

**Interface:**
```python
class ModelTrainingService:
    def train_random_forest(self, X_train, y_train, params: Dict) -> Model
    def train_xgboost(self, X_train, y_train, params: Dict) -> Model
    def train_isolation_forest(self, X_train, params: Dict) -> Model
    def train_lstm_autoencoder(self, X_train, params: Dict) -> Model
    def evaluate_model(self, model: Model, X_test, y_test) -> EvaluationResult
```

**Model Configurations:**

```python
# Random Forest
rf_config = {
    'n_estimators': 100,
    'max_depth': 20,
    'min_samples_split': 10,
    'class_weight': 'balanced'
}

# XGBoost
xgb_config = {
    'n_estimators': 100,
    'max_depth': 10,
    'learning_rate': 0.1,
    'scale_pos_weight': 5  # for imbalanced data
}

# Isolation Forest
iso_config = {
    'n_estimators': 100,
    'contamination': 0.1,
    'max_samples': 256
}

# LSTM Autoencoder
lstm_config = {
    'encoding_dim': 32,
    'epochs': 50,
    'batch_size': 256,
    'learning_rate': 0.001
}
```

#### 2.2.2 Model Registry Service

**Purpose:** Manage model versions and metadata

**Responsibilities:**
- Register models with versions
- Tag models (staging, production, archived)
- Store model metadata
- Track model lineage

**Interface:**
```python
class ModelRegistryService:
    def register_model(self, model: Model, name: str, metadata: Dict) -> str
    def get_model(self, name: str, version: str) -> Model
    def promote_model(self, name: str, version: str, stage: str) -> None
    def list_models(self, stage: Optional[str] = None) -> List[ModelInfo]
    def get_model_metadata(self, name: str, version: str) -> Dict
```

**Model Metadata Schema:**
```python
{
    "model_id": "uuid",
    "name": "xgboost_v1",
    "version": "1.0.0",
    "stage": "production",  # staging, production, archived
    "created_at": "2026-05-28T10:00:00Z",
    "metrics": {
        "accuracy": 0.956,
        "precision": 0.943,
        "recall": 0.951,
        "f1_score": 0.947,
        "auc_roc": 0.978
    },
    "hyperparameters": {...},
    "training_data": {
        "dataset": "CICIDS2017",
        "size": 1960000,
        "features": 78
    },
    "lineage": {
        "parent_model": "xgboost_v0",
        "training_run_id": "mlflow_run_123"
    }
}
```

#### 2.2.3 Prediction Service

**Purpose:** Serve model predictions

**Responsibilities:**
- Load models from registry
- Perform real-time predictions
- Handle batch predictions
- Cache predictions
- Support A/B testing

**Interface:**
```python
class PredictionService:
    def predict(self, features: Dict) -> PredictionResult
    def predict_batch(self, features: List[Dict]) -> List[PredictionResult]
    def predict_with_explanation(self, features: Dict) -> PredictionWithExplanation
    def switch_model(self, model_name: str, version: str) -> None
```

**Prediction Result Schema:**
```python
{
    "prediction_id": "uuid",
    "prediction": "malicious",  # or "benign"
    "confidence": 0.92,
    "probabilities": {
        "benign": 0.08,
        "malicious": 0.92
    },
    "model_info": {
        "name": "xgboost_v1",
        "version": "1.0.0"
    },
    "timestamp": "2026-05-28T10:00:00Z",
    "latency_ms": 45
}
```

### 2.3 Explainability Components

#### 2.3.1 SHAP Explainer

**Purpose:** Generate SHAP explanations

**Responsibilities:**
- Compute SHAP values for predictions
- Generate global feature importance
- Create SHAP visualizations

**Interface:**
```python
class SHAPExplainer:
    def explain_prediction(self, model: Model, features: Dict) -> SHAPExplanation
    def global_importance(self, model: Model, X: pd.DataFrame) -> GlobalImportance
    def generate_summary_plot(self, shap_values: np.ndarray) -> Figure
```

**SHAP Explanation Schema:**
```python
{
    "prediction_id": "uuid",
    "base_value": 0.15,  # baseline prediction
    "shap_values": {
        "packet_size": 0.23,
        "protocol_tcp": 0.18,
        "port": -0.05,
        ...
    },
    "top_features": [
        {"feature": "packet_size", "value": 1500, "shap_value": 0.23},
        {"feature": "protocol_tcp", "value": 1, "shap_value": 0.18},
        ...
    ]
}
```

#### 2.3.2 LIME Explainer

**Purpose:** Generate LIME explanations

**Responsibilities:**
- Create local linear approximations
- Identify influential features
- Generate human-readable explanations

**Interface:**
```python
class LIMEExplainer:
    def explain_prediction(self, model: Model, features: Dict) -> LIMEExplanation
    def generate_explanation_text(self, explanation: LIMEExplanation) -> str
```

### 2.4 MLOps Components

#### 2.4.1 Drift Detection Service

**Purpose:** Detect data and model drift

**Responsibilities:**
- Calculate drift metrics (PSI, KL divergence)
- Monitor prediction distribution
- Detect performance degradation
- Trigger alerts on drift

**Interface:**
```python
class DriftDetectionService:
    def calculate_psi(self, reference: pd.Series, current: pd.Series) -> float
    def calculate_kl_divergence(self, reference: pd.Series, current: pd.Series) -> float
    def detect_data_drift(self, reference_data: pd.DataFrame, current_data: pd.DataFrame) -> DriftReport
    def detect_model_drift(self, model: Model, current_data: pd.DataFrame) -> ModelDriftReport
```

**Drift Metrics:**

1. **Population Stability Index (PSI)**
```python
PSI = Σ (actual% - expected%) * ln(actual% / expected%)

Interpretation:
- PSI < 0.1: No significant drift
- 0.1 ≤ PSI < 0.2: Moderate drift
- PSI ≥ 0.2: Significant drift (trigger retraining)
```

2. **KL Divergence**
```python
KL(P||Q) = Σ P(x) * log(P(x) / Q(x))

Interpretation:
- KL < 0.1: No significant drift
- KL ≥ 0.1: Significant drift
```

**Drift Report Schema:**
```python
{
    "drift_id": "uuid",
    "timestamp": "2026-05-28T10:00:00Z",
    "overall_drift_score": 0.25,
    "drift_detected": true,
    "feature_drift": {
        "packet_size": {
            "psi": 0.15,
            "kl_divergence": 0.12,
            "drift_detected": true
        },
        "protocol": {
            "psi": 0.05,
            "kl_divergence": 0.03,
            "drift_detected": false
        },
        ...
    },
    "recommendation": "Retrain model with recent data"
}
```

#### 2.4.2 Monitoring Service

**Purpose:** Collect and expose metrics

**Responsibilities:**
- Collect prediction latency
- Track throughput
- Monitor error rates
- Expose Prometheus metrics

**Interface:**
```python
class MonitoringService:
    def record_prediction_latency(self, latency_ms: float) -> None
    def record_prediction(self, prediction: str) -> None
    def record_error(self, error_type: str) -> None
    def get_metrics(self) -> Dict
```

**Metrics Collected:**
```python
# Latency metrics
prediction_latency_seconds{quantile="0.5"}
prediction_latency_seconds{quantile="0.95"}
prediction_latency_seconds{quantile="0.99"}

# Throughput metrics
predictions_total
predictions_per_second

# Error metrics
errors_total{type="validation"}
errors_total{type="model"}
errors_total{type="system"}

# Model metrics
model_accuracy
model_drift_score
data_drift_score

# System metrics
cpu_usage_percent
memory_usage_bytes
```

#### 2.4.3 Retraining Service

**Purpose:** Automate model retraining

**Responsibilities:**
- Trigger retraining on drift
- Fetch recent data
- Train new model
- Validate and deploy if improved

**Interface:**
```python
class RetrainingService:
    def trigger_retraining(self, reason: str) -> RetrainingJob
    def fetch_recent_data(self, days: int) -> pd.DataFrame
    def train_new_model(self, data: pd.DataFrame) -> Model
    def validate_new_model(self, model: Model) -> ValidationResult
    def deploy_if_improved(self, new_model: Model, current_model: Model) -> bool
```

**Retraining Pipeline:**
```
Drift Detected → Fetch Recent Data (30 days) → Train New Model → 
Validate on Holdout → Compare with Current → Deploy if Better → 
Update Registry → Notify Team
```

---

## 3. Data Design

### 3.1 Database Schema

#### 3.1.1 PostgreSQL Schema

**predictions table:**
```sql
CREATE TABLE predictions (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    features JSONB NOT NULL,
    prediction VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    latency_ms FLOAT NOT NULL,
    explanation JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_predictions_timestamp ON predictions(timestamp);
CREATE INDEX idx_predictions_model ON predictions(model_name, model_version);
```

**drift_reports table:**
```sql
CREATE TABLE drift_reports (
    id UUID PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    drift_type VARCHAR(50) NOT NULL,  -- 'data' or 'model'
    overall_score FLOAT NOT NULL,
    drift_detected BOOLEAN NOT NULL,
    feature_scores JSONB NOT NULL,
    recommendation TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_drift_timestamp ON drift_reports(timestamp);
```

**retraining_jobs table:**
```sql
CREATE TABLE retraining_jobs (
    id UUID PRIMARY KEY,
    triggered_by VARCHAR(100) NOT NULL,  -- 'drift', 'manual', 'scheduled'
    status VARCHAR(50) NOT NULL,  -- 'running', 'completed', 'failed'
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    old_model_version VARCHAR(50),
    new_model_version VARCHAR(50),
    metrics JSONB,
    deployed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3.2 Feature Store Design

**Feature Storage:**
```python
# features/{version}/{date}/features.parquet
features/
├── v1.0/
│   ├── 2026-05-01/
│   │   └── features.parquet
│   ├── 2026-05-02/
│   │   └── features.parquet
│   └── metadata.json
└── v1.1/
    └── ...
```

**Feature Metadata:**
```json
{
    "version": "1.0",
    "created_at": "2026-05-28T10:00:00Z",
    "features": [
        {
            "name": "packet_size_mean",
            "type": "float",
            "description": "Mean packet size in bytes",
            "computation": "mean(packet_sizes)"
        },
        {
            "name": "protocol_tcp_ratio",
            "type": "float",
            "description": "Ratio of TCP packets",
            "computation": "count(protocol='TCP') / count(all)"
        }
    ]
}
```

### 3.3 Model Storage

**Model Artifacts:**
```
models/
├── random_forest/
│   ├── v1.0/
│   │   ├── model.pkl
│   │   ├── metadata.json
│   │   └── metrics.json
│   └── v1.1/
│       └── ...
├── xgboost/
│   └── ...
└── lstm_autoencoder/
    └── ...
```

---

## 4. API Design

### 4.1 REST API Endpoints

#### 4.1.1 Prediction Endpoints

**POST /api/v1/predict**
```yaml
Summary: Get prediction for single network flow
Request Body:
  {
    "features": {
      "packet_size": 1500,
      "protocol": "TCP",
      "port": 80,
      ...
    },
    "include_explanation": true
  }

Response: 200 OK
  {
    "prediction_id": "uuid",
    "prediction": "malicious",
    "confidence": 0.92,
    "explanation": {...},
    "latency_ms": 45
  }

Errors:
  400: Invalid input
  429: Rate limit exceeded
  500: Internal server error
```

**POST /api/v1/predict/batch**
```yaml
Summary: Get predictions for multiple network flows
Request Body:
  {
    "features": [
      {"packet_size": 1500, ...},
      {"packet_size": 800, ...}
    ]
  }

Response: 200 OK
  {
    "predictions": [
      {"prediction_id": "uuid1", ...},
      {"prediction_id": "uuid2", ...}
    ],
    "total": 2,
    "latency_ms": 120
  }
```

#### 4.1.2 Monitoring Endpoints

**GET /api/v1/metrics**
```yaml
Summary: Get Prometheus metrics
Response: 200 OK (text/plain)
  # HELP prediction_latency_seconds Prediction latency
  # TYPE prediction_latency_seconds summary
  prediction_latency_seconds{quantile="0.5"} 0.045
  prediction_latency_seconds{quantile="0.95"} 0.120
  ...
```

**GET /api/v1/health**
```yaml
Summary: Health check
Response: 200 OK
  {
    "status": "healthy",
    "version": "1.0.0",
    "services": {
      "database": "healthy",
      "mlflow": "healthy",
      "redis": "healthy"
    }
  }
```

**GET /api/v1/drift**
```yaml
Summary: Get drift status
Response: 200 OK
  {
    "data_drift": {
      "score": 0.15,
      "detected": false
    },
    "model_drift": {
      "score": 0.08,
      "detected": false
    },
    "last_check": "2026-05-28T10:00:00Z"
  }
```

#### 4.1.3 Model Management Endpoints

**GET /api/v1/models**
```yaml
Summary: List available models
Query Parameters:
  - stage: staging|production|archived
  
Response: 200 OK
  {
    "models": [
      {
        "name": "xgboost_v1",
        "version": "1.0.0",
        "stage": "production",
        "metrics": {...}
      }
    ]
  }
```

**POST /api/v1/models/deploy**
```yaml
Summary: Deploy a model
Request Body:
  {
    "model_name": "xgboost_v1",
    "version": "1.1.0",
    "stage": "production"
  }

Response: 200 OK
  {
    "message": "Model deployed successfully",
    "model_name": "xgboost_v1",
    "version": "1.1.0"
  }
```

**POST /api/v1/retrain**
```yaml
Summary: Trigger model retraining
Request Body:
  {
    "reason": "drift_detected",
    "model_name": "xgboost_v1"
  }

Response: 202 Accepted
  {
    "job_id": "uuid",
    "status": "running",
    "estimated_time_minutes": 25
  }
```

### 4.2 API Authentication

**API Key Authentication:**
```python
# Header
Authorization: Bearer <api_key>

# Rate Limiting
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1622548800
```

### 4.3 API Versioning

**URL Versioning:**
```
/api/v1/predict  # Current version
/api/v2/predict  # Future version
```

---

## 5. ML Pipeline Design

### 5.1 Training Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    TRAINING PIPELINE                        │
└─────────────────────────────────────────────────────────────┘

Step 1: Data Loading
├── Load raw data from storage
├── Validate data schema
└── Split into train/val/test (70/15/15)

Step 2: Feature Engineering
├── Extract statistical features
├── Extract temporal features
├── Extract network features
└── Store features in feature store

Step 3: Data Preprocessing
├── Handle missing values (imputation)
├── Remove duplicates
├── Normalize/standardize features
├── Encode categorical variables
└── Handle class imbalance (SMOTE)

Step 4: Model Training
├── Train Random Forest (baseline)
├── Train XGBoost
├── Train Isolation Forest
├── Train LSTM Autoencoder
└── Train Ensemble

Step 5: Hyperparameter Tuning
├── Define search space
├── Run Optuna optimization
├── Cross-validation (5-fold)
└── Select best hyperparameters

Step 6: Model Evaluation
├── Calculate metrics on test set
├── Generate confusion matrix
├── Plot ROC and PR curves
├── Measure inference time
└── Compare models

Step 7: Model Selection
├── Select best model based on F1-score
├── Validate on holdout set
└── Document selection rationale

Step 8: Model Registration
├── Register model in MLflow
├── Tag as 'staging'
├── Store metadata
└── Log artifacts

Step 9: Model Deployment
├── Validate model in staging
├── Run smoke tests
├── Promote to production
└── Update API to use new model
```

### 5.2 Inference Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                   INFERENCE PIPELINE                        │
└─────────────────────────────────────────────────────────────┘

Step 1: Request Validation
├── Validate input schema
├── Check feature ranges
└── Reject invalid requests

Step 2: Feature Engineering
├── Apply same transformations as training
├── Extract features from raw input
└── Normalize features

Step 3: Model Loading
├── Load model from registry
├── Cache model in memory
└── Warm up model

Step 4: Prediction
├── Run model inference
├── Get prediction and confidence
└── Measure latency

Step 5: Explanation Generation
├── Compute SHAP values
├── Generate LIME explanation
└── Format explanation

Step 6: Response Formatting
├── Create prediction response
├── Add metadata
└── Return to client

Step 7: Logging & Monitoring
├── Log prediction to database
├── Record metrics (latency, confidence)
└── Update monitoring dashboard
```

### 5.3 Retraining Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                  RETRAINING PIPELINE                        │
└─────────────────────────────────────────────────────────────┘

Trigger: Drift detected OR Manual trigger OR Scheduled

Step 1: Data Collection
├── Fetch recent data (last 30 days)
├── Combine with historical data
└── Validate data quality

Step 2: Drift Analysis
├── Compare with training data
├── Identify drifted features
└── Generate drift report

Step 3: Model Retraining
├── Use same architecture as current model
├── Train on combined dataset
├── Apply hyperparameter tuning
└── Evaluate on holdout set

Step 4: Model Validation
├── Compare with current model
├── Check if performance improved
└── Run A/B test (optional)

Step 5: Deployment Decision
├── If improved: Deploy new model
├── If not improved: Keep current model
└── Log decision and rationale

Step 6: Notification
├── Send alert to team
├── Update dashboard
└── Log retraining job
```

---

This is Part 1 of the design.md. Should I continue with the remaining sections (MLOps Design, Security Design, Deployment Architecture, Technology Stack, and Design Decisions)?

## 6. MLOps Design

### 6.1 Experiment Tracking

**MLflow Integration:**

```python
# Experiment tracking structure
experiments/
├── random_forest/
│   ├── run_001/
│   │   ├── params.json
│   │   ├── metrics.json
│   │   ├── model/
│   │   └── artifacts/
│   └── run_002/
├── xgboost/
└── lstm_autoencoder/
```

**Logged Information:**
```python
# Parameters
mlflow.log_param("n_estimators", 100)
mlflow.log_param("max_depth", 20)
mlflow.log_param("learning_rate", 0.1)

# Metrics
mlflow.log_metric("accuracy", 0.956)
mlflow.log_metric("precision", 0.943)
mlflow.log_metric("recall", 0.951)
mlflow.log_metric("f1_score", 0.947)

# Artifacts
mlflow.log_artifact("confusion_matrix.png")
mlflow.log_artifact("roc_curve.png")
mlflow.log_artifact("feature_importance.png")

# Model
mlflow.sklearn.log_model(model, "model")
```

### 6.2 Model Versioning Strategy

**Semantic Versioning:**
```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes (new features, different output format)
MINOR: New features (backward compatible)
PATCH: Bug fixes, performance improvements

Examples:
- 1.0.0: Initial production model
- 1.0.1: Bug fix in preprocessing
- 1.1.0: Added new features
- 2.0.0: Changed model architecture
```

**Model Lifecycle:**
```
Development → Staging → Production → Archived

Development: Model being trained/tuned
Staging: Model validated, ready for testing
Production: Model serving live traffic
Archived: Old model, kept for reference
```

### 6.3 A/B Testing Framework

**Traffic Splitting:**
```python
class ABTestingService:
    def __init__(self):
        self.model_a = load_model("xgboost_v1.0")  # Current
        self.model_b = load_model("xgboost_v1.1")  # New
        self.split_ratio = 0.9  # 90% A, 10% B
    
    def predict(self, features: Dict) -> PredictionResult:
        # Route traffic based on split ratio
        if random.random() < self.split_ratio:
            return self.model_a.predict(features)
        else:
            return self.model_b.predict(features)
    
    def collect_metrics(self):
        # Track metrics per model
        metrics_a = calculate_metrics(self.model_a)
        metrics_b = calculate_metrics(self.model_b)
        
        # Statistical significance test
        p_value = ttest_ind(metrics_a, metrics_b)
        
        if p_value < 0.05 and metrics_b > metrics_a:
            return "Model B is significantly better"
```

**A/B Test Metrics:**
```python
{
    "test_id": "uuid",
    "model_a": {
        "name": "xgboost_v1.0",
        "traffic_percentage": 90,
        "predictions": 9000,
        "accuracy": 0.956,
        "avg_latency_ms": 45
    },
    "model_b": {
        "name": "xgboost_v1.1",
        "traffic_percentage": 10,
        "predictions": 1000,
        "accuracy": 0.962,
        "avg_latency_ms": 48
    },
    "statistical_significance": {
        "p_value": 0.03,
        "significant": true
    },
    "recommendation": "Promote Model B to production"
}
```

### 6.4 CI/CD Pipeline

**GitHub Actions Workflow:**

```yaml
name: ML Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linting
        run: |
          ruff check .
          black --check .
      
      - name: Run unit tests
        run: pytest tests/ --cov=src --cov-report=xml
      
      - name: Run integration tests
        run: pytest tests/integration/
  
  model-validation:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Load test data
        run: python scripts/load_test_data.py
      
      - name: Validate model performance
        run: python scripts/validate_model.py
      
      - name: Check model metrics
        run: |
          python scripts/check_metrics.py \
            --min-accuracy 0.90 \
            --min-precision 0.88 \
            --min-recall 0.88
  
  deploy-staging:
    runs-on: ubuntu-latest
    needs: model-validation
    if: github.ref == 'refs/heads/develop'
    steps:
      - name: Build Docker image
        run: docker build -t netsentinel-ml:staging .
      
      - name: Deploy to staging
        run: |
          docker-compose -f docker-compose.staging.yml up -d
      
      - name: Run smoke tests
        run: python scripts/smoke_tests.py --env staging
  
  deploy-production:
    runs-on: ubuntu-latest
    needs: model-validation
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Build Docker image
        run: docker build -t netsentinel-ml:production .
      
      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.prod.yml up -d
      
      - name: Run smoke tests
        run: python scripts/smoke_tests.py --env production
      
      - name: Notify team
        run: |
          curl -X POST $SLACK_WEBHOOK \
            -d '{"text": "NetSentinel-ML deployed to production"}'
```

---

## 7. Security Design

### 7.1 Authentication & Authorization

**API Key Authentication:**
```python
class APIKeyAuth:
    def __init__(self):
        self.api_keys = load_api_keys()  # From secure storage
    
    def authenticate(self, api_key: str) -> bool:
        return api_key in self.api_keys
    
    def get_rate_limit(self, api_key: str) -> int:
        # Different rate limits per key
        return self.api_keys[api_key]["rate_limit"]
```

**Rate Limiting:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/predict")
@limiter.limit("100/minute")
async def predict(request: Request, data: PredictionRequest):
    # Rate limited to 100 requests per minute
    ...
```

### 7.2 Input Validation

**Request Validation:**
```python
from pydantic import BaseModel, validator, Field

class PredictionRequest(BaseModel):
    features: Dict[str, float] = Field(..., description="Network traffic features")
    
    @validator('features')
    def validate_features(cls, v):
        required_features = ['packet_size', 'protocol', 'port', ...]
        
        # Check required features
        for feature in required_features:
            if feature not in v:
                raise ValueError(f"Missing required feature: {feature}")
        
        # Validate ranges
        if v['port'] < 0 or v['port'] > 65535:
            raise ValueError("Port must be between 0 and 65535")
        
        if v['packet_size'] < 0:
            raise ValueError("Packet size must be non-negative")
        
        return v
```

### 7.3 Data Security

**Sensitive Data Handling:**
```python
# Encrypt sensitive data at rest
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())
    
    def decrypt(self, encrypted_data: bytes) -> str:
        return self.cipher.decrypt(encrypted_data).decode()
```

**Secrets Management:**
```python
# Use environment variables for secrets
import os

DATABASE_URL = os.getenv("DATABASE_URL")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
API_SECRET_KEY = os.getenv("API_SECRET_KEY")

# Never hardcode secrets in code
# Never commit .env files to git
```

### 7.4 Audit Logging

**Security Event Logging:**
```python
class AuditLogger:
    def log_authentication(self, api_key: str, success: bool):
        log_entry = {
            "event": "authentication",
            "api_key_hash": hash(api_key),
            "success": success,
            "timestamp": datetime.now(),
            "ip_address": get_client_ip()
        }
        self.write_log(log_entry)
    
    def log_prediction(self, prediction_id: str, user: str):
        log_entry = {
            "event": "prediction",
            "prediction_id": prediction_id,
            "user": user,
            "timestamp": datetime.now()
        }
        self.write_log(log_entry)
    
    def log_model_deployment(self, model_name: str, version: str, user: str):
        log_entry = {
            "event": "model_deployment",
            "model_name": model_name,
            "version": version,
            "user": user,
            "timestamp": datetime.now()
        }
        self.write_log(log_entry)
```

---

## 8. Deployment Architecture

### 8.1 Docker Architecture

**Multi-Container Setup:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  # FastAPI Backend
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/netsentinel
      - MLFLOW_TRACKING_URI=http://mlflow:5000
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - mlflow
      - redis
    volumes:
      - ./models:/app/models
      - ./data:/app/data
    networks:
      - netsentinel-network
  
  # Streamlit Dashboard
  dashboard:
    build:
      context: .
      dockerfile: Dockerfile.dashboard
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://api:8000
    depends_on:
      - api
    networks:
      - netsentinel-network
  
  # PostgreSQL Database
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=netsentinel
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - netsentinel-network
  
  # MLflow Server
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    ports:
      - "5000:5000"
    environment:
      - BACKEND_STORE_URI=postgresql://user:pass@postgres:5432/mlflow
      - ARTIFACT_ROOT=/mlflow/artifacts
    volumes:
      - mlflow_artifacts:/mlflow/artifacts
    depends_on:
      - postgres
    networks:
      - netsentinel-network
  
  # Redis Cache
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - netsentinel-network
  
  # Prometheus (Monitoring)
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - netsentinel-network

volumes:
  postgres_data:
  mlflow_artifacts:
  redis_data:
  prometheus_data:

networks:
  netsentinel-network:
    driver: bridge
```

### 8.2 Dockerfile Design

**Multi-Stage Build:**

```dockerfile
# Dockerfile
FROM python:3.10-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY src/ ./src/
COPY models/ ./models/
COPY scripts/ ./scripts/

# Set environment variables
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Run application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 8.3 Environment Configuration

**Environment-Specific Configs:**

```python
# config/development.py
class DevelopmentConfig:
    DEBUG = True
    DATABASE_URL = "postgresql://localhost:5432/netsentinel_dev"
    MLFLOW_TRACKING_URI = "http://localhost:5000"
    LOG_LEVEL = "DEBUG"
    RATE_LIMIT = 1000  # Higher for development

# config/staging.py
class StagingConfig:
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL")
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
    LOG_LEVEL = "INFO"
    RATE_LIMIT = 500

# config/production.py
class ProductionConfig:
    DEBUG = False
    DATABASE_URL = os.getenv("DATABASE_URL")
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
    LOG_LEVEL = "WARNING"
    RATE_LIMIT = 100
    ENABLE_METRICS = True
    ENABLE_ALERTING = True
```

---

## 9. Technology Stack

### 9.1 Core Technologies

**Programming Language:**
- Python 3.10+

**Web Framework:**
- FastAPI 0.104+ (async API)
- Uvicorn (ASGI server)

**Data Processing:**
- pandas 2.0+
- numpy 1.24+
- pydantic 2.0+ (validation)
- great_expectations 0.17+ (data quality)

**Machine Learning:**
- scikit-learn 1.3+
- xgboost 2.0+
- tensorflow 2.13+ or pytorch 2.0+ (LSTM)
- imbalanced-learn 0.11+ (SMOTE)

**Explainability:**
- shap 0.42+
- lime 0.2+
- eli5 0.13+

**MLOps:**
- mlflow 2.7+ (experiment tracking, model registry)
- optuna 3.3+ (hyperparameter tuning)
- evidently 0.4+ (drift detection)

**API & Caching:**
- redis 5.0+ (caching)
- slowapi 0.1+ (rate limiting)

**Database:**
- PostgreSQL 15+ (metadata)
- SQLAlchemy 2.0+ (ORM)

**Monitoring:**
- prometheus-client 0.17+
- loguru 0.7+ (logging)

**Frontend:**
- streamlit 1.28+
- plotly 5.17+
- altair 5.1+

**Deployment:**
- docker 24.0+
- docker-compose 2.20+

**Testing:**
- pytest 7.4+
- pytest-cov 4.1+
- pytest-asyncio 0.21+
- locust 2.16+ (load testing)

**CI/CD:**
- GitHub Actions

### 9.2 Technology Justification

| Technology | Why Chosen | Alternatives Considered |
|------------|------------|------------------------|
| FastAPI | Async support, auto-docs, modern | Flask (no async), Django (too heavy) |
| PostgreSQL | ACID compliance, JSONB support | MySQL (less features), MongoDB (not relational) |
| MLflow | Industry standard, comprehensive | Weights & Biases (paid), Neptune (paid) |
| Redis | Fast, simple, widely used | Memcached (less features) |
| Streamlit | Rapid prototyping, Python-native | React (more complex), Dash (less intuitive) |
| Docker | Portability, reproducibility | Kubernetes (overkill for this scale) |
| XGBoost | Best performance on tabular data | LightGBM (similar), CatBoost (slower) |
| SHAP | Model-agnostic, theoretically sound | LIME only (less comprehensive) |

---

## 10. Design Decisions

### 10.1 Key Design Decisions

#### Decision 1: Hybrid Model Approach

**Decision:** Train multiple model types (RF, XGBoost, Isolation Forest, LSTM) and compare

**Rationale:**
- Different models capture different patterns
- Ensemble can improve performance
- Shows ML breadth to recruiters
- Allows comparison and learning

**Alternatives Considered:**
- Single model (XGBoost only): Simpler but less impressive
- Deep learning only: Overkill for tabular data

**Trade-offs:**
- ✅ Better performance through ensemble
- ✅ More impressive portfolio
- ❌ More complex codebase
- ❌ Longer training time

#### Decision 2: MLflow for Experiment Tracking

**Decision:** Use MLflow for all experiment tracking and model registry

**Rationale:**
- Industry standard
- Open-source and free
- Comprehensive features
- Good documentation

**Alternatives Considered:**
- Weights & Biases: Better UI but paid
- Custom solution: Too much work
- Neptune: Paid, less popular

**Trade-offs:**
- ✅ Free and open-source
- ✅ Industry recognition
- ❌ UI could be better
- ❌ Requires separate server

#### Decision 3: Evidently for Drift Detection

**Decision:** Use Evidently library for drift detection

**Rationale:**
- Purpose-built for ML monitoring
- Supports multiple drift metrics
- Good visualizations
- Active development

**Alternatives Considered:**
- Custom implementation: Too complex
- Alibi-detect: Less comprehensive
- Manual PSI calculation: Limited

**Trade-offs:**
- ✅ Comprehensive drift metrics
- ✅ Easy to use
- ❌ Another dependency
- ❌ Learning curve

#### Decision 4: PostgreSQL for Metadata

**Decision:** Use PostgreSQL for storing predictions, drift reports, and metadata

**Rationale:**
- ACID compliance for critical data
- JSONB support for flexible schema
- Mature and reliable
- Good Python support

**Alternatives Considered:**
- MongoDB: Less structure, eventual consistency
- SQLite: Not suitable for production
- MySQL: Less features than PostgreSQL

**Trade-offs:**
- ✅ Reliable and mature
- ✅ JSONB for flexibility
- ❌ Requires separate server
- ❌ More complex than SQLite

#### Decision 5: Docker Compose for Deployment

**Decision:** Use Docker Compose for local/single-server deployment

**Rationale:**
- Simple and reproducible
- Good for portfolio projects
- Easy to understand
- No cloud costs

**Alternatives Considered:**
- Kubernetes: Overkill for this scale
- Cloud deployment: Costs money
- Manual setup: Not reproducible

**Trade-offs:**
- ✅ Simple and free
- ✅ Reproducible
- ❌ Not production-scale
- ❌ Single-server limitation

### 10.2 Performance Optimization Decisions

#### Caching Strategy

**Decision:** Cache predictions for identical inputs

**Implementation:**
```python
@lru_cache(maxsize=1000)
def predict_cached(features_hash: str) -> PredictionResult:
    return model.predict(features)
```

**Rationale:**
- Reduce latency for repeated queries
- Save compute resources
- Simple to implement

#### Batch Processing

**Decision:** Support batch predictions with optimized processing

**Implementation:**
```python
def predict_batch(features_list: List[Dict]) -> List[PredictionResult]:
    # Vectorized prediction
    features_array = np.array([extract_features(f) for f in features_list])
    predictions = model.predict(features_array)  # Single call
    return [format_result(p) for p in predictions]
```

**Rationale:**
- More efficient than individual predictions
- Better resource utilization
- Lower latency per prediction

#### Model Loading

**Decision:** Load model once at startup, keep in memory

**Implementation:**
```python
# Load at startup
@app.on_event("startup")
async def load_models():
    global model
    model = load_model_from_registry("xgboost_v1", "production")
```

**Rationale:**
- Avoid loading overhead per request
- Faster predictions
- Acceptable memory usage

### 10.3 Scalability Considerations

**Current Design (Single Server):**
- Suitable for: 100-500 requests/sec
- Limitations: Single point of failure, limited scale

**Future Scaling Path:**
```
Phase 1 (Current): Single server with Docker Compose
Phase 2: Multiple API instances with load balancer
Phase 3: Separate services (prediction, monitoring, retraining)
Phase 4: Kubernetes deployment with auto-scaling
Phase 5: Cloud-native with managed services
```

### 10.4 Monitoring Strategy

**Three-Level Monitoring:**

1. **System Level:**
   - CPU, memory, disk usage
   - Network I/O
   - Container health

2. **Application Level:**
   - Request latency
   - Throughput
   - Error rate
   - API endpoint metrics

3. **ML Level:**
   - Model accuracy
   - Prediction distribution
   - Drift scores
   - Feature importance changes

---

## 11. Future Enhancements

### 11.1 Short-term (Post-MVP)

- [ ] Add Grafana dashboards for better visualization
- [ ] Implement automated A/B testing
- [ ] Add more drift detection methods
- [ ] Improve explainability visualizations
- [ ] Add model performance alerts via email/Slack

### 11.2 Medium-term

- [ ] Real-time streaming with Kafka
- [ ] Distributed training with Ray
- [ ] Advanced ensemble methods
- [ ] Adversarial attack detection
- [ ] Network topology visualization

### 11.3 Long-term

- [ ] Cloud deployment (AWS/GCP)
- [ ] Kubernetes orchestration
- [ ] Multi-model serving with Seldon
- [ ] Integration with SIEM systems
- [ ] Automated incident response

---

## 12. Appendix

### 12.1 Glossary

- **PSI**: Population Stability Index - metric for data drift
- **SHAP**: SHapley Additive exPlanations - explainability method
- **LIME**: Local Interpretable Model-agnostic Explanations
- **MLOps**: Machine Learning Operations - practices for ML lifecycle
- **AUC-ROC**: Area Under Receiver Operating Characteristic Curve
- **SMOTE**: Synthetic Minority Over-sampling Technique

### 12.2 References

- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently AI Documentation](https://docs.evidentlyai.com/)
- [SHAP Documentation](https://shap.readthedocs.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [CICIDS2017 Dataset](https://www.unb.ca/cic/datasets/ids-2017.html)

---

**Document Status:** Complete  
**Next Steps:** Review and approve design, proceed to implementation (tasks.md)  
**Reviewers:** [Your Name]  
**Approval Date:** [To be filled]
