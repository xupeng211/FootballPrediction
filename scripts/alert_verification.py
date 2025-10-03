import os
#!/usr/bin/env python3
"""
告警策略验证脚本

用于制造特定场景来验证监控告警系统：
1. 数据采集失败场景（API错误/超时）
2. 调度延迟场景（人为延迟>600秒）

验证 Prometheus 指标正确反映问题状态，并确认 AlertManager 触发告警。
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

import aiohttp  # noqa: E402

from src.monitoring.metrics_exporter import get_metrics_exporter  # noqa: E402

logger = logging.getLogger(__name__)


class AlertVerificationTester:
    """告警验证测试器"""

    def __init__(self):
        self.metrics_exporter = get_metrics_exporter()
        self.prometheus_url = "http://localhost:9090"
        self.alertmanager_url = "http://localhost:9093"
        self.verification_log = []

    async def run_all_verifications(self) -> Dict[str, Any]:
        """运行所有告警验证测试"""
        print("🚀 开始执行告警策略验证...")

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
        场景1: 制造数据采集失败场景
        - 模拟API返回错误/超时
        - 验证 football_data_collection_errors_total 指标增加
        """
        print("\n📊 场景1: 验证数据采集失败告警...")

        # 记录初始指标值
        initial_errors = await self._get_prometheus_metric_value(
            "football_data_collection_errors_total"
        )

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
            self.metrics_exporter.data_collection_total.labels(
                data_source=data_source, collection_type=collection_type
            ).inc()

            # 模拟采集失败
            self.metrics_exporter.data_collection_errors.labels(
                data_source=data_source,
                collection_type=collection_type,
                error_type=error_type,
            ).inc()

            print(f"    ❌ 模拟 {data_source}/{collection_type} 采集失败: {error_type}")

            # 短暂等待确保指标更新
            await asyncio.sleep(0.5)

        # 等待5分钟让Prometheus采集指标并触发告警规则
        print("  ⏱️  等待5分钟让告警规则生效...")
        await asyncio.sleep(300)  # 5分钟

        # 验证指标增加
        final_errors = await self._get_prometheus_metric_value(
            "football_data_collection_errors_total"
        )

        # 验证告警状态
        failure_rate_alert = await self._check_alert_status(
            "DataCollectionFailureRateHigh"
        )

        self.verification_log.append(
            {
                "scenario": "data_collection_failure",
                "timestamp": datetime.now().isoformat(),
                "initial_errors": initial_errors,
                "final_errors": final_errors,
                "errors_increased": final_errors > initial_errors,
                "alert_triggered": failure_rate_alert["active"],
                "details": {
                    "failures_created": len(failure_scenarios),
                    "alert_info": failure_rate_alert,
                },
            }
        )

        result = {
            "success": final_errors > initial_errors and failure_rate_alert["active"],
            "initial_errors": initial_errors,
            "final_errors": final_errors,
            "alert_status": failure_rate_alert,
            "failures_simulated": len(failure_scenarios),
        }

        print(f"  ✅ 采集失败验证完成: 成功={result['success']}")
        return result

    async def verify_scheduler_delay(self) -> Dict[str, Any]:
        """
        场景2: 制造调度延迟场景
        - 人为延迟任务 > 600秒
        - 验证 football_scheduler_task_delay_seconds > 600
        """
        print("\n📊 场景2: 验证调度延迟告警...")

        # 制造调度延迟场景
        delayed_tasks = [
            ("fixtures_collection", 650),
            ("odds_collection", 720),
            ("data_cleaning", 800),
            ("feature_calculation", 900),
        ]

        print("  🔥 制造调度延迟场景...")
        for task_name, delay_seconds in delayed_tasks:
            # 设置延迟指标
            self.metrics_exporter.scheduler_task_delay.labels(task_name=task_name).set(
                delay_seconds
            )

            print(f"    ⏰ 设置任务 {task_name} 延迟: {delay_seconds}秒")

            await asyncio.sleep(0.5)

        # 等待2分钟让告警规则生效
        print("  ⏱️  等待2分钟让告警规则生效...")
        await asyncio.sleep(120)  # 2分钟

        # 验证告警状态
        delay_alert = await self._check_alert_status("SchedulerDelayHigh")

        # 获取当前延迟指标值
        current_delays = {}
        for task_name, delay_seconds in delayed_tasks:
            current_delays[task_name] = await self._get_prometheus_metric_value(
                f'football_scheduler_task_delay_seconds{{task_name = os.getenv("ALERT_VERIFICATION_TASK_NAME_172")}}'
            )

        self.verification_log.append(
            {
                "scenario": "scheduler_delay",
                "timestamp": datetime.now().isoformat(),
                "delays_set": dict(delayed_tasks),
                "current_delays": current_delays,
                "alert_triggered": delay_alert["active"],
                "details": {"alert_info": delay_alert},
            }
        )

        result = {
            "success": delay_alert["active"],
            "delays_set": dict(delayed_tasks),
            "alert_status": delay_alert,
            "max_delay": max(delay_seconds for _, delay_seconds in delayed_tasks),
        }

        print(f"  ✅ 调度延迟验证完成: 成功={result['success']}")
        return result

    async def verify_prometheus_metrics(self) -> Dict[str, Any]:
        """验证 Prometheus 指标正确反映问题状态"""
        print("\n📊 验证 Prometheus 指标状态...")

        metrics_to_check = [
            "football_data_collection_total",
            "football_data_collection_errors_total",
            "football_scheduler_task_delay_seconds",
        ]

        metrics_values = {}
        for metric in metrics_to_check:
            value = await self._get_prometheus_metric_value(metric)
            metrics_values[metric] = value
            print(f"  📈 {metric}: {value}")

        # 检查指标是否符合预期
        expected_conditions = {
            "collection_errors_increased": metrics_values[
                "football_data_collection_errors_total"
            ]
            > 0,
            "scheduler_delay_high": any(
                await self._get_prometheus_metric_value(
                    f'football_scheduler_task_delay_seconds{{task_name = os.getenv("ALERT_VERIFICATION_TASK_NAME_220")}}'
                )
                > 600
                for task in [
                    "fixtures_collection",
                    "odds_collection",
                    "data_cleaning",
                    "feature_calculation",
                ]
            ),
        }

        result = {
            "success": all(expected_conditions.values()),
            "metrics_values": metrics_values,
            "conditions_met": expected_conditions,
        }

        print(f"  ✅ Prometheus指标验证完成: 成功={result['success']}")
        return result

    async def verify_alertmanager_alerts(self) -> Dict[str, Any]:
        """验证 AlertManager 是否触发 Slack/邮件告警"""
        print("\n📊 验证 AlertManager 告警状态...")

        alerts_to_check = ["DataCollectionFailureRateHigh", "SchedulerDelayHigh"]

        alert_statuses = {}
        for alert_name in alerts_to_check:
            status = await self._check_alert_status(alert_name)
            alert_statuses[alert_name] = status

            if status["active"]:
                print(f"  🚨 告警 {alert_name} 已触发")
                print(f"    - 开始时间: {status.get('starts_at', 'Unknown')}")
                print(f"    - 严重程度: {status.get('severity', 'Unknown')}")
                print(f"    - 描述: {status.get('description', 'No description')}")
            else:
                print(f"  ℹ️  告警 {alert_name} 未触发")

        # 生成告警通知示例
        notification_examples = await self._generate_notification_examples(
            alert_statuses
        )

        result = {
            "success": any(alert["active"] for alert in alert_statuses.values()),
            "alert_statuses": alert_statuses,
            "notification_examples": notification_examples,
        }

        print(f"  ✅ AlertManager验证完成: 成功={result['success']}")
        return result

    async def _get_prometheus_metric_value(self, metric_query: str) -> float:
        """从 Prometheus 获取指标值"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.prometheus_url}/api/v1/query",
                    params={"query": metric_query},
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["status"] == "success" and data["data"]["result"]:
                            return float(data["data"]["result"][0]["value"][1])
                    return 0.0
        except Exception as e:
            logger.warning(f"获取Prometheus指标失败: {e}")
            return 0.0

    async def _check_alert_status(self, alert_name: str) -> Dict[str, Any]:
        """检查指定告警的状态"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.alertmanager_url}/api/v1/alerts"
                ) as response:
                    if response.status == 200:
                        alerts = await response.json()
                        for alert in alerts:
                            if alert.get("labels", {}).get("alertname") == alert_name:
                                return {
                                    "active": True,
                                    "starts_at": alert.get("startsAt"),
                                    "severity": alert.get("labels", {}).get("severity"),
                                    "description": alert.get("annotations", {}).get(
                                        "description"
                                    ),
                                    "summary": alert.get("annotations", {}).get(
                                        "summary"
                                    ),
                                    "component": alert.get("labels", {}).get(
                                        "component"
                                    ),
                                }
                        return {"active": False}
        except Exception as e:
            logger.warning(f"检查AlertManager告警状态失败: {e}")
            return {"active": False, "error": str(e)}

    async def _generate_notification_examples(
        self, alert_statuses: Dict[str, Dict]
    ) -> Dict[str, str]:
        """生成告警通知示例内容"""
        examples = {}

        for alert_name, status in alert_statuses.items():
            if status["active"]:
                # 邮件通知示例
                examples[f"{alert_name}_email"] = (
                    f"""
主题: 🚨 Football Platform Alert: {alert_name}

告警: {status.get('summary', alert_name)}
详情: {status.get('description', '无详细描述')}
时间: {status.get('starts_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}
严重程度: {status.get('severity', 'unknown')}
组件: {status.get('component', 'unknown')}

请立即检查系统状态并处理相关问题。
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

请立即处理！
                """.strip()
                )

        return examples

    def generate_verification_summary(self) -> Dict[str, Any]:
        """生成验证总结报告"""
        summary = {
            "verification_time": datetime.now().isoformat(),
            "total_scenarios": len(self.verification_log),
            "successful_scenarios": sum(
                1 for log in self.verification_log if log.get("success", False)
            ),
            "scenarios_details": self.verification_log,
            "recommendations": [],
        }

        # 添加建议
        if summary["successful_scenarios"] < summary["total_scenarios"]:
            summary["recommendations"].append("部分告警场景验证失败，请检查监控配置")

        if summary["successful_scenarios"] == summary["total_scenarios"]:
            summary["recommendations"].append("所有告警场景验证成功，监控系统运行正常")

        return summary


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format = os.getenv("ALERT_VERIFICATION_FORMAT_385"),
    )

    tester = AlertVerificationTester()

    try:
        # 运行完整的告警验证
        results = await tester.run_all_verifications()

        # 保存验证结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"logs/alert_verification_{timestamp}.json"

        Path("logs").mkdir(exist_ok=True)
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        print(f"\n📋 验证结果已保存到: {results_file}")

        # 输出总结
        print("\n🎯 告警策略验证总结:")
        print("=" * 50)

        overall_success = True
        for scenario, result in results.items():
            if scenario != "verification_summary" and isinstance(result, dict):
                success = result.get("success", False)
                overall_success = overall_success and success
                status = "✅ 成功" if success else "❌ 失败"
                print(f"{scenario}: {status}")

        print("=" * 50)
        final_status = os.getenv("ALERT_VERIFICATION_FINAL_STATUS_417") if overall_success else "⚠️ 部分失败"
        print(f"整体验证状态: {final_status}")

        if overall_success:
            print("\n🎉 告警策略验证完成 - 监控系统运行正常！")
        else:
            print("\n⚠️ 告警策略验证完成 - 存在问题需要修复！")

    except Exception as e:
        logger.error(f"告警验证过程中发生错误: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
