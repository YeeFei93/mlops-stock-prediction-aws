#!/usr/bin/env python3
"""
Fixed Web Dashboard for MLOps Monitoring
Creates a working HTML dashboard that auto-refreshes
"""

import json
import os
import sys
from datetime import datetime, timedelta

# Add the project root to the path to import from monitoring directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monitor_deployment import MLOpsMonitor

def generate_html_dashboard():
    """Generate an HTML dashboard"""
    
    # Get current status
    monitor = MLOpsMonitor()
    status = monitor.check_aws_resources()
    
    now = datetime.utcnow()
    next_deployment = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if now.hour >= 0:
        next_deployment += timedelta(days=1)
    next_collection = now.replace(hour=9, minute=0, second=0, microsecond=0)  
    if now.hour >= 9:
        next_collection += timedelta(days=1)
    
    deployment_in = next_deployment - now
    collection_in = next_collection - now
    
    # Get status information safely
    s3_status = "healthy" if status and status.get('details', {}).get('s3', {}).get('status') == 'healthy' else "missing"
    lambda_status = "healthy" if status and status.get('details', {}).get('lambda', {}).get('status') == 'healthy' else "missing"
    eventbridge_status = "healthy" if status and status.get('details', {}).get('eventbridge', {}).get('status') == 'healthy' else "missing"
    
    s3_files = status.get('details', {}).get('s3', {}).get('files', 0) if status else 0
    lambda_state = status.get('details', {}).get('lambda', {}).get('state', 'Unknown') if status else 'Unknown'
    
    overall_healthy = status and status.get('resources_healthy', False)
    
    # Generate HTML with safe string formatting
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>MLOps Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="300">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }
        .dashboard {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 30px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.2);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid rgba(255,255,255,0.3);
            padding-bottom: 20px;
        }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .status-card {
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.2);
        }
        .healthy { border-left: 5px solid #4CAF50; }
        .missing { border-left: 5px solid #F44336; }
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 5px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .countdown {
            font-size: 1.5em;
            font-weight: bold;
            text-align: center;
            background: rgba(255,255,255,0.1);
            border-radius: 10px;
            padding: 20px;
            margin: 20px 0;
        }
        .status-green { color: #4CAF50; }
        .status-red { color: #F44336; }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.3);
            opacity: 0.7;
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <h1>🎯 MLOps Stock Prediction Dashboard</h1>
            <p>🕒 Last Update: """ + now.strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
            <p>📊 Account: 255945442255 | 🌐 Region: us-east-1</p>
        </div>
        
        <div class="status-grid">
            <div class="status-card """ + ("healthy" if s3_status == "healthy" else "missing") + """">
                <h3>📦 S3 Storage</h3>
                <div class="metric">
                    <span>Status:</span>
                    <span class=\"""" + ("status-green" if s3_status == "healthy" else "status-red") + """\">""" + ("✅ Healthy" if s3_status == "healthy" else "❌ Missing") + """</span>
                </div>
                <div class="metric">
                    <span>Bucket:</span>
                    <span>mlops-stock-data-255945442255-us-east-1</span>
                </div>
                <div class="metric">
                    <span>Files:</span>
                    <span>""" + str(s3_files) + """</span>
                </div>
            </div>
            
            <div class="status-card """ + ("healthy" if lambda_status == "healthy" else "missing") + """">
                <h3>⚡ Lambda Function</h3>
                <div class="metric">
                    <span>Status:</span>
                    <span class=\"""" + ("status-green" if lambda_status == "healthy" else "status-red") + """\">""" + ("✅ Healthy" if lambda_status == "healthy" else "❌ Missing") + """</span>
                </div>
                <div class="metric">
                    <span>Function:</span>
                    <span>stock-data-collector</span>
                </div>
                <div class="metric">
                    <span>State:</span>
                    <span>""" + lambda_state + """</span>
                </div>
            </div>
            
            <div class="status-card """ + ("healthy" if eventbridge_status == "healthy" else "missing") + """">
                <h3>📅 EventBridge</h3>
                <div class="metric">
                    <span>Status:</span>
                    <span class=\"""" + ("status-green" if eventbridge_status == "healthy" else "status-red") + """\">""" + ("✅ Healthy" if eventbridge_status == "healthy" else "❌ Missing") + """</span>
                </div>
                <div class="metric">
                    <span>Rule:</span>
                    <span>daily-stock-collection</span>
                </div>
                <div class="metric">
                    <span>Schedule:</span>
                    <span>Daily at 9 AM UTC</span>
                </div>
            </div>
        </div>
        
        <div class="countdown">
            <h3>⏰ Next Events</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div>
                    <div>🌅 Next Deployment</div>
                    <div style="font-size: 0.7em; margin-top: 5px;">""" + str(deployment_in).split('.')[0] + """</div>
                    <div style="font-size: 0.5em; margin-top: 5px;">(8 AM Singapore)</div>
                </div>
                <div>
                    <div>📊 Next Collection</div>
                    <div style="font-size: 0.7em; margin-top: 5px;">""" + str(collection_in).split('.')[0] + """</div>
                    <div style="font-size: 0.5em; margin-top: 5px;">(5 PM Singapore)</div>
                </div>
            </div>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
            <div class="status-card">
                <h3>💰 Cost Monitoring</h3>
                <div class="metric"><span>Daily:</span><span>~$0.000004</span></div>
                <div class="metric"><span>Monthly:</span><span>~$0.00012</span></div>
                <div class="metric"><span>Yearly:</span><span>~$0.0014</span></div>
                <div style="text-align: center; margin-top: 15px; color: #4CAF50;">
                    🎯 Practically FREE!
                </div>
            </div>
            
            <div class="status-card">
                <h3>🔗 Quick Links</h3>
                <div style="margin: 10px 0;">
                    <a href="https://github.com/YeeFei93/mlops-stock-prediction-aws/actions" target="_blank" 
                       style="color: #87CEEB; text-decoration: none;">
                        📱 GitHub Actions →
                    </a>
                </div>
                <div style="margin: 10px 0;">
                    <a href="https://console.aws.amazon.com/lambda/home?region=us-east-1#/functions/stock-data-collector" target="_blank"
                       style="color: #87CEEB; text-decoration: none;">
                        ⚡ AWS Lambda →
                    </a>
                </div>
                <div style="margin: 10px 0;">
                    <a href="https://console.aws.amazon.com/s3/buckets/mlops-stock-data-255945442255-us-east-1" target="_blank"
                       style="color: #87CEEB; text-decoration: none;">
                        📦 S3 Bucket →
                    </a>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 MLOps Stock Prediction System | Auto-refreshes every 5 minutes</p>
            <p>""" + ("🟢 SYSTEM HEALTHY" if overall_healthy else "🔴 ATTENTION NEEDED") + """</p>
            <p style="font-size: 0.9em;">
                """ + ("🎉 Your automated MLOps pipeline is working perfectly!" if overall_healthy else "🔧 Resources will be auto-deployed at 8 AM Singapore time") + """
            </p>
        </div>
    </div>
</body>
</html>"""
    
    return html_content

def main():
    """Generate and save HTML dashboard"""
    try:
        html = generate_html_dashboard()
        # Save to project root, not monitoring directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dashboard_file = os.path.join(project_root, "mlops_dashboard.html")
        
        with open(dashboard_file, 'w') as f:
            f.write(html)
            
        print(f"✅ Fixed HTML Dashboard generated: {dashboard_file}")
        print(f"🌐 Open in browser: file://{dashboard_file}")
        print(f"🔄 Auto-refreshes every 5 minutes")
        
    except Exception as e:
        print(f"❌ Error generating dashboard: {e}")

if __name__ == "__main__":
    main()
