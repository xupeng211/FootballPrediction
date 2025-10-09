"""
增强的指标收集器 / Enhanced Metrics Collector

主收集器类，整合所有指标收集功能。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .metric_types import MetricPoint
from .aggregator import MetricsAggregator
from .prometheus_metrics import PrometheusMetricsManager
from .business_metrics import BusinessMetricsCollector
from .system_metrics import SystemMetricsCollector
from .alerting import AlertManager, DefaultAlertHandlers
from .decorators import track_prediction_performance, track_cache_performance

logger = logging.getLogger(__name__)


class EnhancedMetricsCollector:
    """增强的指标收集器

    整合所有指标收集功能，提供统一的接口。
    """

    def __init__(self, registry=None):
        """
        初始化指标收集器

        Args:
            registry: Prometheus注册表
        """
        # 初始化各个组件
        self.prometheus = PrometheusMetricsManager(registry)
        self.aggregator = MetricsAggregator(window_size=300)  # 5分钟窗口
        self.alert_manager = AlertManager()

        # 初始化专门的收集器
        self.business_collector = BusinessMetricsCollector(
            self.prometheus, self.aggregator
        )
        self.system_collector = SystemMetricsCollector(self.prometheus, self.aggregator)

        # 定期聚合任务
        self._aggregation_task: Optional[asyncio.Task] = None

        # 设置默认告警规则
        self._setup_default_alerts()

        # 注册默认告警处理器
        self.alert_manager.add_alert_handler(DefaultAlertHandlers.log_handler)

    def _setup_default_alerts(self):
        """设置默认告警规则"""
        # 高延迟告警
        self.alert_manager.add_alert_rule(
            name="prediction_latency_high",
            condition=lambda m: self._check_prediction_latency(m),
            severity="high",
            description="Prediction latency exceeds 5 seconds",
            cooldown=300,
        )

        # 低准确率告警
        self.alert_manager.add_alert_rule(
            name="prediction_accuracy_low",
            condition=lambda m: self._check_prediction_accuracy(m),
            severity="medium",
            description="Prediction accuracy below 60%",
            cooldown=600,
        )

        # 高错误率告警
        self.alert_manager.add_alert_rule(
            name="error_rate_high",
            condition=lambda m: self._check_error_rate(m),
            severity="high",
            description="Error rate exceeds 10%",
            cooldown=300,
        )

        # 内存使用告警
        self.alert_manager.add_alert_rule(
            name="memory_usage_high",
            condition=lambda m: self._check_memory_usage(m),
            severity="medium",
            description="Memory usage exceeds 80%",
            cooldown=600,
        )

    def _check_prediction_latency(self, metrics: Dict[str, Any]) -> bool:
        """检查预测延迟"""
        aggregates = metrics.get("aggregates", {})
        if "prediction_duration" in aggregates:
            for label_values, summary in aggregates["prediction_duration"].items():
                if summary.avg > 5.0:  # 超过5秒
                    return True
        return False

    def _check_prediction_accuracy(self, metrics: Dict[str, Any]) -> bool:
        """检查预测准确率"""
        business = metrics.get("business", {})
        accuracy = business.get("predictions", {}).get("accuracy", 1.0)
        return accuracy < 0.6  # 低于60%

    def _check_error_rate(self, metrics: Dict[str, Any]) -> bool:
        """检查错误率"""
        # 简单实现：如果有错误计数就告警
        errors = metrics.get("system", {}).get("errors", {})
        total_errors = errors.get("total", 0)
        return total_errors > 10  # 超过10个错误

    def _check_memory_usage(self, metrics: Dict[str, Any]) -> bool:
        """检查内存使用"""
        aggregates = metrics.get("aggregates", {})
        if "memory_rss" in aggregates:
            for label_values, summary in aggregates["memory_rss"].items():
                # 假设超过1GB为高内存使用
                if summary.last > 1024 * 1024 * 1024:
                    return True
        return False

    # 业务指标接口
    def record_prediction(
        self,
        model_version: str,
        predicted_result: str,
        confidence: float,
        duration: float,
        success: bool = True,
    ):
        """记录预测指标"""
        self.business_collector.record_prediction(
            model_version, predicted_result, confidence, duration, success
        )

    def record_prediction_verification(
        self, model_version: str, is_correct: bool, time_window: str = "1h"
    ):
        """记录预测验证指标"""
        self.business_collector.record_prediction_verification(
            model_version, is_correct, time_window
        )

    def record_model_load(
        self, model_name: str, model_version: str, success: bool, load_time: float
    ):
        """记录模型加载指标"""
        self.business_collector.record_model_load(
            model_name, model_version, success, load_time
        )

    def record_data_collection(
        self, source: str, data_type: str, records: int, success: bool, duration: float
    ):
        """记录数据收集指标"""
        self.business_collector.record_data_collection(
            source, data_type, records, success, duration
        )

    def record_value_bet(
        self, bookmaker: str, confidence_level: str, expected_value: float
    ):
        """记录价值投注指标"""
        self.business_collector.record_value_bet(
            bookmaker, confidence_level, expected_value
        )

    # 系统指标接口
    def update_system_metrics(self):
        """更新系统指标"""
        self.system_collector.update_system_metrics()

    def record_error(self, error_type: str, component: str, severity: str = "medium"):
        """记录错误指标"""
        self.system_collector.record_error(error_type, component, severity)

    def record_cache_operation(
        self,
        cache_type: str,
        operation: str,
        hit: Optional[bool] = None,
        size: Optional[int] = None,
        duration: Optional[float] = None,
    ):
        """记录缓存操作指标"""
        self.system_collector.record_cache_operation(
            cache_type, operation, hit, size, duration
        )

    def update_connection_metrics(self, connection_counts: Dict[str, int]):
        """更新连接数指标"""
        self.system_collector.update_connection_metrics(connection_counts)

    def record_database_metrics(
        self,
        pool_size: int,
        active_connections: int,
        idle_connections: int,
        query_duration: Optional[float] = None,
    ):
        """记录数据库指标"""
        self.system_collector.record_database_metrics(
            pool_size, active_connections, idle_connections, query_duration
        )

    # 指标查询接口
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        business_summary = self.business_collector.get_business_summary()
        system_summary = self.system_collector.get_system_summary()
        alert_summary = self.alert_manager.get_alert_summary()

        return {
            "business": business_summary,
            "system": system_summary,
            "alerts": alert_summary,
            "aggregates": self.aggregator.get_all_metrics(),
            "last_updated": datetime.now().isoformat(),
        }

    def get_prometheus_metrics(self) -> str:
        """获取Prometheus格式的指标"""
        return self.prometheus.get_metrics_text()

    def get_alerts(self) -> Dict[str, Any]:
        """获取告警信息"""
        return {
            "active": [a.to_dict() for a in self.alert_manager.get_active_alerts()],
            "summary": self.alert_manager.get_alert_summary(),
        }

    # 异步任务管理
    async def start_aggregation_task(self, interval: int = 60):
        """
        启动定期聚合任务

        Args:
            interval: 任务间隔（秒）
        """
        if self._aggregation_task:
            return

        async def aggregation_loop():
            while True:
                try:
                    # 更新系统指标
                    self.update_system_metrics()

                    # 检查告警
                    metrics = self.get_metrics_summary()
                    self.alert_manager.check_alerts(metrics)

                    # 清理过期的聚合数据
                    self.aggregator.clear_expired_metrics(max_age=3600)

                    await asyncio.sleep(interval)
                except Exception as e:
                    logger.error(f"Aggregation task error: {e}")
                    await asyncio.sleep(5)

        self._aggregation_task = asyncio.create_task(aggregation_loop())
        logger.info("Metrics aggregation task started")

    async def stop_aggregation_task(self):
        """停止聚合任务"""
        if self._aggregation_task:
            self._aggregation_task.cancel()
            try:
                await self._aggregation_task
            except asyncio.CancelledError:
                pass
            self._aggregation_task = None
            logger.info("Metrics aggregation task stopped")

    # 告警管理接口
    def add_alert_handler(self, handler):
        """添加告警处理器"""
        self.alert_manager.add_alert_handler(handler)

    def add_alert_rule(
        self,
        name: str,
        condition,
        severity: str = "medium",
        description: str = "",
        cooldown: int = 300,
    ):
        """添加告警规则"""
        self.alert_manager.add_alert_rule(
            name, condition, severity, description, cooldown
        )

    def resolve_alert(self, name: str, message: str = ""):
        """解决告警"""
        self.alert_manager.resolve_alert(name, message)


# 全局实例
_metrics_collector: Optional[EnhancedMetricsCollector] = None


def get_metrics_collector() -> EnhancedMetricsCollector:
    """
    获取全局指标收集器

    Returns:
        指标收集器实例
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = EnhancedMetricsCollector()
    return _metrics_collector


def set_metrics_collector(collector: EnhancedMetricsCollector):
    """
    设置全局指标收集器（用于测试）

    Args:
        collector: 指标收集器实例
    """
    global _metrics_collector
    _metrics_collector = collector