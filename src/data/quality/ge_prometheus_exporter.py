import os
"""
Great Expectations Prometheus 指标导出器

将GE数据质量断言结果转换为Prometheus指标，
支持数据质量监控和Grafana可视化。

导出指标：
- football_data_quality_check_success_rate: 数据质量检查通过率
- football_data_quality_expectations_total: 总断言数量
- football_data_quality_expectations_failed: 失败断言数量
- football_data_quality_anomaly_records: 异常记录数
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from prometheus_client import Gauge, Histogram, Info
from prometheus_client.core import CollectorRegistry

from .great_expectations_config import GreatExpectationsConfig


class GEPrometheusExporter:
    """
    Great Expectations Prometheus 指标导出器

    负责收集GE验证结果并转换为Prometheus指标格式，
    支持实时数据质量监控和告警。
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化指标导出器

        Args:
            registry: Prometheus注册器，默认使用全局注册器
        """
        self.registry = registry
        self.logger = logging.getLogger(f"quality.{self.__class__.__name__}")
        self.ge_config = GreatExpectationsConfig()

        # 定义Prometheus指标
        self._define_metrics()

    def _define_metrics(self):
        """定义Prometheus指标"""
        # 数据质量检查通过率 (百分比)
        self.data_quality_success_rate = Gauge(
            "football_data_quality_check_success_rate",
            "Data quality check success rate percentage",
            ["table_name", "suite_name"],
            registry=self.registry,
        )

        # 总断言数量
        self.expectations_total = Gauge(
            "football_data_quality_expectations_total",
            "Total number of data quality expectations",
            ["table_name", "suite_name"],
            registry=self.registry,
        )

        # 失败断言数量
        self.expectations_failed = Gauge(
            "football_data_quality_expectations_failed",
            "Number of failed data quality expectations",
            ["table_name", "suite_name", "expectation_type"],
            registry=self.registry,
        )

        # 异常记录数量
        self.anomaly_records = Gauge(
            "football_data_quality_anomaly_records",
            "Number of anomalous records detected",
            ["table_name", "anomaly_type", "severity"],
            registry=self.registry,
        )

        # 数据质量检查执行时间
        self.quality_check_duration = Histogram(
            "football_data_quality_check_duration_seconds",
            "Time spent on data quality checks",
            ["table_name"],
            registry=self.registry,
        )

        # 数据新鲜度 (小时)
        self.data_freshness_hours = Gauge(
            "football_data_freshness_hours",
            "Hours since last data update",
            ["table_name", "data_type"],
            registry=self.registry,
        )

        # 数据质量评分
        self.quality_score = Gauge(
            "football_data_quality_score",
            "Overall data quality score (0-100)",
            ["table_name"],
            registry=self.registry,
        )

        # GE验证结果信息
        self.validation_info = Info(
            "football_data_quality_validation_info",
            "Information about the latest data quality validation",
            registry=self.registry,
        )

    async def export_ge_validation_results(
        self, validation_results: Dict[str, Any]
    ) -> None:
        """
        导出GE验证结果到Prometheus指标

        Args:
            validation_results: GE验证结果字典
        """
        try:
            start_time = datetime.now()

            # 处理单表验证结果
            if "table_results" in validation_results:
                # 批量验证结果
                for table_result in validation_results["table_results"]:
                    await self._export_table_validation_result(table_result)

                # 导出总体统计
                overall_stats = validation_results.get("overall_statistics", {})
                self._export_overall_statistics(overall_stats)

            else:
                # 单表验证结果
                await self._export_table_validation_result(validation_results)

            # 记录导出执行时间
            duration = (datetime.now() - start_time).total_seconds()
            self.logger.info(f"GE验证结果导出完成，耗时 {duration:.2f} 秒")

        except Exception as e:
            self.logger.error(f"导出GE验证结果失败: {str(e)}")
            # 设置错误指标
            self._set_error_metrics(str(e))

    async def _export_table_validation_result(
        self, table_result: Dict[str, Any]
    ) -> None:
        """导出单表验证结果"""
        table_name = table_result.get("table_name", "unknown")
        suite_name = table_result.get("suite_name", "unknown")

        # 基础指标
        success_rate = table_result.get("success_rate", 0)
        total_expectations = table_result.get("total_expectations", 0)

        # 设置Prometheus指标
        self.data_quality_success_rate.labels(
            table_name=table_name, suite_name=suite_name
        ).set(success_rate)

        self.expectations_total.labels(
            table_name=table_name, suite_name=suite_name
        ).set(total_expectations)

        # 处理失败的断言
        failed_expectations = table_result.get("failed_expectations", [])
        for failed_exp in failed_expectations:
            expectation_type = failed_exp.get("expectation_type", "unknown")
            self.expectations_failed.labels(
                table_name=table_name,
                suite_name=suite_name,
                expectation_type=expectation_type,
            ).inc()

        # 设置数据质量评分
        quality_score = min(success_rate, 100)  # 确保不超过100
        self.quality_score.labels(table_name=table_name).set(quality_score)

        # 更新验证信息
        validation_info = {
            "table_name": table_name,
            "last_validation_time": table_result.get("validation_time", "unknown"),
            "status": table_result.get("status", "unknown"),
            "rows_checked": str(table_result.get("rows_checked", 0)),
            "ge_validation_id": table_result.get("ge_validation_result_id", "unknown"),
        }
        self.validation_info.info(validation_info)

        self.logger.debug(
            f"已导出表 {table_name} 的验证结果: 成功率 {success_rate:.1f}%"
        )

    def _export_overall_statistics(self, overall_stats: Dict[str, Any]) -> None:
        """导出总体统计信息"""
        try:
            total_tables = overall_stats.get("total_tables", 0)
            passed_tables = overall_stats.get("passed_tables", 0)
            failed_tables = overall_stats.get("failed_tables", 0)
            error_tables = overall_stats.get("error_tables", 0)
            overall_success_rate = overall_stats.get("overall_success_rate", 0)

            # 设置总体质量评分
            self.quality_score.labels(table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_204")).set(overall_success_rate)

            # 记录总体统计
            self.logger.info(
                f"总体数据质量统计 - 总表数: {total_tables}, "
                f"通过: {passed_tables}, 失败: {failed_tables}, "
                f"错误: {error_tables}, 总体成功率: {overall_success_rate:.1f}%"
            )

        except Exception as e:
            self.logger.error(f"导出总体统计失败: {str(e)}")

    async def export_data_freshness_metrics(
        self, freshness_data: Dict[str, Any]
    ) -> None:
        """
        导出数据新鲜度指标

        Args:
            freshness_data: 数据新鲜度检查结果
        """
        try:
            details = freshness_data.get("details", {})

            # 导出赛程数据新鲜度
            if "fixtures" in details:
                fixtures_data = details["fixtures"]
                hours_since_update = fixtures_data.get(
                    "hours_since_update", float("inf")
                )
                self.data_freshness_hours.labels(
                    table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_234"), data_type = os.getenv("GE_PROMETHEUS_EXPORTER_DATA_TYPE_234")
                ).set(hours_since_update if hours_since_update != float("inf") else 999)

            # 导出赔率数据新鲜度
            if "odds" in details:
                odds_data = details["odds"]
                hours_since_update = odds_data.get("hours_since_update", float("inf"))
                self.data_freshness_hours.labels(
                    table_name="odds", data_type="odds"
                ).set(hours_since_update if hours_since_update != float("inf") else 999)

            self.logger.debug("数据新鲜度指标导出完成")

        except Exception as e:
            self.logger.error(f"导出数据新鲜度指标失败: {str(e)}")

    async def export_anomaly_metrics(self, anomalies: List[Dict[str, Any]]) -> None:
        """
        导出异常检测指标

        Args:
            anomalies: 异常检测结果列表
        """
        try:
            # 清零之前的异常指标
            self.anomaly_records._metrics.clear()

            # 按类型和严重性统计异常
            anomaly_stats: Dict[str, Any] = {}
            for anomaly in anomalies:
                anomaly_type = anomaly.get("type", "unknown")
                severity = anomaly.get("severity", "unknown")
                table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_265")

                # 根据异常类型确定表名
                if "odds" in anomaly_type.lower():
                    table_name = "odds"
                elif "score" in anomaly_type.lower() or "match" in anomaly_type.lower():
                    table_name = os.getenv("GE_PROMETHEUS_EXPORTER_TABLE_NAME_270")

                key = (table_name, anomaly_type, severity)
                anomaly_stats[key] = anomaly_stats.get(key, 0) + 1

            # 设置异常指标
            for (table_name, anomaly_type, severity), count in anomaly_stats.items():
                self.anomaly_records.labels(
                    table_name=table_name, anomaly_type=anomaly_type, severity=severity
                ).set(count)

            self.logger.debug(f"异常检测指标导出完成，共 {len(anomalies)} 个异常")

        except Exception as e:
            self.logger.error(f"导出异常检测指标失败: {str(e)}")

    def _set_error_metrics(self, error_message: str) -> None:
        """设置错误状态指标"""
        # 设置错误状态的质量评分为0
        self.quality_score.labels(table_name="error").set(0)

        # 更新错误信息
        error_info = {
            "status": "error",
            "error_message": error_message,
            "error_time": datetime.now().isoformat(),
        }
        self.validation_info.info(error_info)

    async def run_full_quality_check_and_export(self) -> Dict[str, Any]:
        """
        运行完整的数据质量检查并导出指标

        Returns:
            Dict: 检查和导出结果汇总
        """
        try:
            start_time = datetime.now()

            # 1. 运行GE验证
            self.logger.info("开始运行数据质量检查...")
            validation_results = await self.ge_config.validate_all_tables()

            # 2. 导出GE验证结果
            await self.export_ge_validation_results(validation_results)

            # 3. 运行数据新鲜度检查（使用现有的DataQualityMonitor）
            from .data_quality_monitor import DataQualityMonitor

            monitor = DataQualityMonitor()

            freshness_results = await monitor.check_data_freshness()
            await self.export_data_freshness_metrics(freshness_results)

            # 4. 运行异常检测
            anomalies = await monitor.detect_anomalies()
            await self.export_anomaly_metrics(anomalies)

            # 5. 记录总执行时间
            total_duration = (datetime.now() - start_time).total_seconds()

            result_summary = {
                "execution_time": total_duration,
                "validation_results": validation_results,
                "freshness_results": freshness_results,
                "anomalies_count": len(anomalies),
                "prometheus_export_status": "success",
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(
                f"完整数据质量检查完成，耗时 {total_duration:.2f} 秒，"
                f"检测到 {len(anomalies)} 个异常"
            )

            return result_summary

        except Exception as e:
            self.logger.error(f"完整数据质量检查失败: {str(e)}")
            self._set_error_metrics(str(e))
            return {
                "execution_time": 0,
                "prometheus_export_status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_current_metrics_summary(self) -> Dict[str, Any]:
        """
        获取当前指标摘要

        Returns:
            Dict: 当前指标状态
        """
        try:
            # 收集当前指标值（示例实现）
            metrics_summary = {
                "timestamp": datetime.now().isoformat(),
                "metrics_defined": [
                    "football_data_quality_check_success_rate",
                    "football_data_quality_expectations_total",
                    "football_data_quality_expectations_failed",
                    "football_data_quality_anomaly_records",
                    "football_data_quality_check_duration_seconds",
                    "football_data_freshness_hours",
                    "football_data_quality_score",
                ],
                "registry_status": "active" if self.registry else "default",
                "exporter_status": "ready",
            }

            return metrics_summary

        except Exception as e:
            self.logger.error(f"获取指标摘要失败: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "exporter_status": "error",
                "error": str(e),
            }
