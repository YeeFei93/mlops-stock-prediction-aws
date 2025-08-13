"""
Stock Data Collector for MLOps Pipeline
Fetches stock data from various APIs and stores in S3
"""

import os
import boto3
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging
from typing import List, Dict

class StockDataCollector:
    def __init__(self, s3_bucket: str):
        """
        Initialize Stock Data Collector
        
        Args:
            s3_bucket: S3 bucket name for data storage
        """
        self.s3_bucket = s3_bucket
        self.s3_client = boto3.client('s3')
        self.logger = logging.getLogger(__name__)
        
    def fetch_stock_data(self, symbols: List[str], period: str = "1y") -> Dict[str, pd.DataFrame]:
        """
        Fetch stock data for given symbols
        
        Args:
            symbols: List of stock symbols
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            Dictionary of symbol -> DataFrame mappings
        """
        stock_data = {}
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period=period)
                
                # Add technical indicators
                data = self._add_technical_indicators(data)
                
                stock_data[symbol] = data
                self.logger.info(f"Successfully fetched data for {symbol}")
                
            except Exception as e:
                self.logger.error(f"Error fetching data for {symbol}: {str(e)}")
                continue
                
        return stock_data
    
    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to stock data"""
        # Moving Averages
        df['MA_5'] = df['Close'].rolling(window=5).mean()
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['MA_50'] = df['Close'].rolling(window=50).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        # Volume indicators
        df['Volume_MA'] = df['Volume'].rolling(window=20).mean()
        
        return df
    
    def upload_to_s3(self, data_dict: Dict[str, pd.DataFrame], prefix: str = "raw-data") -> bool:
        """
        Upload stock data to S3
        
        Args:
            data_dict: Dictionary of symbol -> DataFrame mappings
            prefix: S3 key prefix
            
        Returns:
            Success status
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for symbol, data in data_dict.items():
            try:
                # Create S3 key
                s3_key = f"{prefix}/{symbol}/{timestamp}.parquet"
                
                # Convert to parquet and upload
                parquet_buffer = data.to_parquet()
                
                self.s3_client.put_object(
                    Bucket=self.s3_bucket,
                    Key=s3_key,
                    Body=parquet_buffer
                )
                
                self.logger.info(f"Uploaded {symbol} data to s3://{self.s3_bucket}/{s3_key}")
                
            except Exception as e:
                self.logger.error(f"Error uploading {symbol} data: {str(e)}")
                return False
                
        return True

def lambda_handler(event, context):
    """
    AWS Lambda handler for scheduled data collection
    """
    # Configuration
    S3_BUCKET = os.environ.get('S3_BUCKET', 'mlops-stock-data')
    SYMBOLS = event.get('symbols', ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN'])
    
    # Initialize collector
    collector = StockDataCollector(S3_BUCKET)
    
    # Fetch and upload data
    stock_data = collector.fetch_stock_data(SYMBOLS)
    success = collector.upload_to_s3(stock_data)
    
    return {
        'statusCode': 200 if success else 500,
        'body': f'Successfully processed {len(stock_data)} symbols'
    }

if __name__ == "__main__":
    # For local testing
    collector = StockDataCollector("test-bucket")
    data = collector.fetch_stock_data(['AAPL', 'GOOGL'])
    print(data['AAPL'].head())
