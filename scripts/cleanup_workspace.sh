#!/bin/bash
# Workspace Cleanup Script
# Removes temporary files and organizes the project structure

echo "🧹 MLOps Workspace Cleanup"
echo "========================="

cd /home/yeefei93/mlops-eks-pipeline

# Remove temporary files
echo "🗑️  Removing temporary files..."
rm -f monitoring_status_*.json
rm -f response.json
rm -f test_response.json
rm -f alert_*.log
rm -f lambda-deployment.zip
rm -f lambda_update.zip
rm -f test-response.json

# Clean Python cache
echo "🐍 Cleaning Python cache..."
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
rm -rf .pytest_cache/
rm -f .coverage

# Clean up duplicate files
echo "📁 Removing duplicates..."
rm -f *_fixed.* *_simple.* *_temp.*

# Organize log files
echo "📋 Organizing logs..."
mkdir -p logs
mv *.log logs/ 2>/dev/null || true

echo "✅ Workspace cleanup completed!"
echo ""
echo "📂 Current Structure:"
echo "├── deployment/     # AWS deployment scripts"
echo "├── docs/          # Documentation and guides"
echo "├── infrastructure/ # CloudFormation templates"  
echo "├── logs/          # Log files"
echo "├── monitoring/    # Monitoring and alerting"
echo "├── scripts/       # Setup and utility scripts"
echo "├── src/           # Core application code"
echo "├── tests/         # Test files"
echo "└── mlruns/        # MLflow experiment data"
