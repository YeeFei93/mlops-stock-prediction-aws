# Terraform Variables Configuration
# Define all input variables for the MLOps infrastructure

variable "aws_region" {
  description = "AWS region where resources will be deployed"
  type        = string
  default     = "us-east-1"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.aws_region))
    error_message = "AWS region must be a valid region identifier."
  }
}

variable "project_name" {
  description = "Name prefix for all MLOps resources"
  type        = string
  default     = "mlops-stock-prediction"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "lambda_memory" {
  description = "Memory allocation for Lambda function in MB"
  type        = number
  default     = 512
  validation {
    condition     = var.lambda_memory >= 128 && var.lambda_memory <= 10240
    error_message = "Lambda memory must be between 128 and 10240 MB."
  }
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function in seconds"
  type        = number
  default     = 300
  validation {
    condition     = var.lambda_timeout >= 1 && var.lambda_timeout <= 900
    error_message = "Lambda timeout must be between 1 and 900 seconds."
  }
}

variable "s3_lifecycle_days" {
  description = "Number of days after which objects are deleted from S3"
  type        = number
  default     = 90
  validation {
    condition     = var.s3_lifecycle_days > 0
    error_message = "S3 lifecycle days must be a positive number."
  }
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 14
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "Log retention days must be a valid CloudWatch retention period."
  }
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for data collection"
  type        = string
  default     = "cron(0 9 * * ? *)"  # Daily at 9 AM UTC (5 PM Singapore time)
  validation {
    condition     = can(regex("^(rate|cron)\\(.*\\)$", var.schedule_expression))
    error_message = "Schedule expression must be a valid EventBridge rate or cron expression."
  }
}

variable "enable_vpc" {
  description = "Whether to deploy Lambda functions in VPC"
  type        = bool
  default     = true
}

variable "enable_api_gateway" {
  description = "Whether to create API Gateway for REST endpoints"
  type        = bool
  default     = true
}

variable "api_gateway_stage" {
  description = "API Gateway deployment stage name"
  type        = string
  default     = "v1"
  validation {
    condition     = can(regex("^[a-zA-Z0-9]+$", var.api_gateway_stage))
    error_message = "API Gateway stage name must contain only alphanumeric characters."
  }
}

variable "enable_monitoring" {
  description = "Whether to enable enhanced monitoring and alerting"
  type        = bool
  default     = true
}

variable "cost_alert_threshold" {
  description = "Monthly cost threshold for billing alerts (USD)"
  type        = number
  default     = 10.00
  validation {
    condition     = var.cost_alert_threshold > 0
    error_message = "Cost alert threshold must be a positive number."
  }
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Environment-specific configurations
variable "environment_configs" {
  description = "Environment-specific configuration overrides"
  type = map(object({
    lambda_memory       = number
    lambda_timeout      = number
    log_retention_days  = number
    s3_lifecycle_days   = number
  }))
  default = {
    dev = {
      lambda_memory      = 256
      lambda_timeout     = 180
      log_retention_days = 7
      s3_lifecycle_days  = 30
    }
    staging = {
      lambda_memory      = 512
      lambda_timeout     = 300
      log_retention_days = 14
      s3_lifecycle_days  = 60
    }
    prod = {
      lambda_memory      = 512
      lambda_timeout     = 300
      log_retention_days = 30
      s3_lifecycle_days  = 90
    }
  }
}

# Stock symbols to collect data for
variable "stock_symbols" {
  description = "List of stock symbols to collect data for"
  type        = list(string)
  default     = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
  validation {
    condition     = length(var.stock_symbols) > 0
    error_message = "At least one stock symbol must be specified."
  }
}
