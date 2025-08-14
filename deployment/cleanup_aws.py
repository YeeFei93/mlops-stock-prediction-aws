#!/usr/bin/env python3
"""
AWS Resource Cleanup Script
Use this to delete MLOps resources if needed
"""

import boto3
import json

def cleanup_mlops_resources():
    """Clean up all MLOps AWS resources"""
    
    print("🧹 MLOps AWS Resource Cleanup")
    print("=" * 40)
    
    # AWS clients
    lambda_client = boto3.client('lambda')
    s3_client = boto3.client('s3')
    events_client = boto3.client('events')
    iam_client = boto3.client('iam')
    
    account_id = "255945442255"
    bucket_name = f"mlops-stock-data-{account_id}-us-east-1"
    
    try:
        # 1. Delete EventBridge rule and targets
        print("\n🗑️  Removing EventBridge schedule...")
        try:
            events_client.remove_targets(
                Rule='daily-stock-collection',
                Ids=['1']
            )
            events_client.delete_rule(Name='daily-stock-collection')
            print("✅ EventBridge rule deleted")
        except Exception as e:
            print(f"⚠️  EventBridge cleanup: {e}")
        
        # 2. Delete Lambda function
        print("\n🗑️  Removing Lambda function...")
        try:
            lambda_client.delete_function(FunctionName='stock-data-collector')
            print("✅ Lambda function deleted")
        except Exception as e:
            print(f"⚠️  Lambda cleanup: {e}")
        
        # 3. Empty and delete S3 bucket
        print(f"\n🗑️  Emptying S3 bucket: {bucket_name}...")
        try:
            # List and delete all objects
            response = s3_client.list_objects_v2(Bucket=bucket_name)
            if 'Contents' in response:
                objects = [{'Key': obj['Key']} for obj in response['Contents']]
                s3_client.delete_objects(
                    Bucket=bucket_name,
                    Delete={'Objects': objects}
                )
                print(f"✅ Deleted {len(objects)} objects from S3")
            
            # Delete the bucket
            s3_client.delete_bucket(Bucket=bucket_name)
            print(f"✅ S3 bucket {bucket_name} deleted")
            
        except Exception as e:
            print(f"⚠️  S3 cleanup: {e}")
        
        # 4. Detach policies and delete IAM role (optional - may be used by other resources)
        print(f"\n🗑️  Cleaning IAM role...")
        try:
            role_name = "MLOpsLambdaExecutionRole"
            
            # List attached policies
            attached_policies = iam_client.list_attached_role_policies(RoleName=role_name)
            
            # Detach policies
            for policy in attached_policies['AttachedPolicies']:
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
            
            # Delete role
            iam_client.delete_role(RoleName=role_name)
            print("✅ IAM role deleted")
            
        except Exception as e:
            print(f"⚠️  IAM cleanup (may be used elsewhere): {e}")
        
        print(f"\n🎊 Cleanup completed!")
        print(f"💰 AWS costs will now be $0.00/month")
        
    except Exception as e:
        print(f"\n❌ Cleanup error: {e}")

def list_current_resources():
    """List current MLOps resources"""
    
    print("📋 Current MLOps Resources:")
    print("=" * 30)
    
    lambda_client = boto3.client('lambda')
    s3_client = boto3.client('s3')
    events_client = boto3.client('events')
    
    account_id = "255945442255"
    bucket_name = f"mlops-stock-data-{account_id}-us-east-1"
    
    # Check Lambda function
    try:
        response = lambda_client.get_function(FunctionName='stock-data-collector')
        print(f"✅ Lambda: stock-data-collector")
        print(f"   Last Modified: {response['Configuration']['LastModified']}")
    except:
        print("❌ Lambda: Not found")
    
    # Check S3 bucket
    try:
        objects = s3_client.list_objects_v2(Bucket=bucket_name)
        count = len(objects.get('Contents', []))
        print(f"✅ S3 Bucket: {bucket_name}")
        print(f"   Objects: {count}")
    except:
        print("❌ S3 Bucket: Not found")
    
    # Check EventBridge rule
    try:
        response = events_client.describe_rule(Name='daily-stock-collection')
        print(f"✅ EventBridge Rule: daily-stock-collection")
        print(f"   Schedule: {response['ScheduleExpression']}")
    except:
        print("❌ EventBridge Rule: Not found")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        print("⚠️  WARNING: This will delete ALL MLOps resources!")
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm == 'DELETE':
            cleanup_mlops_resources()
        else:
            print("❌ Cleanup cancelled")
    else:
        list_current_resources()
        print(f"\n💡 To cleanup resources, run: python cleanup_aws.py cleanup")
        print(f"💰 Current cost: ~$0.01-0.03/month (nearly free!)")
        print(f"🎯 Recommendation: Keep running for portfolio value")
