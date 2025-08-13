"""
Stock Price Prediction Model Training with MLflow Integration
Supports LSTM, Prophet, and ARIMA models
"""

import os
import boto3
import pandas as pd
import numpy as np
from datetime import datetime
import joblib
import logging
from typing import Tuple, Dict, Any
import warnings
warnings.filterwarnings('ignore')

# MLflow integration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mlflow_integration.mlflow_manager import MLflowManager

# ML Libraries
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA

class StockPricePredictor:
    def __init__(self, s3_bucket: str, model_type: str = 'lstm'):
        """
        Initialize Stock Price Predictor with MLflow integration
        
        Args:
            s3_bucket: S3 bucket for model artifacts
            model_type: Type of model ('lstm', 'prophet', 'arima')
        """
        self.s3_bucket = s3_bucket
        self.model_type = model_type.lower()
        self.s3_client = boto3.client('s3')
        self.scaler = MinMaxScaler()
        self.model = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize MLflow
        self.mlflow_manager = MLflowManager(
            experiment_name=f"stock_prediction_{model_type}",
            s3_bucket=s3_bucket
        )
        
    def load_data_from_s3(self, symbol: str, prefix: str = "raw-data") -> pd.DataFrame:
        """Load stock data from S3"""
        try:
            # List objects with the prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=f"{prefix}/{symbol}/"
            )
            
            # Get the latest file
            objects = response.get('Contents', [])
            if not objects:
                raise FileNotFoundError(f"No data found for {symbol}")
                
            latest_object = max(objects, key=lambda x: x['LastModified'])
            
            # Download and read the parquet file
            obj = self.s3_client.get_object(
                Bucket=self.s3_bucket,
                Key=latest_object['Key']
            )
            
            df = pd.read_parquet(obj['Body'])
            return df
            
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {str(e)}")
            raise
    
    def prepare_lstm_data(self, df: pd.DataFrame, lookback: int = 60) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare data for LSTM model"""
        # Use Close price and technical indicators
        features = ['Close', 'Volume', 'MA_5', 'MA_20', 'RSI', 'BB_Upper', 'BB_Lower']
        data = df[features].dropna().values
        
        # Scale the data
        scaled_data = self.scaler.fit_transform(data)
        
        X, y = [], []
        for i in range(lookback, len(scaled_data)):
            X.append(scaled_data[i-lookback:i])
            y.append(scaled_data[i, 0])  # Predict Close price
            
        return np.array(X), np.array(y)
    
    def build_lstm_model(self, input_shape: Tuple[int, int]) -> tf.keras.Model:
        """Build LSTM model architecture"""
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=input_shape),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(25),
            Dense(1)
        ])
        
        model.compile(
            optimizer='adam',
            loss='mean_squared_error',
            metrics=['mae']
        )
        
        return model
    
    def train_lstm(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train LSTM model with MLflow tracking"""
        with self.mlflow_manager.start_run(
            run_name=f"lstm_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ) as run:
            
            # Log dataset info
            self.mlflow_manager.log_stock_data_info(
                symbol="stock_data", 
                data_shape=df.shape,
                date_range=f"{df.index[0]} to {df.index[-1]}"
            )
            
            X, y = self.prepare_lstm_data(df)
            
            # Split data
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]
            
            # Build and train model
            self.model = self.build_lstm_model((X.shape[1], X.shape[2]))
            
            # Log model parameters
            model_params = {
                "epochs": 50,
                "batch_size": 32,
                "lookback_window": 60,
                "lstm_units": 50,
                "dropout_rate": 0.2,
                "train_test_split": 0.8
            }
            self.mlflow_manager.log_model_params("lstm", model_params)
            
            # Train with callbacks for MLflow logging
            history = self.model.fit(
                X_train, y_train,
                batch_size=32,
                epochs=50,
                validation_data=(X_test, y_test),
                verbose=0
            )
            
            # Log training metrics by epoch
            for epoch, (loss, val_loss) in enumerate(zip(
                history.history['loss'], 
                history.history['val_loss']
            )):
                self.mlflow_manager.log_training_metrics({
                    "train_loss": loss,
                    "val_loss": val_loss,
                    "train_mae": history.history['mae'][epoch],
                    "val_mae": history.history['val_mae'][epoch]
                }, step=epoch)
            
            # Evaluate model
            y_pred = self.model.predict(X_test)
            metrics = self._calculate_metrics(y_test, y_pred)
            
            # Log final metrics
            self.mlflow_manager.log_training_metrics(metrics)
            
            # Log model and artifacts
            self.mlflow_manager.log_model_artifacts(
                model=self.model,
                model_type="lstm",
                symbol="stock",
                additional_artifacts={
                    "scaler": self.scaler,
                    "training_history": history.history,
                    "model_config": model_params
                }
            )
            
            return {
                'model': self.model,
                'scaler': self.scaler,
                'metrics': metrics,
                'history': history.history,
                'run_id': run.info.run_id
            }
    
    def train_prophet(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Train Prophet model with MLflow tracking"""
        with self.mlflow_manager.start_run(
            run_name=f"prophet_training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ) as run:
            
            # Log dataset info
            self.mlflow_manager.log_stock_data_info(
                symbol="stock_data",
                data_shape=df.shape, 
                date_range=f"{df.index[0]} to {df.index[-1]}"
            )
            
            # Prepare data for Prophet
            prophet_df = df.reset_index()[['Date', 'Close']].rename(
                columns={'Date': 'ds', 'Close': 'y'}
            )
            
            # Split data
            split_idx = int(len(prophet_df) * 0.8)
            train_df = prophet_df[:split_idx]
            test_df = prophet_df[split_idx:]
            
            # Model parameters
            model_params = {
                "daily_seasonality": True,
                "weekly_seasonality": True,
                "yearly_seasonality": True,
                "changepoint_prior_scale": 0.05,
                "seasonality_prior_scale": 10.0
            }
            
            # Log model parameters
            self.mlflow_manager.log_model_params("prophet", model_params)
            
            # Train model
            self.model = Prophet(**model_params)
            self.model.fit(train_df)
            
            # Make predictions on test set
            future = self.model.make_future_dataframe(periods=len(test_df))
            forecast = self.model.predict(future)
            
            # Calculate metrics
            y_test = test_df['y'].values
            y_pred = forecast['yhat'].iloc[split_idx:].values
            metrics = self._calculate_metrics(y_test, y_pred)
            
            # Log metrics
            self.mlflow_manager.log_training_metrics(metrics)
            
            # Log model and artifacts
            self.mlflow_manager.log_model_artifacts(
                model=self.model,
                model_type="prophet",
                symbol="stock",
                additional_artifacts={
                    "forecast": forecast.to_dict(),
                    "model_params": model_params,
                    "components": self.model.predict_components(future).to_dict()
                }
            )
            
            return {
                'model': self.model,
                'metrics': metrics,
                'forecast': forecast,
                'run_id': run.info.run_id
            }
    
    def train_arima(self, df: pd.DataFrame, order: Tuple[int, int, int] = (5, 1, 0)) -> Dict[str, Any]:
        """Train ARIMA model"""
        # Prepare data
        close_prices = df['Close'].dropna()
        
        # Split data
        split_idx = int(len(close_prices) * 0.8)
        train_data = close_prices[:split_idx]
        test_data = close_prices[split_idx:]
        
        # Train model
        self.model = ARIMA(train_data, order=order)
        fitted_model = self.model.fit()
        
        # Make predictions
        y_pred = fitted_model.forecast(steps=len(test_data))
        metrics = self._calculate_metrics(test_data.values, y_pred)
        
        return {
            'model': fitted_model,
            'metrics': metrics
        }
    
    def _calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate model performance metrics"""
        return {
            'mae': mean_absolute_error(y_true, y_pred),
            'mse': mean_squared_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'r2': r2_score(y_true, y_pred)
        }
    
    def save_model_to_s3(self, model_artifacts: Dict[str, Any], symbol: str) -> str:
        """Save model artifacts to S3"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_key = f"models/{self.model_type}/{symbol}/{timestamp}/"
        
        try:
            if self.model_type == 'lstm':
                # Save Keras model
                model_path = f"/tmp/{symbol}_lstm_model.h5"
                model_artifacts['model'].save(model_path)
                
                with open(model_path, 'rb') as f:
                    self.s3_client.put_object(
                        Bucket=self.s3_bucket,
                        Key=f"{model_key}model.h5",
                        Body=f.read()
                    )
                
                # Save scaler
                scaler_path = f"/tmp/{symbol}_scaler.pkl"
                joblib.dump(model_artifacts['scaler'], scaler_path)
                
                with open(scaler_path, 'rb') as f:
                    self.s3_client.put_object(
                        Bucket=self.s3_bucket,
                        Key=f"{model_key}scaler.pkl",
                        Body=f.read()
                    )
            
            elif self.model_type in ['prophet', 'arima']:
                # Save model with joblib
                model_path = f"/tmp/{symbol}_{self.model_type}_model.pkl"
                joblib.dump(model_artifacts['model'], model_path)
                
                with open(model_path, 'rb') as f:
                    self.s3_client.put_object(
                        Bucket=self.s3_bucket,
                        Key=f"{model_key}model.pkl",
                        Body=f.read()
                    )
            
            # Save metrics
            metrics_key = f"{model_key}metrics.json"
            import json
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=metrics_key,
                Body=json.dumps(model_artifacts['metrics'])
            )
            
            self.logger.info(f"Model saved to s3://{self.s3_bucket}/{model_key}")
            return model_key
            
        except Exception as e:
            self.logger.error(f"Error saving model: {str(e)}")
            raise

def train_model(symbol: str, model_type: str = 'lstm'):
    """Training function for batch job"""
    S3_BUCKET = os.environ.get('S3_BUCKET', 'mlops-stock-data')
    
    predictor = StockPricePredictor(S3_BUCKET, model_type)
    
    # Load data
    df = predictor.load_data_from_s3(symbol)
    
    # Train model based on type
    if model_type == 'lstm':
        model_artifacts = predictor.train_lstm(df)
    elif model_type == 'prophet':
        model_artifacts = predictor.train_prophet(df)
    elif model_type == 'arima':
        model_artifacts = predictor.train_arima(df)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
    
    # Save model
    model_key = predictor.save_model_to_s3(model_artifacts, symbol)
    
    print(f"Training completed for {symbol} using {model_type}")
    print(f"Metrics: {model_artifacts['metrics']}")
    print(f"Model saved to: {model_key}")

if __name__ == "__main__":
    import sys
    symbol = sys.argv[1] if len(sys.argv) > 1 else 'AAPL'
    model_type = sys.argv[2] if len(sys.argv) > 2 else 'lstm'
    train_model(symbol, model_type)
