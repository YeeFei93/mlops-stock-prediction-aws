#!/usr/bin/env python3
"""
Quick model training script - Run this to train your first model!
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import mlflow
import mlflow.sklearn

def train_stock_model(symbol='AAPL'):
    """Train a simple stock prediction model"""
    print(f"🚀 Training model for {symbol}...")
    
    # Get real stock data
    import yfinance as yf
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1y")
    
    # Add technical indicators
    data['MA_5'] = data['Close'].rolling(5).mean()
    data['MA_20'] = data['Close'].rolling(20).mean()
    data['RSI'] = 50  # Simplified RSI
    data['Volume_MA'] = data['Volume'].rolling(20).mean()
    
    data = data.dropna()
    print(f"✅ Data collected: {len(data)} days for {symbol}")
    
    # Set up MLflow
    mlflow.set_experiment(f"stock_prediction_{symbol}")
    
    with mlflow.start_run(run_name=f"{symbol}_training_{datetime.now().strftime('%m%d_%H%M')}"):
        
        # Prepare features
        features = ['MA_5', 'MA_20', 'RSI', 'Volume_MA'] 
        X = data[features]
        y = data['Close'].shift(-1).dropna()  # Next day price
        X = X[:-1]  # Remove last row to match y
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, shuffle=False
        )
        
        # Train model
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # Predictions and metrics
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        # Log to MLflow
        mlflow.log_param("symbol", symbol)
        mlflow.log_param("features", features)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2", r2)
        
        # Log model
        mlflow.sklearn.log_model(
            model, 
            "model",
            registered_model_name=f"stock_predictor_{symbol}"
        )
        
        print(f"✅ Model trained!")
        print(f"   MAE: ${mae:.2f}")
        print(f"   R²: {r2:.4f}")
        print(f"   Latest price: ${data['Close'].iloc[-1]:.2f}")
        print(f"   Prediction for tomorrow: ${model.predict(X.iloc[[-1]])[0]:.2f}")
        
        return model, mae, r2

if __name__ == "__main__":
    # Train models for different stocks
    symbols = ['AAPL', 'GOOGL', 'MSFT']
    
    results = {}
    for symbol in symbols:
        try:
            model, mae, r2 = train_stock_model(symbol)
            results[symbol] = {'mae': mae, 'r2': r2}
        except Exception as e:
            print(f"❌ Failed to train {symbol}: {e}")
    
    print("\n📊 Training Summary:")
    print("-" * 40)
    for symbol, metrics in results.items():
        print(f"{symbol}: MAE=${metrics['mae']:.2f}, R²={metrics['r2']:.4f}")
    
    print(f"\n🔬 View results in MLflow UI: http://localhost:5000")
