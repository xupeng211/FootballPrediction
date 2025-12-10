"""性能监控工具
Performance Monitoring Tools.

提供系统性能监控和分析工具。
Provides system performance monitoring and analysis tools.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """性能指标数据类."""

    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    active_connections: int
    response_time_avg: float
    requests_per_second: float
    error_rate: float


class SystemMonitor:
    """系统资源监控器."""

    def __init__(self):
        self.metrics_history: list[PerformanceMetrics] = []
        self.max_history = 1000  # 保留最近1000个数据点

    def get_current_metrics(self) -> PerformanceMetrics:
        """获取当前系统指标."""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 内存使用情况
            memory = psutil.virtual_memory()
            memory_percent = getattr(memory, "percent", 0.0)
            # 处理Mock对象的除法问题
            memory_used = getattr(memory, "used", 0)
            memory_available = getattr(memory, "available", 0)
            # 确保是数值类型
            try:
                memory_used_mb = float(memory_used) / (1024 * 1024)
            except (TypeError, ValueError):
                memory_used_mb = 0.0
            try:
                memory_available_mb = float(memory_available) / (1024 * 1024)
            except (TypeError, ValueError):
                memory_available_mb = 0.0

            # 磁盘使用情况
            disk = psutil.disk_usage("/")
            disk_usage_percent = getattr(disk, "percent", 0.0)

            # 网络连接数
            network = psutil.net_connections()
            active_connections = len(
                [conn for conn in network if conn.status == "ESTABLISHED"]
            )

            # 获取应用性能指标（如果有）
            response_time_avg = self._get_avg_response_time()
            requests_per_second = self._get_requests_per_second()
            error_rate = self._get_error_rate()

            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                active_connections=active_connections,
                response_time_avg=response_time_avg,
                requests_per_second=requests_per_second,
                error_rate=error_rate,
            )

        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_usage_percent=0.0,
                active_connections=0,
                response_time_avg=0.0,
                requests_per_second=0.0,
                error_rate=0.0,
            )

    def _get_avg_response_time(self) -> float:
        """获取平均响应时间."""
        # 这里应该从性能监控中间件获取数据
        # 暂时返回模拟数据
        return 0.5

    def _get_requests_per_second(self) -> float:
        """获取每秒请求数."""
        # 这里应该从性能监控中间件获取数据
        # 暂时返回模拟数据
        return 10.0

    def _get_error_rate(self) -> float:
        """获取错误率."""
        # 这里应该从性能监控中间件获取数据
        # 暂时返回模拟数据
        return 0.01

    def record_metrics(self, metrics: PerformanceMetrics):
        """记录性能指标."""
        self.metrics_history.append(metrics)

        # 限制历史记录数量
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history :]

    def get_metrics_summary(self, minutes: int = 5) -> dict[str, Any]:
        """获取指标摘要."""
        if not self.metrics_history:
            return {}

        # 获取指定时间范围内的数据
        cutoff_time = time.time() - (minutes * 60)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]

        if not recent_metrics:
            return {}

        # 计算统计信息
        cpu_values = [m.cpu_percent for m in recent_metrics]
        memory_values = [m.memory_percent for m in recent_metrics]
        response_times = [m.response_time_avg for m in recent_metrics]
        error_rates = [m.error_rate for m in recent_metrics]

        return {
            "time_range_minutes": minutes,
            "sample_count": len(recent_metrics),
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "min": min(cpu_values),
                "max": max(cpu_values),
                "current": recent_metrics[-1].cpu_percent,
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "min": min(memory_values),
                "max": max(memory_values),
                "current": recent_metrics[-1].memory_percent,
            },
            "performance": {
                "avg_response_time": sum(response_times) / len(response_times),
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "current_response_time": recent_metrics[-1].response_time_avg,
                "avg_requests_per_second": sum(
                    m.requests_per_second for m in recent_metrics
                )
                / len(recent_metrics),
                "avg_error_rate": sum(error_rates) / len(error_rates),
                "current_error_rate": recent_metrics[-1].error_rate,
            },
            "resources": {
                "avg_memory_used_mb": sum(m.memory_used_mb for m in recent_metrics)
                / len(recent_metrics),
                "current_memory_used_mb": recent_metrics[-1].memory_used_mb,
                "avg_connections": sum(m.active_connections for m in recent_metrics)
                / len(recent_metrics),
                "current_connections": recent_metrics[-1].active_connections,
            },
        }

    def check_performance_alerts(self) -> list[dict[str, Any]]:
        """检查性能警报."""
        alerts = []
        current_metrics = self.get_current_metrics()

        # CPU使用率警报
        if current_metrics.cpu_percent > 80:
            alerts.append(
                {
                    "typing.Type": "cpu_high",
                    "severity": (
                        "warning" if current_metrics.cpu_percent < 90 else "critical"
                    ),
                    "message": f"CPU使用率过高: {current_metrics.cpu_percent:.1f}%",
                    "value": current_metrics.cpu_percent,
                    "threshold": 80,
                }
            )

        # 内存使用率警报
        if current_metrics.memory_percent > 85:
            alerts.append(
                {
                    "typing.Type": "memory_high",
                    "severity": (
                        "warning" if current_metrics.memory_percent < 95 else "critical"
                    ),
                    "message": f"内存使用率过高: {current_metrics.memory_percent:.1f}%",
                    "value": current_metrics.memory_percent,
                    "threshold": 85,
                }
            )

        # 磁盘使用率警报
        if current_metrics.disk_usage_percent > 90:
            alerts.append(
                {
                    "typing.Type": "disk_high",
                    "severity": "warning",
                    "message": f"磁盘使用率过高: {current_metrics.disk_usage_percent:.1f}%",
                    "value": current_metrics.disk_usage_percent,
                    "threshold": 90,
                }
            )

        # 响应时间警报
        if current_metrics.response_time_avg > 2.0:
            alerts.append(
                {
                    "typing.Type": "response_time_high",
                    "severity": (
                        "warning"
                        if current_metrics.response_time_avg < 5.0
                        else "critical"
                    ),
                    "message": f"平均响应时间过长: {current_metrics.response_time_avg:.3f}s",
                    "value": current_metrics.response_time_avg,
                    "threshold": 2.0,
                }
            )

        # 错误率警报
        if current_metrics.error_rate > 0.05:  # 5%
            alerts.append(
                {
                    "typing.Type": "error_rate_high",
                    "severity": (
                        "warning" if current_metrics.error_rate < 0.1 else "critical"
                    ),
                    "message": f"错误率过高: {current_metrics.error_rate:.1%}",
                    "value": current_metrics.error_rate,
                    "threshold": 0.05,
                }
            )

        return alerts


class PerformanceAnalyzer:
    """性能分析器."""

    def __init__(self):
        self.metrics_history = []
        self.analysis_results = {}

    def analyze_trends(self, hours: int = 1) -> dict[str, Any]:
        """分析性能趋势."""
        cutoff_time = time.time() - (hours * 3600)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]

        if len(recent_metrics) < 2:
            return {"error": "Insufficient data for trend analysis"}

        # 分析CPU趋势
        cpu_values = [m.cpu_percent for m in recent_metrics]
        cpu_trend = self._calculate_trend(cpu_values)

        # 分析内存趋势
        memory_values = [m.memory_percent for m in recent_metrics]
        memory_trend = self._calculate_trend(memory_values)

        # 分析响应时间趋势
        response_times = [m.response_time_avg for m in recent_metrics]
        response_trend = self._calculate_trend(response_times)

        return {
            "time_range_hours": hours,
            "data_points": len(recent_metrics),
            "trends": {
                "cpu": {
                    "trend": cpu_trend,
                    "change": (
                        cpu_values[-1] - cpu_values[0] if len(cpu_values) > 1 else 0
                    ),
                },
                "memory": {
                    "trend": memory_trend,
                    "change": (
                        memory_values[-1] - memory_values[0]
                        if len(memory_values) > 1
                        else 0
                    ),
                },
                "response_time": {
                    "trend": response_trend,
                    "change": (
                        response_times[-1] - response_times[0]
                        if len(response_times) > 1
                        else 0
                    ),
                },
            },
        }

    def _calculate_trend(self, values: list[float]) -> str:
        """计算趋势."""
        if len(values) < 2:
            return "insufficient_data"

        # 简单的线性趋势分析
        n = len(values)
        x = list(range(n))

        # 计算线性回归斜率
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xx = sum(xi * xi for xi in x)
        sum_xy = sum(xi * yi for xi, yi in zip(x, values, strict=False))

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)

        if slope > 0.1:
            return "increasing"
        elif slope < -0.1:
            return "decreasing"
        else:
            return "stable"

    def get_performance_recommendations(
        self, metrics_summary: dict[str, Any]
    ) -> list[str]:
        """获取性能优化建议."""
        recommendations = []

        # CPU使用率建议
        cpu_avg = metrics_summary.get("cpu", {}).get("avg", 0)
        if cpu_avg > 70:
            recommendations.append("考虑增加CPU资源或优化CPU密集型任务")

        # 内存使用率建议
        memory_avg = metrics_summary.get("memory", {}).get("avg", 0)
        if memory_avg > 75:
            recommendations.append("考虑增加内存资源或优化内存使用")

        # 响应时间建议
        avg_response = metrics_summary.get("performance", {}).get(
            "avg_response_time", 0
        )
        if avg_response > 1.0:
            recommendations.append("优化数据库查询和API响应时间")
        if avg_response > 2.0:
            recommendations.append("实施缓存策略和异步处理")

        # 错误率建议
        error_rate = metrics_summary.get("performance", {}).get("avg_error_rate", 0)
        if error_rate > 0.02:  # 2%
            recommendations.append("检查错误日志并修复导致高错误率的问题")

        # 连接数建议
        avg_connections = metrics_summary.get("resources", {}).get("avg_connections", 0)
        if avg_connections > 100:
            recommendations.append("优化数据库连接池配置")

        return recommendations


# 全局系统监控器实例
_system_monitor: SystemMonitor | None = None


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


def get_performance_analyzer() -> PerformanceAnalyzer:
    """获取性能分析器实例."""
    return PerformanceAnalyzer()
