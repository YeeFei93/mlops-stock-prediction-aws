"""
MLflow deployment configuration for AWS
Sets up MLflow tracking server with PostgreSQL backend and S3 artifacts
"""

import boto3
import os
import subprocess
from typing import Dict, Any

class MLflowAWSDeployer:
    def __init__(self, region: str = 'us-east-1'):
        """Initialize MLflow AWS deployer"""
        self.region = region
        self.ec2_client = boto3.client('ec2', region_name=region)
        self.rds_client = boto3.client('rds', region_name=region)
        self.s3_client = boto3.client('s3', region_name=region)
    
    def create_mlflow_infrastructure(self) -> Dict[str, str]:
        """Create MLflow infrastructure on AWS"""
        
        # 1. Create S3 bucket for artifacts
        bucket_name = f"mlflow-artifacts-{os.urandom(8).hex()}"
        try:
            self.s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={'LocationConstraint': self.region} 
                if self.region != 'us-east-1' else {}
            )
            print(f"✅ Created S3 bucket: {bucket_name}")
        except Exception as e:
            print(f"❌ S3 bucket creation failed: {e}")
            return {}
        
        # 2. Launch RDS PostgreSQL (cost-optimized)
        db_identifier = f"mlflow-db-{os.urandom(4).hex()}"
        try:
            self.rds_client.create_db_instance(
                DBInstanceIdentifier=db_identifier,
                DBInstanceClass='db.t3.micro',  # Free tier eligible
                Engine='postgres',
                MasterUsername='mlflow',
                MasterUserPassword='mlflow123!',  # Change in production
                AllocatedStorage=20,  # Minimum for PostgreSQL
                StorageType='gp2',
                DatabaseName='mlflow',
                BackupRetentionPeriod=0,  # No backups for cost saving
                MultiAZ=False,
                PubliclyAccessible=True,  # For development only
                StorageEncrypted=False,  # Additional cost
                Tags=[
                    {'Key': 'Name', 'Value': 'MLflow-Database'},
                    {'Key': 'Environment', 'Value': 'development'}
                ]
            )
            print(f"✅ Creating RDS instance: {db_identifier}")
        except Exception as e:
            print(f"❌ RDS creation failed: {e}")
        
        # 3. Launch EC2 instance for MLflow server
        user_data_script = f"""#!/bin/bash
# Update system
yum update -y
yum install -y python3 python3-pip git

# Install MLflow and dependencies
pip3 install mlflow psycopg2-binary boto3

# Create MLflow user
useradd mlflow
mkdir -p /home/mlflow
chown mlflow:mlflow /home/mlflow

# Create MLflow service script
cat > /etc/systemd/system/mlflow.service << 'EOF'
[Unit]
Description=MLflow Tracking Server
After=network.target

[Service]
Type=simple
User=mlflow
WorkingDirectory=/home/mlflow
Environment=AWS_DEFAULT_REGION={self.region}
ExecStart=/usr/local/bin/mlflow server \\
    --backend-store-uri postgresql://mlflow:mlflow123!@{db_identifier}.{self.region}.rds.amazonaws.com:5432/mlflow \\
    --default-artifact-root s3://{bucket_name}/artifacts \\
    --host 0.0.0.0 \\
    --port 5000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start MLflow service
systemctl daemon-reload
systemctl enable mlflow
systemctl start mlflow

# Install CloudWatch agent for monitoring
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
rpm -U ./amazon-cloudwatch-agent.rpm
"""
        
        try:
            response = self.ec2_client.run_instances(
                ImageId='ami-0c02fb55956c7d316',  # Amazon Linux 2 AMI
                InstanceType='t3.micro',  # Free tier eligible
                MinCount=1,
                MaxCount=1,
                KeyName='your-key-pair',  # Replace with your key pair
                SecurityGroupIds=['sg-12345678'],  # Replace with your security group
                UserData=user_data_script,
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': 'MLflow-Server'},
                            {'Key': 'Environment', 'Value': 'development'}
                        ]
                    }
                ],
                IamInstanceProfile={
                    'Name': 'MLflowInstanceProfile'  # Create this IAM role
                }
            )
            
            instance_id = response['Instances'][0]['InstanceId']
            print(f"✅ Launching EC2 instance: {instance_id}")
            
        except Exception as e:
            print(f"❌ EC2 launch failed: {e}")
            return {}
        
        return {
            'bucket_name': bucket_name,
            'db_identifier': db_identifier,
            'instance_id': instance_id,
            'mlflow_ui_url': f"http://instance-public-ip:5000"
        }

def get_mlflow_setup_commands():
    """Get setup commands for MLflow"""
    return """
# MLflow Setup Commands
# ====================

# 1. Local Development Setup
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
export MLFLOW_ARTIFACT_URI="./mlruns"
mlflow ui --port 5000

# 2. AWS S3 Backend Setup  
export MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
export MLFLOW_ARTIFACT_URI="s3://your-mlflow-bucket/artifacts"

# 3. Full AWS Setup (EC2 + RDS + S3)
export MLFLOW_TRACKING_URI="http://your-mlflow-server:5000"

# 4. Start MLflow server manually
mlflow server \\
    --backend-store-uri postgresql://user:pass@rds-endpoint:5432/mlflow \\
    --default-artifact-root s3://your-bucket/artifacts \\
    --host 0.0.0.0 \\
    --port 5000

# 5. Environment variables for Lambda
export MLFLOW_TRACKING_URI="http://your-mlflow-server:5000"
export MLFLOW_S3_ENDPOINT_URL="https://s3.amazonaws.com"

# 6. Cost optimization tips
# - Use t3.micro instances (free tier)
# - Use db.t3.micro for RDS (free tier)
# - Set S3 lifecycle policies
# - Stop instances when not in use
"""

def create_mlflow_cloudformation_template():
    """Create CloudFormation template for MLflow infrastructure"""
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "MLflow Tracking Server Infrastructure",
        "Parameters": {
            "Environment": {
                "Type": "String",
                "Default": "dev",
                "AllowedValues": ["dev", "staging", "prod"]
            },
            "KeyPairName": {
                "Type": "AWS::EC2::KeyPair::KeyName",
                "Description": "EC2 Key Pair for SSH access"
            }
        },
        "Resources": {
            # S3 Bucket for artifacts
            "MLflowArtifactsBucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {"Fn::Sub": "mlflow-artifacts-${AWS::StackName}-${AWS::Region}"},
                    "VersioningConfiguration": {"Status": "Enabled"},
                    "LifecycleConfiguration": {
                        "Rules": [{
                            "Id": "ArtifactLifecycle",
                            "Status": "Enabled",
                            "Transitions": [
                                {"TransitionInDays": 30, "StorageClass": "STANDARD_IA"},
                                {"TransitionInDays": 90, "StorageClass": "GLACIER"}
                            ]
                        }]
                    }
                }
            },
            
            # RDS PostgreSQL for backend store
            "MLflowDatabase": {
                "Type": "AWS::RDS::DBInstance",
                "Properties": {
                    "DBInstanceIdentifier": {"Fn::Sub": "mlflow-db-${Environment}"},
                    "DBInstanceClass": "db.t3.micro",
                    "Engine": "postgres",
                    "MasterUsername": "mlflow",
                    "MasterUserPassword": "mlflow123!",  # Use Secrets Manager in production
                    "AllocatedStorage": "20",
                    "StorageType": "gp2",
                    "DatabaseName": "mlflow",
                    "BackupRetentionPeriod": 0,
                    "MultiAZ": False,
                    "PubliclyAccessible": True,
                    "StorageEncrypted": False,
                    "DeletionProtection": False
                }
            },
            
            # IAM Role for EC2
            "MLflowInstanceRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Principal": {"Service": "ec2.amazonaws.com"},
                            "Action": "sts:AssumeRole"
                        }]
                    },
                    "Policies": [{
                        "PolicyName": "MLflowS3Access",
                        "PolicyDocument": {
                            "Version": "2012-10-17",
                            "Statement": [{
                                "Effect": "Allow",
                                "Action": ["s3:*"],
                                "Resource": [
                                    {"Fn::GetAtt": ["MLflowArtifactsBucket", "Arn"]},
                                    {"Fn::Sub": "${MLflowArtifactsBucket}/*"}
                                ]
                            }]
                        }
                    }]
                }
            },
            
            # Instance Profile
            "MLflowInstanceProfile": {
                "Type": "AWS::IAM::InstanceProfile",
                "Properties": {
                    "Roles": [{"Ref": "MLflowInstanceRole"}]
                }
            },
            
            # Security Group
            "MLflowSecurityGroup": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "Security group for MLflow server",
                    "SecurityGroupIngress": [
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 5000,
                            "ToPort": 5000,
                            "CidrIp": "0.0.0.0/0"  # Restrict in production
                        },
                        {
                            "IpProtocol": "tcp",
                            "FromPort": 22,
                            "ToPort": 22,
                            "CidrIp": "0.0.0.0/0"  # Restrict in production
                        }
                    ]
                }
            }
        },
        "Outputs": {
            "MLflowTrackingURI": {
                "Description": "MLflow Tracking Server URI",
                "Value": {"Fn::Sub": "http://${MLflowServer.PublicDnsName}:5000"}
            },
            "ArtifactsBucket": {
                "Description": "S3 bucket for MLflow artifacts",
                "Value": {"Ref": "MLflowArtifactsBucket"}
            }
        }
    }
    
    return template

if __name__ == "__main__":
    print("MLflow AWS Setup Guide")
    print("=" * 30)
    print(get_mlflow_setup_commands())
    
    # Save CloudFormation template
    import json
    template = create_mlflow_cloudformation_template()
    with open('/tmp/mlflow-infrastructure.json', 'w') as f:
        json.dump(template, f, indent=2)
    print("\n✅ CloudFormation template saved to: /tmp/mlflow-infrastructure.json")
