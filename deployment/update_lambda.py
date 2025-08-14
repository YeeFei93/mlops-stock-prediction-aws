#!/usr/bin/env python3
"""
Deploy a simplified Lambda function without external dependencies
"""

import boto3
import json
import zipfile
import tempfile

def deploy_simple_lambda():
    """Deploy a simple Lambda function for stock data collection"""
    
    lambda_client = boto3.client('lambda')
    
    # Simple Lambda function without yfinance dependency
    simple_code = '''
import json
import boto3
import urllib.request
from datetime import datetime
import random

def lambda_handler(event, context):
    """Simple stock data collector without yfinance"""
    
    symbols = event.get("symbols", ["AAPL", "GOOGL", "MSFT"])
    s3_bucket = "mlops-stock-data-255945442255-us-east-1"
    
    print(f"Processing symbols: {symbols}")
    
    results = []
    
    for symbol in symbols:
        try:
            # Mock stock data for demo (in production, use real APIs)
            mock_data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "price": round(100 + random.uniform(-50, 200), 2),  # Mock price
                "volume": random.randint(1000000, 10000000),
                "status": "collected"
            }
            
            # Store in S3
            s3 = boto3.client('s3')
            key = f"mock-data/{symbol}/{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            s3.put_object(
                Bucket=s3_bucket,
                Key=key,
                Body=json.dumps(mock_data),
                ContentType='application/json'
            )
            
            results.append(f"✅ {symbol}: ${mock_data['price']}")
            print(f"Stored {symbol} data to s3://{s3_bucket}/{key}")
            
        except Exception as e:
            error_msg = f"❌ {symbol}: {str(e)}"
            results.append(error_msg)
            print(error_msg)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"Processed {len(symbols)} symbols",
            "results": results,
            "timestamp": datetime.now().isoformat()
        })
    }
'''
    
    # Package and deploy
    try:
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w') as zipf:
                zipf.writestr('lambda_function.py', simple_code)
            
            with open(tmp.name, 'rb') as f:
                zip_content = f.read()
        
        # Update the function
        response = lambda_client.update_function_code(
            FunctionName='stock-data-collector',
            ZipFile=zip_content
        )
        
        print("✅ Lambda function updated with simplified code")
        print(f"   Function ARN: {response['FunctionArn']}")
        
        return response['FunctionArn']
        
    except Exception as e:
        print(f"❌ Error updating Lambda: {e}")
        raise

if __name__ == "__main__":
    print("🔄 Updating Lambda with simplified stock collector...")
    function_arn = deploy_simple_lambda()
    print(f"🎊 Lambda updated successfully!")
