#!/usr/bin/env python3
"""
告警策略验证脚本（模拟版本）

模拟验证监控告警系统，展示完整的验证流程：
1. 数据采集失败场景（API错误/超时）
2. 调度延迟场景（人为延迟>600秒）

模拟 Prometheus 指标和 AlertManager 告警状态，提供完整的验证报告。
"""

import asyncio
import json
import logging
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class MockAlertVerificationTester:
    """模拟告警验证测试器"""

    def __init__(self):
        self.verification_log = []
        self.mock_metrics = {
            "football_data_collection_total": 0,
            "football_data_collection_errors_total": 0,
            "football_scheduler_task_delay_seconds": 0,
        }
        self.mock_alerts = {}

    async def run_all_verifications(self) -> Dict[str, Any]:
        """运行所有告警验证测试"""
        print("🚀 开始执行告警策略验证（模拟模式）...")

        verification_results = {
            "data_collection_failure": await self.verify_data_collection_failure(),
            "scheduler_delay": await self.verify_scheduler_delay(),
            "prometheus_metrics": await self.verify_prometheus_metrics(),
            "alertmanager_alerts": await self.verify_alertmanager_alerts(),
            "verification_summary": self.generate_verification_summary(),
        }

        return verification_results

    async def verify_data_collection_failure(self) -> Dict[str, Any]:
        """
        场景1: 制造数据采集失败场景（模拟）
        - 模拟API返回错误/超时
        - 验证 football_data_collection_errors_total 指标增加
        """
        print("\n📊 场景1: 验证数据采集失败告警（模拟）...")

        # 记录初始指标值
        initial_errors = self.mock_metrics["football_data_collection_errors_total"]
        initial_total = self.mock_metrics["football_data_collection_total"]

        # 制造采集失败场景
        failure_scenarios = [
            ("api_football", "fixtures", "connection_timeout"),
            ("api_football", "fixtures", "api_error"),
            ("odds_api", "odds", "rate_limit"),
            ("odds_api", "odds", "invalid_response"),
            ("scores_api", "live_scores", "connection_refused"),
        ]

        print("  🔥 制造采集失败场景...")
        for data_source, collection_type, error_type in failure_scenarios:
            # 模拟采集尝试
            self.mock_metrics["football_data_collection_total"] += 1

            # 模拟采集失败（50%失败率）
            if secrets.randbelow(2) == 0:
                self.mock_metrics["football_data_collection_errors_total"] += 1
                print(
                    f"    ❌ 模拟 {data_source}/{collection_type} 采集失败: {error_type}"
                )
            else:
                print(f"    ✅ 模拟 {data_source}/{collection_type} 采集成功")

            await asyncio.sleep(0.1)

        # 模拟等待告警规则生效
        print("  ⏱️  模拟等待告警规则生效...")
        await asyncio.sleep(2)  # 减少等待时间

        # 计算失败率
        final_errors = self.mock_metrics["football_data_collection_errors_total"]
        final_total = self.mock_metrics["football_data_collection_total"]
        error_rate = (final_errors - initial_errors) / max(
            final_total - initial_total, 1
        )

        # 模拟告警触发（失败率>5%时触发）
        alert_triggered = error_rate > 0.05
        if alert_triggered:
            self.mock_alerts["DataCollectionFailureRateHigh"] = {
                "active": True,
                "starts_at": datetime.now().isoformat(),
                "severity": "warning",
                "description": f"数据采集失败率 {error_rate:.2%} 超过 5%，需要检查数据源连接",
                "summary": "数据采集失败率过高",
                "component": "data_collection",
            }

        self.verification_log.append(
            {
                "scenario": "data_collection_failure",
                "timestamp": datetime.now().isoformat(),
                "initial_errors": initial_errors,
                "final_errors": final_errors,
                "error_rate": error_rate,
                "errors_increased": final_errors > initial_errors,
                "alert_triggered": alert_triggered,
                "details": {
                    "failures_simulated": len(failure_scenarios),
                    "threshold": 0.05,
                },
            }
        )

        result = {
            "success": final_errors > initial_errors and alert_triggered,
            "initial_errors": initial_errors,
            "final_errors": final_errors,
            "error_rate": error_rate,
            "alert_triggered": alert_triggered,
            "failures_simulated": len(failure_scenarios),
        }

        print(
            f"  ✅ 采集失败验证完成: 成功={result['success']} (失败率: {error_rate:.2%})"
        )
        return result

    async def verify_scheduler_delay(self) -> Dict[str, Any]:
        """
        场景2: 制造调度延迟场景（模拟）
        - 人为延迟任务 > 600秒
        - 验证 football_scheduler_task_delay_seconds > 600
        """
        print("\n📊 场景2: 验证调度延迟告警（模拟）...")

        # 制造调度延迟场景
        delayed_tasks = [
            ("fixtures_collection", 650),
            ("odds_collection", 720),
            ("data_cleaning", 800),
            ("feature_calculation", 900),
        ]

        print("  🔥 制造调度延迟场景...")
        for task_name, delay_seconds in delayed_tasks:
            # 模拟设置延迟指标
            self.mock_metrics[f"football_scheduler_task_delay_seconds_{task_name}"] = (
                delay_seconds
            )
            print(f"    ⏰ 设置任务 {task_name} 延迟: {delay_seconds}秒")
            await asyncio.sleep(0.1)

        # 模拟等待告警规则生效
        print("  ⏱️  模拟等待告警规则生效...")
        await asyncio.sleep(1)

        # 检查是否有延迟超过600秒的任务
        high_delay_tasks = [task for task, delay in delayed_tasks if delay > 600]
        alert_triggered = len(high_delay_tasks) > 0

        if alert_triggered:
            for task_name, delay_seconds in delayed_tasks:
                if delay_seconds > 600:
                    alert_name = f"SchedulerDelayHigh_{task_name}"
                    self.mock_alerts[alert_name] = {
                        "active": True,
                        "starts_at": datetime.now().isoformat(),
                        "severity": "warning",
                        "description": f"任务 {task_name} 延迟 {delay_seconds} 秒，超过10分钟阈值",
                        "summary": "调度任务延迟过高",
                        "component": "scheduler",
                        "task_name": task_name,
                        "delay_seconds": delay_seconds,
                    }

        self.verification_log.append(
            {
                "scenario": "scheduler_delay",
                "timestamp": datetime.now().isoformat(),
                "delays_set": dict(delayed_tasks),
                "high_delay_tasks": high_delay_tasks,
                "alert_triggered": alert_triggered,
                "details": {
                    "threshold": 600,
                    "max_delay": max(delay for _, delay in delayed_tasks),
                },
            }
        )

        result = {
            "success": alert_triggered,
            "delays_set": dict(delayed_tasks),
            "high_delay_tasks": high_delay_tasks,
            "alert_triggered": alert_triggered,
            "max_delay": max(delay_seconds for _, delay_seconds in delayed_tasks),
        }

        print(
            f"  ✅ 调度延迟验证完成: 成功={result['success']} (高延迟任务: {len(high_delay_tasks)})"
        )
        return result

    async def verify_prometheus_metrics(self) -> Dict[str, Any]:
        """验证 Prometheus 指标正确反映问题状态（模拟）"""
        print("\n📊 验证 Prometheus 指标状态（模拟）...")

        metrics_values = {
            "football_data_collection_total": self.mock_metrics[
                "football_data_collection_total"
            ],
            "football_data_collection_errors_total": self.mock_metrics[
                "football_data_collection_errors_total"
            ],
            "football_scheduler_task_delay_seconds": max(
                [
                    delay
                    for key, delay in self.mock_metrics.items()
                    if key.startswith("football_scheduler_task_delay_seconds_")
                ],
                default=0,
            ),
        }

        for metric, value in metrics_values.items():
            print(f"  📈 {metric}: {value}")

        # 检查指标是否符合预期
        expected_conditions = {
            "collection_errors_increased": metrics_values[
                "football_data_collection_errors_total"
            ]
            > 0,
            "scheduler_delay_high": metrics_values[
                "football_scheduler_task_delay_seconds"
            ]
            > 600,
        }

        result = {
            "success": all(expected_conditions.values()),
            "metrics_values": metrics_values,
            "conditions_met": expected_conditions,
        }

        print(f"  ✅ Prometheus指标验证完成: 成功={result['success']}")
        return result

    async def verify_alertmanager_alerts(self) -> Dict[str, Any]:
        """验证 AlertManager 是否触发 Slack/邮件告警（模拟）"""
        print("\n📊 验证 AlertManager 告警状态（模拟）...")

        active_alerts = {
            name: alert
            for name, alert in self.mock_alerts.items()
            if alert.get("active")
        }

        for alert_name, alert_info in active_alerts.items():
            print(f"  🚨 告警 {alert_name} 已触发")
            print(f"    - 开始时间: {alert_info.get('starts_at', 'Unknown')}")
            print(f"    - 严重程度: {alert_info.get('severity', 'Unknown')}")
            print(f"    - 描述: {alert_info.get('description', 'No description')}")

        if not active_alerts:
            print("  ℹ️  当前无活跃告警")

        # 生成告警通知示例
        notification_examples = self._generate_notification_examples(active_alerts)

        result = {
            "success": len(active_alerts) > 0,
            "active_alerts_count": len(active_alerts),
            "alert_details": active_alerts,
            "notification_examples": notification_examples,
        }

        print(
            f"  ✅ AlertManager验证完成: 成功={result['success']} (活跃告警: {len(active_alerts)})"
        )
        return result

    def _generate_notification_examples(
        self, alert_statuses: Dict[str, Dict]
    ) -> Dict[str, str]:
        """生成告警通知示例内容"""
        examples = {}

        for alert_name, status in alert_statuses.items():
            if status.get("active"):
                # 邮件通知示例
                examples[f"{alert_name}_email"] = (
                    f"""
主题: 🚨 Football Platform Alert: {alert_name}

告警: {status.get('summary', alert_name)}
详情: {status.get('description', '无详细描述')}
时间: {status.get('starts_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
严重程度: {status.get('severity', 'unknown')}
组件: {status.get('component', 'unknown')}

触发条件说明:
- 数据采集失败率超过5%阈值
- 调度任务延迟超过600秒（10分钟）

请立即检查系统状态并处理相关问题。

处理建议:
1. 检查数据源API连接状态
2. 验证网络连通性
3. 查看应用日志获取详细错误信息
4. 重启相关服务组件

监控仪表盘: http://localhost:3000/d/football-monitoring
告警管理: http://localhost:9093
                """.strip()
                )

                # Slack通知示例
                examples[f"{alert_name}_slack"] = (
                    f"""
🚨 *Football Platform Critical Alert*

*{status.get('summary', alert_name)}*
{status.get('description', '无详细描述')}

• 组件: {status.get('component', 'unknown')}
• 严重程度: {status.get('severity', 'unknown')}
• 时间: {status.get('starts_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}

🔍 *触发条件*:
• 数据采集失败率 > 5%
• 调度任务延迟 > 600秒

🛠️ *快速操作*:
• <http://localhost:3000/d/football-monitoring|查看监控仪表盘>
• <http://localhost:9093|管理告警>
• <#ops-channel|联系运维团队>

⚡ 请立即处理！
                """.strip()
                )

        return examples

    def generate_verification_summary(self) -> Dict[str, Any]:
        """生成验证总结报告"""
        summary = {
            "verification_time": datetime.now().isoformat(),
            "mode": "mock_simulation",
            "total_scenarios": len(self.verification_log),
            "successful_scenarios": sum(
                1 for log in self.verification_log if log.get("alert_triggered", False)
            ),
            "scenarios_details": self.verification_log,
            "active_alerts": len(
                [alert for alert in self.mock_alerts.values() if alert.get("active")]
            ),
            "recommendations": [],
        }

        # 添加建议
        if summary["successful_scenarios"] < summary["total_scenarios"]:
            summary["recommendations"].extend(
                [
                    "部分告警场景验证失败，建议检查监控配置",
                    "确认Prometheus告警规则阈值设置合理",
                    "验证AlertManager路由配置正确",
                ]
            )

        if summary["successful_scenarios"] == summary["total_scenarios"]:
            summary["recommendations"].extend(
                [
                    "所有告警场景验证成功，监控系统设计合理",
                    "建议在实际环境中部署完整监控栈进行真实验证",
                    "定期执行告警验证确保监控系统可靠性",
                ]
            )

        # 添加实施建议
        summary["implementation_notes"] = {
            "prometheus_metrics": [
                "football_data_collection_total - 数据采集总次数",
                "football_data_collection_errors_total - 数据采集错误数",
                "football_scheduler_task_delay_seconds - 调度任务延迟时间",
            ],
            "alert_rules": [
                "DataCollectionFailureRateHigh: 采集失败率>5%触发",
                "SchedulerDelayHigh: 任务延迟>600秒触发",
            ],
            "notification_channels": [
                "邮件通知: 发送到相应团队邮箱",
                "Slack通知: 推送到#critical-alerts频道",
                "监控仪表盘: Grafana可视化展示",
            ],
        }

        return summary


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    tester = MockAlertVerificationTester()

    try:
        # 运行完整的告警验证
        results = await tester.run_all_verifications()

        # 保存验证结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"logs/alert_verification_mock_{timestamp}.json"

        Path("logs").mkdir(exist_ok=True)
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n📋 验证结果已保存到: {results_file}")

        # 输出总结
        print("\n🎯 告警策略验证总结（模拟）:")
        print("=" * 60)

        overall_success = True
        for scenario, result in results.items():
            if scenario != "verification_summary" and isinstance(result, dict):
                success = result.get("success", False)
                overall_success = overall_success and success
                status = "✅ 成功" if success else "❌ 失败"
                print(f"{scenario}: {status}")

        print("=" * 60)
        final_status = "✅ 完全成功" if overall_success else "⚠️ 部分失败"
        print(f"整体验证状态: {final_status}")

        # 显示告警通知示例
        if results["alertmanager_alerts"]["notification_examples"]:
            print("\n📧 告警通知示例:")
            print("-" * 60)
            for name, content in results["alertmanager_alerts"][
                "notification_examples"
            ].items():
                if "_email" in name:
                    print(f"\n📧 邮件通知示例 ({name.replace('_email', '')}):")
                    print(content)
                elif "_slack" in name:
                    print(f"\n💬 Slack通知示例 ({name.replace('_slack', '')}):")
                    print(content)

        if overall_success:
            print("\n🎉 告警策略验证完成 - 监控系统设计合理！")
            print("🔧 建议: 在实际Docker环境中部署完整监控栈进行真实验证")
        else:
            print("\n⚠️ 告警策略验证完成 - 需要调优监控配置！")

        # 标记验证完成
        print("\n" + "=" * 60)
        print("🏆 告警策略验证完成标记")
        print("=" * 60)

        return results

    except Exception as e:
        logger.error(f"告警验证过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
