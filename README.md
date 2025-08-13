# MLOps Stock Price Prediction Pipeline on AWS EKS

A cost-effective MLOps pipeline for stock price prediction using AWS services with minimal infrastructure costs.

## 🎯 Project Overview

This project demonstrates a complete MLOps workflow for predicting stock prices using:
- **Machine Learning**: Time series forecasting with LSTM/Prophet models
- **Data Pipeline**: Automated data ingestion from financial APIs
- **Model Training**: Scheduled retraining with AWS Batch (Spot instances)
- **Deployment**: Serverless inference with AWS Lambda
- **Monitoring**: Model performance tracking with CloudWatch
- **CI/CD**: Automated deployment with GitHub Actions

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  AWS S3 Bucket  │───▶│  Model Training │
│ (Alpha Vantage, │    │  (Data Lake)    │    │  (AWS Batch)    │
│  Yahoo Finance) │    └─────────────────┘    └─────────────────┘
└─────────────────┘                                     │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │◀───│ AWS Lambda      │◀───│ Model Registry  │
│  (REST API)     │    │ (Inference)     │    │  (S3 + ECR)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 💰 Cost Optimization Strategy

- **Serverless-First**: Lambda for inference, Batch for training
- **Spot Instances**: Up to 90% savings on training compute
- **S3 Lifecycle**: Automated data archiving to reduce storage costs
- **Pay-per-Use**: No idle infrastructure costs
- **Free Tier**: Leverage AWS free tier services

**Estimated Monthly Cost**: $15-30 for moderate usage

## 🚀 Features

- [x] Real-time stock data ingestion
- [x] Automated feature engineering  
- [x] Multiple ML models (LSTM, Prophet, ARIMA)
- [x] **MLflow experiment tracking and model registry**
- [x] **Model versioning and comparison**
- [x] **Automated model deployment pipeline**
- [x] Serverless API for predictions
- [x] Monitoring and alerting
- [x] Cost optimization

## 📊 Supported Stock Predictions

- **Individual Stocks**: AAPL, GOOGL, MSFT, TSLA, AMZN
- **Indices**: S&P 500, NASDAQ, DOW
- **Prediction Horizons**: 1-day, 1-week, 1-month
- **Features**: Price, volume, technical indicators, sentiment analysis

## 🛠️ Quick Start

### 1. Local Development Setup
```bash
# Clone and setup
git clone <your-repo-url>
cd mlops-stock-prediction-aws

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Test locally
python local_setup.py
```

### 2. AWS Infrastructure Deployment
```bash
# Configure AWS CLI
aws configure

# Deploy infrastructure
aws cloudformation deploy \
  --template-file infrastructure/cloudformation-template.yaml \
  --stack-name mlops-stock-prediction \
  --parameter-overrides Environment=dev \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### 3. API Usage
```bash
# Make predictions
curl -X POST https://your-api-url/dev/predict \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "model_type": "prophet",
    "days_ahead": 5
  }'
```

## 📁 Project Structure
```
├── src/
│   ├── data_ingestion/         # Data collection from APIs
│   ├── model_training/         # ML model training with MLflow
│   ├── inference/              # Prediction API with MLflow model loading
│   └── mlflow_integration/     # MLflow setup and utilities
├── infrastructure/             # CloudFormation templates
├── tests/                      # Unit tests
├── .github/workflows/          # CI/CD pipeline
├── requirements.txt            # Python dependencies
└── local_setup.py             # Local testing script
```

## 💡 Cost Optimization Tips

1. **Use Spot Instances**: Save up to 90% on training costs
2. **Lambda Cold Starts**: Keep functions warm with CloudWatch events
3. **S3 Lifecycle**: Automatically archive old data
4. **Reserved Capacity**: For consistent workloads
5. **Monitoring**: Set up billing alerts

## 🔧 Development Workflow

1. **Data Collection**: Scheduled Lambda (daily at 9 AM UTC)
2. **Model Training**: Weekly batch jobs on Spot instances with MLflow tracking
3. **Model Registry**: Automated model versioning and stage transitions
4. **Model Deployment**: Automated via GitHub Actions with MLflow model loading
5. **Monitoring**: CloudWatch dashboards, MLflow metrics, and alerts
6. **Cost Tracking**: Monthly cost analysis reports

## 📊 MLflow Integration

### Experiment Tracking
- **Automatic logging** of all training runs
- **Parameter tracking**: Model hyperparameters, data splits
- **Metrics tracking**: MAE, RMSE, R², validation loss
- **Artifact storage**: Models, scalers, training plots

### Model Registry
- **Versioned models** with stage management (Staging → Production)
- **Model comparison** across different algorithms
- **Automated model promotion** based on performance metrics
- **Model lineage** tracking from data to deployment

### Setup MLflow (Choose one option):

#### Option 1: Local Development
```bash
# Local SQLite backend
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
mlflow ui --port 5000
# Access: http://localhost:5000
```

#### Option 2: AWS S3 Backend (Recommended)
```bash
# S3 for artifacts, local SQLite for metadata
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"  
export MLFLOW_ARTIFACT_URI="s3://your-mlflow-bucket/artifacts"
mlflow ui --port 5000
```

#### Option 3: Full AWS Setup (Production)
```bash
# Deploy MLflow server on EC2 with RDS backend
aws cloudformation deploy \
  --template-file src/mlflow_integration/mlflow-infrastructure.json \
  --stack-name mlflow-tracking-server \
  --capabilities CAPABILITY_IAM

# Set environment variable
export MLFLOW_TRACKING_URI="http://your-mlflow-server:5000"
```

### MLflow Costs:
- **Option 1** (Local): $0
- **Option 2** (S3): $1-3/month (S3 storage)
- **Option 3** (Full AWS): $15-25/month (EC2 t3.micro + RDS db.t3.micro)

## 📈 Model Performance

- **LSTM**: Good for short-term predictions (1-7 days)
- **Prophet**: Excellent for trend analysis (1-30 days)  
- **ARIMA**: Traditional time series (baseline model)

Expected accuracy: 60-75% directional accuracy for next-day predictions.

## 🚨 Monitoring & Alerts

- **Model Drift**: Automatic retraining triggers
- **API Performance**: <200ms response time target
- **Cost Alerts**: $50 monthly budget threshold
- **Data Quality**: Missing data detection

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-model`
3. Run tests: `pytest tests/`
4. Submit pull request

## 📜 License

MIT License - See LICENSE file for details.