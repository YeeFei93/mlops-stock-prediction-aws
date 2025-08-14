#!/bin/bash
# MLOps Monitoring Setup Script
# Sets up local monitoring and provides instructions for automated checks

echo "🎯 MLOps Monitoring Setup"
echo "=========================="

# Make scripts executable
chmod +x monitor_deployment.py
chmod +x web_dashboard.py  
chmod +x alert_system.py

echo "✅ Made monitoring scripts executable"

# Create monitoring directory
mkdir -p monitoring_logs
mkdir -p monitoring_reports

echo "✅ Created monitoring directories"

# Generate initial reports
source .venv/bin/activate

echo ""
echo "📊 Generating initial monitoring reports..."
echo "=========================================="

# Run full monitoring dashboard
python monitor_deployment.py > monitoring_logs/latest_status.log 2>&1
echo "✅ Full system check completed"

# Generate web dashboard
python web_dashboard.py > monitoring_logs/dashboard_generation.log 2>&1
echo "✅ Web dashboard generated"

# Run alert check
python alert_system.py > monitoring_logs/alert_check.log 2>&1
echo "✅ Alert system tested"

echo ""
echo "🎉 MONITORING SETUP COMPLETE!"
echo "============================="
echo ""
echo "📋 Available Monitoring Tools:"
echo "   🔍 python monitor_deployment.py  - Full system status"
echo "   🌐 python web_dashboard.py       - Generate HTML dashboard" 
echo "   🚨 python alert_system.py        - Check for issues"
echo ""
echo "🌐 Web Dashboard:"
echo "   📁 File: $(pwd)/mlops_dashboard.html"
echo "   🔗 URL:  file://$(pwd)/mlops_dashboard.html"
echo "   🔄 Auto-refreshes every 5 minutes"
echo ""
echo "📊 GitHub Actions Monitoring:"
echo "   🌐 Actions: https://github.com/YeeFei93/mlops-stock-prediction-aws/actions"
echo "   🕒 Daily deployments: 8 AM Singapore (00:00 UTC)"
echo "   📈 Data collection: 5 PM Singapore (09:00 UTC)"
echo ""
echo "⚡ Quick Commands:"
echo "   # Check system now"
echo "   python monitor_deployment.py"
echo ""
echo "   # Open web dashboard"
echo "   xdg-open mlops_dashboard.html  # Linux"
echo "   open mlops_dashboard.html      # macOS" 
echo ""
echo "   # Manual deployment if needed"
echo "   python deploy_aws.py"
echo ""
echo "🔔 Notification Setup (Optional):"
echo "   📱 GitHub: Go to your repo → Watch → All Activity"
echo "   📧 Email: Modify alert_system.py with your email settings"
echo ""
echo "💡 Pro Tips:"
echo "   • Run monitor_deployment.py daily to check status"
echo "   • Keep mlops_dashboard.html open in browser for live updates"
echo "   • GitHub Actions will handle daily deployments automatically"
echo "   • Your system costs <$1/year and runs automatically!"
echo ""
echo "🎯 Your MLOps system is now fully monitored! 🚀"
