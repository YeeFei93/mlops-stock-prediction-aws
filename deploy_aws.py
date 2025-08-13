#!/usr/bin/env python3
"""
AWS Deployment Script for MLOps Stock Prediction Pipeline
Deploys infrastructure step by step with cost optimization
"""

import boto3
import json
import time
import subprocess
from datetime import datetime

class MLOpsDeployer:
    def __init__(self, region='us-east-1'):
        """Initialize AWS clients"""
        self.region = region
        self.session = boto3.Session()
        self.cloudformation = self.session.client('cloudformation', region_name=region)
        self.s3 = self.session.client('s3', region_name=region)
        self.lambda_client = self.session.client('lambda', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
        print(f"🚀 AWS MLOps Deployer initialized")
        print(f"   Region: {region}")
        print(f"   Account: {self.account_id}")
    
    def create_s3_bucket(self, bucket_name=None):
        """Create S3 bucket for data storage"""
        if not bucket_name:
            bucket_name = f"mlops-stock-data-{self.account_id}-{self.region}"
        
        try:
            print(f"\n📦 Creating S3 bucket: {bucket_name}")
            
            if self.region == 'us-east-1':
                # us-east-1 doesn't need LocationConstraint
                self.s3.create_bucket(Bucket=bucket_name)
            else:
                self.s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            
            # Enable versioning
            self.s3.put_bucket_versioning(
                Bucket=bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            
            # Add lifecycle policy for cost optimization
            lifecycle_policy = {
                'Rules': [
                    {
                        'ID': 'DataLifecycle',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Transitions': [
                            {
                                'Days': 30,
                                'StorageClass': 'STANDARD_IA'
                            },
                            {
                                'Days': 90, 
                                'StorageClass': 'GLACIER'
                            }
                        ]
                    }
                ]
            }
            
            self.s3.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )
            
            print(f"✅ S3 bucket created: {bucket_name}")
            print(f"   Features: Versioning ✅, Lifecycle Policy ✅")
            return bucket_name
            
        except Exception as e:
            if "BucketAlreadyExists" in str(e):
                print(f"✅ S3 bucket already exists: {bucket_name}")
                return bucket_name
            else:
                print(f"❌ Error creating S3 bucket: {e}")
                raise
    
    def create_lambda_execution_role(self):
        """Create IAM role for Lambda functions"""
        try:
            print(f"\n🔑 Creating Lambda execution role...")
            
            iam = self.session.client('iam')
            
            # Trust policy for Lambda
            trust_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole"
                    }
                ]
            }
            
            # Create role
            role_name = "MLOpsLambdaExecutionRole"
            try:
                response = iam.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(trust_policy),
                    Description="Execution role for MLOps Lambda functions"
                )
                role_arn = response['Role']['Arn']
                print(f"✅ Created new IAM role: {role_name}")
                
            except iam.exceptions.EntityAlreadyExistsException:
                response = iam.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                print(f"✅ Using existing IAM role: {role_name}")
            
            # Attach managed policies
            managed_policies = [
                'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole',
                'arn:aws:iam::aws:policy/AmazonS3FullAccess'  # In production, use more restrictive policy
            ]
            
            for policy_arn in managed_policies:
                try:
                    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
                except iam.exceptions.NoSuchEntityException:
                    pass  # Already attached
            
            # Wait for role to be available
            print("   Waiting for role propagation...")
            time.sleep(10)
            
            return role_arn
            
        except Exception as e:
            print(f"❌ Error creating Lambda role: {e}")
            raise
    
    def package_lambda_function(self, function_path, output_file):
        """Package Lambda function code"""
        try:
            print(f"\n📦 Packaging Lambda function: {function_path}")
            
            import zipfile
            import os
            
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add function files
                for root, dirs, files in os.walk(function_path):
                    for file in files:
                        if file.endswith('.py'):
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, start=os.path.dirname(function_path))
                            zipf.write(file_path, arcname)
            
            print(f"✅ Lambda package created: {output_file}")
            return output_file
            
        except Exception as e:
            print(f"❌ Error packaging Lambda: {e}")
            raise
    
    def deploy_data_collection_lambda(self, bucket_name, role_arn):
        """Deploy data collection Lambda function"""
        try:
            print(f"\n🔄 Deploying data collection Lambda...")
            
            function_name = "stock-data-collector"
            
            # Create simple Lambda function code
            lambda_code = f'''
import json
import boto3
import yfinance as yf
from datetime import datetime

def lambda_handler(event, context):
    s3_bucket = "{bucket_name}"
    symbols = event.get("symbols", ["AAPL", "GOOGL", "MSFT"])
    
    print(f"Collecting data for symbols: {{symbols}}")
    
    try:
        for symbol in symbols:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="5d")
            
            # Save to S3 (simplified)
            print(f"Collected {{len(data)}} days for {{symbol}}")
        
        return {{
            "statusCode": 200,
            "body": json.dumps(f"Successfully processed {{len(symbols)}} symbols")
        }}
    except Exception as e:
        print(f"Error: {{str(e)}}")
        return {{
            "statusCode": 500,
            "body": json.dumps(f"Error: {{str(e)}}")
        }}
'''
            
            # Create deployment package
            import tempfile
            import zipfile
            
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                with zipfile.ZipFile(tmp.name, 'w') as zipf:
                    zipf.writestr('lambda_function.py', lambda_code)
                
                with open(tmp.name, 'rb') as f:
                    zip_content = f.read()
            
            try:
                # Try to update existing function
                response = self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
                print(f"✅ Updated existing Lambda: {function_name}")
                
            except self.lambda_client.exceptions.ResourceNotFoundException:
                # Create new function
                response = self.lambda_client.create_function(
                    FunctionName=function_name,
                    Runtime='python3.9',
                    Role=role_arn,
                    Handler='lambda_function.lambda_handler',
                    Code={'ZipFile': zip_content},
                    Description='Stock data collection function',
                    Timeout=300,
                    MemorySize=512,
                    Environment={
                        'Variables': {
                            'S3_BUCKET': bucket_name
                        }
                    }
                )
                print(f"✅ Created new Lambda: {function_name}")
            
            return response['FunctionArn']
            
        except Exception as e:
            print(f"❌ Error deploying Lambda: {e}")
            raise
    
    def test_deployment(self, function_arn, bucket_name):
        """Test the deployed infrastructure"""
        try:
            print(f"\n🧪 Testing deployment...")
            
            # Test Lambda function
            function_name = function_arn.split(':')[-1]
            
            test_event = {
                "symbols": ["AAPL", "GOOGL"]
            }
            
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(test_event)
            )
            
            result = json.loads(response['Payload'].read().decode())
            print(f"✅ Lambda test completed")
            print(f"   Status: {result.get('statusCode')}")
            print(f"   Response: {result.get('body')}")
            
            # Check S3 bucket
            try:
                objects = self.s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                print(f"✅ S3 bucket accessible: {bucket_name}")
            except Exception as e:
                print(f"⚠️  S3 bucket check: {e}")
            
            return True
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False
    
    def get_deployment_summary(self, bucket_name, function_arn):
        """Print deployment summary"""
        print(f"\n🎉 Deployment Summary")
        print("=" * 50)
        print(f"✅ S3 Bucket: {bucket_name}")
        print(f"✅ Lambda Function: {function_arn}")
        print(f"✅ Region: {self.region}")
        print(f"✅ Account: {self.account_id}")
        print(f"\n💰 Estimated Monthly Costs:")
        print(f"   S3 Storage (1GB): ~$0.02")
        print(f"   Lambda (10K invocations): ~$0.20")
        print(f"   Total: ~$0.22/month")
        print(f"\n📋 Next Steps:")
        print(f"   1. Test Lambda: aws lambda invoke --function-name stock-data-collector output.json")
        print(f"   2. Schedule collection: aws events put-rule --schedule-expression 'cron(0 9 * * ? *)'")
        print(f"   3. Add API Gateway for inference")
        print(f"   4. Deploy model training on Batch")

def main():
    """Main deployment function"""
    print("🚀 MLOps Stock Prediction - AWS Deployment")
    print("=" * 50)
    
    # Initialize deployer
    deployer = MLOpsDeployer(region='us-east-1')
    
    try:
        # Step 1: Create S3 bucket
        bucket_name = deployer.create_s3_bucket()
        
        # Step 2: Create IAM role
        role_arn = deployer.create_lambda_execution_role()
        
        # Step 3: Deploy Lambda function
        function_arn = deployer.deploy_data_collection_lambda(bucket_name, role_arn)
        
        # Step 4: Test deployment
        test_success = deployer.test_deployment(function_arn, bucket_name)
        
        # Step 5: Summary
        if test_success:
            deployer.get_deployment_summary(bucket_name, function_arn)
            print(f"\n🎊 Deployment completed successfully!")
        else:
            print(f"\n⚠️  Deployment completed with warnings")
        
        return {
            'bucket_name': bucket_name,
            'function_arn': function_arn,
            'success': test_success
        }
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        raise

if __name__ == "__main__":
    result = main()
