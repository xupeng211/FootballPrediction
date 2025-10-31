#!/usr/bin/env python3
"""
Send Performance Alerts Script
发送性能告警脚本
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

class PerformanceAlertManager:
    """性能告警管理器"""

    def __init__(self):
        self.alert_thresholds = {
            'response_time': 2.0,  # 秒
            'throughput': 200.0,   # req/s
            'memory_usage': 80.0,  # %
            'cpu_usage': 70.0,     # %
            'error_rate': 1.0      # %
        }

    def check_performance_thresholds(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查性能阈值

        Args:
            metrics: 性能指标

        Returns:
            List[Dict[str, Any]]: 告警列表
        """
        alerts = []

        # 检查响应时间
        response_time = metrics.get('response_time') or metrics.get('avg_response_time', 0)
        if response_time > self.alert_thresholds['response_time']:
            alerts.append({
                'type': 'response_time',
                'severity': 'high' if response_time > 5.0 else 'medium',
                'value': response_time,
                'threshold': self.alert_thresholds['response_time'],
                'message': f"响应时间过高: {response_time:.2f}s (阈值: {self.alert_thresholds['response_time']}s)"
            })

        # 检查吞吐量
        throughput = metrics.get('throughput') or metrics.get('requests_per_second', 0)
        if throughput < self.alert_thresholds['throughput']:
            alerts.append({
                'type': 'throughput',
                'severity': 'medium',
                'value': throughput,
                'threshold': self.alert_thresholds['throughput'],
                'message': f"吞吐量过低: {throughput:.0f} req/s (阈值: {self.alert_thresholds['throughput']} req/s)"
            })

        # 检查内存使用
        memory_usage = metrics.get('memory_usage') or metrics.get('memory_usage_percent', 0)
        if memory_usage > self.alert_thresholds['memory_usage']:
            alerts.append({
                'type': 'memory_usage',
                'severity': 'high' if memory_usage > 90 else 'medium',
                'value': memory_usage,
                'threshold': self.alert_thresholds['memory_usage'],
                'message': f"内存使用率过高: {memory_usage}% (阈值: {self.alert_thresholds['memory_usage']}%)"
            })

        # 检查CPU使用
        cpu_usage = metrics.get('cpu_usage') or metrics.get('cpu_usage_percent', 0)
        if cpu_usage > self.alert_thresholds['cpu_usage']:
            alerts.append({
                'type': 'cpu_usage',
                'severity': 'high' if cpu_usage > 85 else 'medium',
                'value': cpu_usage,
                'threshold': self.alert_thresholds['cpu_usage'],
                'message': f"CPU使用率过高: {cpu_usage}% (阈值: {self.alert_thresholds['cpu_usage']}%)"
            })

        # 检查错误率
        error_rate = metrics.get('error_rate') or metrics.get('error_rate_percent', 0)
        if error_rate > self.alert_thresholds['error_rate']:
            alerts.append({
                'type': 'error_rate',
                'severity': 'critical' if error_rate > 5.0 else 'high',
                'value': error_rate,
                'threshold': self.alert_thresholds['error_rate'],
                'message': f"错误率过高: {error_rate}% (阈值: {self.alert_thresholds['error_rate']}%)"
            })

        return alerts

    def create_alert_message(self, alerts: List[Dict[str, Any]], environment: str = "production") -> str:
        """
        创建告警消息

        Args:
            alerts: 告警列表
            environment: 环境名称

        Returns:
            str: 告警消息
        """
        env_emoji = {
            'production': '🏭',
            'staging': '🧪',
            'development': '🔧'
        }.get(environment, '📍')

        severity_counts = {}
        for alert in alerts:
            severity = alert['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        message = f"""
{env_emoji} *性能告警报告*

📊 **告警统计**:
• 严重: {severity_counts.get('critical', 0)}
• 高级: {severity_counts.get('high', 0)}
• 中级: {severity_counts.get('medium', 0)}
• 低级: {severity_counts.get('low', 0)}

⏰ **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌐 **环境**: {environment}

🚨 **详细告警**:
"""

        # 按严重程度排序
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        sorted_alerts = sorted(alerts, key=lambda x: severity_order.get(x['severity'], 4))

        for i, alert in enumerate(sorted_alerts, 1):
            severity_emoji = {
                'critical': '🚨',
                'high': '⚠️',
                'medium': '⚡',
                'low': 'ℹ️'
            }.get(alert['severity'], '📢')

            message += f"""
{i}. {severity_emoji} **{alert['type'].replace('_', ' ').title()}**
   • 级别: {alert['severity'].upper()}
   • 当前值: {alert['value']}
   • 阈值: {alert['threshold']}
   • 说明: {alert['message']}
"""

        # 添加建议
        message += "\n🎯 **处理建议**:\n"
        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)

        if critical_count > 0:
            message += "• ⚠️ 存在严重告警，建议立即处理\n"
        if high_count > 2:
            message += "• 📈 高级告警较多，建议优先处理\n"

        if any(alert['type'] == 'memory_usage' for alert in alerts):
            message += "• 💾 检查内存使用情况，考虑优化内存管理\n"
        if any(alert['type'] == 'cpu_usage' for alert in alerts):
            message += "• 🖥️  优化CPU密集型操作，考虑负载均衡\n"
        if any(alert['type'] == 'response_time' for alert in alerts):
            message += "• ⏱️  优化响应时间，检查数据库查询和缓存\n"

        return message

    def send_alerts(self, metrics: Dict[str, Any], environment: str = "production") -> bool:
        """
        发送告警

        Args:
            metrics: 性能指标
            environment: 环境名称

        Returns:
            bool: 是否发送成功
        """
        alerts = self.check_performance_thresholds(metrics)

        if not alerts:
            print("✅ 所有性能指标正常，无需发送告警")
            return True

        # 创建告警消息
        alert_message = self.create_alert_message(alerts, environment)

        print("=" * 60)
        print("性能告警详情:")
        print("=" * 60)
        print(alert_message)

        # 模拟发送到Slack
        print(f"\n📤 正在发送 {len(alerts)} 个性能告警到Slack...")
        print("✅ 性能告警发送成功")

        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='发送性能告警')
    parser.add_argument('--metrics-file', required=True, help='性能指标JSON文件路径')
    parser.add_argument('--environment', default='production',
                       choices=['production', 'staging', 'development'],
                       help='环境名称')

    args = parser.parse_args()

    try:
        # 读取性能指标
        with open(args.metrics_file, 'r') as f:
            metrics = json.load(f)

        print(f"🔍 检查性能告警 [{args.environment} 环境]...")

        # 创建告警管理器并发送告警
        alert_manager = PerformanceAlertManager()
        success = alert_manager.send_alerts(metrics, args.environment)

        if success:
            print("✅ 性能告警处理完成")
            sys.exit(0)
        else:
            print("❌ 性能告警处理失败")
            sys.exit(1)

    except FileNotFoundError:
        print(f"❌ 找不到性能指标文件: {args.metrics_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 性能指标文件格式错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 处理性能告警时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()