#!/usr/bin/env python3
"""
MLOps Alert System
Sends notifications when resources are missing or deployments fail
"""

import smtplib
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from monitor_deployment import MLOpsMonitor

class AlertSystem:
    def __init__(self):
        self.monitor = MLOpsMonitor()
        
    def check_and_alert(self):
        """Check system status and send alerts if needed"""
        print("🚨 ALERT SYSTEM CHECK")
        print("=" * 40)
        
        status = self.monitor.check_aws_resources()
        
        if not status or not status.get('resources_healthy', False):
            self.send_alert(status)
            return False
        else:
            print("✅ All systems healthy - no alerts needed")
            return True
            
    def send_alert(self, status):
        """Send alert notification"""
        print("🚨 ALERT: Resources missing!")
        
        # Create alert message
        missing_resources = []
        if status and status.get('details'):
            for resource, info in status['details'].items():
                if info.get('status') != 'healthy':
                    missing_resources.append(resource.upper())
        
        alert_message = self.format_alert_message(missing_resources)
        
        # For demo, just print the alert
        # In production, you'd send via email/Slack/SMS
        print("\n" + "="*50)
        print("📧 ALERT MESSAGE (would be sent via email/Slack):")
        print("="*50)
        print(alert_message)
        print("="*50)
        
        # Save alert to file for logging
        self.log_alert(alert_message, missing_resources)
        
    def format_alert_message(self, missing_resources):
        """Format the alert message"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        
        message = f"""
🚨 MLOps ALERT: Resources Missing

⏰ Time: {timestamp}
🌍 Account: 255945442255
🌐 Region: us-east-1

❌ Missing Resources:
"""
        
        for resource in missing_resources:
            message += f"   • {resource}\n"
            
        message += f"""
🔧 Automatic Resolution:
   • GitHub Actions will redeploy at 8 AM Singapore time
   • Manual deployment: python deploy_aws.py
   
📊 Expected Recovery:
   • Next auto-deployment: Tomorrow 8 AM Singapore (00:00 UTC)
   • Current status: Temporary disruption
   
🔗 Monitor:
   • GitHub Actions: https://github.com/YeeFei93/mlops-stock-prediction-aws/actions
   • Dashboard: Open mlops_dashboard.html in browser
   
This is an automated alert from your MLOps monitoring system.
"""
        return message
        
    def log_alert(self, message, missing_resources):
        """Log alert to file"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        alert_file = f"alert_{timestamp}.log"
        
        try:
            with open(alert_file, 'w') as f:
                f.write(message)
            print(f"📝 Alert logged to: {alert_file}")
        except Exception as e:
            print(f"⚠️  Could not save alert log: {e}")
            
    def setup_email_alerts(self, email_config):
        """Setup email alerts (for future use)"""
        # This would configure SMTP settings
        # email_config = {
        #     'smtp_server': 'smtp.gmail.com',
        #     'smtp_port': 587,
        #     'sender_email': 'your-email@gmail.com',
        #     'sender_password': 'your-app-password',
        #     'recipient_email': 'alerts@yourdomain.com'
        # }
        pass
        
    def send_email_alert(self, message, email_config):
        """Send email alert (for future use)"""
        # Implementation for actual email sending
        pass

def main():
    """Main alert checking function"""
    alert_system = AlertSystem()
    
    print("🎯 MLOps Alert System Starting...")
    healthy = alert_system.check_and_alert()
    
    if healthy:
        print("\n🎉 System Status: ALL GOOD!")
        print("💡 Tip: Run this script regularly (e.g., every hour) to monitor your system")
    else:
        print("\n⚠️  System Status: NEEDS ATTENTION")
        print("🔧 Don't worry - auto-deployment at 8 AM Singapore will fix this!")
        
    print(f"\n📋 Monitoring Commands:")
    print(f"   📊 Full Dashboard: python monitor_deployment.py")
    print(f"   🌐 Web Dashboard: python web_dashboard.py")
    print(f"   🚨 Alert Check: python alert_system.py")

if __name__ == "__main__":
    main()
