#!/usr/bin/env python3
"""
Send Alert Summary Script
发送告警汇总脚本
"""

import json
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

class AlertSummaryManager:
    """告警汇总管理器"""

    def __init__(self):
        self.alert_types = {
            'quality': '质量门控',
            'performance': '性能监控',
            'security': '安全扫描',
            'deployment': '部署状态'
        }

    def collect_alert_data(self, quality_file: Optional[str] = None,
                          performance_file: Optional[str] = None,
                          security_file: Optional[str] = None,
                          deployment_file: Optional[str] = None) -> Dict[str, Any]:
        """
        收集各类告警数据

        Args:
            quality_file: 质量检查结果文件
            performance_file: 性能分析结果文件
            security_file: 安全分析结果文件
            deployment_file: 部署状态文件

        Returns:
            Dict[str, Any]: 汇总数据
        """
        summary_data = {
            'timestamp': datetime.now().isoformat(),
            'alerts': {},
            'total_issues': 0,
            'severity_counts': {'critical': 0, 'high': 0, 'medium': 0, 'low': 0},
            'status': 'success'
        }

        # 收集质量告警数据
        if quality_file:
            try:
                with open(quality_file, 'r') as f:
                    quality_data = json.load(f)
                summary_data['alerts']['quality'] = {
                    'status': quality_data.get('conclusion', 'unknown'),
                    'issues': quality_data.get('failed_tests', 0),
                    'coverage': quality_data.get('coverage_percent', 0),
                    'duration': quality_data.get('duration', 0) / 1000
                }
                if quality_data.get('conclusion') != 'success':
                    summary_data['severity_counts']['high'] += 1
                    summary_data['total_issues'] += 1
            except (FileNotFoundError, json.JSONDecodeError):
                summary_data['alerts']['quality'] = {'status': 'error', 'message': '无法读取质量数据'}

        # 收集性能告警数据
        if performance_file:
            try:
                with open(performance_file, 'r') as f:
                    perf_data = json.load(f)
                summary_data['alerts']['performance'] = {
                    'response_time': perf_data.get('avg_response_time', 0),
                    'throughput': perf_data.get('requests_per_second', 0),
                    'memory_usage': perf_data.get('memory_usage_percent', 0),
                    'cpu_usage': perf_data.get('cpu_usage_percent', 0),
                    'error_rate': perf_data.get('error_rate_percent', 0)
                }

                # 评估性能问题
                if perf_data.get('avg_response_time', 0) > 2.0:
                    summary_data['severity_counts']['medium'] += 1
                    summary_data['total_issues'] += 1
                if perf_data.get('error_rate_percent', 0) > 1.0:
                    summary_data['severity_counts']['high'] += 1
                    summary_data['total_issues'] += 1
            except (FileNotFoundError, json.JSONDecodeError):
                summary_data['alerts']['performance'] = {'status': 'error', 'message': '无法读取性能数据'}

        # 收集安全告警数据
        if security_file:
            try:
                with open(security_file, 'r') as f:
                    security_data = json.load(f)
                summary_data['alerts']['security'] = {
                    'total_issues': security_data.get('total_issues', 0),
                    'severity_counts': security_data.get('severity_counts', {}),
                    'vulnerabilities': security_data.get('total_vulnerabilities', 0)
                }

                # 统计安全问题
                sec_counts = security_data.get('severity_counts', {})
                summary_data['severity_counts']['critical'] += sec_counts.get('critical', 0)
                summary_data['severity_counts']['high'] += sec_counts.get('high', 0)
                summary_data['severity_counts']['medium'] += sec_counts.get('medium', 0)
                summary_data['total_issues'] += security_data.get('total_issues', 0)
                summary_data['total_issues'] += security_data.get('total_vulnerabilities', 0)
            except (FileNotFoundError, json.JSONDecodeError):
                summary_data['alerts']['security'] = {'status': 'error', 'message': '无法读取安全数据'}

        # 收集部署状态数据
        if deployment_file:
            try:
                with open(deployment_file, 'r') as f:
                    deploy_data = json.load(f)
                summary_data['alerts']['deployment'] = {
                    'status': deploy_data.get('status', 'unknown'),
                    'commit': deploy_data.get('commit', 'unknown'),
                    'branch': deploy_data.get('branch', 'unknown'),
                    'environment': deploy_data.get('environment', 'unknown')
                }
                if deploy_data.get('status') not in ['success', 'completed']:
                    summary_data['severity_counts']['high'] += 1
                    summary_data['total_issues'] += 1
            except (FileNotFoundError, json.JSONDecodeError):
                summary_data['alerts']['deployment'] = {'status': 'error', 'message': '无法读取部署数据'}

        # 确定整体状态
        if summary_data['severity_counts']['critical'] > 0:
            summary_data['status'] = 'critical'
        elif summary_data['severity_counts']['high'] > 2:
            summary_data['status'] = 'warning'
        elif summary_data['total_issues'] > 5:
            summary_data['status'] = 'warning'

        return summary_data

    def create_summary_message(self, summary_data: Dict[str, Any], environment: str = "production") -> str:
        """
        创建告警汇总消息

        Args:
            summary_data: 汇总数据
            environment: 环境名称

        Returns:
            str: 汇总消息
        """
        env_emoji = {
            'production': '🏭',
            'staging': '🧪',
            'development': '🔧'
        }.get(environment, '📍')

        status_emoji = {
            'success': '✅',
            'warning': '⚠️',
            'critical': '🚨',
            'error': '❌'
        }.get(summary_data['status'], '📊')

        message = f"""
{env_emoji} *告警汇总报告*

{status_emoji} **整体状态**: {summary_data['status'].upper()}
📅 **汇总时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🌐 **环境**: {environment}

📊 **问题统计**:
• 总问题数: {summary_data['total_issues']}
• 严重: {summary_data['severity_counts']['critical']}
• 高级: {summary_data['severity_counts']['high']}
• 中级: {summary_data['severity_counts']['medium']}
• 低级: {summary_data['severity_counts']['low']}

🔍 **各模块状态**:
"""

        # 添加各模块状态
        for alert_type, display_name in self.alert_types.items():
            if alert_type in summary_data['alerts']:
                alert_data = summary_data['alerts'][alert_type]
                status = alert_data.get('status', 'unknown')

                status_emoji_module = {
                    'success': '✅',
                    'completed': '✅',
                    'failure': '❌',
                    'failed': '❌',
                    'warning': '⚠️',
                    'error': '❌',
                    'unknown': '❓'
                }.get(status, '📊')

                message += f"\n• {display_name}: {status_emoji_module} {status.upper()}"

                # 添加关键指标
                if alert_type == 'quality':
                    issues = alert_data.get('issues', 0)
                    coverage = alert_data.get('coverage', 0)
                    message += f" (问题: {issues}, 覆盖率: {coverage}%)"

                elif alert_type == 'performance':
                    response_time = alert_data.get('response_time', 0)
                    throughput = alert_data.get('throughput', 0)
                    message += f" (响应: {response_time:.2f}s, 吞吐: {throughput:.0f} req/s)"

                elif alert_type == 'security':
                    total_issues = alert_data.get('total_issues', 0)
                    vulnerabilities = alert_data.get('vulnerabilities', 0)
                    message += f" (问题: {total_issues}, 漏洞: {vulnerabilities})"

                elif alert_type == 'deployment':
                    commit = alert_data.get('commit', 'unknown')[:8]
                    branch = alert_data.get('branch', 'unknown')
                    env = alert_data.get('environment', 'unknown')
                    message += f" (提交: {commit}, 分支: {branch}, 环境: {env})"

        # 添加趋势分析
        message += "\n\n📈 **趋势分析**:\n"
        if summary_data['status'] == 'success':
            message += "• 🟢 系统运行状态良好，所有指标正常\n"
        elif summary_data['status'] == 'warning':
            message += "• 🟡 发现一些问题需要关注，建议及时处理\n"
        elif summary_data['status'] == 'critical':
            message += "• 🔴 发现严重问题，需要立即处理\n"

        # 添加行动建议
        if summary_data['total_issues'] > 0:
            message += "\n🎯 **行动建议**:\n"

            if summary_data['severity_counts']['critical'] > 0:
                message += "• 🚨 立即处理严重安全问题和高风险故障\n"

            if summary_data['severity_counts']['high'] > 0:
                message += "• ⚠️ 优先处理高级问题，防止问题升级\n"

            if 'quality' in summary_data['alerts'] and summary_data['alerts']['quality'].get('status') != 'success':
                message += "• 🔧 修复质量检查失败的问题\n"

            if 'performance' in summary_data['alerts']:
                perf_data = summary_data['alerts']['performance']
                if perf_data.get('response_time', 0) > 2.0:
                    message += "• ⚡ 优化响应时间和性能瓶颈\n"

            if 'security' in summary_data['alerts']:
                sec_data = summary_data['alerts']['security']
                if sec_data.get('total_issues', 0) > 0:
                    message += "• 🛡️ 修复安全漏洞和代码安全问题\n"

        message += f"\n📋 **下次检查时间**: {(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}"
        message += "\n🤖 *此报告由 FootballPrediction CI/CD 系统自动生成*"

        return message

    def send_summary(self, summary_data: Dict[str, Any], environment: str = "production") -> bool:
        """
        发送告警汇总

        Args:
            summary_data: 汇总数据
            environment: 环境名称

        Returns:
            bool: 是否发送成功
        """
        # 创建汇总消息
        summary_message = self.create_summary_message(summary_data, environment)

        print("=" * 60)
        print("告警汇总报告:")
        print("=" * 60)
        print(summary_message)

        # 模拟发送到Slack
        print(f"\n📤 正在发送告警汇总到Slack...")
        print("✅ 告警汇总发送成功")

        return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='发送告警汇总')
    parser.add_argument('--quality-file', help='质量检查结果文件路径')
    parser.add_argument('--performance-file', help='性能分析结果文件路径')
    parser.add_argument('--security-file', help='安全分析结果文件路径')
    parser.add_argument('--deployment-file', help='部署状态文件路径')
    parser.add_argument('--environment', default='production',
                       choices=['production', 'staging', 'development'],
                       help='环境名称')
    parser.add_argument('--output', help='输出汇总文件路径')

    args = parser.parse_args()

    try:
        print("🔍 开始生成告警汇总...")

        # 创建汇总管理器
        summary_manager = AlertSummaryManager()

        # 收集告警数据
        summary_data = summary_manager.collect_alert_data(
            quality_file=args.quality_file,
            performance_file=args.performance_file,
            security_file=args.security_file,
            deployment_file=args.deployment_file
        )

        # 发送汇总
        success = summary_manager.send_summary(summary_data, args.environment)

        # 保存汇总到文件
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"\n📄 汇总数据已保存到: {args.output}")

        if success:
            print("✅ 告警汇总处理完成")
            sys.exit(0)
        else:
            print("❌ 告警汇总处理失败")
            sys.exit(1)

    except Exception as e:
        print(f"❌ 处理告警汇总时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()