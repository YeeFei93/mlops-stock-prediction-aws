"""
Simplified Lambda function for stock data collection
Uses basic HTTP requests instead of yfinance to avoid dependency issues
"""

import json
import boto3
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

def lambda_handler(event, context):
    """
    Stock data collection Lambda function
    Collects basic stock data and stores in S3
    """
    
    print(f"Event received: {json.dumps(event)}")
    
    # Configuration
    s3_bucket = "mlops-stock-data-255945442255-us-east-1"  # Your bucket name
    symbols = event.get("symbols", ["AAPL", "GOOGL", "MSFT"])
    
    s3_client = boto3.client('s3')
    collected_data = {}
    
    try:
        for symbol in symbols:
            print(f"Processing symbol: {symbol}")
            
            # Simulate data collection (in real deployment, you'd use a proper API)
            # For now, we'll create mock data to demonstrate the pipeline
            mock_data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "price": 150.0 + hash(symbol) % 100,  # Mock price
                "volume": 1000000 + hash(symbol) % 5000000,  # Mock volume
                "status": "collected"
            }
            
            # Store in S3
            s3_key = f"raw-data/{symbol}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            s3_client.put_object(
                Bucket=s3_bucket,
                Key=s3_key,
                Body=json.dumps(mock_data),
                ContentType='application/json'
            )
            
            collected_data[symbol] = mock_data
            print(f"✅ Stored data for {symbol} at s3://{s3_bucket}/{s3_key}")
        
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "message": f"Successfully processed {len(symbols)} symbols",
                "symbols": symbols,
                "data_collected": collected_data,
                "timestamp": datetime.now().isoformat()
            })
        }
        
        print(f"Success response: {response}")
        return response
        
    except Exception as e:
        error_response = {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "message": "Failed to collect stock data",
                "timestamp": datetime.now().isoformat()
            })
        }
        
        print(f"Error response: {error_response}")
        return error_response
