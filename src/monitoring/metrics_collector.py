"""
监控指标收集器 - 向后兼容性包装器
Monitoring Metrics Collector - Backward Compatibility Wrapper

⚠️  警告：此文件已被重构为模块化结构
⚠️  Warning: This file has been refactored into a modular structure

新的实现位于 src/monitoring/metrics/ 目录下：
- types.py - 指标类型和单位定义
- aggregator.py - 指标聚合器
- exporters.py - 各种导出器实现
- base.py - 基础收集器抽象类
- collectors.py - 具体收集器实现
- global_collector.py - 全局收集器管理

此文件保留用于向后兼容性，建议新代码直接导入新的模块。
"""

import logging
from typing import Any, Dict, List, Optional

# 从新的模块化结构导入所有功能
from .metrics import (
    # Types
    MetricType,
    MetricUnit,
    # Aggregator
    MetricsAggregator,
    # Exporters
    StatsdExporter,
    # Collectors
    MetricsCollector as OriginalMetricsCollector,
    SystemMetricsCollector,
    DatabaseMetricsCollector,
    ApplicationMetricsCollector,
    # Global functions
    get_metrics_collector,
    start_metrics_collection,
    stop_metrics_collection,
    get_async_session,
)

# 从配置中导入常量
from src.core.config import get_settings

_settings = get_settings()

# 导出常量
ENABLE_METRICS = bool(_settings.metrics_enabled)
DEFAULT_TABLES: List[str] = (
    list(_settings.metrics_tables)
    if getattr(_settings, "metrics_tables", None)
    else [
        "matches",
        "teams",
        "leagues",
        "odds",
        "features",
        "raw_match_data",
        "raw_odds_data",
        "raw_scores_data",
        "data_collection_logs",
    ]
)

logger = logging.getLogger(__name__)

# =============================================================================
# 向后兼容性别名
# =============================================================================

# 为了保持向后兼容，使用原始的类名
MetricsCollector = OriginalMetricsCollector

# PrometheusExporter 的别名
from .metrics_exporter import MetricsExporter
PrometheusExporter = MetricsExporter

# 保持原有的 __all__ 导出
__all__ = [
    # Constants
    "ENABLE_METRICS",
    "DEFAULT_TABLES",
    # Classes
    "MetricsCollector",
    "SystemMetricsCollector",
    "DatabaseMetricsCollector",
    "ApplicationMetricsCollector",
    "StatsdExporter",
    "MetricsAggregator",
    "MetricType",
    "MetricUnit",
    "PrometheusExporter",
    # Functions
    "get_metrics_collector",
    "start_metrics_collection",
    "stop_metrics_collection",
    "get_async_session",
]

# =============================================================================
# 模块信息
# =============================================================================

def get_module_info() -> Dict[str, Any]:
    """获取模块信息"""
    return {
        "module": "metrics_collector",
        "status": "refactored",
        "message": "This module has been refactored into a modular structure",
        "new_location": "src.monitoring.metrics",
        "components": [
            "types - Metric type and unit definitions",
            "aggregator - Metrics aggregation functionality",
            "exporters - Various exporter implementations (StatsD, Prometheus, CloudWatch)",
            "base - Base collector abstract class",
            "collectors - Specific collector implementations",
            "global_collector - Global collector management",
        ],
        "migration_guide": {
            "old_import": "from src.monitoring.metrics_collector import XXX",
            "new_import": "from src.monitoring.metrics import XXX",
        },
        "enhanced_features": [
            "More modular structure for better maintainability",
            "Separate exporter implementations for different monitoring systems",
            "Enhanced metrics aggregation with percentiles",
            "Flexible collector management system",
            "Better separation of concerns",
            "Support for multiple metric types and units",
        ],
    }


# 记录模块加载信息
logger.info(
    "Loading metrics_collector module (deprecated) - "
    "consider importing from src.monitoring.metrics instead"
)


if __name__ == "__main__":
    """
    独立运行指标收集器
    """

    import asyncio

    async def main():
        collector = MetricsCollector(collection_interval=10)  # 10秒间隔用于测试

        try:
            await collector.start()
            # 保持运行直到被中断
            while collector.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到中断信号")
        finally:
            await collector.stop()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())