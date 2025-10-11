"""
工具函数 / Utility Functions

提供指标导出器使用的工具函数。
"""

import logging
from datetime import datetime

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
    CollectorRegistry,
    Counter,
    Gauge,
)

logger = logging.getLogger(__name__)


def get_or_create_counter(
    name: str,
    description: str,
    labels: list,
    registry: CollectorRegistry,
) -> Counter:
    """
    获取或创建 Counter 指标，避免重复注册

    Args:
        name: 指标名称
        description: 指标描述
        labels: 标签列表
        registry: 注册表

    Returns:
        Counter: Counter 实例
    """
    try:
        return Counter(name, description, labels, registry=registry)
    except ValueError as e:
        logger.warning(f"指标 {name} 已存在: {e}")
        # 尝试从注册表获取现有指标
        for collector in registry._collector_to_names:
            if hasattr(collector, "_name") and collector._name == name:
                return collector  # type: ignore
        # 如果找不到，返回一个 mock counter
        return _create_mock_counter()  # type: ignore


def get_or_create_gauge(
    name: str,
    description: str,
    labels: list,
    registry: CollectorRegistry,
) -> Gauge:
    """
    获取或创建 Gauge 指标，避免重复注册

    Args:
        name: 指标名称
        description: 指标描述
        labels: 标签列表
        registry: 注册表

    Returns:
        Gauge: Gauge 实例
    """
    try:
        return Gauge(name, description, labels, registry=registry)
    except ValueError as e:
        logger.warning(f"指标 {name} 已存在: {e}")
        # 尝试从注册表获取现有指标
        for collector in registry._collector_to_names:
            if hasattr(collector, "_name") and collector._name == name:
                return collector  # type: ignore
        # 如果找不到，返回一个 mock gauge
        return _create_mock_gauge()  # type: ignore


def _create_mock_counter():
    """创建 Mock Counter 用于测试"""
    from unittest.mock import Mock

    mock = Mock()
    mock.inc = Mock()
    mock.labels = Mock(return_value=mock)
    return mock


def _create_mock_gauge():
    """创建 Mock Gauge 用于测试"""
    from unittest.mock import Mock

    mock = Mock()
    mock.set = Mock()
    mock.labels = Mock(return_value=mock)
    return mock


def validate_table_name(table_name: str) -> bool:
    """
    验证表名是否安全

    Args:
        table_name: 表名

    Returns:
        bool: 是否安全
    """
    # 只允许字母、数字和下划线
    if not table_name:
        return False
    return table_name.replace("_", "").isalnum()


def format_metrics_for_prometheus(registry: CollectorRegistry) -> tuple[str, str]:
    """
    格式化指标为 Prometheus 格式

    Args:
        registry: 注册表

    Returns:
        tuple[str, str]: (content_type, metrics_data)
    """
    try:
        metrics_data = generate_latest(registry)
        return CONTENT_TYPE_LATEST, metrics_data.decode("utf-8")
    except (ValueError, TypeError, OSError, IOError) as e:
        logger.error(f"生成 Prometheus 格式指标失败: {e}")
        return CONTENT_TYPE_LATEST, "# Error generating metrics\n"


def calculate_delay_seconds(scheduled_time: datetime, actual_time: datetime) -> float:
    """
    计算延迟时间（秒）

    Args:
        scheduled_time: 计划时间
        actual_time: 实际时间

    Returns:
        float: 延迟秒数
    """
    if actual_time >= scheduled_time:
        return (actual_time - scheduled_time).total_seconds()
    else:
        # 如果实际时间早于计划时间，延迟为负数
        return -(scheduled_time - actual_time).total_seconds()


def safe_cast_to_float(value, default: float = 0.0) -> float:
    """
    安全地将值转换为 float

    Args:
        value: 要转换的值
        default: 默认值

    Returns:
        float: 转换后的值
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def filter_metrics_by_prefix(metrics_data: str, prefix: str) -> str:
    """
    根据前缀过滤指标

    Args:
        metrics_data: 指标数据
        prefix: 前缀

    Returns:
        str: 过滤后的指标数据
    """
    lines = metrics_data.split("\n")
    filtered_lines = []

    for line in lines:
        # 保留以 prefix 开头或以 # 开头的行（注释和帮助信息）
        if line.startswith(prefix) or line.startswith("#") or not line:
            filtered_lines.append(line)

    return "\n".join(filtered_lines)


def get_metric_summary(registry: CollectorRegistry) -> dict:
    """
    获取指标摘要信息

    Args:
        registry: 注册表

    Returns:
        dict: 指标摘要
    """
    summary = {
        "total_metrics": 0,
        "metrics_by_type": {
            "counter": 0,
            "gauge": 0,
            "histogram": 0,
            "summary": 0,
            "info": 0,
        },
        "metric_names": [],
    }

    try:
        for collector in registry._collector_to_names:
            metric_type = type(collector).__name__.lower()
            if "counter" in metric_type:
                summary["metrics_by_type"]["counter"] += 1  # type: ignore
            elif "gauge" in metric_type:
                summary["metrics_by_type"]["gauge"] += 1  # type: ignore
            elif "histogram" in metric_type:
                summary["metrics_by_type"]["histogram"] += 1  # type: ignore
            elif "summary" in metric_type:
                summary["metrics_by_type"]["summary"] += 1  # type: ignore
            elif "info" in metric_type:
                summary["metrics_by_type"]["info"] += 1  # type: ignore

            if hasattr(collector, "_name"):
                summary["metric_names"].append(collector._name)  # type: ignore

            summary["total_metrics"] += 1  # type: ignore

    except (ValueError, TypeError, OSError, IOError) as e:
        logger.error(f"获取指标摘要失败: {e}")

    return summary
