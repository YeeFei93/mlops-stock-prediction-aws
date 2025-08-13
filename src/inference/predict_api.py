"""
Serverless Inference API for Stock Price Predictions with MLflow Integration
AWS Lambda function for real-time predictions
"""

import json
import boto3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import os
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')

# MLflow integration
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from mlflow_integration.mlflow_manager import MLflowManager

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class StockPredictor:
    def __init__(self, s3_bucket: str):
        """Initialize predictor with S3 bucket and MLflow"""
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3')
        self.models = {}  # Cache for loaded models
        
        # Initialize MLflow manager
        self.mlflow_manager = MLflowManager(
            experiment_name="stock_prediction_inference",
            s3_bucket=s3_bucket
        )
        
    def load_latest_model(self, symbol: str, model_type: str = 'lstm') -> Dict[str, Any]:
        """Load the latest trained model from S3"""
        try:
            # List model objects
            prefix = f"models/{model_type}/{symbol}/"
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                raise FileNotFoundError(f"No models found for {symbol}")
            
            # Get latest model directory
            model_dirs = set()
            for obj in response['Contents']:
                # Extract model directory (timestamp)
                parts = obj['Key'].split('/')
                if len(parts) >= 4:
                    model_dirs.add('/'.join(parts[:4]) + '/')
            
            if not model_dirs:
                raise FileNotFoundError(f"No valid model directories found for {symbol}")
            
            latest_model_dir = max(model_dirs)
            
            # Load model artifacts based on type
            model_artifacts = {}
            
            if model_type == 'lstm':
                # Load Keras model and scaler
                try:
                    import tensorflow as tf
                    import joblib
                    from sklearn.preprocessing import MinMaxScaler
                    
                    # Download model file
                    model_obj = self.s3_client.get_object(
                        Bucket=self.s3_bucket,
                        Key=f"{latest_model_dir}model.h5"
                    )
                    
                    # Save temporarily and load
                    model_path = f"/tmp/{symbol}_model.h5"
                    with open(model_path, 'wb') as f:
                        f.write(model_obj['Body'].read())
                    
                    model_artifacts['model'] = tf.keras.models.load_model(model_path)
                    
                    # Load scaler
                    scaler_obj = self.s3_client.get_object(
                        Bucket=self.s3_bucket,
                        Key=f"{latest_model_dir}scaler.pkl"
                    )
                    
                    scaler_path = f"/tmp/{symbol}_scaler.pkl"
                    with open(scaler_path, 'wb') as f:
                        f.write(scaler_obj['Body'].read())
                    
                    model_artifacts['scaler'] = joblib.load(scaler_path)
                    
                except ImportError as e:
                    logger.error(f"Required libraries not available: {e}")
                    raise
                    
            elif model_type in ['prophet', 'arima']:
                try:
                    import joblib
                    
                    # Load model
                    model_obj = self.s3_client.get_object(
                        Bucket=self.s3_bucket,
                        Key=f"{latest_model_dir}model.pkl"
                    )
                    
                    model_path = f"/tmp/{symbol}_{model_type}.pkl"
                    with open(model_path, 'wb') as f:
                        f.write(model_obj['Body'].read())
                    
                    model_artifacts['model'] = joblib.load(model_path)
                    
                except ImportError as e:
                    logger.error(f"Required libraries not available: {e}")
                    raise
            
            # Load metrics
            try:
                metrics_obj = self.s3_client.get_object(
                    Bucket=self.s3_bucket,
                    Key=f"{latest_model_dir}metrics.json"
                )
                model_artifacts['metrics'] = json.loads(metrics_obj['Body'].read())
            except:
                model_artifacts['metrics'] = {}
            
            # Cache the model
            cache_key = f"{symbol}_{model_type}"
            self.models[cache_key] = model_artifacts
            
            logger.info(f"Loaded model for {symbol} ({model_type})")
            return model_artifacts
            
        except Exception as e:
            logger.error(f"Error loading model for {symbol}: {str(e)}")
            raise
    
    def get_recent_stock_data(self, symbol: str, days: int = 60) -> pd.DataFrame:
        """Get recent stock data for prediction"""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=f"{days}d")
            
            # Add technical indicators (same as training)
            data['MA_5'] = data['Close'].rolling(window=5).mean()
            data['MA_20'] = data['Close'].rolling(window=20).mean()
            data['MA_50'] = data['Close'].rolling(window=50).mean()
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['RSI'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            data['BB_Middle'] = data['Close'].rolling(window=20).mean()
            bb_std = data['Close'].rolling(window=20).std()
            data['BB_Upper'] = data['BB_Middle'] + (bb_std * 2)
            data['BB_Lower'] = data['BB_Middle'] - (bb_std * 2)
            
            # Volume indicators
            data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
            
            return data
            
        except Exception as e:
            logger.error(f"Error fetching recent data for {symbol}: {str(e)}")
            raise
    
    def predict_lstm(self, symbol: str, days_ahead: int = 1) -> Dict[str, Any]:
        """Make LSTM prediction"""
        try:
            # Load model if not cached
            cache_key = f"{symbol}_lstm"
            if cache_key not in self.models:
                self.load_latest_model(symbol, 'lstm')
            
            model_artifacts = self.models[cache_key]
            model = model_artifacts['model']
            scaler = model_artifacts['scaler']
            
            # Get recent data
            data = self.get_recent_stock_data(symbol, 60)
            
            # Prepare features (same as training)
            features = ['Close', 'Volume', 'MA_5', 'MA_20', 'RSI', 'BB_Upper', 'BB_Lower']
            feature_data = data[features].dropna().values
            
            # Scale data
            scaled_data = scaler.transform(feature_data)
            
            # Prepare input for prediction
            lookback = 60
            X = scaled_data[-lookback:].reshape(1, lookback, len(features))
            
            # Make predictions
            predictions = []
            current_input = X.copy()
            
            for _ in range(days_ahead):
                pred = model.predict(current_input, verbose=0)
                predictions.append(pred[0, 0])
                
                # Update input for next prediction (simple approach)
                # In practice, you might want a more sophisticated approach
                current_input = np.roll(current_input, -1, axis=1)
                current_input[0, -1, 0] = pred[0, 0]
            
            # Inverse transform predictions
            # Create dummy array for inverse scaling
            dummy_array = np.zeros((len(predictions), len(features)))
            dummy_array[:, 0] = predictions
            inverse_scaled = scaler.inverse_transform(dummy_array)
            final_predictions = inverse_scaled[:, 0].tolist()
            
            return {
                'symbol': symbol,
                'model_type': 'lstm',
                'predictions': final_predictions,
                'current_price': float(data['Close'].iloc[-1]),
                'prediction_dates': [(datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d') 
                                   for i in range(days_ahead)],
                'confidence': 'medium',  # Could implement proper confidence intervals
                'metrics': model_artifacts.get('metrics', {})
            }
            
        except Exception as e:
            logger.error(f"Error making LSTM prediction: {str(e)}")
            raise
    
    def predict_prophet(self, symbol: str, days_ahead: int = 1) -> Dict[str, Any]:
        """Make Prophet prediction"""
        try:
            # Load model if not cached
            cache_key = f"{symbol}_prophet"
            if cache_key not in self.models:
                self.load_latest_model(symbol, 'prophet')
            
            model = self.models[cache_key]['model']
            
            # Create future dates
            future = model.make_future_dataframe(periods=days_ahead)
            forecast = model.predict(future)
            
            # Get recent data for current price
            data = self.get_recent_stock_data(symbol, 5)
            
            # Extract predictions
            predictions = forecast['yhat'].tail(days_ahead).tolist()
            lower_bounds = forecast['yhat_lower'].tail(days_ahead).tolist()
            upper_bounds = forecast['yhat_upper'].tail(days_ahead).tolist()
            
            return {
                'symbol': symbol,
                'model_type': 'prophet',
                'predictions': predictions,
                'lower_bounds': lower_bounds,
                'upper_bounds': upper_bounds,
                'current_price': float(data['Close'].iloc[-1]),
                'prediction_dates': [(datetime.now() + timedelta(days=i+1)).strftime('%Y-%m-%d') 
                                   for i in range(days_ahead)],
                'confidence': 'high',  # Prophet provides confidence intervals
                'metrics': self.models[cache_key].get('metrics', {})
            }
            
        except Exception as e:
            logger.error(f"Error making Prophet prediction: {str(e)}")
            raise

def lambda_handler(event, context):
    """
    AWS Lambda handler for stock price predictions
    
    Expected event format:
    {
        "symbol": "AAPL",
        "model_type": "lstm",
        "days_ahead": 5
    }
    """
    try:
        # Parse request
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        symbol = body.get('symbol', 'AAPL').upper()
        model_type = body.get('model_type', 'lstm').lower()
        days_ahead = min(body.get('days_ahead', 1), 30)  # Limit to 30 days
        
        # Validate inputs
        if model_type not in ['lstm', 'prophet', 'arima']:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Initialize predictor
        s3_bucket = os.environ.get('S3_BUCKET', 'mlops-stock-data')
        predictor = StockPredictor(s3_bucket)
        
        # Make prediction based on model type
        if model_type == 'lstm':
            result = predictor.predict_lstm(symbol, days_ahead)
        elif model_type == 'prophet':
            result = predictor.predict_prophet(symbol, days_ahead)
        else:
            raise NotImplementedError(f"Prediction for {model_type} not yet implemented")
        
        # Add metadata
        result.update({
            'timestamp': datetime.now().isoformat(),
            'request_id': context.aws_request_id if context else 'local-test',
            'status': 'success'
        })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(result, default=str)
        }
        
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'status': 'error',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }

# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        'symbol': 'AAPL',
        'model_type': 'prophet',
        'days_ahead': 5
    }
    
    class MockContext:
        aws_request_id = 'test-request'
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(json.loads(result['body']), indent=2))
