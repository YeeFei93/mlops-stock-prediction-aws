#!/bin/bash
# MLOps Stock Prediction - Comprehensive Deployment Script
# Supports multiple deployment methods: AWS Serverless, Docker, Kubernetes, Terraform

set -euo pipefail

# Configuration
PROJECT_NAME="mlops-stock-prediction"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
DEPLOYMENT_METHOD="${DEPLOYMENT_METHOD:-serverless}"
ENVIRONMENT="${ENVIRONMENT:-prod}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_DIR/deployment.log"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_DIR/deployment.log"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_DIR/deployment.log"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_DIR/deployment.log"
}

# Usage function
usage() {
    cat << EOF
MLOps Stock Prediction Deployment Script

Usage: $0 [OPTIONS]

OPTIONS:
    -m, --method METHOD     Deployment method: serverless, docker, kubernetes, terraform
    -e, --environment ENV   Environment: dev, staging, prod (default: prod)
    -r, --region REGION     AWS region (default: us-east-1)
    -c, --cleanup          Cleanup existing resources before deployment
    -t, --test            Run tests after deployment
    -h, --help            Show this help message

DEPLOYMENT METHODS:
    serverless    Deploy using AWS Lambda + S3 + EventBridge (default)
    docker        Build and run Docker containers locally
    kubernetes    Deploy to Kubernetes cluster
    terraform     Deploy using Terraform Infrastructure as Code
    ansible       Deploy using Ansible automation

EXAMPLES:
    $0 --method serverless --environment prod
    $0 --method docker --test
    $0 --method terraform --region us-west-2 --cleanup
    $0 --method kubernetes --environment staging

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--method)
                DEPLOYMENT_METHOD="$2"
                shift 2
                ;;
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -r|--region)
                AWS_DEFAULT_REGION="$2"
                shift 2
                ;;
            -c|--cleanup)
                CLEANUP_FIRST=true
                shift
                ;;
            -t|--test)
                RUN_TESTS=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites for deployment method: $DEPLOYMENT_METHOD"
    
    # Common prerequisites
    command -v python3 >/dev/null 2>&1 || { log_error "Python 3 is required"; exit 1; }
    
    case $DEPLOYMENT_METHOD in
        serverless|terraform)
            command -v aws >/dev/null 2>&1 || { log_error "AWS CLI is required"; exit 1; }
            aws sts get-caller-identity >/dev/null 2>&1 || { log_error "AWS credentials not configured"; exit 1; }
            ;;
        docker)
            command -v docker >/dev/null 2>&1 || { log_error "Docker is required"; exit 1; }
            docker info >/dev/null 2>&1 || { log_error "Docker daemon not running"; exit 1; }
            ;;
        kubernetes)
            command -v kubectl >/dev/null 2>&1 || { log_error "kubectl is required"; exit 1; }
            kubectl cluster-info >/dev/null 2>&1 || { log_error "Kubernetes cluster not accessible"; exit 1; }
            ;;
        terraform)
            command -v terraform >/dev/null 2>&1 || { log_error "Terraform is required"; exit 1; }
            ;;
        ansible)
            command -v ansible-playbook >/dev/null 2>&1 || { log_error "Ansible is required"; exit 1; }
            ;;
    esac
    
    log_success "Prerequisites check passed"
}

# Initialize deployment
init_deployment() {
    log_info "Initializing deployment"
    
    # Create log directory
    mkdir -p "$LOG_DIR"
    
    # Set default AWS region if not set
    export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
    
    # Generate deployment ID
    DEPLOYMENT_ID="deploy_$(date +%Y%m%d_%H%M%S)_$$"
    
    log_info "Deployment ID: $DEPLOYMENT_ID"
    log_info "Environment: $ENVIRONMENT"
    log_info "Region: $AWS_DEFAULT_REGION"
    log_info "Method: $DEPLOYMENT_METHOD"
}

# Cleanup existing resources
cleanup_resources() {
    if [[ "${CLEANUP_FIRST:-false}" == "true" ]]; then
        log_info "Cleaning up existing resources"
        
        case $DEPLOYMENT_METHOD in
            serverless)
                python3 "$PROJECT_ROOT/deployment/cleanup_aws.py" || true
                ;;
            docker)
                docker-compose -f "$PROJECT_ROOT/docker/docker-compose.yml" down --volumes --remove-orphans || true
                docker rmi "$PROJECT_NAME:latest" || true
                ;;
            kubernetes)
                kubectl delete namespace "$PROJECT_NAME" --ignore-not-found=true || true
                ;;
            terraform)
                cd "$PROJECT_ROOT/infrastructure/terraform"
                terraform destroy -auto-approve -var="environment=$ENVIRONMENT" || true
                cd "$PROJECT_ROOT"
                ;;
        esac
        
        log_success "Cleanup completed"
    fi
}

# Deploy using serverless method
deploy_serverless() {
    log_info "Deploying using serverless architecture"
    
    cd "$PROJECT_ROOT"
    python3 deployment/deploy_aws.py
    
    # Update Lambda function
    if [[ -f "lambda_deployment.zip" ]]; then
        log_info "Updating Lambda function code"
        python3 deployment/update_lambda.py || true
    fi
    
    log_success "Serverless deployment completed"
}

# Deploy using Docker
deploy_docker() {
    log_info "Deploying using Docker"
    
    cd "$PROJECT_ROOT/docker"
    
    # Build images
    docker-compose build
    
    # Start services
    docker-compose up -d
    
    # Wait for services to be ready
    log_info "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    if curl -f http://localhost:8080/health >/dev/null 2>&1; then
        log_success "Docker deployment completed - Services are healthy"
    else
        log_warning "Docker deployment completed - Services may need more time to start"
    fi
}

# Deploy using Kubernetes
deploy_kubernetes() {
    log_info "Deploying using Kubernetes"
    
    cd "$PROJECT_ROOT/kubernetes"
    
    # Apply manifests
    kubectl apply -f deployment.yaml
    kubectl apply -f jobs.yaml
    kubectl apply -f rbac.yaml
    
    # Wait for deployment
    kubectl wait --for=condition=available --timeout=300s deployment/mlops-api -n "$PROJECT_NAME"
    
    log_success "Kubernetes deployment completed"
}

# Deploy using Terraform
deploy_terraform() {
    log_info "Deploying using Terraform"
    
    cd "$PROJECT_ROOT/infrastructure/terraform"
    
    # Initialize Terraform
    terraform init
    
    # Plan deployment
    terraform plan -var="environment=$ENVIRONMENT" -var="aws_region=$AWS_DEFAULT_REGION"
    
    # Apply deployment
    terraform apply -auto-approve -var="environment=$ENVIRONMENT" -var="aws_region=$AWS_DEFAULT_REGION"
    
    # Save outputs
    terraform output > "$LOG_DIR/terraform_outputs.txt"
    
    cd "$PROJECT_ROOT"
    log_success "Terraform deployment completed"
}

# Deploy using Ansible
deploy_ansible() {
    log_info "Deploying using Ansible"
    
    cd "$PROJECT_ROOT/ansible"
    
    # Run Ansible playbook
    ansible-playbook -i localhost, site.yml \
        -e "environment=$ENVIRONMENT" \
        -e "aws_region=$AWS_DEFAULT_REGION" \
        --connection=local
    
    cd "$PROJECT_ROOT"
    log_success "Ansible deployment completed"
}

# Run deployment tests
run_tests() {
    if [[ "${RUN_TESTS:-false}" == "true" ]]; then
        log_info "Running deployment tests"
        
        # Run Python tests
        python3 -m pytest tests/ -v || log_warning "Some tests failed"
        
        # Test API endpoints based on deployment method
        case $DEPLOYMENT_METHOD in
            serverless)
                # Test Lambda function
                if command -v aws >/dev/null 2>&1; then
                    aws lambda invoke --function-name "$PROJECT_NAME-data-collector" \
                        --payload '{"test": true}' /tmp/lambda_test_response.json || true
                fi
                ;;
            docker)
                # Test Docker service
                curl -f http://localhost:8080/health || log_warning "Docker service health check failed"
                ;;
            kubernetes)
                # Test Kubernetes service
                kubectl get pods -n "$PROJECT_NAME" || true
                ;;
        esac
        
        log_success "Tests completed"
    fi
}

# Generate deployment report
generate_report() {
    log_info "Generating deployment report"
    
    REPORT_FILE="$LOG_DIR/deployment_report_$DEPLOYMENT_ID.txt"
    
    cat > "$REPORT_FILE" << EOF
MLOps Stock Prediction Deployment Report
========================================

Deployment ID: $DEPLOYMENT_ID
Timestamp: $(date)
Environment: $ENVIRONMENT
Method: $DEPLOYMENT_METHOD
Region: $AWS_DEFAULT_REGION

Status: SUCCESS
Duration: $((SECONDS / 60)) minutes $((SECONDS % 60)) seconds

Resources Deployed:
EOF

    case $DEPLOYMENT_METHOD in
        serverless)
            echo "- AWS Lambda Function" >> "$REPORT_FILE"
            echo "- S3 Bucket" >> "$REPORT_FILE"
            echo "- EventBridge Rule" >> "$REPORT_FILE"
            echo "- IAM Roles" >> "$REPORT_FILE"
            if [[ "${enable_api_gateway:-true}" == "true" ]]; then
                echo "- API Gateway" >> "$REPORT_FILE"
            fi
            ;;
        docker)
            echo "- Docker Containers" >> "$REPORT_FILE"
            echo "- Docker Networks" >> "$REPORT_FILE"
            echo "- Docker Volumes" >> "$REPORT_FILE"
            ;;
        kubernetes)
            echo "- Kubernetes Namespace" >> "$REPORT_FILE"
            echo "- Deployment" >> "$REPORT_FILE"
            echo "- Service" >> "$REPORT_FILE"
            echo "- ConfigMap" >> "$REPORT_FILE"
            echo "- Secrets" >> "$REPORT_FILE"
            ;;
        terraform)
            echo "- Infrastructure as Code" >> "$REPORT_FILE"
            if [[ -f "$LOG_DIR/terraform_outputs.txt" ]]; then
                echo "" >> "$REPORT_FILE"
                echo "Terraform Outputs:" >> "$REPORT_FILE"
                cat "$LOG_DIR/terraform_outputs.txt" >> "$REPORT_FILE"
            fi
            ;;
    esac
    
    cat >> "$REPORT_FILE" << EOF

Next Steps:
1. Verify all services are running correctly
2. Test the prediction API endpoints
3. Monitor system performance and costs
4. Set up automated monitoring and alerts

For more information, check the logs in: $LOG_DIR
EOF

    log_success "Deployment report generated: $REPORT_FILE"
}

# Main deployment function
main() {
    local start_time=$SECONDS
    
    log_info "Starting MLOps Stock Prediction deployment"
    
    # Parse arguments
    parse_args "$@"
    
    # Initialize
    init_deployment
    
    # Check prerequisites
    check_prerequisites
    
    # Cleanup if requested
    cleanup_resources
    
    # Deploy based on method
    case $DEPLOYMENT_METHOD in
        serverless)
            deploy_serverless
            ;;
        docker)
            deploy_docker
            ;;
        kubernetes)
            deploy_kubernetes
            ;;
        terraform)
            deploy_terraform
            ;;
        ansible)
            deploy_ansible
            ;;
        *)
            log_error "Unknown deployment method: $DEPLOYMENT_METHOD"
            usage
            exit 1
            ;;
    esac
    
    # Run tests
    run_tests
    
    # Generate report
    generate_report
    
    local end_time=$SECONDS
    local duration=$((end_time - start_time))
    
    log_success "🎉 Deployment completed successfully in $((duration / 60))m $((duration % 60))s"
    log_info "Check $LOG_DIR for detailed logs and reports"
}

# Trap errors
trap 'log_error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"
