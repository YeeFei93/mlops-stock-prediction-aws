# MLOps Stock Prediction - Terraform Infrastructure
# Alternative to CloudFormation for enterprise flexibility

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Optional: Use S3 backend for state management
  # backend "s3" {
  #   bucket = "mlops-terraform-state-bucket"
  #   key    = "mlops/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name of the MLOps project"
  type        = string
  default     = "mlops-stock-prediction"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
    Owner       = "mlops-team"
    CostCenter  = "engineering"
  }
}

# VPC and Networking (Production-grade) - Conditional based on enable_vpc
resource "aws_vpc" "mlops_vpc" {
  count = var.enable_vpc ? 1 : 0
  
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-vpc"
  })
}

resource "aws_internet_gateway" "mlops_igw" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id = aws_vpc.mlops_vpc[0].id
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-igw"
  })
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_subnet" "mlops_subnet_public" {
  count = var.enable_vpc ? 2 : 0
  
  vpc_id            = aws_vpc.mlops_vpc[0].id
  cidr_block        = "10.0.${count.index + 1}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  map_public_ip_on_launch = true
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
    Type = "public"
  })
}

resource "aws_subnet" "mlops_subnet_private" {
  count = var.enable_vpc ? 2 : 0
  
  vpc_id            = aws_vpc.mlops_vpc[0].id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-private-subnet-${count.index + 1}"
    Type = "private"
  })
}

resource "aws_route_table" "mlops_public_rt" {
  count = var.enable_vpc ? 1 : 0
  
  vpc_id = aws_vpc.mlops_vpc[0].id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.mlops_igw[0].id
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-public-rt"
  })
}

resource "aws_route_table_association" "mlops_public_rta" {
  count = var.enable_vpc ? length(aws_subnet.mlops_subnet_public) : 0
  
  subnet_id      = aws_subnet.mlops_subnet_public[count.index].id
  route_table_id = aws_route_table.mlops_public_rt[0].id
}

# Security Groups
resource "aws_security_group" "lambda_sg" {
  count = var.enable_vpc ? 1 : 0
  
  name_prefix = "${var.project_name}-lambda-"
  vpc_id      = aws_vpc.mlops_vpc[0].id
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-lambda-sg"
  })
}

resource "aws_security_group" "api_gateway_sg" {
  count = var.enable_api_gateway && var.enable_vpc ? 1 : 0
  
  name_prefix = "${var.project_name}-api-"
  vpc_id      = aws_vpc.mlops_vpc[0].id
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from anywhere"
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound traffic"
  }
  
  tags = merge(local.common_tags, {
    Name = "${var.project_name}-api-sg"
  })
}

# S3 Bucket for data storage
resource "aws_s3_bucket" "mlops_data_bucket" {
  bucket = "${var.project_name}-data-${local.account_id}-${local.region}"
  
  tags = local.common_tags
}

resource "aws_s3_bucket_versioning" "mlops_data_versioning" {
  bucket = aws_s3_bucket.mlops_data_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_encryption" "mlops_data_encryption" {
  bucket = aws_s3_bucket.mlops_data_bucket.id
  
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "mlops_data_lifecycle" {
  bucket = aws_s3_bucket.mlops_data_bucket.id
  
  rule {
    id     = "delete_old_data"
    status = "Enabled"
    
    expiration {
      days = var.s3_lifecycle_days
    }
    
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
  
  tags = local.common_tags
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy"
  role = aws_iam_role.lambda_execution_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.mlops_data_bucket.arn,
          "${aws_s3_bucket.mlops_data_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:CreateNetworkInterface",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DeleteNetworkInterface"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "stock_data_collector" {
  filename      = "lambda_deployment.zip"
  function_name = "${var.project_name}-data-collector"
  role         = aws_iam_role.lambda_execution_role.arn
  handler      = "lambda_simple.lambda_handler"
  runtime      = "python3.9"
  memory_size  = var.lambda_memory
  timeout      = var.lambda_timeout
  
  dynamic "vpc_config" {
    for_each = var.enable_vpc ? [1] : []
    content {
      subnet_ids         = aws_subnet.mlops_subnet_private[*].id
      security_group_ids = [aws_security_group.lambda_sg[0].id]
    }
  }
  
  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.mlops_data_bucket.bucket
      ENVIRONMENT = var.environment
      STOCK_SYMBOLS = join(",", var.stock_symbols)
    }
  }
  
  tags = local.common_tags
  
  depends_on = [aws_iam_role_policy.lambda_policy]
}

# API Gateway (conditional)
resource "aws_api_gateway_rest_api" "mlops_api" {
  count = var.enable_api_gateway ? 1 : 0
  
  name        = "${var.project_name}-api"
  description = "MLOps Stock Prediction API"
  
  endpoint_configuration {
    types = ["REGIONAL"]
  }
  
  tags = local.common_tags
}

resource "aws_api_gateway_resource" "predict" {
  count = var.enable_api_gateway ? 1 : 0
  
  rest_api_id = aws_api_gateway_rest_api.mlops_api[0].id
  parent_id   = aws_api_gateway_rest_api.mlops_api[0].root_resource_id
  path_part   = "predict"
}

resource "aws_api_gateway_method" "predict_post" {
  count = var.enable_api_gateway ? 1 : 0
  
  rest_api_id   = aws_api_gateway_rest_api.mlops_api[0].id
  resource_id   = aws_api_gateway_resource.predict[0].id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_integration" {
  count = var.enable_api_gateway ? 1 : 0
  
  rest_api_id = aws_api_gateway_rest_api.mlops_api[0].id
  resource_id = aws_api_gateway_resource.predict[0].id
  http_method = aws_api_gateway_method.predict_post[0].http_method
  
  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = aws_lambda_function.stock_data_collector.invoke_arn
}

resource "aws_lambda_permission" "api_gateway" {
  count = var.enable_api_gateway ? 1 : 0
  
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stock_data_collector.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.mlops_api[0].execution_arn}/*/*"
}

resource "aws_api_gateway_deployment" "mlops_deployment" {
  count = var.enable_api_gateway ? 1 : 0
  
  depends_on = [
    aws_api_gateway_method.predict_post,
    aws_api_gateway_integration.lambda_integration,
  ]
  
  rest_api_id = aws_api_gateway_rest_api.mlops_api[0].id
  
  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "mlops_stage" {
  count = var.enable_api_gateway ? 1 : 0
  
  deployment_id = aws_api_gateway_deployment.mlops_deployment[0].id
  rest_api_id   = aws_api_gateway_rest_api.mlops_api[0].id
  stage_name    = var.api_gateway_stage
  
  tags = local.common_tags
}

# EventBridge Rule for scheduled execution
resource "aws_cloudwatch_event_rule" "daily_collection" {
  name                = "${var.project_name}-daily-collection"
  description         = "Trigger stock data collection daily"
  schedule_expression = var.schedule_expression
  
  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_collection.name
  target_id = "StockDataCollectorTarget"
  arn       = aws_lambda_function.stock_data_collector.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stock_data_collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_collection.arn
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.stock_data_collector.function_name}"
  retention_in_days = var.log_retention_days
  
  tags = local.common_tags
}

# Outputs
output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = "${aws_api_gateway_deployment.mlops_deployment.invoke_url}/predict"
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.mlops_data_bucket.bucket
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.stock_data_collector.function_name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.mlops_vpc.id
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.mlops_vpc.cidr_block
}
