# Terraform Outputs
# Define all output values from the MLOps infrastructure

# API Gateway Outputs
output "api_gateway_url" {
  description = "URL of the API Gateway for making prediction requests"
  value       = var.enable_api_gateway ? "${aws_api_gateway_deployment.mlops_deployment[0].invoke_url}/${var.api_gateway_stage}/predict" : "API Gateway not enabled"
}

output "api_gateway_id" {
  description = "ID of the API Gateway REST API"
  value       = var.enable_api_gateway ? aws_api_gateway_rest_api.mlops_api[0].id : null
}

output "api_gateway_stage" {
  description = "API Gateway deployment stage"
  value       = var.enable_api_gateway ? var.api_gateway_stage : null
}

# S3 Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket storing ML data"
  value       = aws_s3_bucket.mlops_data_bucket.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.mlops_data_bucket.arn
}

output "s3_bucket_domain_name" {
  description = "Domain name of the S3 bucket"
  value       = aws_s3_bucket.mlops_data_bucket.bucket_domain_name
}

# Lambda Outputs
output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.stock_data_collector.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.stock_data_collector.arn
}

output "lambda_invoke_arn" {
  description = "Invoke ARN of the Lambda function"
  value       = aws_lambda_function.stock_data_collector.invoke_arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

# VPC Outputs (when VPC is enabled)
output "vpc_id" {
  description = "ID of the VPC"
  value       = var.enable_vpc ? aws_vpc.mlops_vpc[0].id : null
}

output "vpc_cidr" {
  description = "CIDR block of the VPC"
  value       = var.enable_vpc ? aws_vpc.mlops_vpc[0].cidr_block : null
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = var.enable_vpc ? aws_subnet.mlops_subnet_public[*].id : []
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = var.enable_vpc ? aws_subnet.mlops_subnet_private[*].id : []
}

output "internet_gateway_id" {
  description = "ID of the Internet Gateway"
  value       = var.enable_vpc ? aws_internet_gateway.mlops_igw[0].id : null
}

# Security Group Outputs
output "lambda_security_group_id" {
  description = "ID of the Lambda security group"
  value       = var.enable_vpc ? aws_security_group.lambda_sg[0].id : null
}

output "api_security_group_id" {
  description = "ID of the API Gateway security group"
  value       = var.enable_api_gateway && var.enable_vpc ? aws_security_group.api_gateway_sg[0].id : null
}

# EventBridge Outputs
output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule for scheduled execution"
  value       = aws_cloudwatch_event_rule.daily_collection.name
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.daily_collection.arn
}

output "schedule_expression" {
  description = "EventBridge schedule expression"
  value       = var.schedule_expression
}

# CloudWatch Outputs
output "log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.lambda_logs.arn
}

# Monitoring Outputs (when enabled)
output "cost_alert_threshold" {
  description = "Monthly cost alert threshold in USD"
  value       = var.cost_alert_threshold
}

output "monitoring_enabled" {
  description = "Whether enhanced monitoring is enabled"
  value       = var.enable_monitoring
}

# Environment Information
output "environment" {
  description = "Deployment environment"
  value       = var.environment
}

output "project_name" {
  description = "Project name used for resource naming"
  value       = var.project_name
}

output "aws_region" {
  description = "AWS region where resources are deployed"
  value       = var.aws_region
}

output "account_id" {
  description = "AWS account ID"
  value       = data.aws_caller_identity.current.account_id
}

# Stock Configuration
output "stock_symbols" {
  description = "List of stock symbols being monitored"
  value       = var.stock_symbols
}

# Resource Tags
output "common_tags" {
  description = "Common tags applied to all resources"
  value       = local.common_tags
}

# Deployment Information
output "terraform_workspace" {
  description = "Terraform workspace used for deployment"
  value       = terraform.workspace
}

output "deployment_timestamp" {
  description = "Timestamp of the deployment"
  value       = timestamp()
}

# URLs and Endpoints
output "lambda_console_url" {
  description = "AWS Console URL for the Lambda function"
  value       = "https://${var.aws_region}.console.aws.amazon.com/lambda/home?region=${var.aws_region}#/functions/${aws_lambda_function.stock_data_collector.function_name}"
}

output "s3_console_url" {
  description = "AWS Console URL for the S3 bucket"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.mlops_data_bucket.bucket}"
}

output "cloudwatch_logs_url" {
  description = "AWS Console URL for CloudWatch logs"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#logsV2:log-groups/log-group/${replace(aws_cloudwatch_log_group.lambda_logs.name, "/", "$252F")}"
}

# Cost Estimation
output "estimated_monthly_cost" {
  description = "Estimated monthly cost in USD (approximate)"
  value       = "Less than $1.00 for typical usage"
}
