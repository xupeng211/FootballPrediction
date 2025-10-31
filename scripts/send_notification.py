#!/usr/bin/env python3
"""
Smart Notification Sender
智能通知发送器
"""

import json
import os
import sys
import requests
from datetime import datetime
from typing import Dict, Any, Optional

class NotificationSender:
    def __init__(self):
        self.webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.email_enabled = os.getenv('EMAIL_NOTIFICATIONS', 'false').lower() == 'true'
        self.github_token = os.getenv('GITHUB_TOKEN')

    def send_slack_notification(self, message: str, color: str = 'good') -> bool:
        """发送Slack通知"""
        if not self.webhook_url:
            print("ℹ️  Slack webhook URL not configured")
            return False

        payload = {
            "attachments": [{
                "color": color,
                "text": message,
                "footer": "FootballPrediction CI/CD",
                "ts": datetime.now().timestamp()
            }]
        }

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ Slack notification sent: {color}")
            return True
        except Exception as e:
            print(f"❌ Failed to send Slack notification: {e}")
            return False

    def create_quality_message(self, status: str, workflow: str, data_file: str) -> str:
        """创建质量报告消息"""
        message = f"""
🔍 *Quality Gate Report*

*Workflow*: {workflow}
*Status*: {status.upper()}
*Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # 分析数据文件
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)

            # 添加关键指标
            if 'conclusion' in data:
                message += f"*Conclusion*: {data['conclusion']}\n"

            if 'duration' in data:
                duration = data.get('duration', 0) / 1000  # 转换为秒
                message += f"*Duration*: {duration:.1f}s\n"

        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️  Could not analyze data file: {e}")

        return message

    def create_performance_message(self, metrics: Dict[str, Any]) -> str:
        """创建性能报告消息"""
        message = """
⚡ *Performance Report*

"""

        # 添加性能指标
        if 'response_time' in metrics:
            message += f"*Response Time*: {metrics['response_time']:.2f}s\n"

        if 'throughput' in metrics:
            message += f"*Throughput*: {metrics['throughput']:.0f} req/s\n"

        if 'memory_usage' in metrics:
            message += f"*Memory Usage*: {metrics['memory_usage']}%\n"

        if 'cpu_usage' in metrics:
            message += f"*CPU Usage*: {metrics['cpu_usage']}%\n"

        return message

    def create_security_message(self, issues: Dict[str, Any]) -> str:
        """创建安全报告消息"""
        message = """
🛡️ *Security Report*

"""

        # 添加安全问题统计
        if 'bandit' in issues:
            high = issues['bandit'].get('high', 0)
            medium = issues['bandit'].get('medium', 0)
            low = issues['bandit'].get('low', 0)
            message += f"*Bandit Issues*: {high} High, {medium} Medium, {low} Low\n"

        if 'safety' in issues:
            vulnerabilities = len(issues['safety'].get('vulnerabilities', []))
            message += f"*Dependency Vulnerabilities*: {vulnerabilities}\n"

        return message

    def send_notification(self, notification_type: str, **kwargs) -> bool:
        """发送通知"""
        message = ""
        color = "good"

        if notification_type == "quality":
            status = kwargs.get('status', 'unknown')
            workflow = kwargs.get('workflow', 'unknown')
            data_file = kwargs.get('data', 'workflow_details.json')

            message = self.create_quality_message(status, workflow, data_file)
            color = "good" if status == "success" else "danger"

        elif notification_type == "performance":
            metrics = kwargs.get('metrics', {})
            message = self.create_performance_message(metrics)

            # 根据性能指标决定颜色
            if metrics.get('response_time', 0) > 2.0:
                color = "warning"
            if metrics.get('response_time', 0) > 5.0:
                color = "danger"

        elif notification_type == "security":
            issues = kwargs.get('issues', {})
            message = self.create_security_message(issues)

            # 根据安全问题决定颜色
            total_issues = sum(
                issues.get('bandit', {}).get('high', 0) +
                len(issues.get('safety', {}).get('vulnerabilities', []))
            )
            if total_issues > 0:
                color = "warning"
            if total_issues > 5:
                color = "danger"

        elif notification_type == "deployment":
            commit = kwargs.get('commit', 'unknown')
            branch = kwargs.get('branch', 'unknown')
            status = kwargs.get('status', 'unknown')

            status_emoji = {
                'started': '🚀',
                'success': '✅',
                'failed': '❌'
            }.get(status, '❓')

            message = f"""
🚀 *Deployment Status*

{status_emoji} *Status*: {status.upper()}
*Commit*: {commit[:8]}
*Branch*: {branch}
*Time*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            color = "good" if status == "success" else "danger"

        else:
            message = f"📢 *Notification*\n\nUnknown notification type: {notification_type}"
            color = "warning"

        # 发送到Slack
        return self.send_slack_notification(message, color)

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Send smart notifications')
    parser.add_argument('--type', required=True, choices=['quality', 'performance', 'security', 'deployment'])
    parser.add_argument('--status', help='Status (success/failure/started)')
    parser.add_argument('--workflow', help='Workflow name')
    parser.add_argument('--commit', help='Commit hash')
    parser.add_argument('--branch', help='Branch name')
    parser.add_argument('--data', help='Data file path')

    args = parser.parse_args()

    sender = NotificationSender()

    kwargs = {}
    if args.status:
        kwargs['status'] = args.status
    if args.workflow:
        kwargs['workflow'] = args.workflow
    if args.commit:
        kwargs['commit'] = args.commit
    if args.branch:
        kwargs['branch'] = args.branch
    if args.data:
        kwargs['data'] = args.data

    success = sender.send_notification(args.type, **kwargs)

    if success:
        print("✅ Notification sent successfully")
        sys.exit(0)
    else:
        print("❌ Failed to send notification")
        sys.exit(1)

if __name__ == "__main__":
    main()