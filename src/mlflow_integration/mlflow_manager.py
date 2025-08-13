"""
MLflow integration for MLOps Stock Prediction Pipeline
Handles experiment tracking, model versioning, and model registry
"""

import mlflow
import mlflow.tensorflow
import mlflow.sklearn
import mlflow.pytorch
from mlflow.tracking import MlflowClient
import os
import boto3
import json
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class MLflowManager:
    def __init__(self, 
                 experiment_name: str = "stock_prediction",
                 s3_bucket: str = None,
                 tracking_uri: str = None):
        """
        Initialize MLflow manager
        
        Args:
            experiment_name: Name of the MLflow experiment
            s3_bucket: S3 bucket for artifact storage
            tracking_uri: MLflow tracking server URI (optional)
        """
        self.experiment_name = experiment_name
        self.s3_bucket = s3_bucket
        self.client = MlflowClient()
        
        # Set tracking URI - use remote server or local
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)
        elif os.environ.get('MLFLOW_TRACKING_URI'):
            mlflow.set_tracking_uri(os.environ.get('MLFLOW_TRACKING_URI'))
        else:
            # Use local SQLite for development
            mlflow.set_tracking_uri("sqlite:///mlflow.db")
        
        # Set artifact URI to S3 if available
        if s3_bucket:
            artifact_uri = f"s3://{s3_bucket}/mlflow-artifacts/"
            os.environ['MLFLOW_ARTIFACT_URI'] = artifact_uri
        
        # Create or get experiment
        try:
            self.experiment_id = mlflow.create_experiment(
                experiment_name,
                artifact_location=os.environ.get('MLFLOW_ARTIFACT_URI')
            )
        except mlflow.exceptions.MlflowException:
            # Experiment already exists
            experiment = mlflow.get_experiment_by_name(experiment_name)
            self.experiment_id = experiment.experiment_id
        
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow experiment set to: {experiment_name}")
    
    def start_run(self, run_name: str = None, tags: Dict[str, str] = None) -> mlflow.ActiveRun:
        """Start a new MLflow run"""
        if run_name is None:
            run_name = f"stock_prediction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        run = mlflow.start_run(run_name=run_name)
        
        # Set default tags
        default_tags = {
            "project": "stock_prediction",
            "environment": os.environ.get('ENVIRONMENT', 'dev'),
            "version": "1.0.0"
        }
        
        if tags:
            default_tags.update(tags)
        
        for key, value in default_tags.items():
            mlflow.set_tag(key, value)
        
        return run
    
    def log_stock_data_info(self, symbol: str, data_shape: tuple, date_range: str):
        """Log stock data information"""
        mlflow.log_param("symbol", symbol)
        mlflow.log_param("data_rows", data_shape[0])
        mlflow.log_param("data_columns", data_shape[1])
        mlflow.log_param("date_range", date_range)
    
    def log_model_params(self, model_type: str, model_params: Dict[str, Any]):
        """Log model parameters"""
        mlflow.log_param("model_type", model_type)
        
        for key, value in model_params.items():
            mlflow.log_param(f"model_{key}", value)
    
    def log_training_metrics(self, metrics: Dict[str, float], step: int = None):
        """Log training metrics"""
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value, step=step)
    
    def log_model_artifacts(self, 
                          model, 
                          model_type: str,
                          symbol: str,
                          additional_artifacts: Dict[str, Any] = None):
        """Log model and associated artifacts"""
        
        # Log the model based on type
        if model_type == 'lstm':
            mlflow.tensorflow.log_model(
                model,
                artifact_path="model",
                registered_model_name=f"stock_prediction_lstm_{symbol}",
                signature=None  # You can add input/output signature
            )
        elif model_type == 'prophet':
            mlflow.sklearn.log_model(
                model,
                artifact_path="model",
                registered_model_name=f"stock_prediction_prophet_{symbol}"
            )
        elif model_type == 'arima':
            mlflow.sklearn.log_model(
                model,
                artifact_path="model", 
                registered_model_name=f"stock_prediction_arima_{symbol}"
            )
        
        # Log additional artifacts
        if additional_artifacts:
            for artifact_name, artifact in additional_artifacts.items():
                if isinstance(artifact, dict):
                    # Save as JSON
                    with open(f"/tmp/{artifact_name}.json", 'w') as f:
                        json.dump(artifact, f, default=str, indent=2)
                    mlflow.log_artifact(f"/tmp/{artifact_name}.json")
                else:
                    # Save as pickle
                    import joblib
                    artifact_path = f"/tmp/{artifact_name}.pkl"
                    joblib.dump(artifact, artifact_path)
                    mlflow.log_artifact(artifact_path)
    
    def register_model(self, 
                      model_name: str, 
                      model_version: str = None,
                      stage: str = "Staging") -> str:
        """Register model in MLflow Model Registry"""
        try:
            # Create registered model if it doesn't exist
            try:
                self.client.create_registered_model(model_name)
                logger.info(f"Created new registered model: {model_name}")
            except mlflow.exceptions.MlflowException:
                logger.info(f"Registered model {model_name} already exists")
            
            # Get latest version if not specified
            if model_version is None:
                latest_versions = self.client.get_latest_versions(
                    model_name, 
                    stages=["None", "Staging", "Production"]
                )
                if latest_versions:
                    model_version = str(max([int(v.version) for v in latest_versions]) + 1)
                else:
                    model_version = "1"
            
            # Transition model to specified stage
            self.client.transition_model_version_stage(
                name=model_name,
                version=model_version,
                stage=stage
            )
            
            logger.info(f"Model {model_name} version {model_version} transitioned to {stage}")
            return model_version
            
        except Exception as e:
            logger.error(f"Error registering model: {str(e)}")
            raise
    
    def load_model(self, model_name: str, stage: str = "Production"):
        """Load model from MLflow Model Registry"""
        try:
            model_uri = f"models:/{model_name}/{stage}"
            model = mlflow.pyfunc.load_model(model_uri)
            logger.info(f"Loaded model {model_name} from {stage} stage")
            return model
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def get_model_info(self, model_name: str, stage: str = "Production") -> Dict[str, Any]:
        """Get model information from registry"""
        try:
            model_version = self.client.get_latest_versions(
                model_name, 
                stages=[stage]
            )[0]
            
            return {
                "name": model_version.name,
                "version": model_version.version,
                "stage": model_version.current_stage,
                "creation_timestamp": model_version.creation_timestamp,
                "last_updated_timestamp": model_version.last_updated_timestamp,
                "description": model_version.description,
                "run_id": model_version.run_id
            }
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {}
    
    def compare_models(self, run_ids: list) -> Dict[str, Any]:
        """Compare multiple model runs"""
        comparison_data = {
            "runs": [],
            "metrics": {}
        }
        
        for run_id in run_ids:
            run = self.client.get_run(run_id)
            run_data = {
                "run_id": run_id,
                "params": run.data.params,
                "metrics": run.data.metrics,
                "start_time": run.info.start_time,
                "end_time": run.info.end_time,
                "status": run.info.status
            }
            comparison_data["runs"].append(run_data)
        
        # Aggregate metrics for comparison
        all_metrics = set()
        for run_data in comparison_data["runs"]:
            all_metrics.update(run_data["metrics"].keys())
        
        for metric in all_metrics:
            comparison_data["metrics"][metric] = [
                run_data["metrics"].get(metric, None) 
                for run_data in comparison_data["runs"]
            ]
        
        return comparison_data
    
    def promote_model(self, 
                     model_name: str, 
                     version: str,
                     from_stage: str = "Staging",
                     to_stage: str = "Production"):
        """Promote model from one stage to another"""
        try:
            # Get current production models and archive them
            if to_stage == "Production":
                current_prod_models = self.client.get_latest_versions(
                    model_name, 
                    stages=["Production"]
                )
                
                for model in current_prod_models:
                    self.client.transition_model_version_stage(
                        name=model_name,
                        version=model.version,
                        stage="Archived"
                    )
                    logger.info(f"Archived model version {model.version}")
            
            # Promote the new model
            self.client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=to_stage
            )
            
            logger.info(f"Promoted model {model_name} v{version} to {to_stage}")
            
        except Exception as e:
            logger.error(f"Error promoting model: {str(e)}")
            raise

def setup_mlflow_server():
    """Setup MLflow tracking server on AWS (optional)"""
    # This would typically be done via CloudFormation or Terraform
    # For now, we'll use local tracking or provide instructions
    
    print("""
    To setup MLflow tracking server on AWS:
    
    1. Launch EC2 instance (t3.micro for cost optimization)
    2. Install MLflow: pip install mlflow psycopg2-binary boto3
    3. Setup PostgreSQL RDS (db.t3.micro)
    4. Configure S3 bucket for artifacts
    5. Start MLflow server:
       mlflow server \\
         --backend-store-uri postgresql://user:pass@rds-endpoint:5432/mlflow \\
         --default-artifact-root s3://your-mlflow-bucket/artifacts \\
         --host 0.0.0.0 \\
         --port 5000
    
    Estimated monthly cost: $15-25 (EC2 + RDS)
    """)

if __name__ == "__main__":
    # Example usage
    mlflow_manager = MLflowManager(
        experiment_name="stock_prediction_test",
        s3_bucket="mlops-stock-data"
    )
    
    # Start a run
    with mlflow_manager.start_run(run_name="test_run") as run:
        # Log some test data
        mlflow_manager.log_stock_data_info("AAPL", (252, 7), "2023-01-01 to 2023-12-31")
        mlflow_manager.log_model_params("lstm", {"epochs": 50, "batch_size": 32})
        mlflow_manager.log_training_metrics({"mae": 2.5, "rmse": 3.2, "r2": 0.85})
        
        print(f"Run ID: {run.info.run_id}")
        print("MLflow integration test completed!")
