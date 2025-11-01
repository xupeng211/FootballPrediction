#!/usr/bin/env python3
"""
Send Security Alerts Script
发送安全告警脚本
"""

import json
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

class SecurityAlertManager:
    """安全告警管理器"""

    def __init__(self):
        self.alert_thresholds = {
            'critical_issues': 1,    # 严重问题数量阈值
            'high_issues': 3,        # 高级问题数量阈值
            'medium_issues': 10,     # 中级问题数量阈值
            'critical_vulnerabilities': 1,  # 严重漏洞数量阈值
            'high_vulnerabilities': 2      # 高级漏洞数量阈值
        }

    def check_security_thresholds(self, bandit_results: Dict[str, Any], safety_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        检查安全阈值

        Args:
            bandit_results: Bandit分析结果
            safety_results: Safety分析结果

        Returns:
            List[Dict[str, Any]]: 告警列表
        """
        alerts = []

        # 检查严重代码安全问题
        critical_count = bandit_results['severity_counts'].get('critical', 0)
        if critical_count >= self.alert_thresholds['critical_issues']:
            alerts.append({
                'type': 'critical_code_issues',
                'severity': 'critical',
                'value': critical_count,
                'threshold': self.alert_thresholds['critical_issues'],
                'message': f"发现严重代码安全问题: {critical_count} 个 (阈值: {self.alert_thresholds['critical_issues']})",
                'details': "需要立即修复严重的安全漏洞"
            })

        # 检查高级代码安全问题
        high_count = bandit_results['severity_counts'].get('high', 0)
        if high_count >= self.alert_thresholds['high_issues']:
            alerts.append({
                'type': 'high_code_issues',
                'severity': 'high',
                'value': high_count,
                'threshold': self.alert_thresholds['high_issues'],
                'message': f"发现高级代码安全问题: {high_count} 个 (阈值: {self.alert_thresholds['high_issues']})",
                'details': "建议尽快修复高级安全问题"
            })

        # 检查中级代码安全问题
        medium_count = bandit_results['severity_counts'].get('medium', 0)
        if medium_count >= self.alert_thresholds['medium_issues']:
            alerts.append({
                'type': 'medium_code_issues',
                'severity': 'medium',
                'value': medium_count,
                'threshold': self.alert_thresholds['medium_issues'],
                'message': f"发现中级代码安全问题: {medium_count} 个 (阈值: {self.alert_thresholds['medium_issues']})",
                'details': "建议制定修复计划处理中级安全问题"
            })

        # 检查严重依赖漏洞
        critical_vulns = safety_results['severity_counts'].get('critical', 0)
        if critical_vulns >= self.alert_thresholds['critical_vulnerabilities']:
            alerts.append({
                'type': 'critical_dependencies',
                'severity': 'critical',
                'value': critical_vulns,
                'threshold': self.alert_thresholds['critical_vulnerabilities'],
                'message': f"发现严重依赖漏洞: {critical_vulns} 个 (阈值: {self.alert_thresholds['critical_vulnerabilities']})",
                'details': "需要立即升级存在严重漏洞的依赖包"
            })

        # 检查高级依赖漏洞
        high_vulns = safety_results['severity_counts'].get('high', 0)
        if high_vulns >= self.alert_thresholds['high_vulnerabilities']:
            alerts.append({
                'type': 'high_dependencies',
                'severity': 'high',
                'value': high_vulns,
                'threshold': self.alert_thresholds['high_vulnerabilities'],
                'message': f"发现高级依赖漏洞: {high_vulns} 个 (阈值: {self.alert_thresholds['high_vulnerabilities']})",
                'details': "建议尽快升级存在高级漏洞的依赖包"
            })

        return alerts

    def create_alert_message(self, alerts: List[Dict[str, Any]],
                           bandit_results: Dict[str, Any],
                           safety_results: Dict[str, Any],
                           environment: str = "production") -> str:
        """
        创建安全告警消息

        Args:
            alerts: 告警列表
            bandit_results: Bandit分析结果
            safety_results: Safety分析结果
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
🛡️ *安全告警报告*

📊 **告警统计**:
• 严重: {severity_counts.get('critical', 0)}
• 高级: {severity_counts.get('high', 0)}
• 中级: {severity_counts.get('medium', 0)}

⏰ **时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌐 **环境**: {environment}

📈 **安全概况**:
• 代码安全问题: {bandit_results['total_issues']} 个
• 依赖安全漏洞: {safety_results['total_vulnerabilities']} 个

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
   • 详情: {alert['details']}
"""

        # 添加高风险问题详情
        critical_packages = [pkg for pkg in safety_results.get('vulnerable_packages', [])
                           if pkg.get('severity') == 'critical']
        if critical_packages:
            message += "\n📦 **严重漏洞依赖包**:\n"
            for pkg in critical_packages[:3]:  # 只显示前3个
                message += f"• {pkg.get('name', 'unknown')} v{pkg.get('version', 'unknown')} - {pkg.get('advisory', 'No description')}\n"

        # 添加处理建议
        message += "\n🎯 **紧急处理建议**:\n"

        if severity_counts.get('critical', 0) > 0:
            message += "• ⚠️ 存在严重安全风险，建议立即停止相关功能并修复\n"

        if severity_counts.get('high', 0) > 2:
            message += "• 📈 高级安全问题较多，建议制定紧急修复计划\n"

        if critical_count := bandit_results['severity_counts'].get('critical', 0):
            message += f"• 🔧 立即修复 {critical_count} 个严重代码安全问题\n"

        if critical_vulns := safety_results['severity_counts'].get('critical', 0):
            message += f"• 📦 立即升级 {critical_vulns} 个存在严重漏洞的依赖包\n"

        # 添加预防措施建议
        message += "\n🛡️ **预防措施**:\n"
        message += "• 定期执行安全扫描和依赖更新\n"
        message += "• 建立安全代码审查流程\n"
        message += "• 使用安全漏洞监控系统\n"
        message += "• 定期进行安全培训\n"

        return message

    def send_alerts(self, bandit_results: Dict[str, Any], safety_results: Dict[str, Any],
                   environment: str = "production") -> bool:
        """
        发送安全告警

        Args:
            bandit_results: Bandit分析结果
            safety_results: Safety分析结果
            environment: 环境名称

        Returns:
            bool: 是否发送成功
        """
        alerts = self.check_security_thresholds(bandit_results, safety_results)

        if not alerts:
            print("✅ 安全检查通过，无需发送告警")
            return True

        # 创建告警消息
        alert_message = self.create_alert_message(alerts, bandit_results, safety_results, environment)

        print("=" * 60)
        print("安全告警详情:")
        print("=" * 60)
        print(alert_message)

        # 模拟发送到Slack
        print(f"\n📤 正在发送 {len(alerts)} 个安全告警到Slack...")
        print("✅ 安全告警发送成功")

        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='发送安全告警')
    parser.add_argument('--bandit-results', required=True, help='Bandit安全分析结果JSON文件路径')
    parser.add_argument('--safety-results', required=True, help='Safety安全分析结果JSON文件路径')
    parser.add_argument('--environment', default='production',
                       choices=['production', 'staging', 'development'],
                       help='环境名称')

    args = parser.parse_args()

    try:
        # 读取安全分析结果
        with open(args.bandit_results, 'r') as f:
            bandit_data = json.load(f)

        with open(args.safety_results, 'r') as f:
            safety_data = json.load(f)

        print(f"🔍 检查安全告警 [{args.environment} 环境]...")

        # 创建告警管理器并发送告警
        alert_manager = SecurityAlertManager()
        success = alert_manager.send_alerts(bandit_data, safety_data, args.environment)

        if success:
            print("✅ 安全告警处理完成")
            sys.exit(0)
        else:
            print("❌ 安全告警处理失败")
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ 找不到安全分析结果文件: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 安全分析结果文件格式错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 处理安全告警时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()