"""
具体被观察者实现
Concrete Subject Implementations

提供各种被观察者的具体实现.
Provides concrete implementations for various subjects.
"""

import asyncio
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base import ObservableEvent, ObservableEventType, Subject


class SystemMetricsSubject(Subject):
    """系统指标被观察者"

    监控系统级别的指标变化.
    Monitors system-level metric changes.
    """

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """初始化系统指标被观察者"""
        super().__init__("SystemMetrics")
        self._metrics: Dict[str, float] = {}
        self._thresholds: Dict[str, Dict[str, float]] = {}
        self._last_notification: Dict[str, float] = {}
        self._notification_interval = 60  # 秒

    def set_metric(self, name: str, value: float) -> None:
        """设置指标值"

        Args:
            name: 指标名称
            value: 指标值
        """
        old_value = self._metrics.get(name)
        self._metrics[name] = value

        # 检查阈值
        asyncio.create_task(self._check_thresholds(name, old_value, value))

    def set_threshold(
        self,
        metric_name: str,
        warning: Optional[float] = None,
        critical: Optional[float] = None,
        direction: str = "above",
    ) -> None:
        """设置指标阈值"

        Args:
            metric_name: 指标名称
            warning: 警告阈值
            critical: 严重阈值
            direction: 方向（above/below）
        """
        self._thresholds[metric_name] = {
            "warning": warning,
            "critical": critical,
            "direction": direction,
        }

    async def _check_thresholds(
        self, metric_name: str, old_value: Optional[float], new_value: float
    ) -> None:
        """检查指标是否超过阈值"""
        if metric_name not in self._thresholds:
            return None
        threshold = self._thresholds[metric_name]
        last_notified = self._last_notification.get(metric_name, 0)

        # 检查通知间隔
        if time.time() - last_notified < self._notification_interval:
            return None
        # 检查严重阈值
        if threshold["critical"] is not None:
            if self._is_threshold_exceeded(
                new_value,
                threshold["critical"],
                threshold["direction"],
            ):
                event = ObservableEvent(
                    event_type=ObservableEventType.SYSTEM_ALERT,
                    source=f"SystemMetrics:{metric_name}",
                    severity="critical",
                    data={
                        "metric_name": metric_name,
                        "metric_value": new_value,
                        "threshold": threshold["critical"],
                        "direction": threshold["direction"],
                        "old_value": old_value,
                    },
                )
                await self.notify(event)
                self._last_notification[metric_name] = time.time()
                return None
        # 检查警告阈值
        if threshold["warning"] is not None:
            if self._is_threshold_exceeded(
                new_value,
                threshold["warning"],
                threshold["direction"],
            ):
                event = ObservableEvent(
                    event_type=ObservableEventType.THRESHOLD_EXCEEDED,
                    source=f"SystemMetrics:{metric_name}",
                    severity="warning",
                    data={
                        "metric_name": metric_name,
                        "metric_value": new_value,
                        "threshold": threshold["warning"],
                        "direction": threshold["direction"],
                        "old_value": old_value,
                    },
                )
                await self.notify(event)
                self._last_notification[metric_name] = time.time()

    def _is_threshold_exceeded(
        self, value: float, threshold: float, direction: str
    ) -> bool:
        """检查是否超过阈值"""
        if direction == "above":
            return value > threshold
        else:
            return value < threshold

    async def collect_metrics(self) -> None:
        """收集系统指标"""
        # 这里可以收集实际的系统指标
        # 例如:CPU,内存,磁盘使用率等

        # 模拟数据
        import random

        metrics = {
            "cpu_usage": random.uniform(20, 90),
            "memory_usage": random.uniform(40, 85),
            "disk_usage": random.uniform(30, 70),
            "network_io": random.uniform(10, 100),
        }

        for name, value in metrics.items():
            self.set_metric(name, value)

    def get_metrics(self) -> Dict[str, float]:
        """获取所有指标"""
        return dict(self._metrics)


class PredictionMetricsSubject(Subject):
    """预测指标被观察者"

    监控预测相关的指标.
    Monitors prediction-related metrics.
    """

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """初始化预测指标被观察者"""
        super().__init__("PredictionMetrics")
        self._prediction_counts: Dict[str, int] = defaultdict(int)
        self._accuracy_metrics: Dict[str, List[float]] = defaultdict(list)
        self._response_times: List[float] = []
        self._strategy_performance: Dict[str, Dict[str, Any]] = defaultdict(dict)

    async def record_prediction(
        self,
        strategy_name: str,
        response_time_ms: float,
        success: bool = True,
        confidence: Optional[float] = None,
        actual_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录预测事件"

        Args:
            strategy_name: 策略名称
            response_time_ms: 响应时间（毫秒）
            success: 是否成功
            confidence: 预测置信度
            actual_result: 实际结果（用于计算准确率）
        """
        timestamp = datetime.utcnow()

        # 更新计数
        self._prediction_counts[strategy_name] += 1
        if success:
            self._prediction_counts[f"{strategy_name}_success"] += 1
        else:
            self._prediction_counts[f"{strategy_name}_failure"] += 1

        # 记录响应时间
        self._response_times.append(response_time_ms)
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-500:]

        # 更新策略性能
        self._update_strategy_performance(
            strategy_name, success, confidence, actual_result
        )

        # 发送事件
        event = ObservableEvent(
            event_type=ObservableEventType.PREDICTION_COMPLETED,
            source=f"PredictionMetrics:{strategy_name}",
            data={
                "strategy_name": strategy_name,
                "response_time_ms": response_time_ms,
                "success": success,
                "confidence": confidence,
                "timestamp": timestamp.isoformat(),
            },
        )
        await self.notify(event)

    def _update_strategy_performance(
        self,
        strategy_name: str,
        success: bool,
        confidence: Optional[float],
        actual_result: Optional[Dict[str, Any]],
    ) -> None:
        """更新策略性能统计"""
        perf = self._strategy_performance[strategy_name]

        # 更新成功率
        total = self._prediction_counts[strategy_name]
        success_count = self._prediction_counts[f"{strategy_name}_success"]
        perf["success_rate"] = success_count / total if total > 0 else 0

        # 更新平均置信度
        if confidence is not None:
            confidences = perf.get("confidences", [])
            confidences.append(confidence)
            if len(confidences) > 100:
                confidences = confidences[-50:]
            perf["confidences"] = confidences
            perf["avg_confidence"] = sum(confidences) / len(confidences)

        # 更新准确率（如果有实际结果）
        if actual_result is not None:
            # 这里可以根据实际结果计算准确率
            # 简化实现
            perf["accuracy"] = perf.get("accuracy", 0.8)  # 模拟值

    async def check_performance_degradation(self) -> None:
        """检查性能下降"""
        # 检查响应时间
        if self._response_times:
            recent_times = self._response_times[-100:]
            avg_time = sum(recent_times) / len(recent_times)

            # 如果平均响应时间超过阈值
            if avg_time > 1000:  # 1秒
                event = ObservableEvent(
                    event_type=ObservableEventType.PERFORMANCE_DEGRADATION,
                    source="PredictionMetrics",
                    severity="warning",
                    data={
                        "type": "response_time",
                        "value": avg_time,
                        "threshold": 1000,
                    },
                )
                await self.notify(event)

        # 检查成功率
        for strategy_name, perf in self._strategy_performance.items():
            success_rate = perf.get("success_rate", 1.0)
            if success_rate < 0.9:  # 成功率低于90%
                event = ObservableEvent(
                    event_type=ObservableEventType.PERFORMANCE_DEGRADATION,
                    source=f"PredictionMetrics:{strategy_name}",
                    severity="warning",
                    data={
                        "type": "success_rate",
                        "value": success_rate,
                        "threshold": 0.9,
                    },
                )
                await self.notify(event)

    def get_prediction_metrics(self) -> Dict[str, Any]:
        """获取预测指标"""
        result = {
            "total_predictions": sum(
                count
                for key, count in self._prediction_counts.items()
                if not key.endswith("_success") and not key.endswith("_failure")
            ),
            "prediction_counts": dict(self._prediction_counts),
            "strategy_performance": dict(self._strategy_performance),
        }

        # 响应时间统计
        if self._response_times:
            times = self._response_times[-100:]
            result["response_time"] = {
                "avg": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "p95": sorted(times)[int(len(times) * 0.95)],
            }

        return result


class AlertSubject(Subject):
    """告警被观察者"

    管理告警事件.
    Manages alert events.
    """

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """初始化告警被观察者"""
        super().__init__("AlertManager")
        self._alert_counts: Dict[str, int] = defaultdict(int)
        self._alert_levels: Dict[str, List[datetime]] = defaultdict(list)
        self._suppression_rules: Dict[str, Dict[str, Any]] = {}

    async def trigger_alert(
        self,
        alert_type: str,
        severity: str,
        message: str,
        source: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """触发告警"

        Args:
            alert_type: 告警类型
            severity: 严重性
            message: 告警消息
            source: 告警源
            data: 附加数据
        """
        # 检查抑制规则
        if await self._is_suppressed(alert_type, severity, source):
            return None
        # 更新计数
        self._alert_counts[alert_type] += 1
        self._alert_levels[severity].append(datetime.utcnow())

        # 清理旧的告警记录（保留最近100条）
        if len(self._alert_levels[severity]) > 100:
            self._alert_levels[severity] = self._alert_levels[severity][-50:]

        # 创建事件
        event = ObservableEvent(
            event_type=ObservableEventType.SYSTEM_ALERT,
            source=source or f"AlertManager:{alert_type}",
            severity=severity,
            data={
                "alert_type": alert_type,
                "message": message,
                **(data or {}),
            },
        )
        await self.notify(event)

    async def _is_suppressed(
        self, alert_type: str, severity: str, source: Optional[str]
    ) -> bool:
        """检查告警是否被抑制"""
        key = f"{alert_type}:{severity}:{source or 'default'}"

        if key not in self._suppression_rules:
            return False

        rule = self._suppression_rules[key]

        # 检查时间窗口
        if "time_window" in rule:
            window_start = datetime.utcnow() - timedelta(seconds=rule["time_window"])
            recent_alerts = [
                t for t in self._alert_levels.get(severity, []) if t > window_start
            ]
            if len(recent_alerts) >= rule.get("max_alerts", 5):
                return True

        return False

    def add_suppression_rule(
        self,
        alert_type: str,
        severity: str,
        source: Optional[str] = None,
        max_alerts: int = 5,
        time_window: int = 300,
    ) -> None:
        """添加告警抑制规则"

        Args:
            alert_type: 告警类型
            severity: 严重性
            source: 告警源
            max_alerts: 时间窗口内最大告警数
            time_window: 时间窗口（秒）
        """
        key = f"{alert_type}:{severity}:{source or 'default'}"
        self._suppression_rules[key] = {
            "max_alerts": max_alerts,
            "time_window": time_window,
        }

    def get_alert_statistics(self) -> Dict[str, Any]:
        """获取告警统计"""
        return {
            "alert_counts": dict(self._alert_counts),
            "alert_levels": {
                level: len(alerts) for level, alerts in self._alert_levels.items()
            },
            "suppression_rules": len(self._suppression_rules),
        }


class CacheSubject(Subject):
    """缓存被观察者"

    监控缓存相关事件.
    Monitors cache-related events.
    """

    def __init__(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """初始化缓存被观察者"""
        super().__init__("CacheMonitor")
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
        }
        self._cache_sizes: Dict[str, int] = {}
        self._hit_rates: Dict[str, float] = {}

    async def record_cache_hit(self, cache_name: str, key: str) -> None:
        """记录缓存命中"""
        self._cache_stats["hits"] += 1
        self._update_hit_rate(cache_name)

        event = ObservableEvent(
            event_type=ObservableEventType.CACHE_HIT,
            source=f"Cache:{cache_name}",
            data={
                "cache_name": cache_name,
                "key": key,
            },
        )
        await self.notify(event)

    async def record_cache_miss(self, cache_name: str, key: str) -> None:
        """记录缓存未命中"""
        self._cache_stats["misses"] += 1
        self._update_hit_rate(cache_name)

        event = ObservableEvent(
            event_type=ObservableEventType.CACHE_MISS,
            source=f"Cache:{cache_name}",
            data={
                "cache_name": cache_name,
                "key": key,
            },
        )
        await self.notify(event)

    async def record_cache_set(
        self, cache_name: str, key: str, ttl: Optional[int] = None
    ) -> None:
        """记录缓存设置"""
        self._cache_stats["sets"] += 1

    async def record_cache_delete(self, cache_name: str, key: str) -> None:
        """记录缓存删除"""
        self._cache_stats["deletes"] += 1

    def _update_hit_rate(self, cache_name: str) -> None:
        """更新缓存命中率"""
        hits = self._cache_stats["hits"]
        misses = self._cache_stats["misses"]
        total = hits + misses

        if total > 0:
            self._hit_rates[cache_name] = hits / total

    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (
            self._cache_stats["hits"] / total_requests if total_requests > 0 else 0
        )

        return {
            "stats": dict(self._cache_stats),
            "overall_hit_rate": hit_rate,
            "cache_hit_rates": dict(self._hit_rates),
            "total_requests": total_requests,
        }
