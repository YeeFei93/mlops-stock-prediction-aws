"""
Test suite for stock data collector
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import boto3
from moto import mock_aws
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from data_ingestion.stock_data_collector import StockDataCollector

class TestStockDataCollector(unittest.TestCase):
    
    @mock_aws
    def setUp(self):
        """Set up test fixtures"""
        self.bucket_name = 'test-mlops-bucket'
        
        # Create S3 client and bucket
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_client.create_bucket(Bucket=self.bucket_name)
        
        # Initialize collector
        self.collector = StockDataCollector(self.bucket_name)
    
    def test_init(self):
        """Test collector initialization"""
        self.assertEqual(self.collector.s3_bucket, self.bucket_name)
        self.assertIsNotNone(self.collector.s3_client)
    
    @patch('yfinance.Ticker')
    def test_fetch_stock_data_success(self, mock_ticker):
        """Test successful stock data fetching"""
        # Mock data
        mock_data = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [104.0, 105.0, 106.0],
            'Volume': [1000, 1100, 1200]
        })
        
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value = mock_data
        mock_ticker.return_value = mock_ticker_instance
        
        # Test
        result = self.collector.fetch_stock_data(['AAPL'])
        
        # Assertions
        self.assertIn('AAPL', result)
        self.assertIsInstance(result['AAPL'], pd.DataFrame)
        
        # Check if technical indicators were added
        self.assertIn('MA_5', result['AAPL'].columns)
        self.assertIn('RSI', result['AAPL'].columns)
    
    @patch('yfinance.Ticker')
    def test_fetch_stock_data_error(self, mock_ticker):
        """Test stock data fetching with error"""
        mock_ticker.side_effect = Exception("API Error")
        
        result = self.collector.fetch_stock_data(['INVALID'])
        
        # Should return empty dict on error
        self.assertEqual(result, {})
    
    def test_add_technical_indicators(self):
        """Test technical indicators calculation"""
        # Create sample data
        df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109,
                     110, 111, 112, 113, 114, 115, 116, 117, 118, 119],
            'Volume': [1000] * 20
        })
        
        result = self.collector._add_technical_indicators(df)
        
        # Check if indicators were added
        self.assertIn('MA_5', result.columns)
        self.assertIn('MA_20', result.columns)
        self.assertIn('RSI', result.columns)
        self.assertIn('BB_Upper', result.columns)
        self.assertIn('BB_Lower', result.columns)
        
        # Check if calculations are reasonable
        self.assertFalse(result['MA_5'].iloc[-1] == 0)
        self.assertTrue(0 <= result['RSI'].iloc[-1] <= 100)
    
    @mock_aws
    def test_upload_to_s3_success(self):
        """Test successful S3 upload"""
        # Reinitialize S3 for this test
        s3_client = boto3.client('s3', region_name='us-east-1')
        s3_client.create_bucket(Bucket=self.bucket_name)
        
        # Create new collector instance for this test
        collector = StockDataCollector(self.bucket_name)
        
        # Create test data
        test_data = {
            'AAPL': pd.DataFrame({
                'Close': [100, 101, 102],
                'Volume': [1000, 1100, 1200]
            })
        }
        
        # Test upload
        result = collector.upload_to_s3(test_data)
        
        # Should return True on success
        self.assertTrue(result)
        
        # Check if object was uploaded
        response = s3_client.list_objects_v2(
            Bucket=self.bucket_name,
            Prefix='raw-data/AAPL/'
        )
        self.assertIn('Contents', response)
        self.assertEqual(len(response['Contents']), 1)
    
    def test_lambda_handler(self):
        """Test Lambda handler function"""
        from data_ingestion.stock_data_collector import lambda_handler
        
        with patch.dict(os.environ, {'S3_BUCKET': 'test-bucket'}):
            with patch('data_ingestion.stock_data_collector.StockDataCollector') as mock_collector:
                # Mock collector methods
                mock_instance = Mock()
                mock_instance.fetch_stock_data.return_value = {'AAPL': pd.DataFrame()}
                mock_instance.upload_to_s3.return_value = True
                mock_collector.return_value = mock_instance
                
                # Test event
                event = {'symbols': ['AAPL', 'GOOGL']}
                context = {}
                
                result = lambda_handler(event, context)
                
                # Check response
                self.assertEqual(result['statusCode'], 200)
                self.assertIn('Successfully processed', result['body'])

if __name__ == '__main__':
    unittest.main()
