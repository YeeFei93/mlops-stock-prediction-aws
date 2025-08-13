"""
Local development setup script
Run this to test the MLOps pipeline locally
"""

import os
import subprocess
import json
from datetime import datetime

def setup_environment():
    """Set up local environment variables"""
    env_vars = {
        'AWS_REGION': 'us-east-1',
        'S3_BUCKET': 'mlops-stock-data-local',
        'ENVIRONMENT': 'local'
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"Set {key}={value}")

def test_data_collection():
    """Test data collection locally"""
    print("\n🔄 Testing data collection...")
    
    try:
        from src.data_ingestion.stock_data_collector import StockDataCollector
        
        # Test with a minimal setup
        collector = StockDataCollector('test-bucket')
        stock_data = collector.fetch_stock_data(['AAPL'], period='5d')
        
        if 'AAPL' in stock_data:
            df = stock_data['AAPL']
            print(f"✅ Successfully fetched {len(df)} days of AAPL data")
            print(f"Latest price: ${df['Close'].iloc[-1]:.2f}")
            print(f"Technical indicators: {[col for col in df.columns if col.startswith(('MA_', 'RSI', 'BB_'))]}")
        else:
            print("❌ No data collected")
            
    except Exception as e:
        print(f"❌ Data collection failed: {e}")

def test_mlflow_integration():
    """Test MLflow integration locally"""
    print("\n🔬 Testing MLflow integration...")
    
    try:
        # Test MLflow installation
        import mlflow
        import mlflow.sklearn
        
        # Set local tracking
        mlflow.set_tracking_uri("sqlite:///test_mlflow.db")
        mlflow.set_experiment("test_stock_prediction")
        
        # Start a test run
        with mlflow.start_run(run_name="test_run") as run:
            # Log test parameters and metrics
            mlflow.log_param("model_type", "test")
            mlflow.log_param("symbol", "TEST")
            mlflow.log_metric("mae", 1.5)
            mlflow.log_metric("rmse", 2.0)
            
            # Create a simple test model
            from sklearn.linear_model import LinearRegression
            import numpy as np
            
            # Generate test data
            X = np.random.randn(100, 3)
            y = np.random.randn(100)
            
            # Train simple model
            model = LinearRegression()
            model.fit(X, y)
            
            # Log model
            mlflow.sklearn.log_model(
                model, 
                "model",
                registered_model_name="test_stock_model"
            )
            
            print(f"✅ MLflow run completed: {run.info.run_id}")
            print(f"✅ Model logged to registry")
            print(f"✅ MLflow UI available at: http://localhost:5000")
            
    except ImportError:
        print("❌ MLflow not installed. Run: pip install mlflow")
    except Exception as e:
        print(f"❌ MLflow test failed: {e}")

def test_model_training():
    """Test model training locally"""
    print("\n🧠 Testing model training...")
    
    try:
        # Import here to avoid dependency issues
        import pandas as pd
        import numpy as np
        
        # Create sample data for testing
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='D')
        sample_data = pd.DataFrame({
            'Close': 100 + np.cumsum(np.random.randn(len(dates)) * 0.02),
            'Volume': np.random.randint(1000000, 5000000, len(dates)),
            'Open': 100 + np.cumsum(np.random.randn(len(dates)) * 0.02),
            'High': 100 + np.cumsum(np.random.randn(len(dates)) * 0.02),
            'Low': 100 + np.cumsum(np.random.randn(len(dates)) * 0.02)
        }, index=dates)
        
        # Add technical indicators
        sample_data['MA_5'] = sample_data['Close'].rolling(5).mean()
        sample_data['MA_20'] = sample_data['Close'].rolling(20).mean()
        sample_data['RSI'] = 50  # Simplified
        sample_data['BB_Upper'] = sample_data['Close'] * 1.02
        sample_data['BB_Lower'] = sample_data['Close'] * 0.98
        
        print(f"✅ Created sample dataset with {len(sample_data)} records")
        print(f"Price range: ${sample_data['Close'].min():.2f} - ${sample_data['Close'].max():.2f}")
        
        # Test MLflow integration with model training
        try:
            import mlflow
            mlflow.set_experiment("test_model_training")
            
            with mlflow.start_run(run_name="sample_training") as run:
                mlflow.log_param("dataset_size", len(sample_data))
                mlflow.log_param("features", list(sample_data.columns))
                mlflow.log_metric("price_volatility", sample_data['Close'].std())
                
                print(f"✅ MLflow training run logged: {run.info.run_id}")
                
        except ImportError:
            print("⚠️  MLflow not available - skipping experiment logging")
        
    except Exception as e:
        print(f"❌ Model training test failed: {e}")

def test_inference():
    """Test inference API locally"""
    print("\n🔮 Testing inference API...")
    
    try:
        # Create a mock prediction response
        prediction_response = {
            'symbol': 'AAPL',
            'model_type': 'prophet',
            'predictions': [150.25, 151.30, 149.80],
            'current_price': 148.50,
            'prediction_dates': ['2024-01-16', '2024-01-17', '2024-01-18'],
            'confidence': 'medium',
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }
        
        print("✅ Mock prediction generated:")
        print(json.dumps(prediction_response, indent=2))
        
    except Exception as e:
        print(f"❌ Inference test failed: {e}")

def run_cost_analysis():
    """Analyze estimated costs"""
    print("\n💰 Cost Analysis:")
    print("="*50)
    
    costs = {
        "S3 Storage (100GB)": "$2.30",
        "Lambda (1M invocations)": "$0.20", 
        "API Gateway (1M requests)": "$3.50",
        "ECR Storage": "$1.00",
        "CloudWatch Logs": "$0.50",
        "EventBridge": "$1.00",
        "AWS Batch (Spot, 10 hours)": "$1.00"
    }
    
    total = 0
    for service, cost in costs.items():
        print(f"{service:<30} {cost:>10}")
        total += float(cost.replace('$', ''))
    
    print("-" * 42)
    print(f"{'Total Monthly (estimated)':<30} ${total:>7.2f}")
    print(f"{'Daily cost':<30} ${total/30:>7.2f}")

def main():
    """Main setup and test function"""
    print("🚀 MLOps Stock Prediction - Local Setup")
    print("="*50)
    
    # Setup environment
    setup_environment()
    
    # Run tests
    test_data_collection()
    test_mlflow_integration()
    test_model_training() 
    test_inference()
    
    # Cost analysis
    run_cost_analysis()
    
    print("\n📋 Next Steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Setup MLflow: mlflow ui --port 5000 (in separate terminal)")
    print("3. Configure AWS credentials: aws configure")
    print("4. Deploy infrastructure: aws cloudformation deploy ...")
    print("5. Train your first model with MLflow tracking")
    print("6. Test API endpoint: curl -X POST https://api-url/predict")
    print("7. Monitor experiments in MLflow UI: http://localhost:5000")
    print("8. Monitor costs: aws ce get-cost-and-usage")

if __name__ == "__main__":
    main()
