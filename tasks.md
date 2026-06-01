# NetSentinel-ML - Tasks Breakdown

## Document Information

**Project:** NetSentinel-ML  
**Version:** 1.0  
**Last Updated:** May 28, 2026  
**Timeline:** 21 days (3 weeks)  
**Status:** Planning

---

## Task Organization

### Task Format
```
TASK-XXX: Task Title
Priority: High/Medium/Low
Story Points: 1-13 (Fibonacci)
Dependencies: [TASK-YYY, TASK-ZZZ]
Assignee: [Your Name]
Status: Not Started / In Progress / Completed / Blocked

Description:
[What needs to be done]

Acceptance Criteria:
- [ ] Criterion 1
- [ ] Criterion 2

Implementation Notes:
[Technical details, code snippets, references]
```

---

## Week 1: Foundation & Data Pipeline (Days 1-7)

### Day 1: Project Setup

**TASK-001: Initialize Project Structure**
- Priority: High
- Story Points: 3
- Dependencies: None
- Status: Not Started

Description:
Set up the complete project structure with all necessary directories and configuration files.

Acceptance Criteria:
- [ ] Project directory structure created
- [ ] Git repository initialized
- [ ] .gitignore configured
- [ ] README.md created
- [ ] requirements.txt created
- [ ] Docker files created
- [ ] Environment variables template created

Implementation:
```bash
netsentinel-ml/
├── src/
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── utils/
├── tests/
├── data/
├── models/
├── notebooks/
├── scripts/
├── docs/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

---

**TASK-002: Set Up Development Environment**
- Priority: High
- Story Points: 2
- Dependencies: TASK-001
- Status: Not Started

Description:
Configure development environment with all necessary tools and dependencies.

Acceptance Criteria:
- [ ] Python 3.10+ installed
- [ ] Virtual environment created
- [ ] All dependencies installed
- [ ] Pre-commit hooks configured
- [ ] IDE configured (VS Code/PyCharm)
- [ ] Docker and Docker Compose installed

Implementation:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

---

**TASK-003: Configure MLflow Server**
- Priority: High
- Story Points: 3
- Dependencies: TASK-002
- Status: Not Started

Description:
Set up MLflow tracking server for experiment tracking and model registry.

Acceptance Criteria:
- [ ] MLflow server running
- [ ] PostgreSQL backend configured
- [ ] Artifact storage configured
- [ ] MLflow UI accessible
- [ ] Test experiment logged successfully

Implementation:
```bash
# Start MLflow server
mlflow server \
  --backend-store-uri postgresql://user:pass@localhost:5432/mlflow \
  --default-artifact-root ./mlflow/artifacts \
  --host 0.0.0.0 \
  --port 5000
```

---

### Day 2: Data Collection & Exploration

**TASK-004: Download CICIDS2017 Dataset**
- Priority: High
- Story Points: 2
- Dependencies: TASK-001
- Status: Not Started

Description:
Download and organize the CICIDS2017 dataset for training and evaluation.

Acceptance Criteria:
- [ ] Dataset downloaded from official source
- [ ] Data files organized in data/raw/
- [ ] Dataset documentation saved
- [ ] Data integrity verified (checksums)
- [ ] Dataset statistics documented

Implementation:
```python
# scripts/download_data.py
import requests
from pathlib import Path

def download_cicids2017():
    """Download CICIDS2017 dataset"""
    base_url = "https://www.unb.ca/cic/datasets/ids-2017.html"
    data_dir = Path("data/raw/cicids2017")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Download CSV files
    files = [
        "Monday-WorkingHours.pcap_ISCX.csv",
        "Tuesday-WorkingHours.pcap_ISCX.csv",
        # ... other files
    ]
    
    for file in files:
        # Download logic
        pass
```

---

**TASK-005: Exploratory Data Analysis**
- Priority: High
- Story Points: 5
- Dependencies: TASK-004
- Status: Not Started

Description:
Perform comprehensive EDA to understand data characteristics, distributions, and quality issues.

Acceptance Criteria:
- [ ] Jupyter notebook created (notebooks/01_eda.ipynb)
- [ ] Dataset statistics calculated
- [ ] Feature distributions visualized
- [ ] Class imbalance analyzed
- [ ] Missing values identified
- [ ] Outliers detected
- [ ] Correlation analysis performed
- [ ] EDA report generated

Implementation:
```python
# notebooks/01_eda.ipynb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Load data
df = pd.read_csv("data/raw/cicids2017/Monday-WorkingHours.pcap_ISCX.csv")

# Basic statistics
print(df.info())
print(df.describe())

# Class distribution
df['Label'].value_counts().plot(kind='bar')

# Feature correlations
corr_matrix = df.corr()
sns.heatmap(corr_matrix, annot=False)

# Missing values
missing = df.isnull().sum()
print(missing[missing > 0])
```

---

### Day 3: Data Preprocessing

**TASK-006: Implement Data Validation Service**
- Priority: High
- Story Points: 5
- Dependencies: TASK-005
- Status: Not Started

Description:
Create service to validate data quality and schema.

Acceptance Criteria:
- [ ] DataValidationService class implemented
- [ ] Schema validation working
- [ ] Type checking implemented
- [ ] Range validation working
- [ ] Missing value detection working
- [ ] Outlier detection implemented
- [ ] Quality report generation working
- [ ] Unit tests written (>80% coverage)

Implementation:
```python
# src/services/data_validation.py
from typing import Dict, List
import pandas as pd
from pydantic import BaseModel

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    quality_score: float

class DataValidationService:
    def __init__(self, schema: Dict):
        self.schema = schema
    
    def validate_schema(self, df: pd.DataFrame) -> ValidationResult:
        """Validate dataframe against schema"""
        errors = []
        warnings = []
        
        # Check required columns
        required_cols = set(self.schema.keys())
        actual_cols = set(df.columns)
        missing_cols = required_cols - actual_cols
        
        if missing_cols:
            errors.append(f"Missing columns: {missing_cols}")
        
        # Check data types
        for col, expected_type in self.schema.items():
            if col in df.columns:
                actual_type = df[col].dtype
                if not self._is_compatible_type(actual_type, expected_type):
                    errors.append(f"Column {col}: expected {expected_type}, got {actual_type}")
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(df, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score
        )
    
    def detect_outliers(self, df: pd.DataFrame, method: str = "iqr") -> pd.DataFrame:
        """Detect outliers using IQR method"""
        outliers = pd.DataFrame()
        
        for col in df.select_dtypes(include=['float64', 'int64']).columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers[col] = (df[col] < lower_bound) | (df[col] > upper_bound)
        
        return outliers
    
    def check_missing_values(self, df: pd.DataFrame) -> Dict:
        """Check for missing values"""
        missing = df.isnull().sum()
        missing_pct = (missing / len(df)) * 100
        
        return {
            "total_missing": missing.sum(),
            "missing_by_column": missing[missing > 0].to_dict(),
            "missing_percentage": missing_pct[missing_pct > 0].to_dict()
        }
```

---

**TASK-007: Implement Data Cleaning Pipeline**
- Priority: High
- Story Points: 5
- Dependencies: TASK-006
- Status: Not Started

Description:
Create pipeline to clean and preprocess raw data.

Acceptance Criteria:
- [ ] DataCleaningPipeline class implemented
- [ ] Missing value imputation working
- [ ] Duplicate removal working
- [ ] Outlier handling implemented
- [ ] Data normalization working
- [ ] Categorical encoding working
- [ ] Pipeline is reproducible
- [ ] Unit tests written

Implementation:
```python
# src/services/data_cleaning.py
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
import pandas as pd

class DataCleaningPipeline:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.imputer = SimpleImputer(strategy='median')
    
    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Fit and transform data"""
        df_clean = df.copy()
        
        # Remove duplicates
        df_clean = df_clean.drop_duplicates()
        
        # Handle missing values
        numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
        df_clean[numeric_cols] = self.imputer.fit_transform(df_clean[numeric_cols])
        
        # Encode categorical variables
        categorical_cols = df_clean.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            if col != 'Label':  # Don't encode target
                le = LabelEncoder()
                df_clean[col] = le.fit_transform(df_clean[col].astype(str))
                self.label_encoders[col] = le
        
        # Normalize numeric features
        df_clean[numeric_cols] = self.scaler.fit_transform(df_clean[numeric_cols])
        
        return df_clean
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform new data using fitted pipeline"""
        df_clean = df.copy()
        
        # Apply same transformations
        numeric_cols = df_clean.select_dtypes(include=['float64', 'int64']).columns
        df_clean[numeric_cols] = self.imputer.transform(df_clean[numeric_cols])
        
        for col, le in self.label_encoders.items():
            if col in df_clean.columns:
                df_clean[col] = le.transform(df_clean[col].astype(str))
        
        df_clean[numeric_cols] = self.scaler.transform(df_clean[numeric_cols])
        
        return df_clean
```

---

### Day 4: Feature Engineering

**TASK-008: Implement Feature Engineering Service**
- Priority: High
- Story Points: 8
- Dependencies: TASK-007
- Status: Not Started

Description:
Create service to extract and engineer features from raw network traffic data.

Acceptance Criteria:
- [ ] FeatureEngineeringService class implemented
- [ ] Statistical features extracted
- [ ] Temporal features extracted
- [ ] Network-specific features extracted
- [ ] Feature versioning implemented
- [ ] Feature documentation auto-generated
- [ ] Unit tests written

Implementation:
```python
# src/services/feature_engineering.py
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List

class FeatureEngineeringService:
    def __init__(self, version: str = "1.0"):
        self.version = version
        self.feature_metadata = {}
    
    def extract_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract statistical features"""
        features = pd.DataFrame()
        
        # For each numeric column, calculate statistics
        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        
        for col in numeric_cols:
            features[f'{col}_mean'] = df[col].mean()
            features[f'{col}_std'] = df[col].std()
            features[f'{col}_min'] = df[col].min()
            features[f'{col}_max'] = df[col].max()
            features[f'{col}_median'] = df[col].median()
            features[f'{col}_q25'] = df[col].quantile(0.25)
            features[f'{col}_q75'] = df[col].quantile(0.75)
            features[f'{col}_skew'] = df[col].skew()
            features[f'{col}_kurtosis'] = df[col].kurtosis()
        
        return features
    
    def extract_temporal_features(self, df: pd.DataFrame, timestamp_col: str = 'Timestamp') -> pd.DataFrame:
        """Extract time-based features"""
        features = pd.DataFrame()
        
        if timestamp_col in df.columns:
            df[timestamp_col] = pd.to_datetime(df[timestamp_col])
            
            features['hour'] = df[timestamp_col].dt.hour
            features['day_of_week'] = df[timestamp_col].dt.dayofweek
            features['is_weekend'] = (df[timestamp_col].dt.dayofweek >= 5).astype(int)
            features['is_business_hours'] = ((df[timestamp_col].dt.hour >= 9) & 
                                            (df[timestamp_col].dt.hour <= 17)).astype(int)
        
        return features
    
    def extract_network_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract network-specific features"""
        features = pd.DataFrame()
        
        # Packet size statistics
        if 'Total Length of Fwd Packets' in df.columns:
            features['fwd_packet_size_mean'] = df['Total Length of Fwd Packets'].mean()
            features['fwd_packet_size_std'] = df['Total Length of Fwd Packets'].std()
        
        # Protocol distribution
        if 'Protocol' in df.columns:
            protocol_counts = df['Protocol'].value_counts(normalize=True)
            for protocol, ratio in protocol_counts.items():
                features[f'protocol_{protocol}_ratio'] = ratio
        
        # Port usage patterns
        if 'Destination Port' in df.columns:
            features['unique_dst_ports'] = df['Destination Port'].nunique()
            features['most_common_dst_port'] = df['Destination Port'].mode()[0]
        
        # Connection duration
        if 'Flow Duration' in df.columns:
            features['flow_duration_mean'] = df['Flow Duration'].mean()
            features['flow_duration_std'] = df['Flow Duration'].std()
        
        # Bytes per second
        if 'Flow Bytes/s' in df.columns:
            features['bytes_per_sec_mean'] = df['Flow Bytes/s'].mean()
            features['bytes_per_sec_max'] = df['Flow Bytes/s'].max()
        
        # Packets per second
        if 'Flow Packets/s' in df.columns:
            features['packets_per_sec_mean'] = df['Flow Packets/s'].mean()
            features['packets_per_sec_max'] = df['Flow Packets/s'].max()
        
        return features
    
    def create_feature_store(self, features: pd.DataFrame, metadata: Dict) -> None:
        """Store features with versioning"""
        from pathlib import Path
        import json
        
        # Create feature store directory
        feature_dir = Path(f"data/features/v{self.version}")
        feature_dir.mkdir(parents=True, exist_ok=True)
        
        # Save features
        features.to_parquet(feature_dir / "features.parquet")
        
        # Save metadata
        with open(feature_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
```

---

### Day 5: Model Training - Baseline

**TASK-009: Implement Model Training Service**
- Priority: High
- Story Points: 8
- Dependencies: TASK-008
- Status: Not Started

Description:
Create service to train multiple ML models with MLflow tracking.

Acceptance Criteria:
- [ ] ModelTrainingService class implemented
- [ ] Random Forest training working
- [ ] XGBoost training working
- [ ] Isolation Forest training working
- [ ] All experiments logged to MLflow
- [ ] Model artifacts saved
- [ ] Unit tests written

Implementation:
```python
# src/services/model_training.py
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from xgboost import XGBClassifier
from sklearn.model_selection import cross_val_score
import mlflow
import mlflow.sklearn
from typing import Dict, Tuple
import numpy as np

class ModelTrainingService:
    def __init__(self, mlflow_tracking_uri: str):
        mlflow.set_tracking_uri(mlflow_tracking_uri)
    
    def train_random_forest(self, X_train, y_train, params: Dict = None) -> RandomForestClassifier:
        """Train Random Forest model"""
        if params is None:
            params = {
                'n_estimators': 100,
                'max_depth': 20,
                'min_samples_split': 10,
                'class_weight': 'balanced',
                'random_state': 42,
                'n_jobs': -1
            }
        
        with mlflow.start_run(run_name="random_forest"):
            # Log parameters
            mlflow.log_params(params)
            
            # Train model
            model = RandomForestClassifier(**params)
            model.fit(X_train, y_train)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='f1_weighted')
            mlflow.log_metric("cv_f1_mean", cv_scores.mean())
            mlflow.log_metric("cv_f1_std", cv_scores.std())
            
            # Log model
            mlflow.sklearn.log_model(model, "model")
            
            return model
    
    def train_xgboost(self, X_train, y_train, params: Dict = None) -> XGBClassifier:
        """Train XGBoost model"""
        if params is None:
            params = {
                'n_estimators': 100,
                'max_depth': 10,
                'learning_rate': 0.1,
                'scale_pos_weight': 5,  # Handle imbalance
                'random_state': 42,
                'n_jobs': -1
            }
        
        with mlflow.start_run(run_name="xgboost"):
            mlflow.log_params(params)
            
            model = XGBClassifier(**params)
            model.fit(X_train, y_train)
            
            cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring='f1_weighted')
            mlflow.log_metric("cv_f1_mean", cv_scores.mean())
            mlflow.log_metric("cv_f1_std", cv_scores.std())
            
            mlflow.xgboost.log_model(model, "model")
            
            return model
    
    def train_isolation_forest(self, X_train, params: Dict = None) -> IsolationForest:
        """Train Isolation Forest for anomaly detection"""
        if params is None:
            params = {
                'n_estimators': 100,
                'contamination': 0.1,
                'max_samples': 256,
                'random_state': 42,
                'n_jobs': -1
            }
        
        with mlflow.start_run(run_name="isolation_forest"):
            mlflow.log_params(params)
            
            model = IsolationForest(**params)
            model.fit(X_train)
            
            mlflow.sklearn.log_model(model, "model")
            
            return model
```

---

**TASK-010: Implement Model Evaluation Service**
- Priority: High
- Story Points: 5
- Dependencies: TASK-009
- Status: Not Started

Description:
Create service to comprehensively evaluate trained models.

Acceptance Criteria:
- [ ] ModelEvaluationService class implemented
- [ ] All classification metrics calculated
- [ ] Confusion matrix generated
- [ ] ROC and PR curves plotted
- [ ] Per-class metrics calculated
- [ ] Inference time measured
- [ ] Evaluation report generated
- [ ] Unit tests written

Implementation:
```python
# src/services/model_evaluation.py
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_auc_score, roc_curve, precision_recall_curve,
    classification_report
)
import matplotlib.pyplot as plt
import seaborn as sns
import time
import numpy as np
from typing import Dict, Tuple

class EvaluationResult:
    def __init__(self):
        self.metrics = {}
        self.confusion_matrix = None
        self.classification_report = None
        self.inference_time_ms = 0.0

class ModelEvaluationService:
    def evaluate(self, model, X_test, y_test) -> EvaluationResult:
        """Comprehensive model evaluation"""
        result = EvaluationResult()
        
        # Predictions
        start_time = time.time()
        y_pred = model.predict(X_test)
        inference_time = (time.time() - start_time) * 1000  # ms
        result.inference_time_ms = inference_time / len(X_test)  # per sample
        
        # Calculate metrics
        result.metrics['accuracy'] = accuracy_score(y_test, y_pred)
        result.metrics['precision'] = precision_score(y_test, y_pred, average='weighted')
        result.metrics['recall'] = recall_score(y_test, y_pred, average='weighted')
        result.metrics['f1_score'] = f1_score(y_test, y_pred, average='weighted')
        
        # AUC-ROC (if binary classification)
        if hasattr(model, 'predict_proba'):
            y_proba = model.predict_proba(X_test)
            if y_proba.shape[1] == 2:  # Binary
                result.metrics['auc_roc'] = roc_auc_score(y_test, y_proba[:, 1])
        
        # Confusion matrix
        result.confusion_matrix = confusion_matrix(y_test, y_pred)
        
        # Classification report
        result.classification_report = classification_report(y_test, y_pred)
        
        return result
    
    def plot_confusion_matrix(self, cm, class_names, save_path: str = None):
        """Plot confusion matrix"""
        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                   xticklabels=class_names, yticklabels=class_names)
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        
        if save_path:
            plt.savefig(save_path)
        plt.close()
    
    def plot_roc_curve(self, y_test, y_proba, save_path: str = None):
        """Plot ROC curve"""
        fpr, tpr, _ = roc_curve(y_test, y_proba)
        auc = roc_auc_score(y_test, y_proba)
        
        plt.figure(figsize=(8, 6))
        plt.plot(fpr, tpr, label=f'ROC Curve (AUC = {auc:.3f})')
        plt.plot([0, 1], [0, 1], 'k--', label='Random')
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curve')
        plt.legend()
        
        if save_path:
            plt.savefig(save_path)
        plt.close()
```

---

This is Part 1 of tasks.md. Should I continue with Week 2 and Week 3 tasks?