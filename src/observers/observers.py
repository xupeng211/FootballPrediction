"""
具体观察者实现
Concrete Observer Implementations

提供各种观察者的具体实现。
Provides concrete implementations for various observers.
"""

import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable

from .base import Observer, ObservableEvent, ObservableEventType

logger = logging.getLogger(__name__)

class MetricsObserver(Observer):
    """指标收集观察者

    收集和聚合系统指标数据。
    Collects and aggregates system metrics.
    """

    def __init__(self, aggregation_window: int = 60):
        """初始化指标观察者

        Args:
            aggregation_window: 聚合窗口大小（秒）
        """
        super().__init__("MetricsObserver")
        self._aggregation_window = aggregation_window
        self._metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._last_cleanup = time.time()

    async def update(self, event: ObservableEvent) -> None:
        """处理事件并更新指标"""
        now = time.time()

        # 定期清理过期数据
        if now - self._last_cleanup > 30:
            await self._cleanup_old_metrics()
            self._last_cleanup = now

        # 根据事件类型更新指标
        if event.event_type == ObservableEventType.METRIC_UPDATE:
            await self._handle_metric_update(event)
        elif event.event_type == ObservableEventType.PREDICTION_COMPLETED:
            await self._handle_prediction_completed(event)
        elif event.event_type == ObservableEventType.CACHE_HIT:
            self._counters["cache_hits"] += 1
        elif event.event_type == ObservableEventType.CACHE_MISS:
            self._counters["cache_misses"] += 1
        elif event.event_type == ObservableEventType.ERROR_OCCURRED:
            self._counters["errors"] += 1

    async def _handle_metric_update(self, event: ObservableEvent) -> None:
        """处理指标更新事件"""
        metric_name = event.data.get("metric_name")
        metric_value = event.data.get("metric_value")
        metric_type = event.data.get("metric_type", "gauge")

        if not metric_name or metric_value is None:
            return

        timestamp = event.timestamp.timestamp()

        if metric_type == "counter":
            self._counters[metric_name] = metric_value
        elif metric_type == "gauge":
            self._gauges[metric_name] = metric_value
            self._metrics[metric_name].append((timestamp, metric_value))
        elif metric_type == "histogram":
            self._histograms[metric_name].append(metric_value)
            # 限制历史数据大小
            if len(self._histograms[metric_name]) > 10000:
                self._histograms[metric_name] = self._histograms[metric_name][-5000:]

    async def _handle_prediction_completed(self, event: ObservableEvent) -> None:
        """处理预测完成事件"""
        self._counters["predictions_completed"] += 1

        # 记录预测延迟
        latency = event.data.get("latency_ms")
        if latency:
            self._metrics["prediction_latency"].append((time.time(), latency))

    async def _cleanup_old_metrics(self) -> None:
        """清理过期的指标数据"""
        cutoff_time = time.time() - self._aggregation_window

        for metric_name, values in self._metrics.items():
            while values and values[0][0] < cutoff_time:
                values.popleft()

    def get_observed_event_types(self) -> List[ObservableEventType]:
        """返回观察的事件类型"""
        return [
            ObservableEventType.METRIC_UPDATE,
            ObservableEventType.PREDICTION_COMPLETED,
            ObservableEventType.CACHE_HIT,
            ObservableEventType.CACHE_MISS,
            ObservableEventType.ERROR_OCCURRED,
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """获取聚合后的指标"""
        result = {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "aggregations": {},
        }

        # 计算滑动窗口聚合
        for metric_name, values in self._metrics.items():
            if not values:
                continue

            recent_values = [v for _, v in values]
            result["aggregations"][metric_name] = {
                "count": len(recent_values),
                "min": min(recent_values),
                "max": max(recent_values),
                "avg": sum(recent_values) / len(recent_values),
                "latest": recent_values[-1] if recent_values else None,
            }

        # 计算直方图统计
        for metric_name, values in self._histograms.items():
            if not values:
                continue

            sorted_values = sorted(values)
            count = len(sorted_values)
            result["aggregations"][f"{metric_name}_histogram"] = {
                "count": count,
                "sum": sum(sorted_values),
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "mean": sum(sorted_values) / count,
                "p50": sorted_values[int(count * 0.5)],
                "p95": sorted_values[int(count * 0.95)],
                "p99": sorted_values[int(count * 0.99)],
            }

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取观察者统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "metrics_count": len(self._metrics)
                + len(self._counters)
                + len(self._gauges),
                "total_data_points": sum(len(v) for v in self._metrics.values()),
            }
        )
        return stats

class LoggingObserver(Observer):
    """日志记录观察者

    将事件记录到日志系统。
    Logs events to the logging system.
    """

    def __init__(self, log_level: int = logging.INFO):
        """初始化日志观察者

        Args:
            log_level: 日志级别
        """
        super().__init__("LoggingObserver")
        self._logger = logging.getLogger(f"{__name__}.{self.name}")
        self._logger.setLevel(log_level)
        self._log_counts: Dict[str, int] = defaultdict(int)

    async def update(self, event: ObservableEvent) -> None:
        """记录事件到日志"""
        # 更新计数
        self._log_counts[event.event_type.value] += 1

        # 根据严重性选择日志级别
        log_method = self._get_log_method(event.severity)

        # 格式化日志消息
        message = self._format_log_message(event)

        # 记录日志
        log_method(message)

        # 如果是错误或严重事件，额外记录详细信息
        if event.severity in ["error", "critical"]:
            self._logger.debug(f"Event details: {event.data}")

    def _get_log_method(self, severity: str) -> Callable:
        """根据严重性获取日志方法"""
        severity_map = {
            "debug": self._logger.debug,
            "info": self._logger.info,
            "warning": self._logger.warning,
            "error": self._logger.error,
            "critical": self._logger.critical,
        }
        return severity_map.get(severity.lower(), self._logger.info)

    def _format_log_message(self, event: ObservableEvent) -> str:
        """格式化日志消息"""
        parts = [
            f"Event: {event.event_type.value}",
            f"Source: {event.source or 'Unknown'}",
            f"Time: {event.timestamp.isoformat()}",
        ]

        if event.data:
            key_data = {
                k: v
                for k, v in event.data.items()
                if k in ["message", "value", "count", "duration"]
            }
            if key_data:
                parts.append(f"Data: {key_data}")

        return " | ".join(parts)

    def get_observed_event_types(self) -> List[ObservableEventType]:
        """返回观察的事件类型"""
        # 日志观察者观察所有事件类型
        return list(ObservableEventType)

    def get_log_counts(self) -> Dict[str, int]:
        """获取日志计数统计"""
        return dict(self._log_counts)

    def get_stats(self) -> Dict[str, Any]:
        """获取观察者统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "total_logs": sum(self._log_counts.values()),
                "log_counts": dict(self._log_counts),
            }
        )
        return stats

class AlertingObserver(Observer):
    """告警通知观察者

    监控事件并触发告警。
    Monitors events and triggers alerts.
    """

    def __init__(self):
        """初始化告警观察者"""
        super().__init__("AlertingObserver")
        self._alert_rules: Dict[str, Dict[str, Any]] = {}
        self._alert_history: deque = deque(maxlen=1000)
        self._alert_cooldown: Dict[str, datetime] = {}
        self._default_cooldown = timedelta(minutes=5)

    def add_alert_rule(
        self,
        name: str,
        condition: Callable[[ObservableEvent], bool],
        severity: str = "warning",
        message_template: str = None,
        cooldown_minutes: int = 5,
    ) -> None:
        """添加告警规则

        Args:
            name: 规则名称
            condition: 触发条件函数
            severity: 告警严重性
            message_template: 消息模板
            cooldown_minutes: 冷却时间（分钟）
        """
        self._alert_rules[name] = {
            "condition": condition,
            "severity": severity,
            "message_template": message_template or f"Alert triggered: {name}",
            "cooldown": timedelta(minutes=cooldown_minutes),
            "trigger_count": 0,
            "last_triggered": None,
        }

    async def update(self, event: ObservableEvent) -> None:
        """检查事件并触发告警"""
        for rule_name, rule in self._alert_rules.items():
            await self._check_rule(rule_name, rule, event)

    async def _check_rule(
        self, rule_name: str, rule: Dict[str, Any], event: ObservableEvent
    ) -> None:
        """检查单个告警规则"""
        # 检查冷却时间
        if rule_name in self._alert_cooldown:
            if datetime.utcnow() < self._alert_cooldown[rule_name]:
                return

        # 检查触发条件
        if rule["condition"](event):
            await self._trigger_alert(rule_name, rule, event)

    async def _trigger_alert(
        self, rule_name: str, rule: Dict[str, Any], event: ObservableEvent
    ) -> None:
        """触发告警"""
        # 更新规则统计
        rule["trigger_count"] += 1
        rule["last_triggered"] = datetime.utcnow()

        # 设置冷却时间
        self._alert_cooldown[rule_name] = datetime.utcnow() + rule["cooldown"]

        # 创建告警
        alert = {
            "id": f"alert_{int(time.time())}_{rule_name}",
            "rule_name": rule_name,
            "severity": rule["severity"],
            "message": rule["message_template"].format(
                event=event,
                event_type=event.event_type.value,
                source=event.source,
                **event.data,
            ),
            "timestamp": datetime.utcnow(),
            "event": event,
        }

        # 记录告警历史
        self._alert_history.append(alert)

        # 发送告警通知
        await self._send_alert(alert)

    async def _send_alert(self, alert: Dict[str, Any]) -> None:
        """发送告警通知"""
        # 这里可以集成各种通知渠道：
        # - 邮件
        # - 短信
        # - Slack/Teams
        # - Webhook

        # 简化实现：记录到日志
        logger.warning(f"ALERT [{alert['severity'].upper()}]: {alert['message']}")

        # 如果是严重告警，记录到错误日志
        if alert["severity"] == "critical":
            logger.error(
                f"CRITICAL ALERT: {alert['message']} | "
                f"Event: {alert['event'].event_type.value} | "
                f"Source: {alert['event'].source}"
            )

    def get_observed_event_types(self) -> List[ObservableEventType]:
        """返回观察的事件类型"""
        return [
            ObservableEventType.SYSTEM_ALERT,
            ObservableEventType.PERFORMANCE_DEGRADATION,
            ObservableEventType.ERROR_OCCURRED,
            ObservableEventType.THRESHOLD_EXCEEDED,
        ]

    def get_alert_history(
        self,
        severity: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """获取告警历史"""
        history = list(self._alert_history)

        # 过滤严重性
        if severity:
            history = [a for a in history if a["severity"] == severity]

        # 过滤时间
        if since:
            history = [a for a in history if a["timestamp"] >= since]

        # 排序并限制数量
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        return history[:limit]

    def get_alert_rules(self) -> Dict[str, Dict[str, Any]]:
        """获取所有告警规则"""
        return {
            name: {
                "severity": rule["severity"],
                "trigger_count": rule["trigger_count"],
                "last_triggered": rule["last_triggered"],
                "cooldown_minutes": rule["cooldown"].total_seconds() / 60,
            }
            for name, rule in self._alert_rules.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取观察者统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "alert_rules_count": len(self._alert_rules),
                "alerts_count": len(self._alert_history),
                "active_cooldowns": len(self._alert_cooldown),
            }
        )
        return stats

class PerformanceObserver(Observer):
    """性能监控观察者

    监控系统性能指标。
    Monitors system performance metrics.
    """

    def __init__(self, window_size: int = 100):
        """初始化性能观察者

        Args:
            window_size: 滑动窗口大小
        """
        super().__init__("PerformanceObserver")
        self._window_size = window_size
        self._response_times: deque = deque(maxlen=window_size)
        self._throughput_data: deque = deque(maxlen=window_size)
        self._error_rates: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=window_size)
        )
        self._last_throughput_calc = time.time()
        self._request_count = 0

    async def update(self, event: ObservableEvent) -> None:
        """更新性能指标"""
        if event.event_type == ObservableEventType.PREDICTION_COMPLETED:
            response_time = event.data.get("response_time_ms")
            if response_time:
                self._response_times.append(response_time)
                self._request_count += 1

            # 计算吞吐量
            now = time.time()
            self._throughput_data.append(now)

            # 每秒计算一次吞吐量
            if now - self._last_throughput_calc > 1:
                await self._calculate_throughput()
                self._last_throughput_calc = now

        elif event.event_type == ObservableEventType.ERROR_OCCURRED:
            source = event.source or "unknown"
            self._error_rates[source].append(time.time())

        elif event.event_type == ObservableEventType.PERFORMANCE_DEGRADATION:
            # 记录性能下降事件
            await self._handle_performance_degradation(event)

    async def _calculate_throughput(self) -> None:
        """计算当前吞吐量"""
        now = time.time()
        recent_requests = [t for t in self._throughput_data if now - t < 1]

        if len(recent_requests) > 1:
            # 计算每秒请求数
            throughput = len(recent_requests)
            self._current_throughput = throughput

    async def _handle_performance_degradation(self, event: ObservableEvent) -> None:
        """处理性能下降事件"""
        degradation_type = event.data.get("type")
        degradation_value = event.data.get("value")

        logger.warning(
            f"Performance degradation detected: {degradation_type} = {degradation_value}"
        )

    def get_observed_event_types(self) -> List[ObservableEventType]:
        """返回观察的事件类型"""
        return [
            ObservableEventType.PREDICTION_COMPLETED,
            ObservableEventType.ERROR_OCCURRED,
            ObservableEventType.PERFORMANCE_DEGRADATION,
        ]

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        result = {}

        # 响应时间统计
        if self._response_times:
            response_times = list(self._response_times)
            result["response_time"] = {
                "avg": sum(response_times) / len(response_times),
                "min": min(response_times),
                "max": max(response_times),
                "p50": sorted(response_times)[len(response_times) // 2],
                "p95": sorted(response_times)[int(len(response_times) * 0.95)],
                "p99": sorted(response_times)[int(len(response_times) * 0.99)],
                "count": len(response_times),
            }

        # 吞吐量
        result["throughput"] = {
            "current": getattr(self, "_current_throughput", 0),
            "total_requests": self._request_count,
        }

        # 错误率
        result["error_rates"] = {}
        for source, errors in self._error_rates.items():
            if errors:
                now = time.time()
                recent_errors = [e for e in errors if now - e < 60]  # 最近1分钟
                result["error_rates"][source] = {
                    "count": len(recent_errors),
                    "rate_per_minute": len(recent_errors),
                }

        return result

    def get_stats(self) -> Dict[str, Any]:
        """获取观察者统计信息"""
        stats = super().get_stats()
        stats.update(
            {
                "response_times_count": len(self._response_times),
                "total_requests": self._request_count,
            }
        )
        return stats
