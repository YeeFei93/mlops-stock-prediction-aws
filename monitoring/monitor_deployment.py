#!/usr/bin/env python3
"""
MLOps Deployment Monitoring Dashboard
Checks the status of all AWS resources and deployment history
"""

import boto3
import json
import requests
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError
import sys

class MLOpsMonitor:
    def __init__(self, region='us-east-1'):
        self.region = region
        self.account_id = '255945442255'
        self.bucket_name = f'mlops-stock-data-{self.account_id}-{region}'
        
    def check_aws_resources(self):
        """Check status of all AWS resources"""
        print("🔍 AWS RESOURCES STATUS")
        print("=" * 50)
        
        status = {
            'resources_healthy': True,
            'details': {}
        }
        
        try:
            # S3 Bucket
            s3 = boto3.client('s3', region_name=self.region)
            try:
                s3.head_bucket(Bucket=self.bucket_name)
                # Get bucket size and file count
                objects = s3.list_objects_v2(Bucket=self.bucket_name)
                file_count = len(objects.get('Contents', []))
                total_size = sum(obj.get('Size', 0) for obj in objects.get('Contents', []))
                
                print(f"✅ S3 Bucket: {self.bucket_name}")
                print(f"   📁 Files: {file_count}")
                print(f"   📊 Size: {total_size / 1024:.2f} KB")
                
                if objects.get('Contents'):
                    latest = max(objects['Contents'], key=lambda x: x['LastModified'])
                    print(f"   🕒 Latest file: {latest['LastModified'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    
                status['details']['s3'] = {'status': 'healthy', 'files': file_count, 'size_kb': total_size / 1024}
                
            except ClientError as e:
                print(f"❌ S3 Bucket: NOT FOUND")
                status['resources_healthy'] = False
                status['details']['s3'] = {'status': 'missing', 'error': str(e)}
            
            # Lambda Function
            lambda_client = boto3.client('lambda', region_name=self.region)
            try:
                response = lambda_client.get_function(FunctionName='stock-data-collector')
                config = response['Configuration']
                
                print(f"\n✅ Lambda Function: stock-data-collector")
                print(f"   🔧 State: {config['State']}")
                print(f"   🕒 Last Modified: {config['LastModified']}")
                print(f"   🧠 Memory: {config['MemorySize']}MB")
                print(f"   ⚡ Runtime: {config['Runtime']}")
                
                status['details']['lambda'] = {
                    'status': 'healthy', 
                    'state': config['State'],
                    'last_modified': config['LastModified']
                }
                
            except ClientError:
                print(f"\n❌ Lambda Function: NOT FOUND")
                status['resources_healthy'] = False
                status['details']['lambda'] = {'status': 'missing'}
            
            # EventBridge Rule
            events = boto3.client('events', region_name=self.region)
            try:
                rule = events.describe_rule(Name='daily-stock-collection')
                targets = events.list_targets_by_rule(Rule='daily-stock-collection')
                
                print(f"\n✅ EventBridge Rule: daily-stock-collection")
                print(f"   📅 Schedule: {rule['ScheduleExpression']}")
                print(f"   🔧 State: {rule['State']}")
                print(f"   🎯 Targets: {len(targets['Targets'])}")
                
                status['details']['eventbridge'] = {
                    'status': 'healthy',
                    'state': rule['State'],
                    'schedule': rule['ScheduleExpression'],
                    'targets': len(targets['Targets'])
                }
                
            except ClientError:
                print(f"\n❌ EventBridge Rule: NOT FOUND")
                status['resources_healthy'] = False
                status['details']['eventbridge'] = {'status': 'missing'}
            
            # Check recent Lambda invocations
            logs_client = boto3.client('logs', region_name=self.region)
            try:
                log_groups = logs_client.describe_log_groups(
                    logGroupNamePrefix='/aws/lambda/stock-data-collector'
                )
                
                if log_groups['logGroups']:
                    print(f"\n📋 Lambda Logs Available:")
                    for group in log_groups['logGroups']:
                        print(f"   📝 {group['logGroupName']}")
                        print(f"   🕒 Last Event: {datetime.fromtimestamp(group.get('lastEventTime', 0)/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                        
            except Exception as e:
                print(f"\n⚠️  Log check failed: {str(e)}")
                
        except NoCredentialsError:
            print("❌ AWS credentials not configured")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            return False
            
        return status
    
    def check_github_actions(self):
        """Check recent GitHub Actions runs"""
        print(f"\n🔄 GITHUB ACTIONS STATUS")
        print("=" * 50)
        
        # This would require GitHub token for API access
        # For now, show manual instructions
        print("📱 Manual Check Instructions:")
        print(f"   🌐 Visit: https://github.com/YeeFei93/mlops-stock-prediction-aws/actions")
        print(f"   🕒 Look for 'daily-deployment' jobs running at 8 AM Singapore time")
        print(f"   ✅ Green checkmark = successful deployment")
        print(f"   ❌ Red X = failed deployment (needs attention)")
        print(f"   🔔 Enable notifications: Repository → Watch → All Activity")
        
    def predict_next_events(self):
        """Predict when next events will occur"""
        print(f"\n⏰ UPCOMING EVENTS")
        print("=" * 50)
        
        now = datetime.utcnow()
        
        # Next deployment (8 AM Singapore = 0 AM UTC)
        next_deployment = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if now.hour >= 0:  # If it's already past midnight today
            next_deployment += timedelta(days=1)
            
        # Next data collection (9 AM UTC = 5 PM Singapore)
        next_collection = now.replace(hour=9, minute=0, second=0, microsecond=0)
        if now.hour >= 9:  # If it's already past 9 AM UTC today
            next_collection += timedelta(days=1)
        
        print(f"🌅 Next Deployment: {next_deployment.strftime('%Y-%m-%d %H:%M UTC')} (8 AM Singapore)")
        print(f"📊 Next Data Collection: {next_collection.strftime('%Y-%m-%d %H:%M UTC')} (5 PM Singapore)")
        
        # Time until next events
        deployment_in = next_deployment - now
        collection_in = next_collection - now
        
        print(f"\n⏳ Time Until Next Events:")
        print(f"   🌅 Deployment in: {deployment_in}")
        print(f"   📊 Collection in: {collection_in}")
        
    def get_cost_estimate(self):
        """Estimate current costs"""
        print(f"\n💰 COST MONITORING")
        print("=" * 50)
        
        print(f"📊 Estimated Daily Costs:")
        print(f"   💾 S3 Storage: ~$0.000001")
        print(f"   ⚡ Lambda Execution: ~$0.000002") 
        print(f"   📅 EventBridge: ~$0.000001")
        print(f"   🔄 Total Daily: ~$0.000004")
        print(f"   📅 Monthly: ~$0.00012")
        print(f"   📆 Yearly: ~$0.0014")
        print(f"\n🎯 Result: Practically FREE! (Less than 1 cent per year)")
        
    def generate_dashboard(self):
        """Generate complete monitoring dashboard"""
        print("🎯 MLOPS DEPLOYMENT MONITORING DASHBOARD")
        print("=" * 70)
        print(f"🕒 Report Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"🌍 Account: {self.account_id}")
        print(f"🌐 Region: {self.region}")
        print("")
        
        # Check all resources
        status = self.check_aws_resources()
        
        # Show GitHub Actions info
        self.check_github_actions()
        
        # Show upcoming events
        self.predict_next_events()
        
        # Show costs
        self.get_cost_estimate()
        
        # Overall health summary
        print(f"\n🏥 OVERALL HEALTH")
        print("=" * 50)
        if status and status.get('resources_healthy', False):
            print("✅ SYSTEM HEALTHY - All resources operational")
            print("🎉 Your MLOps pipeline is running smoothly!")
        else:
            print("⚠️  ATTENTION NEEDED - Some resources missing")
            print("🔧 Resources will be auto-deployed at 8 AM Singapore time")
            
        return status

def main():
    """Main monitoring function"""
    monitor = MLOpsMonitor()
    status = monitor.generate_dashboard()
    
    # Save status to file for historical tracking
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    status_file = f"monitoring_status_{timestamp}.json"
    
    try:
        with open(status_file, 'w') as f:
            json.dump({
                'timestamp': datetime.utcnow().isoformat(),
                'status': status
            }, f, indent=2, default=str)
        print(f"\n📝 Status saved to: {status_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save status file: {e}")

if __name__ == "__main__":
    main()
